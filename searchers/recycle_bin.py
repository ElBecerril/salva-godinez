"""Busqueda de archivos (cualquier tipo) en la papelera de reciclaje via
PowerShell."""

import json
import os
import subprocess


def search_recycle_bin(name_filter: str = "") -> list[dict]:
    """Busca archivos en la papelera de reciclaje, sin importar su tipo.

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
            ruta_fisica = item.get("RealPath", "")
            # Windows por defecto oculta la extension conocida en el nombre
            # que muestra el Explorador (columna 0 de GetDetailsOf), asi que
            # `item_name` puede venir sin ella (ej. "presentacion" en vez de
            # "presentacion.pptx"). El archivo fisico dentro de $Recycle.Bin
            # SIEMPRE conserva su extension original sin importar ese ajuste,
            # asi que la extension real se saca de ahi, no del nombre visible.
            item_name = _apply_real_extension(item_name, ruta_fisica)
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
                "ruta_fisica": ruta_fisica,
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


def _apply_real_extension(display_name: str, ruta_fisica: str) -> str:
    """Corrige `display_name` para que muestre la extension real del archivo.

    `display_name` viene de GetDetailsOf(item, 0), que respeta la opcion de
    Windows "ocultar las extensiones de archivos conocidos" (activada por
    defecto) y puede no traer extension. `ruta_fisica` es la ruta dentro de
    $Recycle.Bin (ej. C:\\$Recycle.Bin\\S-1-5-21-...\\$RA1B2C3.pptx), que
    SIEMPRE conserva la extension original sin importar esa opcion.

    Si ruta_fisica esta vacia o no tiene extension (carpetas borradas, o
    archivos genuinamente sin extension), se devuelve display_name tal cual.
    """
    if not display_name or not ruta_fisica:
        return display_name
    # ruta_fisica siempre es una ruta de Windows (separador `\`), sin
    # importar el SO donde corra este codigo (en Linux, en desarrollo, se
    # prueba con datos falsos; os.path.basename ahi NO separa por `\` y
    # devolveria la ruta completa). Se calcula el nombre base a mano en vez
    # de depender de os.path/ntpath para que el resultado sea el mismo en
    # cualquier plataforma.
    last_sep = max(ruta_fisica.rfind("\\"), ruta_fisica.rfind("/"))
    base_name = ruta_fisica[last_sep + 1:]
    real_ext = _get_extension(base_name)
    if not real_ext:
        return display_name
    if display_name.lower().endswith(real_ext):
        return display_name
    return display_name + real_ext
