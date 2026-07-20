"""Busqueda de archivos Office en la papelera de reciclaje via PowerShell."""

import json
import os
import subprocess
from config import OFFICE_EXTENSIONS


def search_recycle_bin(name_filter: str = "") -> list[dict]:
    """Busca archivos Office en la papelera de reciclaje.

    Args:
        name_filter: Texto parcial para filtrar por nombre (sin extension).

    Returns:
        Lista de dicts con nombre, ruta_original, tamano y fecha.
    """
    ps_script = r"""
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$shell = New-Object -ComObject Shell.Application
$folder = $shell.NameSpace(0x0a)
$items = $folder.Items()
$results = @()
foreach ($item in $items) {
    $name = $folder.GetDetailsOf($item, 0)
    # OJO: la columna 1 devuelve la CARPETA original del archivo, no la ruta
    # completa. Hay que combinarla con el nombre (columna 0) para reconstruir
    # la ruta real.
    $originalFolder = $folder.GetDetailsOf($item, 1)
    $date = $folder.GetDetailsOf($item, 2)
    $size = $folder.GetDetailsOf($item, 3)
    # OJO: el archivo NO esta en su ruta original, esta renombrado dentro de
    # $Recycle.Bin (algo como C:\$Recycle.Bin\S-1-5-21-...\$RXXXXXX.docx).
    # $item.Path es esa ruta fisica y es la unica desde la que se puede copiar.
    $realPath = $item.Path
    $results += @{
        Name = $name
        OriginalFolder = $originalFolder
        DeleteDate = $date
        Size = $size
        RealPath = $realPath
    }
}
$results | ConvertTo-Json -Compress
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
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
            if ext not in OFFICE_EXTENSIONS:
                continue
            if name_lower and name_lower not in item_name.lower():
                continue
            original_folder = item.get("OriginalFolder", "")
            if original_folder:
                ruta = os.path.join(original_folder, item_name)
            else:
                ruta = "Desconocida"
            found.append({
                "nombre": item_name,
                "ruta": ruta,
                "ruta_fisica": item.get("RealPath", ""),
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
