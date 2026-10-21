"""Regresion de tools/wifi_passwords: leer netsh en cualquier idioma.

Bug que cubre (comprobado en un Windows 10 en espanol): netsh escribe su salida
con la pagina de codigos OEM (cp850), no UTF-8. La app la decodificaba como
UTF-8, asi que 'Autenticacion' (con tilde, byte 0xA2) llegaba como 'Autenticaci?n',
nunca coincidia con lo que buscaba y la columna "Seguridad" salia SIEMPRE vacia;
y una red con n con tilde o acentos en el nombre quedaba corrupta, con lo que
`netsh wlan show profile <nombre corrupto>` fallaba y se perdia su contrasena.

Tambien cubre ingles, redes abiertas, fallos de netsh y que _mask no filtre nada.
Todo con subprocess parchado (no toca los perfiles WiFi reales). Solo stdlib:

    python3 tests/test_wifi_passwords.py
"""

import os
import subprocess
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

from tools import wifi_passwords as wp  # noqa: E402


fallos = 0


def check(nombre, cond, extra=""):
    global fallos
    fallos += not cond
    marca = "OK " if cond else "FAIL"
    detalle = f" -> {extra}" if not cond and extra else ""
    print(f"[{marca}] {nombre}{detalle}")


class _Salida:
    def __init__(self, stdout=b"", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, b"", returncode


def netsh_falso(listado, detalles, codificacion, falla_en=None, listado_rc=0):
    """Devuelve un subprocess.run falso que habla como netsh: bytes en la pagina
    de codigos del sistema. `detalles` mapea nombre de perfil -> texto."""
    def _run(cmd, **kwargs):
        if cmd[:4] == ["netsh", "wlan", "show", "profiles"]:
            return _Salida(listado.encode(codificacion), listado_rc)
        if cmd[:4] == ["netsh", "wlan", "show", "profile"]:
            nombre = cmd[4]
            if falla_en and nombre == falla_en:
                raise subprocess.TimeoutExpired("netsh", 10)
            # netsh recibe el nombre tal cual lo escribio el usuario; uno
            # corrupto (decodificado con otra pagina de codigos) no existe.
            return _Salida(detalles.get(nombre, "").encode(codificacion))
        raise AssertionError(f"comando inesperado: {cmd}")
    return _run


def ejecutar(listado, detalles, codificacion, **kw):
    run_orig, oem_orig = wp.subprocess.run, getattr(wp, "_oem_encoding", None)
    wp.subprocess.run = netsh_falso(listado, detalles, codificacion, **kw)
    if oem_orig is not None:
        wp._oem_encoding = lambda: codificacion
    try:
        return wp.get_wifi_passwords()
    finally:
        wp.subprocess.run = run_orig
        if oem_orig is not None:
            wp._oem_encoding = oem_orig


# ------------------------------------------------------- Windows en espanol
listado_es = ("Perfiles en la interfaz Wi-Fi:\n\nPerfiles de directiva de grupo (solo lectura)\n"
              "---------------------------------\n    <Ninguno>\n\nPerfiles de usuario\n"
              "-------------------\n"
              "    Perfil de todos los usuarios : Casa\n"
              "    Perfil de todos los usuarios : Cafetería Ñandú\n"
              "    Perfil de todos los usuarios : Invitados\n")
detalles_es = {
    "Casa": ("    Autenticación             : WPA2-Personal\n"
             "    Cifrado                    : CCMP\n"
             "    Contenido de la clave      : clave-de-casa\n"),
    "Cafetería Ñandú": ("    Autenticación             : WPA2-Personal\n"
                      "    Contenido de la clave      : café-con-ñ\n"),
    "Invitados": ("    Autenticación             : Abierta\n"
                  "    Cifrado                    : Ninguno\n"),
}
r = ejecutar(listado_es, detalles_es, "cp850")
por_red = {x["red"]: x for x in r}
check("espanol: encuentra las 3 redes", set(por_red) == {"Casa", "Cafetería Ñandú", "Invitados"}, list(por_red))
check("espanol: lee la contrasena ('Contenido de la clave')", por_red.get("Casa", {}).get("contrasena") == "clave-de-casa", por_red.get("Casa"))
check("espanol: lee el tipo de seguridad aunque 'Autenticación' lleve tilde",
      por_red.get("Casa", {}).get("seguridad") == "WPA2-Personal", por_red.get("Casa"))
check("espanol: red con tildes y n con tilde en el nombre -> nombre y clave correctos",
      por_red.get("Cafetería Ñandú", {}).get("contrasena") == "café-con-ñ", por_red.get("Cafetería Ñandú"))
check("espanol: red abierta -> sin contrasena",
      por_red.get("Invitados", {}).get("contrasena") == "", por_red.get("Invitados"))

# ----------------------------------------------------------- Windows en ingles
listado_en = ("Profiles on interface Wi-Fi:\n\nUser profiles\n-------------\n"
              "    All User Profile     : Office\n    All User Profile     : Guest\n")
detalles_en = {
    "Office": "    Authentication         : WPA2-Personal\n    Key Content            : office-pass\n",
    "Guest": "    Authentication         : Open\n    Cipher                 : None\n",
}
r = ejecutar(listado_en, detalles_en, "cp437")
por_red = {x["red"]: x for x in r}
check("ingles: contrasena y seguridad de una red WPA2",
      por_red.get("Office") == {"red": "Office", "contrasena": "office-pass", "seguridad": "WPA2-Personal"}, por_red.get("Office"))
check("ingles: red abierta ('Open') no se reporta como tipo de seguridad",
      por_red.get("Guest") == {"red": "Guest", "contrasena": "", "seguridad": ""}, por_red.get("Guest"))

# ------------------------------------------------------------------- fallos
check("netsh con returncode != 0 -> lista vacia",
      ejecutar(listado_en, detalles_en, "cp437", listado_rc=1) == [])
check("sin perfiles guardados -> lista vacia",
      ejecutar("Profiles on interface Wi-Fi:\n\n    <None>\n", {}, "cp437") == [])
r = ejecutar(listado_en, detalles_en, "cp437", falla_en="Office")
por_red = {x["red"]: x for x in r}
check("timeout al leer una red -> 'Error al obtener' y las demas siguen",
      por_red.get("Office", {}).get("contrasena") == "Error al obtener"
      and por_red.get("Guest", {}).get("red") == "Guest", r)

run_orig = wp.subprocess.run


def _sin_netsh(*a, **k):
    raise OSError("netsh no existe")


wp.subprocess.run = _sin_netsh
try:
    check("netsh inexistente (OSError) -> lista vacia, sin excepcion", wp.get_wifi_passwords() == [])
finally:
    wp.subprocess.run = run_orig

# -------------------------------------------------------------------- _mask
check("_mask no revela nada: largo fijo y solo asteriscos",
      wp._mask("a") == wp._mask("una-clave-larguisima-123") == "********")
check("_mask no contiene ningun caracter de la clave", "S3" not in wp._mask("S3cr3t"))


print()
if fallos:
    print(f"RESULTADO: {fallos} FALLO(S)")
    sys.exit(1)
print("RESULTADO: TODO VERDE")
