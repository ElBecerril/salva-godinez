"""Busqueda de archivos Excel en Shadow Copies (VSS) de Windows."""

import os
import re
import subprocess
from datetime import datetime

from config import EXCEL_EXTENSIONS


def _list_shadow_copies() -> list[dict]:
    """Lista las shadow copies disponibles usando vssadmin."""
    try:
        result = subprocess.run(
            ["vssadmin", "list", "shadows"],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            return []

        shadows = []
        current = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if "Shadow Copy Volume" in line:
                match = re.search(r"(\\\\[?]\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy\d+)", line)
                if match:
                    current["path"] = match.group(1)
            elif "creation date" in line.lower() or "fecha de creacion" in line.lower():
                # Capturar la fecha despues del ":"
                parts = line.split(":", 1)
                if len(parts) > 1:
                    current["date"] = parts[1].strip()
            elif "Original Volume" in line or "Volumen original" in line:
                match = re.search(r"\(([A-Z]):\\\)", line, re.IGNORECASE)
                if match:
                    current["drive"] = match.group(1)

            # Cuando tenemos un shadow copy completo, guardarlo
            if "path" in current and "drive" in current:
                shadows.append(current)
                current = {}

        return shadows
    except (subprocess.TimeoutExpired, OSError):
        return []


def _format_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def search_shadow_copies(name_filter: str, original_path: str = "") -> list[dict]:
    """Busca un archivo Excel en las shadow copies disponibles.

    Requiere permisos de administrador para acceder a VSS.

    Args:
        name_filter: Nombre parcial del archivo a buscar.
        original_path: Ruta original del archivo (si se conoce).

    Returns:
        Lista de resultados encontrados en shadow copies.
    """
    results = []
    name_lower = name_filter.lower()

    shadows = _list_shadow_copies()
    if not shadows:
        return results

    for shadow in shadows:
        shadow_path = shadow.get("path", "")
        shadow_date = shadow.get("date", "?")

        # Si conocemos la ruta original, buscar directamente
        if original_path:
            # Convertir C:\Users\... a \\?\GLOBALROOT\...\Users\...
            rel_path = original_path
            if len(rel_path) > 2 and rel_path[1] == ":":
                rel_path = rel_path[2:]  # quitar "C:"

            shadow_file = shadow_path + rel_path
            if os.path.isfile(shadow_file):
                try:
                    stat = os.stat(shadow_file)
                    results.append({
                        "nombre": os.path.basename(shadow_file),
                        "ruta": shadow_file,
                        "tamano": _format_size(stat.st_size),
                        "fecha": shadow_date,
                        "origen": "Shadow Copy (VSS)",
                    })
                except OSError:
                    pass
        else:
            # Busqueda por nombre - intentar en rutas comunes
            drive = shadow.get("drive", "C")
            common_dirs = [
                "\\Users",
                "\\Documents and Settings",
            ]
            for cdir in common_dirs:
                search_root = shadow_path + cdir
                if not os.path.isdir(search_root):
                    continue
                try:
                    for dirpath, dirnames, filenames in os.walk(search_root):
                        # Limitar profundidad para no tardar demasiado
                        depth = dirpath.count("\\") - search_root.count("\\")
                        if depth > 5:
                            dirnames.clear()
                            continue
                        for fname in filenames:
                            ext = os.path.splitext(fname)[1].lower()
                            if ext not in EXCEL_EXTENSIONS:
                                continue
                            if name_lower not in fname.lower():
                                continue
                            filepath = os.path.join(dirpath, fname)
                            try:
                                stat = os.stat(filepath)
                                results.append({
                                    "nombre": fname,
                                    "ruta": filepath,
                                    "tamano": _format_size(stat.st_size),
                                    "fecha": shadow_date,
                                    "origen": "Shadow Copy (VSS)",
                                })
                            except OSError:
                                continue
                except OSError:
                    continue

    return results
