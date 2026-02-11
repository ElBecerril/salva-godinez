"""Busqueda de archivos Excel en la papelera de reciclaje via PowerShell."""

import json
import subprocess
from config import EXCEL_EXTENSIONS


def search_recycle_bin(name_filter: str = "") -> list[dict]:
    """Busca archivos Excel en la papelera de reciclaje.

    Args:
        name_filter: Texto parcial para filtrar por nombre (sin extension).

    Returns:
        Lista de dicts con nombre, ruta_original, tamano y fecha.
    """
    ps_script = r"""
$shell = New-Object -ComObject Shell.Application
$folder = $shell.NameSpace(0x0a)
$items = $folder.Items()
$results = @()
foreach ($item in $items) {
    $name = $folder.GetDetailsOf($item, 0)
    $originalPath = $folder.GetDetailsOf($item, 1)
    $date = $folder.GetDetailsOf($item, 2)
    $size = $folder.GetDetailsOf($item, 3)
    $results += @{
        Name = $name
        OriginalPath = $originalPath
        DeleteDate = $date
        Size = $size
    }
}
$results | ConvertTo-Json -Compress
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            return []

        output = result.stdout.strip()
        if not output:
            return []

        data = json.loads(output)
        # PowerShell devuelve un objeto si es un solo item, lista si son varios
        if isinstance(data, dict):
            data = [data]

        found = []
        name_lower = name_filter.lower()
        for item in data:
            item_name = item.get("Name", "")
            ext = _get_extension(item_name)
            if ext not in EXCEL_EXTENSIONS:
                continue
            if name_lower and name_lower not in item_name.lower():
                continue
            found.append({
                "nombre": item_name,
                "ruta": item.get("OriginalPath", "Desconocida"),
                "tamano": item.get("Size", "?"),
                "fecha": item.get("DeleteDate", "?"),
                "origen": "Papelera de reciclaje",
            })
        return found

    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return []


def _get_extension(filename: str) -> str:
    dot = filename.rfind(".")
    if dot == -1:
        return ""
    return filename[dot:].lower()
