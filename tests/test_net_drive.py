"""Regresion de tools/net_drive: leer `net use` y no filtrar contrasenas.

Cubre:
  - el parser de la salida de `net use` en ingles y espanol, con estados
    ("OK", "Disconnected", "No disponible"), conexiones sin letra (IPC$) y
    carpetas compartidas con ESPACIOS en el nombre (\\\\NAS\\Carpeta Compartida:
    antes se mostraba cortada en el primer espacio);
  - que un fallo real de `net use` (timeout/OSError) se distinga de "no hay
    unidades";
  - que la contrasena viaje por STDIN y NUNCA en la linea de comandos (visible
    para cualquier proceso del equipo).

Todo con subprocess parchado: no toca ninguna unidad de red. Solo stdlib:

    python3 tests/test_net_drive.py
"""

import os
import subprocess
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

from tools import net_drive as nd  # noqa: E402


fallos = 0


def check(nombre, cond, extra=""):
    global fallos
    fallos += not cond
    marca = "OK " if cond else "FAIL"
    detalle = f" -> {extra}" if not cond and extra else ""
    print(f"[{marca}] {nombre}{detalle}")


class _Salida:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


UNC = "\\\\"  # dos barras invertidas
RAYA = "-" * 79


def parsear(salida, returncode=0):
    original = nd._run_net_use
    nd._run_net_use = lambda args, password=None: _Salida(salida, returncode)
    try:
        return nd._parse_net_use_output()
    finally:
        nd._run_net_use = original


# ----------------------------------------------------------------- parser
ingles = (f"New connections will be remembered.\n\nStatus       Local     Remote                    Network\n{RAYA}\n"
          f"OK           Z:        {UNC}srv\\datos               Microsoft Windows Network\n"
          f"Disconnected Y:        {UNC}srv\\otro                Microsoft Windows Network\n"
          "The command completed successfully.\n")
r = parsear(ingles)
check("ingles: dos unidades con estado, letra y ruta",
      r == [{"status": "OK", "letter": "Z:", "remote": f"{UNC}srv\\datos"},
            {"status": "Disconnected", "letter": "Y:", "remote": f"{UNC}srv\\otro"}], r)

espanol = (f"Se recordaran las nuevas conexiones.\n\nEstado        Local     Remoto                    Red\n{RAYA}\n"
           f"OK            Z:        {UNC}srv\\datos               Red de Microsoft Windows\n"
           f"No disponible Y:        {UNC}srv\\otro                Red de Microsoft Windows\n"
           "Se ha completado el comando correctamente.\n")
r = parsear(espanol)
check("espanol: estado con espacios ('No disponible') y ruta sin el nombre de la red",
      r == [{"status": "OK", "letter": "Z:", "remote": f"{UNC}srv\\datos"},
            {"status": "No disponible", "letter": "Y:", "remote": f"{UNC}srv\\otro"}], r)

con_espacios = (f"Status       Local     Remote                    Network\n{RAYA}\n"
                f"OK           Z:        {UNC}NAS\\Carpeta Compartida   Microsoft Windows Network\n")
r = parsear(con_espacios)
check("carpeta compartida con espacios -> ruta COMPLETA (no cortada en el primer espacio)",
      r == [{"status": "OK", "letter": "Z:", "remote": f"{UNC}NAS\\Carpeta Compartida"}], r)

larga = (f"Status       Local     Remote                    Network\n{RAYA}\n"
         f"OK           Z:        {UNC}servidor\\una_carpeta_con_nombre_muy_largo Microsoft Windows Network\n")
r = parsear(larga)
check("ruta tan larga que no deja hueco de 2 espacios -> toma solo la ruta, no el nombre de la red",
      r == [{"status": "OK", "letter": "Z:", "remote": f"{UNC}servidor\\una_carpeta_con_nombre_muy_largo"}], r)

sin_letra = (f"Status       Local     Remote                    Network\n{RAYA}\n"
             f"OK                     {UNC}srv\\IPC$                Microsoft Windows Network\n")
check("conexion sin letra (IPC$) no se lista como unidad", parsear(sin_letra) == [])
check("salida vacia -> []", parsear("") == [])
check("'No hay entradas en la lista' -> []", parsear("No hay entradas en la lista.\n") == [])
check("net use con returncode != 0 -> []", parsear(ingles, returncode=2) == [])

# --------------------------------------- fallo real != "no hay unidades"
original = nd._run_net_use
try:
    for exc in (subprocess.TimeoutExpired("net", 30), OSError("no se puede ejecutar")):
        def _falla(args, password=None, exc=exc):
            raise exc
        nd._run_net_use = _falla
        try:
            nd._parse_net_use_output()
            check(f"{type(exc).__name__} -> NetUseError", False, "no lanzo nada")
        except nd.NetUseError:
            check(f"{type(exc).__name__} se reporta como NetUseError (no como 'sin unidades')", True)
finally:
    nd._run_net_use = original

# --------------------------------- contrasena por stdin, nunca en argv
capturas = []
run_orig = nd.subprocess.run
nd.subprocess.run = lambda cmd, **k: capturas.append((cmd, k)) or _Salida("ok")
try:
    clave = "S3cr3t@Dominio!"
    nd._run_net_use(["Z:", f"{UNC}srv\\datos", "*", "/user:DOM\\ana", "/persistent:yes"], password=clave)
    cmd, kw = capturas[-1]
    check("con password: se entrega por stdin (input) con salto de linea",
          kw.get("input") == clave + "\n", kw.get("input"))
    check("con password: la clave NO aparece en la linea de comandos",
          all(clave not in parte for parte in cmd), cmd)
    check("el comando es 'net use ...' y pide la clave con '*'",
          cmd[:2] == ["net", "use"] and "*" in cmd, cmd)
    check("sin ventana de consola (creationflags)", "creationflags" in kw)
    check("tiene timeout (no se cuelga si el servidor no responde)", kw.get("timeout"))

    nd._run_net_use(["Z:", "/delete"])
    cmd, kw = capturas[-1]
    check("sin password: no se manda stdin", "input" not in kw, kw.keys())
    check("desconectar usa 'net use Z: /delete'", cmd == ["net", "use", "Z:", "/delete"], cmd)
finally:
    nd.subprocess.run = run_orig


print()
if fallos:
    print(f"RESULTADO: {fallos} FALLO(S)")
    sys.exit(1)
print("RESULTADO: TODO VERDE")
