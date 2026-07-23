"""Regresion del parser de `vssadmin list shadows` (searchers/shadow_copies.py).

El rescate por Copias de seguridad de Windows estuvo MUERTO dos veces seguidas
por este parser, y las dos veces en silencio (devolvia [] sin error):

  - hasta v2.8.0: el regex de la unidad exigia "(C:\\)" y vssadmin emite "(C:)".
  - hasta v2.9.0: la deteccion de la ruta exigia la etiqueta INGLESA "Shadow
    Copy Volume", pero en Windows en espanol —el de todo el publico de la
    app— dice "Volumen de instantaneas". Se cazo corriendo vssadmin de verdad
    en la VM Win11 es-MX; las pruebas de escritorio no lo veian porque nadie
    tenia a mano una salida real en espanol.

De ahi que la salida es-MX de abajo sea literal, copiada de esa corrida.

    python3 tests/test_shadow_copies_parser.py
"""

import importlib.util
import os
import sys
from unittest.mock import patch

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)


class _StubConfig:
    OFFICE_EXTENSIONS = (".docx", ".xlsx")


def _cargar():
    """Carga searchers.shadow_copies sin arrastrar rich (via utils)."""
    sys.modules.setdefault("config", _StubConfig())
    utils_stub = type(sys)("utils")
    utils_stub.format_size = lambda n: f"{n} B"
    sys.modules.setdefault("utils", utils_stub)
    spec = importlib.util.spec_from_file_location(
        "shadow_copies", os.path.join(_RAIZ, "searchers", "shadow_copies.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sc = _cargar()

fallos = 0


def check(nombre, cond, extra=""):
    global fallos
    fallos += not cond
    print(f"[{'OK ' if cond else 'FAIL'}] {nombre}{(' -> ' + str(extra)) if not cond and extra else ''}")


# Salida REAL de `vssadmin list shadows` en Windows 11 es-MX (VM de pruebas,
# 2026-07-23), con una instantanea creada por Checkpoint-Computer.
SALIDA_ES = """vssadmin 1.1 - Herramienta administrativa de linea de comandos del Servicio de instantaneas de volumen.
(C) Copyright 2001-2013 Microsoft Corp.

Contenido de  id. de conjunto de instantaneas: {a0bde5cf-4c52-4fcb-918e-0dd9aee2ba7b}
   Contenia 1 instantaneas en el momento de su creacion: 23/07/2026 04:52:46 p. m.
      Id. de instantaneas: {504ff6e8-2833-438d-97cf-37bbc36c374a}
         Volumen original: (C:)\\\\?\\Volume{05297703-1946-467b-999f-110a13bacc94}\\
         Volumen de instantaneas: \\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy1
         Equipo de origen: SALVA-PRUEBAS
         Equipo de servicio: SALVA-PRUEBAS
         Proveedor: 'Microsoft Software Shadow Copy provider 1.0'
         Tipo: ClientAccessibleWriters
         Atributos: Persistente, Accesible para el cliente, Sin liberacion automatica, Diferencial, Recuperado automaticamente
"""

# Equivalente en ingles (formato documentado de vssadmin).
SALIDA_EN = """vssadmin 1.1 - Volume Shadow Copy Service administrative command-line tool
(C) Copyright 2001-2013 Microsoft Corp.

Contents of shadow copy set ID: {a0bde5cf-4c52-4fcb-918e-0dd9aee2ba7b}
   Contained 1 shadow copies at creation time: 7/23/2026 4:52:46 PM
      Shadow Copy ID: {504ff6e8-2833-438d-97cf-37bbc36c374a}
         Original Volume: (C:)\\\\?\\Volume{05297703-1946-467b-999f-110a13bacc94}\\
         Shadow Copy Volume: \\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy1
         Originating Machine: SALVA-PRUEBAS
         Service Machine: SALVA-PRUEBAS
         Provider: 'Microsoft Software Shadow Copy provider 1.0'
         Type: ClientAccessibleWriters
         Attributes: Persistent, Client-accessible, No auto release, Differential, Auto recovered
"""

SIN_PERMISOS_ES = """vssadmin 1.1 - Herramienta administrativa de linea de comandos del Servicio de instantaneas de volumen.
(C) Copyright 2001-2013 Microsoft Corp.

Error: No tiene los permisos adecuados para ejecutar este comando. Ejecute esta utilidad desde una ventana de comandos que tenga privilegios elevados de administrador.
"""

SIN_PERMISOS_EN = """Error: You don't have the correct permissions to run this command. Run this utility from a command window that has elevated administrator privileges.
"""

SIN_COPIAS_ES = """vssadmin 1.1 - Herramienta administrativa de linea de comandos del Servicio de instantaneas de volumen.
(C) Copyright 2001-2013 Microsoft Corp.

No se encontraron elementos que cumplan la consulta.
"""


class _Resultado:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def correr(stdout, returncode=0, stderr=""):
    with patch.object(sc.subprocess, "run",
                      lambda *a, **k: _Resultado(stdout, stderr, returncode)), \
         patch.object(sc.subprocess, "CREATE_NO_WINDOW", 0, create=True):
        return sc._list_shadow_copies()


# --- El caso que estaba roto: Windows en espanol ---
shadows = correr(SALIDA_ES)
check("es-MX: encuentra la instantanea (antes devolvia [] siempre)",
      len(shadows) == 1, shadows)
if shadows:
    s = shadows[0]
    check("es-MX: ruta GLOBALROOT correcta",
          s.get("path") == r"\\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy1", s)
    check("es-MX: unidad de origen es C", s.get("drive") == "C", s)
    check("es-MX: fecha capturada", "23/07/2026" in s.get("date", ""), s)
check("es-MX: motivo vacio (todo bien)", sc.ultimo_motivo() == "", sc.ultimo_motivo())

# --- El ingles no se rompio al arreglar el espanol ---
shadows = correr(SALIDA_EN)
check("en-US: encuentra la instantanea", len(shadows) == 1, shadows)
if shadows:
    s = shadows[0]
    check("en-US: ruta GLOBALROOT correcta",
          s.get("path") == r"\\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy1", s)
    check("en-US: unidad de origen es C", s.get("drive") == "C", s)

# --- Deja de mentir: distingue POR QUE no hay resultados ---
check("sin permisos (ES) -> lista vacia",
      correr(SIN_PERMISOS_ES, returncode=1) == [])
check("sin permisos (ES) -> motivo sin_permisos",
      sc.ultimo_motivo() == "sin_permisos", sc.ultimo_motivo())

correr(SIN_PERMISOS_EN, returncode=1)
check("sin permisos (EN) -> motivo sin_permisos",
      sc.ultimo_motivo() == "sin_permisos", sc.ultimo_motivo())

correr(SIN_COPIAS_ES)
check("sin copias -> motivo sin_copias (no se confunde con falta de permisos)",
      sc.ultimo_motivo() == "sin_copias", sc.ultimo_motivo())

correr("", returncode=1)
check("otro error -> motivo error", sc.ultimo_motivo() == "error", sc.ultimo_motivo())

# --- Varias instantaneas ---
dos = SALIDA_ES + SALIDA_ES.replace("ShadowCopy1", "ShadowCopy2")
check("dos instantaneas -> dos resultados", len(correr(dos)) == 2)

# --- Basura no revienta ---
for basura in ("", "ni idea de que es esto", "(C:)\n(D:)\n"):
    try:
        check(f"entrada rara {basura[:20]!r} no lanza", isinstance(correr(basura), list))
    except Exception as e:  # noqa: BLE001
        check(f"entrada rara {basura[:20]!r} no lanza", False, f"{type(e).__name__}: {e}")

print()
if fallos:
    print(f"RESULTADO: {fallos} FALLO(S)")
    sys.exit(1)
print("RESULTADO: TODO VERDE")
