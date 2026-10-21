"""Regresion de tools/usb_eject._eject_drive: nunca expulsar una unidad en uso.

Expulsar una USB con archivos abiertos corrompe datos. La secuencia segura es
abrir el volumen -> BLOQUEARLO -> desmontar -> permitir remocion -> expulsar, y
si el bloqueo falla (hay archivos en uso) NO se debe llegar a desmontar ni
expulsar. Tambien cubre que el handle SIEMPRE se cierre y que "expulsada" solo
se declare si la unidad de verdad desaparecio.

Se parchea ctypes.windll con un kernel32 falso: NO toca ninguna unidad real
(expulsar una de verdad desmontaria la USB del usuario). Solo stdlib:

    python3 tests/test_usb_eject.py
"""

import ctypes
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

from tools import usb_eject as ue  # noqa: E402


fallos = 0


def check(nombre, cond, extra=""):
    global fallos
    fallos += not cond
    marca = "OK " if cond else "FAIL"
    detalle = f" -> {extra}" if not cond and extra else ""
    print(f"[{marca}] {nombre}{detalle}")


FSCTL_LOCK_VOLUME = 0x00090018
FSCTL_DISMOUNT_VOLUME = 0x00090020
IOCTL_STORAGE_MEDIA_REMOVAL = 0x002D4804
IOCTL_STORAGE_EJECT_MEDIA = 0x002D4808
NOMBRES = {FSCTL_LOCK_VOLUME: "LOCK", FSCTL_DISMOUNT_VOLUME: "DISMOUNT",
           IOCTL_STORAGE_MEDIA_REMOVAL: "REMOVAL", IOCTL_STORAGE_EJECT_MEDIA: "EJECT"}


class _CreateFileW:
    """Imita kernel32.CreateFileW (se le asigna restype desde el codigo)."""
    restype = None

    def __init__(self, handle):
        self.handle = handle
        self.rutas = []

    def __call__(self, ruta, *a):
        self.rutas.append(ruta)
        return self.handle


class _Kernel32:
    def __init__(self, handle=1234, lock_ok=True, drive_types=(2, 1), media=(True,)):
        self.CreateFileW = _CreateFileW(handle)
        self.llamadas = []          # codigos IOCTL en orden
        self.cerrados = []          # handles cerrados
        self._lock_ok = lock_ok
        self._tipos = list(drive_types)
        self._media = list(media)   # hay medio listo en cada consulta (se repite el ultimo)
        self.consultas = 0
        self.consultas_media = 0
        self.error_modes = []

    def DeviceIoControl(self, handle, codigo, *a):
        self.llamadas.append(NOMBRES.get(codigo, hex(codigo)))
        if codigo == FSCTL_LOCK_VOLUME:
            return 1 if self._lock_ok else 0
        return 1

    def CloseHandle(self, handle):
        self.cerrados.append(handle)

    def GetDriveTypeW(self, ruta):
        self.consultas += 1
        i = min(self.consultas - 1, len(self._tipos) - 1)
        return self._tipos[i]

    def SetErrorMode(self, modo):
        self.error_modes.append(modo)
        return 0

    def GetDiskFreeSpaceExW(self, ruta, *a):
        self.consultas_media += 1
        i = min(self.consultas_media - 1, len(self._media) - 1)
        return 1 if self._media[i] else 0


class _Windll:
    def __init__(self, k):
        self.kernel32 = k


windll_original = getattr(ctypes, "windll", None)
sleep_original = ue.time.sleep
ue.time.sleep = lambda s: None   # los reintentos y verificaciones no esperan de verdad


def eject(kernel, unidad="G:"):
    ctypes.windll = _Windll(kernel)
    try:
        return ue._eject_drive(unidad)
    finally:
        if windll_original is None:
            del ctypes.windll
        else:
            ctypes.windll = windll_original


try:
    # --- camino feliz: secuencia canonica y la unidad desaparece -----------
    k = _Kernel32(drive_types=(2, 2, 1))   # sigue 2 intentos y luego ya no esta
    r = eject(k, "G:\\")
    check("camino feliz -> 'ejected'", r == {"status": "ejected", "drive": "G:"}, r)
    check("secuencia segura: LOCK, DISMOUNT, REMOVAL, EJECT en ese orden",
          k.llamadas == ["LOCK", "DISMOUNT", "REMOVAL", "EJECT"], k.llamadas)
    check("abre el volumen como \\\\.\\G: (la ruta de volumen, no la raiz)",
          k.CreateFileW.rutas == ["\\\\.\\G:"], k.CreateFileW.rutas)
    check("cierra el handle", k.cerrados == [1234], k.cerrados)
    check("la letra se normaliza ('G:\\\\' -> 'G:')", r["drive"] == "G:")

    # --- USB real expulsada: la letra SIGUE ahi, pero SIN medio ---------------
    # (Get-Disk: "No Media"). Antes se miraba solo el tipo de unidad, asi que
    # esto salia como "still_present" y la app decia "no la retires todavia"
    # despues de haberla expulsado bien. Medido con una memoria USB real.
    k = _Kernel32(drive_types=(2,), media=(True, True, False))
    r = eject(k)
    check("letra removible que queda SIN medio -> 'ejected' (no 'still_present')",
          r == {"status": "ejected", "drive": "G:"}, r)
    check("la consulta de medio evita el dialogo 'inserte un disco' (SEM_FAILCRITICALERRORS)",
          k.error_modes and k.error_modes[0] == 0x0001 and k.error_modes[-1] == 0, k.error_modes)

    # --- unidad en uso: NO desmonta ni expulsa ------------------------------
    k = _Kernel32(lock_ok=False)
    r = eject(k)
    check("bloqueo imposible -> 'in_use'", r == {"status": "in_use", "drive": "G:"}, r)
    check("en uso: reintenta el LOCK (10 veces) y NUNCA desmonta ni expulsa",
          k.llamadas == ["LOCK"] * 10, k.llamadas)
    check("en uso: aun asi cierra el handle", k.cerrados == [1234], k.cerrados)

    # --- sin acceso: handle invalido ----------------------------------------
    for etiqueta, handle in (("handle invalido (-1)", ctypes.c_void_p(-1).value), ("handle nulo", 0)):
        k = _Kernel32(handle=handle)
        r = eject(k)
        check(f"{etiqueta} -> 'access_denied' sin ejecutar ningun IOCTL",
              r["status"] == "access_denied" and k.llamadas == [] and k.cerrados == [], (r, k.llamadas))

    # --- se mando expulsar pero la unidad sigue ahi --------------------------
    k = _Kernel32(drive_types=(2,), media=(True,))   # removible y CON medio = sigue montada
    r = eject(k)
    check("la unidad no desaparece -> 'still_present' (NO dice 'expulsada')",
          r == {"status": "still_present", "drive": "G:"}, r)
    check("verifica varias veces antes de rendirse", k.consultas == 10, k.consultas)

    # --- no se puede verificar (plataforma sin GetDriveType) -----------------
    class _SinVerificar(_Kernel32):
        def GetDriveTypeW(self, ruta):
            raise AttributeError("sin GetDriveTypeW")
    k = _SinVerificar()
    r = eject(k)
    check("sin poder verificar -> 'unverified' (honesto, no 'ejected')",
          r == {"status": "unverified", "drive": "G:"}, r)

    # --- CreateFileW lanza OSError ------------------------------------------
    class _CreateRoto(_Kernel32):
        def __init__(self):
            super().__init__()
            def boom(*a):
                raise OSError("fallo del sistema")
            boom.restype = None
            self.CreateFileW = boom
    r = eject(_CreateRoto())
    check("OSError al abrir -> 'open_error' con el detalle",
          r["status"] == "open_error" and "fallo del sistema" in r["error"], r)

    # --- sin Windows ---------------------------------------------------------
    class _SinKernel:
        @property
        def kernel32(self):
            raise AttributeError("no es Windows")
    ctypes.windll = _SinKernel()
    try:
        r = ue._eject_drive("G:")
    finally:
        ctypes.windll = windll_original
    check("sin kernel32 -> 'no_windows'", r == {"status": "no_windows", "drive": "G:"}, r)

    # --- _drive_still_present --------------------------------------------------
    ctypes.windll = _Windll(_Kernel32(drive_types=(2,), media=(True,)))
    try:
        check("_drive_still_present: removible con medio -> True", ue._drive_still_present("G:") is True)
        ctypes.windll = _Windll(_Kernel32(drive_types=(2,), media=(False,)))
        check("_drive_still_present: removible SIN medio (expulsada) -> False",
              ue._drive_still_present("G:") is False)
        ctypes.windll = _Windll(_Kernel32(drive_types=(1,)))
        check("_drive_still_present: ya no existe -> False", ue._drive_still_present("G:") is False)
        ctypes.windll = _Windll(_Kernel32(drive_types=(3,)))
        check("_drive_still_present: ahora es disco fijo -> False (no es la USB)",
              ue._drive_still_present("G:") is False)
    finally:
        ctypes.windll = windll_original
finally:
    ue.time.sleep = sleep_original
    if windll_original is not None:
        ctypes.windll = windll_original


print()
if fallos:
    print(f"RESULTADO: {fallos} FALLO(S)")
    sys.exit(1)
print("RESULTADO: TODO VERDE")
