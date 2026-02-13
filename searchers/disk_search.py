"""Busqueda de archivos Office por nombre en todos los discos."""

import os
import time
from datetime import datetime

from config import OFFICE_EXTENSIONS, RECENT_DAYS
from utils import format_size as _format_size, get_drives as _get_drives


def _file_info(filepath: str) -> dict | None:
    try:
        stat = os.stat(filepath)
        return {
            "nombre": os.path.basename(filepath),
            "ruta": filepath,
            "tamano": _format_size(stat.st_size),
            "fecha": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "tamano_bytes": stat.st_size,
            "mtime": stat.st_mtime,
        }
    except OSError:
        return None


def search_by_name(name_filter: str, progress_callback=None) -> list[dict]:
    """Busca archivos Office por nombre parcial en todos los discos.

    Args:
        name_filter: Texto parcial del nombre del archivo (sin extension).
        progress_callback: Funcion opcional que recibe el directorio actual.

    Returns:
        Lista de resultados con nombre, ruta, tamano, fecha.
    """
    name_lower = name_filter.lower()
    results = []
    drives = _get_drives()

    for drive in drives:
        for dirpath, dirnames, filenames in os.walk(drive, topdown=True,
                                                     onerror=lambda e: None):
            # Saltar directorios del sistema que causan problemas
            dirnames[:] = [
                d for d in dirnames
                if d not in ("$Recycle.Bin", "System Volume Information",
                             "Windows", "$WinREAgent", "Recovery")
            ]
            try:
                if progress_callback:
                    progress_callback(dirpath)

                for fname in filenames:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in OFFICE_EXTENSIONS:
                        continue
                    if name_lower and name_lower not in fname.lower():
                        continue
                    filepath = os.path.join(dirpath, fname)
                    info = _file_info(filepath)
                    if info:
                        info["origen"] = f"Disco ({drive.rstrip(os.sep)})"
                        results.append(info)
            except (PermissionError, OSError):
                continue

    return results


def search_recent_excel(days: int = RECENT_DAYS, progress_callback=None) -> list[dict]:
    """Busca todos los archivos Office modificados en los ultimos N dias.

    Args:
        days: Numero de dias hacia atras para buscar.
        progress_callback: Funcion opcional que recibe el directorio actual.

    Returns:
        Lista de resultados.
    """
    cutoff = time.time() - (days * 86400)
    results = []
    drives = _get_drives()

    for drive in drives:
        for dirpath, dirnames, filenames in os.walk(drive, topdown=True,
                                                     onerror=lambda e: None):
            dirnames[:] = [
                d for d in dirnames
                if d not in ("$Recycle.Bin", "System Volume Information",
                             "Windows", "$WinREAgent", "Recovery")
            ]
            try:
                if progress_callback:
                    progress_callback(dirpath)

                for fname in filenames:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in OFFICE_EXTENSIONS:
                        continue
                    filepath = os.path.join(dirpath, fname)
                    info = _file_info(filepath)
                    if info and info["mtime"] >= cutoff:
                        info["origen"] = f"Disco ({drive.rstrip(os.sep)})"
                        results.append(info)
            except (PermissionError, OSError):
                continue

    # Ordenar por fecha de modificacion, mas reciente primero
    results.sort(key=lambda x: x["mtime"], reverse=True)
    return results
