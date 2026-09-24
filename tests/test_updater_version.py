"""Regresion de tools/updater.py: _signed_version_matches y _sanitizar_tag.

Cierra el ataque de downgrade/congelamiento: el trusted comment del .minisig
SI esta firmado, asi que atar la firma a la version esperada evita que un
.exe VIEJO con firma legitima se reuse bajo un tag remoto nuevo.

Corre sin dependencias del proyecto (rich, etc.) porque `tools/updater.py`
importa `utils`, que importa `rich`; igual que test_minisign_verify.py, el
modulo se carga por RUTA para no arrastrar esas dependencias.

    python3 tests/test_updater_version.py
"""

import importlib.util
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

_spec = importlib.util.spec_from_file_location(
    "updater", os.path.join(_RAIZ, "tools", "updater.py")
)
_mod = importlib.util.module_from_spec(_spec)
# updater.py hace `from rich... import ...` y `from utils import console` a
# nivel de modulo; si no estan disponibles, este test no puede cargarlo por
# ruta como el de minisign. Se intenta, y si falla se avisa claro (no es el
# candado critico, pero sin esto no se puede probar nada).
try:
    _spec.loader.exec_module(_mod)
except Exception as e:  # noqa: BLE001
    print(f"[FAIL] no se pudo cargar tools/updater.py: {type(e).__name__}: {e}")
    print("RESULTADO: 1 FALLO(S)")
    sys.exit(1)

_signed_version_matches = _mod._signed_version_matches
_sanitizar_tag = _mod._sanitizar_tag


fallos = 0


def check(nombre, cond, extra=""):
    global fallos
    fallos += not cond
    marca = "OK " if cond else "FAIL"
    detalle = f" -> {extra}" if not cond and extra else ""
    print(f"[{marca}] {nombre}{detalle}")


# ============================================================
# _signed_version_matches
# ============================================================

CASOS = [
    ("SalvaGodinez v2.9.0", "v2.9.0", True),
    ("SalvaGodinez v2.9.0", "v2.9.1", False),
    ("SalvaGodinez v2.9.0", "2.9.0", True),
    ("SalvaGodinez v2.9.0", "v99.0.0", False),
    ("", "v2.9.0", False),
    ("comentario basura sin version reconocible", "v2.9.0", False),
    ("SalvaGodinez v2.10.0", "v2.10.0", True),
    ("SalvaGodinez v2.10.0", "v2.1.0", False),
]

for comentario, remote_tag, esperado in CASOS:
    resultado = _signed_version_matches(comentario, remote_tag)
    check(
        f"_signed_version_matches({comentario!r}, {remote_tag!r}) == {esperado}",
        resultado == esperado,
        f"obtenido {resultado}",
    )


# ============================================================
# _sanitizar_tag
# ============================================================

check("_sanitizar_tag('v2.9.0') queda intacto",
      _sanitizar_tag("v2.9.0") == "v2.9.0")

_sucio = _sanitizar_tag("v1/../x")
check("_sanitizar_tag('v1/../x') no trae '/'", "/" not in _sucio, _sucio)


print()
if fallos:
    print(f"RESULTADO: {fallos} FALLO(S)")
    sys.exit(1)
print("RESULTADO: TODO VERDE")
