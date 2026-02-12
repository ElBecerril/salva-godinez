"""Utilidades compartidas para los modulos de herramientas."""

import ctypes


def is_admin() -> bool:
    """Verifica si el proceso actual tiene permisos de administrador."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False
