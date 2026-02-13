"""Busqueda de archivos Office en el historial reciente de Windows (.lnk)."""

import os
from datetime import datetime

from config import OFFICE_EXTENSIONS, RECENT_PATH
from utils import format_size as _format_size, read_lnk_target as _read_lnk_target


def search_recent_files(name_filter: str = "") -> list[dict]:
    """Busca archivos Office en el historial reciente de Windows.

    Args:
        name_filter: Texto parcial opcional para filtrar por nombre.

    Returns:
        Lista de resultados. Incluye si el archivo aun existe o no.
    """
    results = []
    name_lower = name_filter.lower()

    if not os.path.isdir(RECENT_PATH):
        return results

    try:
        for fname in os.listdir(RECENT_PATH):
            if not fname.lower().endswith(".lnk"):
                continue

            lnk_path = os.path.join(RECENT_PATH, fname)
            target = _read_lnk_target(lnk_path)
            if not target:
                continue

            ext = os.path.splitext(target)[1].lower()
            if ext not in OFFICE_EXTENSIONS:
                continue

            target_name = os.path.basename(target)
            if name_lower and name_lower not in target_name.lower():
                continue

            exists = os.path.isfile(target)

            if exists:
                try:
                    stat = os.stat(target)
                    size = _format_size(stat.st_size)
                    fecha = datetime.fromtimestamp(stat.st_mtime).strftime(
                        "%Y-%m-%d %H:%M"
                    )
                except OSError:
                    size = "?"
                    fecha = "?"
            else:
                size = "N/A"
                fecha = "N/A"

            estado = "Existe" if exists else "NO encontrado"

            results.append({
                "nombre": target_name,
                "ruta": target,
                "tamano": size,
                "fecha": fecha,
                "origen": f"Recientes ({estado})",
                "existe": exists,
            })
    except OSError:
        pass

    return results
