"""Utilidades compartidas para los modulos de herramientas."""

import ctypes

# Re-exportar funciones comunes desde utils para mantener
# compatibilidad con imports existentes (from tools import format_size, etc.)
from utils import format_size, get_drives  # noqa: F401


def is_admin() -> bool:
    """Verifica si el proceso actual tiene permisos de administrador."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


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
