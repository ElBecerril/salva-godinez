"""Busqueda de archivos temporales y de autorecuperacion de Excel."""

import os
from datetime import datetime

from config import EXCEL_EXTENSIONS, RECOVERY_PATHS, TEMP_PREFIXES


def _format_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _is_excel_temp(filename: str) -> bool:
    """Determina si un archivo es un temporal de Excel."""
    lower = filename.lower()
    # Archivos temporales de Excel: ~$libro.xlsx, ~libro.tmp
    if any(lower.startswith(p) for p in TEMP_PREFIXES):
        ext = os.path.splitext(lower)[1]
        if ext in EXCEL_EXTENSIONS or ext in (".tmp", ".xlk"):
            return True
    # Archivos de autorecuperacion
    if lower.endswith(".xar") or lower.endswith(".asd"):
        return True
    # Archivos Excel normales en carpetas de recuperacion
    ext = os.path.splitext(lower)[1]
    if ext in EXCEL_EXTENSIONS:
        return True
    return False


def search_temp_files(name_filter: str = "") -> list[dict]:
    """Busca archivos temporales y de autorecuperacion de Excel.

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
                    if not _is_excel_temp(fname):
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
