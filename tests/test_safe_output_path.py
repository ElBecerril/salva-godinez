"""Regresion de tools/_file_helpers.safe_output_path.

Esta funcion protege al usuario de sobrescribir sin querer un archivo de
salida (union de PDFs/Excel, conversion de imagenes, etc.): un error aca es
perdida de datos. Antes vivia duplicada 5 veces en tools/ con pequenas
diferencias; ahora hay una sola version y este test cubre su contrato.

Corre sin dependencias externas (solo stdlib + os/tempfile):

    python3 tests/test_safe_output_path.py
"""

import os
import sys
import tempfile

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

from tools._file_helpers import safe_output_path  # noqa: E402


fallos = 0


def check(nombre, cond, extra=""):
    global fallos
    fallos += not cond
    marca = "OK " if cond else "FAIL"
    detalle = f" -> {extra}" if not cond and extra else ""
    print(f"[{marca}] {nombre}{detalle}")


def touch(path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("x")


with tempfile.TemporaryDirectory(prefix="salvagodinez_test_") as tmp:

    # 1. Archivo inexistente -> misma ruta (normalizada).
    destino = os.path.join(tmp, "reporte.xlsx")
    r = safe_output_path(destino)
    check("inexistente -> misma ruta", r == os.path.normpath(destino), r)

    # 2. Archivo existente -> sufijo "_1".
    touch(destino)
    r = safe_output_path(destino)
    esperado = os.path.join(tmp, "reporte_1.xlsx")
    check("existente -> sufijo _1", r == os.path.normpath(esperado), r)

    # 3. Varios existentes -> siguiente numero libre (deja un hueco: _1 y _3
    #    existen pero _2 no, asi que debe ofrecer _2, no _4).
    touch(os.path.join(tmp, "reporte_1.xlsx"))
    touch(os.path.join(tmp, "reporte_3.xlsx"))
    r = safe_output_path(destino)
    esperado = os.path.join(tmp, "reporte_2.xlsx")
    check("hueco en la numeracion -> usa el primero libre",
          r == os.path.normpath(esperado), r)

    # 3b. Sin huecos: _1.._5 existen -> debe dar _6.
    for i in range(1, 6):
        touch(os.path.join(tmp, f"consecutivo_{i}.txt"))
    touch(os.path.join(tmp, "consecutivo.txt"))
    r = safe_output_path(os.path.join(tmp, "consecutivo.txt"))
    esperado = os.path.join(tmp, "consecutivo_6.txt")
    check("varios consecutivos -> siguiente libre tras el ultimo",
          r == os.path.normpath(esperado), r)

    # 4. Extension multiple ("a.tar.gz"): splitext solo separa el ultimo
    #    punto, asi que el sufijo debe ir antes de ".gz", no antes de ".tar.gz".
    doble_ext = os.path.join(tmp, "backup.tar.gz")
    touch(doble_ext)
    r = safe_output_path(doble_ext)
    esperado = os.path.join(tmp, "backup.tar_1.gz")
    check("extension doble (a.tar.gz) -> sufijo antes de la ultima",
          r == os.path.normpath(esperado), r)

    # 4b. Nombre con punto intermedio que no es doble-extension real
    #     ("reporte.v2.xlsx"): mismo comportamiento de splitext (solo separa
    #     el ultimo punto), el sufijo va antes de ".xlsx".
    con_punto = os.path.join(tmp, "reporte.v2.xlsx")
    touch(con_punto)
    r = safe_output_path(con_punto)
    esperado = os.path.join(tmp, "reporte.v2_1.xlsx")
    check("nombre con punto intermedio (reporte.v2.xlsx) -> sufijo antes de .xlsx",
          r == os.path.normpath(esperado), r)

    # 5. Sin extension.
    sin_ext = os.path.join(tmp, "LEEME")
    touch(sin_ext)
    r = safe_output_path(sin_ext)
    esperado = os.path.join(tmp, "LEEME_1")
    check("sin extension -> sufijo pegado al nombre",
          r == os.path.normpath(esperado), r)

    # 6. Ruta con espacios y acentos (nombres de archivo que un godinez si
    #    usaria de verdad).
    con_acentos = os.path.join(tmp, "Informe de Nomina - Enero (final).xlsx")
    r = safe_output_path(con_acentos)
    check("con espacios/acentos, inexistente -> misma ruta",
          r == os.path.normpath(con_acentos), r)

    touch(con_acentos)
    r = safe_output_path(con_acentos)
    esperado = os.path.join(tmp, "Informe de Nomina - Enero (final)_1.xlsx")
    check("con espacios/acentos, existente -> sufijo _1",
          r == os.path.normpath(esperado), r)

    carpeta_rara = os.path.join(tmp, "reporte final ñ")
    os.makedirs(carpeta_rara, exist_ok=True)
    destino_rara = os.path.join(carpeta_rara, "cálculo.pdf")
    touch(destino_rara)
    r = safe_output_path(destino_rara)
    esperado = os.path.join(carpeta_rara, "cálculo_1.pdf")
    check("directorio con acentos/enie -> sufijo _1",
          r == os.path.normpath(esperado), r)

    # 7. Separadores mezclados (directorio con "/" + nombre unido con "\\",
    #    como puede pasar armando la ruta a mano) -> normpath los deja en
    #    un solo estilo.
    mezclada = tmp.rstrip(os.sep) + "/" + "mixto.txt"
    r = safe_output_path(mezclada)
    check("separadores mezclados -> normpath",
          r == os.path.normpath(mezclada), r)

    # 8. tools.image_converter._safe_output_path: wrapper de firma vieja
    #    (output_dir, base_name, ext) debe delegar igual.
    try:
        import tools._file_helpers  # noqa: F401  (ya importado arriba via safe_output_path)
        from tools import image_converter
        wrapper_disponible = True
    except ImportError as e:
        wrapper_disponible = False
        wrapper_error = e

    if wrapper_disponible:
        destino2 = os.path.join(tmp, "foto.png")
        touch(destino2)
        r = image_converter._safe_output_path(tmp, "foto", ".png")
        esperado = os.path.join(tmp, "foto_1.png")
        check("image_converter._safe_output_path (firma vieja) delega igual",
              r == os.path.normpath(esperado), r)
    else:
        # No deberia pasar en el venv de verificacion (tiene Pillow), pero si
        # falta una dependencia no es un fallo de ESTA funcion.
        print(f"[SKIP] image_converter._safe_output_path -> {wrapper_error}")


print()
if fallos:
    print(f"RESULTADO: {fallos} FALLO(S)")
    sys.exit(1)
print("RESULTADO: TODO VERDE")
