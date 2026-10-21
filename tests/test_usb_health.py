"""Regresion de tools/usb_health: diagnostico de velocidad y autenticidad.

Bug que cubre (medido en una USB real que escribe a ~20 MB/s): la prueba de
velocidad leia el archivo recien escrito con una lectura normal, que sale de la
CACHE de Windows y no de la memoria, asi que la "velocidad de lectura" daba
~1000 MB/s y la pantalla la mostraba como real. Ahora se lee con
FILE_FLAG_NO_BUFFERING (en la USB real: ~35 MB/s) y, si el sistema no lo
permite, se avisa con `read_cached`.

Tambien cubre _select_offsets, el parser de chkdsk (sano vs con errores, en
ingles y espanol) y que las pruebas dejen limpia la unidad (sin temporales).

Corre sobre una carpeta temporal que hace de "unidad". Solo stdlib:

    python3 tests/test_usb_health.py
"""

import errno
import os
import sys
import tempfile

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

from tools import usb_health as uh  # noqa: E402


fallos = 0


def check(nombre, cond, extra=""):
    global fallos
    fallos += not cond
    marca = "OK " if cond else "FAIL"
    detalle = f" -> {extra}" if not cond and extra else ""
    print(f"[{marca}] {nombre}{detalle}")


TMP_SPEED = ".salva_speedtest.tmp"
TMP_FAKE = ".salva_faketest.tmp"

with tempfile.TemporaryDirectory(prefix="salvagodinez_test_") as tmp:

    # --- _read_uncached --------------------------------------------------
    if os.name == "nt":
        datos = os.urandom(3 * 1024 * 1024 + 123)   # NO multiplo del sector
        ruta = os.path.join(tmp, "datos.bin")
        with open(ruta, "wb") as f:
            f.write(datos)
        r = uh._read_uncached(ruta)
        check("_read_uncached: lee TODOS los bytes aunque el tamano no sea multiplo del sector",
              r is not None and r[0] == len(datos), r)
        check("_read_uncached: mide un tiempo positivo", r is not None and r[1] > 0, r)
        check("_read_uncached: archivo inexistente -> None (para caer a lectura normal)",
              uh._read_uncached(os.path.join(tmp, "no_existe.bin")) is None)
        vacio = os.path.join(tmp, "vacio.bin")
        open(vacio, "wb").close()
        check("_read_uncached: archivo vacio -> (0 bytes)", uh._read_uncached(vacio)[0] == 0)
    else:
        print("[SKIP] _read_uncached -> requiere Windows")

    # --- _speed_test -------------------------------------------------------
    r = uh._speed_test(tmp, 2)
    check("speed_test: mide escritura y lectura", "error" not in r and r["write_mbps"] > 0 and r["read_mbps"] > 0, r)
    check("speed_test: informa si la lectura pudo venir de la cache ('read_cached')",
          isinstance(r.get("read_cached"), bool), r)
    if os.name == "nt":
        check("speed_test (Windows): la lectura se hizo SIN cache", r.get("read_cached") is False, r)
    check("speed_test: no deja el archivo temporal", not os.path.exists(os.path.join(tmp, TMP_SPEED)))

    # Fallback: si no se puede leer sin cache, usa la lectura normal y lo avisa.
    original = uh._read_uncached
    uh._read_uncached = lambda *a, **k: None
    try:
        r = uh._speed_test(tmp, 1)
        check("speed_test: sin lectura sin-cache -> usa la normal y marca read_cached=True",
              "error" not in r and r["read_mbps"] > 0 and r["read_cached"] is True, r)
        # Una lectura sin cache que devuelva MENOS bytes de los escritos no se acepta.
        uh._read_uncached = lambda *a, **k: (10, 0.001)
        r = uh._speed_test(tmp, 1)
        check("speed_test: lectura sin cache incompleta -> se descarta y cae a la normal",
              r.get("read_cached") is True, r)
    finally:
        uh._read_uncached = original

    r = uh._speed_test(os.path.join(tmp, "carpeta_que_no_existe"), 1)
    check("speed_test: unidad inexistente -> error explicado, sin excepcion",
          r.get("error") and r["write_mbps"] == 0 and r["read_mbps"] == 0, r)

    # --- _select_offsets -----------------------------------------------------
    ch = 256 * 1024
    check("offsets: prueba mas chica que un chunk -> solo el 0", uh._select_offsets(ch, ch) == [0])
    check("offsets: 4 puntos cuando caben", len(uh._select_offsets(100 * ch, ch)) == 4)
    off = uh._select_offsets(100 * ch, ch)
    check("offsets: empiezan en 0, terminan en test_size-chunk y nunca se solapan",
          off[0] == 0 and off[-1] == 99 * ch and all(b - a >= ch for a, b in zip(off, off[1:])), off)
    off = uh._select_offsets(int(2.5 * ch), ch)
    check("offsets: poco espacio -> menos puntos pero sin solaparse",
          all(b - a >= ch for a, b in zip(off, off[1:])) and len(off) < 4, off)

    # --- _detect_fake_usb -------------------------------------------------------
    r = uh._detect_fake_usb(tmp, 50 * 1024 * 1024)
    check("detect_fake_usb: unidad sana -> authentic=True", r.get("authentic") is True, r)
    check("detect_fake_usb: no deja el archivo temporal", not os.path.exists(os.path.join(tmp, TMP_FAKE)))
    r = uh._detect_fake_usb(tmp, 0)
    check("detect_fake_usb: sin tamano reportado -> prueba minima, sin excepcion",
          r.get("authentic") in (True, None), r)

    # unidad "que falsea": lo escrito no coincide al leerlo.
    open_original = open
    def open_mentiroso(path, mode="r", *a, **k):
        f = open_original(path, mode, *a, **k)
        if "rb" in mode and str(path).endswith(TMP_FAKE):
            real_read = f.read
            f.read = lambda n=-1: b"\x00" * len(real_read(n))
        return f
    import builtins
    builtins.open = open_mentiroso
    try:
        r = uh._detect_fake_usb(tmp, 50 * 1024 * 1024)
    finally:
        builtins.open = open_original
    check("detect_fake_usb: datos que no coinciden -> authentic=False", r.get("authentic") is False, r)
    check("detect_fake_usb: aun asi limpia el temporal", not os.path.exists(os.path.join(tmp, TMP_FAKE)))

    # Disco lleno: NO se acusa de "USB falsa" (autentic=None), esto era enganoso.
    du_original = uh.shutil.disk_usage
    class _Uso:
        free = 100 * 1024   # menos de un chunk
    uh.shutil.disk_usage = lambda p: _Uso()
    try:
        r = uh._detect_fake_usb(tmp, 50 * 1024 * 1024)
    finally:
        uh.shutil.disk_usage = du_original
    check("detect_fake_usb: casi sin espacio libre -> authentic=None, no 'falsa'", r.get("authentic") is None, r)

    def open_enospc(path, mode="r", *a, **k):
        if "w" in mode and str(path).endswith(TMP_FAKE):
            raise OSError(errno.ENOSPC, "No space left on device")
        return open_original(path, mode, *a, **k)
    builtins.open = open_enospc
    try:
        r = uh._detect_fake_usb(tmp, 50 * 1024 * 1024)
    finally:
        builtins.open = open_original
    check("detect_fake_usb: ENOSPC al escribir -> authentic=None (no 'falsa')", r.get("authentic") is None, r)

# --- parser de chkdsk --------------------------------------------------------
sano_en = ("The type of the file system is NTFS.\nWindows has scanned the file system and found no problems.\n"
           "No further action is required.\n 0 KB in bad sectors.\n")
sano_es = ("El tipo de sistema de archivos es exFAT.\nWindows analizó el sistema de archivos y no encontró problemas.\n"
           "No se requiere ninguna otra acción.\n          0 KB en sectores defectuosos.\n")
roto_es = "Windows encontró errores en el sistema de archivos.\n   16 KB en sectores defectuosos.\n"
roto_en = "Errors found.  CHKDSK cannot continue in read-only mode.\n"
check("chkdsk: disco sano en ingles -> sin errores", uh._chkdsk_output_has_errors(sano_en) is False)
check("chkdsk: disco sano en espanol ('no encontro problemas') -> sin errores", uh._chkdsk_output_has_errors(sano_es) is False)
check("chkdsk: sectores danados > 0 -> con errores", uh._chkdsk_output_has_errors("   16 KB in bad sectors.\n") is True)
check("chkdsk: espanol con errores -> con errores", uh._chkdsk_output_has_errors(roto_es) is True)
check("chkdsk: ingles con errores -> con errores", uh._chkdsk_output_has_errors(roto_en) is True)
check("chkdsk: salida vacia -> sin errores", uh._chkdsk_output_has_errors("") is False)


print()
if fallos:
    print(f"RESULTADO: {fallos} FALLO(S)")
    sys.exit(1)
print("RESULTADO: TODO VERDE")
