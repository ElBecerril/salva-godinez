"""Utilidades compartidas para los modulos de herramientas."""

import ctypes
import os
import string


def is_admin() -> bool:
    """Verifica si el proceso actual tiene permisos de administrador."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def format_size(size_bytes: int) -> str:
    """Formatea bytes a unidad legible: '1.5 MB'."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_drives() -> list[str]:
    """Detecta las unidades de disco disponibles en Windows."""
    drives = []
    for letter in string.ascii_uppercase:
        path = f"{letter}:\\"
        if os.path.exists(path):
            drives.append(path)
    return drives


def get_removable_drives() -> list[str]:
    """Detecta unidades USB removibles."""
    drives = []
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
        path = f"{letter}:\\"
        try:
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(path)
            if drive_type == 2:  # DRIVE_REMOVABLE
                drives.append(path)
        except (AttributeError, OSError):
            continue
    return drives
