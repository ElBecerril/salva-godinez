"""Busqueda de archivos temporales y de autorecuperacion (cualquier tipo) en
las carpetas conocidas de Office/Windows."""

import os
from datetime import datetime

from config import RECOVERY_PATHS, RECOVERY_EXTENSIONS, TEMP_PREFIXES
from utils import format_size as _format_size


# Ruta generica de temporales del sistema: a diferencia de las carpetas de
# Office (Excel/Word/PowerPoint/UnsavedFiles), %TEMP% recibe basura de
# CUALQUIER programa (instaladores, cache de npm, etc.), asi que ahi si hace
# falta seguir exigiendo un patron de temporal/autorecuperacion reconocible;
# si no, un usuario que solo busca "informe" veria miles de archivos ajenos.
_GENERIC_TEMP_DIR = os.path.normcase(os.path.normpath(os.environ.get("TEMP", "")))


def _has_temp_signature(filename: str) -> bool:
    """Detecta si el nombre tiene el PATRON de un temporal/autorecuperado
    (sin importar el tipo de archivo original que representa)."""
    lower = filename.lower()
    # Prefijo de lock/temporal de Office: ~$libro.xlsx, ~$reporte.zip, etc.
    # Cualquier extension cuenta ahora: el prefijo ya es la senal fuerte.
    if any(lower.startswith(p) for p in TEMP_PREFIXES):
        return True
    # Extensiones genericas de temporal/autorecuperacion (no exclusivas de
    # Office: cualquier app puede dejar un .tmp/.asd por ahi). La lista vive en
    # config.RECOVERY_EXTENSIONS para compartirla con disk_cleaner (que las
    # PROTEGE al limpiar %TEMP%).
    ext = os.path.splitext(lower)[1]
    return ext in RECOVERY_EXTENSIONS


def _is_recoverable(filename: str, base_path: str) -> bool:
    """Determina si un archivo cuenta como temporal/autorecuperado.

    Antes esta funcion exigia que el archivo tuviera extension de Office
    (OFFICE_EXTENSIONS). Se quito ese filtro para las carpetas ESPECIFICAS
    de Office (AppData\\Excel, \\Word, \\PowerPoint, UnsavedFiles): ya son
    carpetas de proposito unico, asi que cualquier archivo que caiga ahi es
    candidato valido sin importar su tipo (ej. Office guarda autorecuperados
    en UnsavedFiles con nombre y extension normales, sin prefijo `~$`) — el
    filtro real que decide que se muestra es el nombre que escribe el
    usuario.

    Para la carpeta generica %TEMP% (compartida por todo el sistema, no solo
    Office) SI se sigue exigiendo el patron de temporal (_has_temp_signature)
    para no listar cualquier archivo suelto que un programa cualquiera dejo
    ahi.
    """
    if os.path.normcase(os.path.normpath(base_path)) == _GENERIC_TEMP_DIR and _GENERIC_TEMP_DIR:
        return _has_temp_signature(filename)
    return True


def search_temp_files(name_filter: str = "") -> list[dict]:
    """Busca archivos temporales y de autorecuperacion (cualquier tipo) en
    las carpetas conocidas de Office/Windows.

    Args:
        name_filter: Texto parcial opcional para filtrar por nombre.

    Returns:
        Lista de resultados con nombre, ruta, tamano, fecha, origen.
    """
    results = []
    name_lower = name_filter.lower()

    for base_path in RECOVERY_PATHS:
        if not os.path.isdir(base_path):
            continue
        try:
            for dirpath, _, filenames in os.walk(base_path):
                for fname in filenames:
                    if not _is_recoverable(fname, base_path):
                        continue
                    if name_lower and name_lower not in fname.lower():
                        continue
                    filepath = os.path.join(dirpath, fname)
                    try:
                        stat = os.stat(filepath)
                        results.append({
                            "nombre": fname,
                            "ruta": filepath,
                            "tamano": _format_size(stat.st_size),
                            "fecha": datetime.fromtimestamp(stat.st_mtime).strftime(
                                "%Y-%m-%d %H:%M"
                            ),
                            "origen": "Autorecuperacion / Temp",
                        })
                    except OSError:
                        continue
        except OSError:
            continue

    return results
