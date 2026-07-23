"""Regresion de tools/minisign_verify.py — el candado del auto-updater.

Ese modulo implementa Ed25519 a mano (para no sumarle ~10 MB de `cryptography`
al .exe), y es lo unico que separa al usuario de instalar un .exe firmado por
otro. Si se toca, esto tiene que seguir en verde ANTES de publicar.

Corre sin dependencias y sin Windows:

    python3 tests/test_minisign_verify.py

Las dos fuentes de verdad son independientes de nuestra implementacion:
  1. Los vectores de prueba oficiales del RFC 8032 (seccion 7.1) para el
     Ed25519 crudo.
  2. Firmas y llave REALES en formato minisign, generadas con una
     implementacion de terceros y congeladas aqui como fixtures.
"""

import binascii
import importlib.util
import os
import sys
import tempfile

# Se carga el modulo por RUTA en vez de `from tools.minisign_verify import ...`
# a proposito: `tools/__init__.py` importa utils, que importa rich, y entonces
# este test necesitaria las dependencias del proyecto instaladas. El modulo de
# firma solo usa la libreria estandar (base64 + hashlib), asi que cargandolo
# directo esto corre en cualquier Python pelon.
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "minisign_verify", os.path.join(_RAIZ, "tools", "minisign_verify.py")
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
ed25519_verify, verify_file = _mod.ed25519_verify, _mod.verify_file


fallos = 0


def check(nombre, cond, extra=""):
    global fallos
    fallos += not cond
    marca = "OK " if cond else "FAIL"
    detalle = f" -> {extra}" if not cond and extra else ""
    print(f"[{marca}] {nombre}{detalle}")


# ============================================================
# 1. Ed25519 crudo: vectores oficiales del RFC 8032, seccion 7.1
# ============================================================

H = binascii.unhexlify

VECTORES_RFC8032 = [
    # (llave publica, mensaje, firma) — los 3 primeros vectores del RFC.
    ("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
     "",
     "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555f"
     "b8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
    ("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
     "72",
     "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da08"
     "5ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
    ("fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025",
     "af82",
     "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18"
     "ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"),
]

for pub, msg, sig in VECTORES_RFC8032:
    check(f"RFC 8032: vector de {len(msg) // 2} byte(s) verifica",
          ed25519_verify(H(pub), H(msg), H(sig)))

pub, msg, sig = VECTORES_RFC8032[2]

sig_alterada = bytearray(H(sig))
sig_alterada[0] ^= 1
check("firma con un bit cambiado NO verifica",
      not ed25519_verify(H(pub), H(msg), bytes(sig_alterada)))

msg_alterado = bytearray(H(msg))
msg_alterado[0] ^= 1
check("mensaje con un bit cambiado NO verifica",
      not ed25519_verify(H(pub), bytes(msg_alterado), H(sig)))

# Maleabilidad: si no se rechaza s >= L, a una firma valida se le puede sumar
# el orden del grupo y sigue "verificando" — dos firmas distintas para el mismo
# archivo.
_L = 2**252 + 27742317777372353535851937790883648493
_s = int.from_bytes(H(sig)[32:], "little")
check("firma maleable (s + L) se rechaza",
      not ed25519_verify(H(pub), H(msg),
                         H(sig)[:32] + ((_s + _L) % 2**256).to_bytes(32, "little")))

for basura in (b"", b"x" * 31, b"x" * 33):
    try:
        check(f"llave de {len(basura)} bytes devuelve False sin excepcion",
              ed25519_verify(basura, b"m", b"y" * 64) is False)
    except Exception as e:  # noqa: BLE001
        check(f"llave de {len(basura)} bytes devuelve False sin excepcion",
              False, f"{type(e).__name__}: {e}")


# ============================================================
# 2. Formato minisign: llave y firmas reales congeladas
# ============================================================
#
# Generadas con una implementacion de terceros sobre el contenido de CONTENIDO.
# La llave privada correspondiente se descarto: estos fixtures solo sirven para
# comprobar que sabemos LEER y VERIFICAR el formato.

PUB = "RWQv0p3pAT1SUsGPwu3z8tXyDkaqX4eTejLp+dgVSgRUsBb7JDXh7EMT"

CONTENIDO = b"SalvaGodinez .exe de prueba\n" * 40

SIG_PREHASH = (
    "untrusted comment: minisign signature 2FD29DE9013D5252\n"
    "RUQv0p3pAT1SUi4qlydnXMhjjpQ6uF2dkbCvIXLFDidn/+ur/oH3G+LOaImSv/3auQ7B4FSq"
    "p2Mw4VHSXjPg6bveGMROsh34pQg=\n"
    "trusted comment: SalvaGodinez v9.9.9\n"
    "DMrEgHzu4UK574FJrvfHzbvpbVjKbAAuK7QXJalfWnrAgwNyqAd4CXpUplp7UvRXdlae9n9c"
    "0U0ZLIVnwn0UBA==\n"
)

SIG_CRUDA = (
    "untrusted comment: minisign signature 2FD29DE9013D5252\n"
    "RWQv0p3pAT1SUn2TQ/ZofqmZJq1eNY67aLA5FvtYjmgIOnqMTBuVn0tVsIXkt3TcMq7H0pHg"
    "zOyQGM1XiFfTsko6mXF0lwATdg8=\n"
    "trusted comment: SalvaGodinez v9.9.9\n"
    "GXX/W+34BLRT18RKtZz0v4mUs5U9lwhg0fVqIin5KnT5RdNINv3hqI0fWh3E6yV0k1bqxmrC"
    "1G58gBGhrc7lAA==\n"
)

SIG_OTRA_LLAVE = (
    "untrusted comment: minisign signature F85E1C94EF0936A1\n"
    "RUT4XhyU7wk2oZbNONEjMhCfSh0292j/UzsmgcVLcSKyEw893PVPOPNEYv0djefzmpLx5PzG"
    "8fcXKeFqtCFI6kH+nIwzoz3KIAY=\n"
    "trusted comment: malicioso\n"
    "sXmb9LPHY34G40URnzUOAh+apuxc5O+mds8jCU2BqTwJLeXIwHxQ3uYHBOS4KviR/X8Bopim"
    "XkiE9P+zvj96Bg==\n"
)

carpeta = tempfile.mkdtemp()
archivo = os.path.join(carpeta, "SalvaGodinez.exe")
with open(archivo, "wb") as f:
    f.write(CONTENIDO)

# `-H` (prehash BLAKE2b, el que usa el proceso de release) y el modo crudo.
for etiqueta, sig_texto in (("prehash (ED)", SIG_PREHASH), ("crudo (Ed)", SIG_CRUDA)):
    r = verify_file(archivo, sig_texto, PUB)
    check(f"{etiqueta}: firma real verifica", r.get("ok") is True, r)
    check(f"{etiqueta}: devuelve el trusted comment",
          r.get("trusted_comment") == "SalvaGodinez v9.9.9", r)

    # Un solo byte distinto en el .exe: es EL caso que esto existe para atrapar.
    alterado = os.path.join(carpeta, "alterado.exe")
    datos = bytearray(CONTENIDO)
    datos[100] ^= 0xFF
    with open(alterado, "wb") as f:
        f.write(datos)
    r = verify_file(alterado, sig_texto, PUB)
    check(f"{etiqueta}: .exe alterado -> signature_mismatch",
          r.get("error") == "signature_mismatch", r)

    # El trusted comment va firmado; reescribirlo tiene que romper la firma.
    lineas = sig_texto.strip().splitlines()
    lineas[2] = "trusted comment: SalvaGodinez v100.0.0"
    r = verify_file(archivo, "\n".join(lineas), PUB)
    check(f"{etiqueta}: trusted comment alterado -> global_sig_mismatch",
          r.get("error") == "global_sig_mismatch", r)

    # El untrusted comment NO va firmado: cambiarlo no debe romper nada.
    lineas = sig_texto.strip().splitlines()
    lineas[0] = "untrusted comment: cualquier cosa"
    r = verify_file(archivo, "\n".join(lineas), PUB)
    check(f"{etiqueta}: untrusted comment alterado sigue verificando",
          r.get("ok") is True, r)

r = verify_file(archivo, SIG_OTRA_LLAVE, PUB)
check("firmado con otra llave -> key_mismatch", r.get("error") == "key_mismatch", r)


# ============================================================
# 3. Basura de la red: error de dato, nunca una excepcion
# ============================================================

MALFORMADOS = [
    ("llave publica vacia", archivo, SIG_PREHASH, "", "bad_pubkey"),
    ("llave publica no base64", archivo, SIG_PREHASH, "no-es-base64!!", "bad_pubkey"),
    ("firma vacia", archivo, "", PUB, "bad_signature"),
    ("firma truncada", archivo, "untrusted comment: x\nAAAA", PUB, "bad_signature"),
    ("firma no base64", archivo, "untrusted comment: x\n!!\ntrusted comment: y\n!!",
     PUB, "bad_signature"),
    ("archivo inexistente", os.path.join(carpeta, "no-existe.exe"), SIG_PREHASH,
     PUB, "read_error"),
]

for nombre, ruta, sig_texto, pubkey, esperado in MALFORMADOS:
    try:
        r = verify_file(ruta, sig_texto, pubkey)
        check(f"{nombre} -> {esperado}", r.get("error") == esperado, r)
    except Exception as e:  # noqa: BLE001
        check(f"{nombre} -> {esperado} sin excepcion", False, f"{type(e).__name__}: {e}")


print()
if fallos:
    print(f"RESULTADO: {fallos} FALLO(S)")
    sys.exit(1)
print("RESULTADO: TODO VERDE")
