"""Regresion de tools/file_unlocker: detectar quien bloquea un archivo y cerrarlo.

Es la herramienta que MATA procesos, asi que dos invariantes importan mas que
el resto:
  - detectar bien al proceso que bloquea (y no inventar uno), usando la API real
    Restart Manager de Windows con un proceso hijo que sostiene un archivo;
  - _kill_process solo toca el PID que se le pide y reporta si de verdad cerro.

Ademas cubre el fallback de PowerShell: su lista vacia NO significa "libre"
(certero=False), porque solo ve EXE/DLL cargados, no archivos de datos.

La parte de Restart Manager y taskkill necesita Windows y se omite en otros SO.
Solo stdlib:

    python3 tests/test_file_unlocker.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

from tools import file_unlocker as fu  # noqa: E402


fallos = 0


def check(nombre, cond, extra=""):
    global fallos
    fallos += not cond
    marca = "OK " if cond else "FAIL"
    detalle = f" -> {extra}" if not cond and extra else ""
    print(f"[{marca}] {nombre}{detalle}")


NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# En un entorno virtual de Windows, sys.executable es un lanzador que arranca al
# interprete real como proceso HIJO: el PID del Popen no seria el que tiene el
# archivo abierto (y al cerrarlo se quedaria huerfano el interprete real). Se
# usa el interprete base, sin lanzador, para que el PID sea el verdadero.
PYTHON = getattr(sys, "_base_executable", sys.executable)


def vivo(pid):
    salida = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                            capture_output=True, text=True, creationflags=NO_WINDOW).stdout
    return str(pid) in salida


def esperar_muerte(pid, segundos=5.0):
    fin = time.time() + segundos
    while time.time() < fin:
        if not vivo(pid):
            return True
        time.sleep(0.2)
    return False


class _Salida:
    """CompletedProcess falso para el fallback de PowerShell."""
    def __init__(self, stdout="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, "", returncode


# ---------------------------------------------------------------- fallback
# Se prueba parcheando subprocess.run: no toca procesos reales.
run_orig = fu.subprocess.run
try:
    fu.subprocess.run = lambda *a, **k: _Salida(json.dumps({"Id": 4242, "ProcessName": "WINWORD"}))
    r = fu._fallback_find_locking("C:\\tmp\\x.docx")
    check("fallback: un solo proceso (JSON dict) -> lista de 1, certero=False",
          r == {"procesos": [{"pid": 4242, "nombre": "WINWORD"}], "certero": False}, r)

    fu.subprocess.run = lambda *a, **k: _Salida(json.dumps(
        [{"Id": 1, "ProcessName": "A"}, {"Id": 2, "ProcessName": "B"}]))
    r = fu._fallback_find_locking("C:\\tmp\\x.docx")
    check("fallback: varios procesos (JSON lista)",
          [p["pid"] for p in r["procesos"]] == [1, 2] and r["certero"] is False, r)

    fu.subprocess.run = lambda *a, **k: _Salida("")
    r = fu._fallback_find_locking("C:\\tmp\\x.docx")
    check("fallback: sin resultados -> vacio y certero=False (NO 'libre')",
          r == {"procesos": [], "certero": False}, r)

    for etiqueta, salida in (("JSON invalido", "esto no es json"),
                             ("JSON sin campos", json.dumps({"x": 1})),
                             ("JSON de tipo inesperado", json.dumps(5))):
        fu.subprocess.run = lambda *a, salida=salida, **k: _Salida(salida)
        try:
            r = fu._fallback_find_locking("C:\\tmp\\x.docx")
            check(f"fallback: {etiqueta} -> vacio y certero=False, sin excepcion",
                  r == {"procesos": [], "certero": False}, r)
        except Exception as e:  # noqa: BLE001
            check(f"fallback: {etiqueta} no debe lanzar excepcion", False, repr(e))

    def _timeout(*a, **k):
        raise subprocess.TimeoutExpired("powershell", 15)
    fu.subprocess.run = _timeout
    r = fu._fallback_find_locking("C:\\tmp\\x.docx")
    check("fallback: timeout de PowerShell -> vacio y certero=False",
          r == {"procesos": [], "certero": False}, r)

    # La ruta con comillas no debe romper el comando de PowerShell (inyeccion).
    comandos = []
    fu.subprocess.run = lambda cmd, *a, **k: comandos.append(cmd) or _Salida("")
    fu._fallback_find_locking('C:\\tmp\\a"; calc; ".docx')
    check("fallback: una ruta con comillas va escapada en el comando de PowerShell",
          comandos and '"; calc; "' not in comandos[0][-1], comandos[0][-1] if comandos else "sin llamada")
finally:
    fu.subprocess.run = run_orig

# ------------------------------------------------------------- _kill_process
if os.name != "nt":
    print("[SKIP] Restart Manager y taskkill -> requieren Windows")
else:
    # taskkill falla -> False; PID inexistente -> False
    check("_kill_process: PID inexistente -> False", fu._kill_process(999999) is False)

    dormilon = subprocess.Popen([PYTHON, "-c", "import time; time.sleep(120)"],
                                creationflags=NO_WINDOW)
    try:
        time.sleep(0.5)
        check("setup: el proceso dormilon esta vivo", vivo(dormilon.pid))
        otro = subprocess.Popen([PYTHON, "-c", "import time; time.sleep(120)"],
                                creationflags=NO_WINDOW)
        try:
            check("_kill_process: cierra el PID pedido -> True", fu._kill_process(dormilon.pid) is True)
            check("el proceso pedido murio de verdad", esperar_muerte(dormilon.pid))
            check("NO toco a otro proceso", otro.poll() is None and vivo(otro.pid))
        finally:
            otro.kill()
    finally:
        dormilon.kill()

    # ------------------------------------------------- Restart Manager real
    with tempfile.TemporaryDirectory(prefix="salvagodinez_test_") as tmp:
        libre = os.path.join(tmp, "libre.txt")
        with open(libre, "w", encoding="utf-8") as f:
            f.write("x")
        r = fu._find_locking_processes(libre)
        check("archivo libre -> sin procesos y certero=True",
              r["procesos"] == [] and r["certero"] is True, r)

        bloqueado = os.path.join(tmp, "bloqueado.txt")
        codigo = (f"import sys, time\nf = open(r'{bloqueado}', 'w')\n"
                  "print('listo', flush=True)\ntime.sleep(120)\n")
        hijo = subprocess.Popen([PYTHON, "-c", codigo], stdout=subprocess.PIPE,
                                text=True, creationflags=NO_WINDOW)
        try:
            hijo.stdout.readline()  # espera a que el hijo tenga el archivo abierto
            r = fu._find_locking_processes(bloqueado)
            pids = [p["pid"] for p in r["procesos"]]
            check("archivo abierto por un hijo -> Restart Manager lo detecta (certero)",
                  hijo.pid in pids and r["certero"] is True, (hijo.pid, r))
            check("el proceso detectado trae un nombre",
                  all(p["nombre"] for p in r["procesos"]), r)
            check("no inventa procesos: solo el que lo tiene abierto",
                  pids == [hijo.pid], pids)
            # Cerrar al bloqueador y comprobar que el archivo queda libre.
            check("cerrar al bloqueador -> True", fu._kill_process(hijo.pid) is True)
            esperar_muerte(hijo.pid)
            r = fu._find_locking_processes(bloqueado)
            check("tras cerrarlo el archivo ya no esta bloqueado",
                  hijo.pid not in [p["pid"] for p in r["procesos"]], r)
        finally:
            hijo.kill()
            hijo.stdout.close()


print()
if fallos:
    print(f"RESULTADO: {fallos} FALLO(S)")
    sys.exit(1)
print("RESULTADO: TODO VERDE")
