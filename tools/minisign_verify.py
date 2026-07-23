"""Verificacion de firmas minisign (Ed25519) — SOLO verificar, nunca firmar.

Para que existe
---------------
El updater ya compara el SHA-256 del .exe descargado contra el hash publicado
en las notas del Release. Eso detecta una descarga corrupta o un asset
cambiado en el CDN, pero NO protege contra quien controle la cuenta de GitHub:
ese atacante cambia el .exe Y el hash de las notas en el mismo movimiento, y el
updater lo instala tan contento en el Escritorio de miles de oficinistas.

La firma cierra ese hueco. La llave PRIVADA vive offline en la maquina del
autor (nunca en el repo ni en GitHub Secrets) y la PUBLICA viaja dentro del
.exe. Un .exe malicioso no se puede firmar sin la llave privada, asi que
comprometer GitHub ya no alcanza.

Por que Ed25519 escrito a mano
------------------------------
Verificar Ed25519 requiere una libreria de criptografia, y `cryptography` o
`PyNaCl` suman ~10 MB al .exe (empaquetan OpenSSL/libsodium). Este proyecto ya
rechazo opencv por +50 MB. La VERIFICACION de Ed25519 son ~80 lineas de
aritmetica modular y aqui se usa la implementacion de referencia del RFC 8032
(dominio publico), verificada contra los vectores de prueba oficiales del
propio RFC.

Ojo con el alcance: esto SOLO verifica. No hay llave privada, no se firma nada
y no se maneja ningun secreto, asi que las precauciones de canal lateral
(tiempo constante) que si importarian al firmar no aplican: todo lo que se
procesa aqui es publico.

Formato minisign
----------------
Llave publica (minisign.pub), 2a linea en base64:
    2 bytes algoritmo ("Ed") + 8 bytes key id + 32 bytes llave publica

Firma (.minisig):
    linea 1: untrusted comment: ...
    linea 2: base64 -> 2 bytes alg + 8 bytes key id + 64 bytes firma
    linea 3: trusted comment: ...
    linea 4: base64 -> 64 bytes firma global sobre (firma || trusted comment)

El algoritmo es "Ed" (se firma el archivo tal cual) o "ED" (se firma el
BLAKE2b-512 del archivo, modo prehash de `minisign -H`). Se soportan los dos.

El "trusted comment" es la parte que SI esta firmada: un atacante puede
reescribir el comentario "untrusted" sin invalidar nada, por eso la firma
global se verifica siempre y el comentario de confianza solo se devuelve tras
verificarla.
"""

import base64
import hashlib


# ============================================================
# Ed25519 — implementacion de referencia del RFC 8032 (dominio publico)
# ============================================================

_p = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493


def _modp_inv(x: int) -> int:
    return pow(x, _p - 2, _p)


_d = -121665 * _modp_inv(121666) % _p
_modp_sqrt_m1 = pow(2, (_p - 1) // 4, _p)


def _recover_x(y: int, sign: int):
    """Recupera la coordenada x de un punto comprimido, o None si no existe."""
    if y >= _p:
        return None
    x2 = (y * y - 1) * _modp_inv(_d * y * y + 1) % _p
    if x2 == 0:
        # x = 0 con signo 1 no es una codificacion valida.
        return None if sign else 0
    x = pow(x2, (_p + 3) // 8, _p)
    if (x * x - x2) % _p != 0:
        x = x * _modp_sqrt_m1 % _p
    if (x * x - x2) % _p != 0:
        return None
    if (x & 1) != sign:
        x = _p - x
    return x


# Punto generador de la curva.
_g_y = 4 * _modp_inv(5) % _p
_g_x = _recover_x(_g_y, 0)
_G = (_g_x, _g_y, 1, _g_x * _g_y % _p)


def _point_add(P, Q):
    """Suma en coordenadas extendidas (X, Y, Z, T). Sin inversiones."""
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % _p
    B = (P[1] + P[0]) * (Q[1] + Q[0]) % _p
    C = 2 * P[3] * Q[3] * _d % _p
    D = 2 * P[2] * Q[2] % _p
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _p, G * H % _p, F * G % _p, E * H % _p)


def _point_mul(s: int, P):
    """Multiplicacion escalar por doble-y-suma."""
    Q = (0, 1, 1, 0)  # elemento neutro
    while s > 0:
        if s & 1:
            Q = _point_add(Q, P)
        P = _point_add(P, P)
        s >>= 1
    return Q


def _point_equal(P, Q) -> bool:
    # Los puntos son proyectivos: hay que comparar X1/Z1 == X2/Z2 en cruz.
    if (P[0] * Q[2] - Q[0] * P[2]) % _p != 0:
        return False
    if (P[1] * Q[2] - Q[1] * P[2]) % _p != 0:
        return False
    return True


def _point_decompress(s: bytes):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        return None
    return (x, y, 1, x * y % _p)


def _sha512_modq(s: bytes) -> int:
    return int.from_bytes(hashlib.sha512(s).digest(), "little") % _L


def ed25519_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """Verifica una firma Ed25519. True solo si es valida.

    Cualquier entrada malformada (tamano incorrecto, punto fuera de la curva,
    escalar fuera de rango) devuelve False, nunca una excepcion: esto lo
    alimenta un archivo bajado de internet.
    """
    try:
        if len(public_key) != 32 or len(signature) != 64:
            return False
        A = _point_decompress(public_key)
        if A is None:
            return False
        Rs = signature[:32]
        R = _point_decompress(Rs)
        if R is None:
            return False
        s = int.from_bytes(signature[32:], "little")
        # s >= L se rechaza: sin esto la firma seria maleable (se le podria
        # sumar L y seguir "verificando").
        if s >= _L:
            return False
        h = _sha512_modq(Rs + public_key + message)
        sB = _point_mul(s, _G)
        hA = _point_mul(h, A)
        return _point_equal(sB, _point_add(R, hA))
    except Exception:  # noqa: BLE001 - dato externo: nunca debe propagar
        return False


# ============================================================
# Formato minisign
# ============================================================


class MinisignError(Exception):
    """Firma o llave con formato invalido (no: firma que no verifica)."""


def parse_public_key(text: str) -> tuple[bytes, bytes]:
    """Lee una llave publica de minisign. Retorna (key_id, public_key).

    Acepta el contenido completo del archivo .pub (con su linea de comentario)
    o solo la linea de base64.
    """
    lineas = [l.strip() for l in (text or "").splitlines() if l.strip()]
    if not lineas:
        raise MinisignError("Llave publica vacia")
    b64 = lineas[-1] if len(lineas) > 1 else lineas[0]
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception as e:  # noqa: BLE001
        raise MinisignError(f"Llave publica no es base64 valido: {e}") from e
    if len(raw) != 42:
        raise MinisignError(f"Llave publica de tamano invalido ({len(raw)} bytes, se esperaban 42)")
    if raw[:2] != b"Ed":
        raise MinisignError(f"Algoritmo de llave no soportado: {raw[:2]!r}")
    return raw[2:10], raw[10:]


def parse_signature(text: str) -> dict:
    """Lee un archivo .minisig.

    Retorna {"alg", "key_id", "signature", "trusted_comment", "global_sig"}.
    """
    lineas = [l.rstrip("\r\n") for l in (text or "").splitlines() if l.strip()]
    if len(lineas) < 4:
        raise MinisignError("Archivo de firma incompleto (se esperaban 4 lineas)")

    try:
        raw = base64.b64decode(lineas[1].strip(), validate=True)
    except Exception as e:  # noqa: BLE001
        raise MinisignError(f"Firma no es base64 valido: {e}") from e
    if len(raw) != 74:
        raise MinisignError(f"Firma de tamano invalido ({len(raw)} bytes, se esperaban 74)")

    alg = raw[:2]
    if alg not in (b"Ed", b"ED"):
        raise MinisignError(f"Algoritmo de firma no soportado: {alg!r}")

    prefijo = "trusted comment:"
    if not lineas[2].startswith(prefijo):
        raise MinisignError("Falta la linea 'trusted comment:'")
    # minisign guarda el comentario tal cual, sin el espacio que sigue a los
    # dos puntos; ese espacio NO es parte de lo firmado.
    trusted = lineas[2][len(prefijo):]
    if trusted.startswith(" "):
        trusted = trusted[1:]

    try:
        global_sig = base64.b64decode(lineas[3].strip(), validate=True)
    except Exception as e:  # noqa: BLE001
        raise MinisignError(f"Firma global no es base64 valido: {e}") from e
    if len(global_sig) != 64:
        raise MinisignError(f"Firma global de tamano invalido ({len(global_sig)} bytes)")

    return {
        "alg": alg,
        "key_id": raw[2:10],
        "signature": raw[10:],
        "trusted_comment": trusted,
        "global_sig": global_sig,
    }


def verify_file(path: str, sig_text: str, pubkey_text: str) -> dict:
    """Verifica que `path` fue firmado por el dueno de `pubkey_text`.

    Retorna {"ok": True, "trusted_comment": str} o
    {"ok": False, "error": razon, "detail": str}, con razon en:
    bad_pubkey | bad_signature | key_mismatch | read_error |
    signature_mismatch | global_sig_mismatch.

    Nunca lanza: todo lo que entra aqui viene de la red.
    """
    try:
        key_id, public_key = parse_public_key(pubkey_text)
    except MinisignError as e:
        return {"ok": False, "error": "bad_pubkey", "detail": str(e)}

    try:
        sig = parse_signature(sig_text)
    except MinisignError as e:
        return {"ok": False, "error": "bad_signature", "detail": str(e)}

    if sig["key_id"] != key_id:
        # La firma es de OTRA llave. Se distingue de "firma invalida" porque
        # suele significar que el autor roto la llave, no un ataque.
        return {
            "ok": False, "error": "key_mismatch",
            "detail": f"la firma es de la llave {sig['key_id'].hex()}, se esperaba {key_id.hex()}",
        }

    try:
        if sig["alg"] == b"ED":
            # Modo prehash: se firma el BLAKE2b-512 del archivo. Se lee por
            # bloques para no cargar 45 MB de .exe en memoria.
            h = hashlib.blake2b(digest_size=64)
            with open(path, "rb") as f:
                for bloque in iter(lambda: f.read(65536), b""):
                    h.update(bloque)
            mensaje = h.digest()
        else:
            with open(path, "rb") as f:
                mensaje = f.read()
    except OSError as e:
        return {"ok": False, "error": "read_error", "detail": str(e)}

    if not ed25519_verify(public_key, mensaje, sig["signature"]):
        return {"ok": False, "error": "signature_mismatch",
                "detail": "el archivo no corresponde a la firma"}

    # La firma global cubre (firma || trusted comment). Sin este paso el
    # trusted comment seria tan poco confiable como el untrusted.
    global_msg = sig["signature"] + sig["trusted_comment"].encode("utf-8")
    if not ed25519_verify(public_key, global_msg, sig["global_sig"]):
        return {"ok": False, "error": "global_sig_mismatch",
                "detail": "el comentario firmado fue alterado"}

    return {"ok": True, "trusted_comment": sig["trusted_comment"]}
