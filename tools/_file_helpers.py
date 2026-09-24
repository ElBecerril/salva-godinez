"""Helpers compartidos entre modulos de tools/ para no sobrescribir salidas.

Antes existian 5 copias casi-identicas de esta logica (pdf_tools,
excel_cell_cleaner, excel_comparator, excel_consolidator, image_converter),
con pequenas diferencias (algunas normalizaban separadores con normpath,
otras no). Se unifican aca en una sola funcion.
"""

import os


def safe_output_path(path: str) -> str:
    """Evita sobrescribir un archivo existente agregando un sufijo numerico.

    Si `path` no existe, se devuelve tal cual (normalizada con normpath). Si
    ya existe, se prueba "<base>_1<ext>", "<base>_2<ext>", ... hasta hallar
    una ruta libre.

    Normaliza los separadores con os.path.normpath: la ruta de salida suele
    armarse uniendo un directorio de dialogo (barras /) con un nombre por
    os.path.join (barra \\ en Windows), y la ruta cruda queda con estilos
    mezclados ("C:/Users/...\\archivo.pdf"). Asi el mensaje que ve el
    usuario y el archivo real en disco usan un solo estilo.
    """
    path = os.path.normpath(path)
    if not os.path.exists(path):
        return path

    base, ext = os.path.splitext(path)
    counter = 1
    while True:
        candidate = os.path.normpath(f"{base}_{counter}{ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1
