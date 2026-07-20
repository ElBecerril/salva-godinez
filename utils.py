"""Funciones utilitarias compartidas entre searchers y tools."""

import ctypes
import os
import string
import struct

from rich.console import Console

# Instancia compartida de Console para todo el proyecto.
console = Console()


def ps_escape(value: str) -> str:
    """Escapa un valor para interpolacion segura en cadenas PowerShell con comillas dobles.

    Previene inyeccion de comandos via $(...), backticks y comillas.
    """
    # Orden: primero backtick (caracter de escape de PS), luego los demas
    value = value.replace("`", "``")
    value = value.replace('"', '`"')
    value = value.replace("$", "`$")
    return value


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


def read_lnk_target(lnk_path: str) -> str | None:
    """Lee la ruta destino de un archivo .lnk (shortcut de Windows).

    Implementacion basada en la especificacion [MS-SHLLINK] que extrae
    la ruta del LocalBasePath del formato Shell Link Binary (.lnk).
    """
    try:
        with open(lnk_path, "rb") as f:
            content = f.read()

        # Verificar magic number del formato .lnk
        if len(content) < 76:
            return None
        # HeaderSize debe ser 0x4C
        header_size = struct.unpack_from("<I", content, 0)[0]
        if header_size != 0x4C:
            return None

        # Flags en offset 0x14
        flags = struct.unpack_from("<I", content, 0x14)[0]
        has_link_target_id = flags & 0x01
        has_link_info = flags & 0x02

        offset = 0x4C  # Despues del header

        # Saltar LinkTargetIDList si existe
        if has_link_target_id:
            if offset + 2 > len(content):
                return None
            id_list_size = struct.unpack_from("<H", content, offset)[0]
            offset += 2 + id_list_size

        # Leer LinkInfo si existe
        if has_link_info:
            if offset + 20 > len(content):
                return None
            link_info_start = offset

            # LinkInfoFlags en offset+8: bit 0 = VolumeIDAndLocalBasePath
            link_info_flags = struct.unpack_from("<I", content, offset + 8)[0]
            if not (link_info_flags & 0x01):
                return None  # No hay ruta local (posible ruta de red)

            # LocalBasePathOffset esta en offset+16 dentro de LinkInfo
            local_base_path_offset = struct.unpack_from("<I", content, offset + 16)[0]

            path_start = link_info_start + local_base_path_offset
            if path_start >= len(content):
                return None

            # Leer string null-terminated (latin-1 para soportar acentos)
            end = content.index(b"\x00", path_start)
            path = content[path_start:end].decode("latin-1")
            if path and os.path.splitext(path)[1]:
                return path

        return None
    except (OSError, struct.error, ValueError):
        return None


def get_openpyxl():
    """Import lazy de openpyxl para no crashear si no esta instalado."""
    try:
        import openpyxl
        return openpyxl
    except ImportError:
        console.print(
            "[bold red]openpyxl no esta instalado.[/bold red]\n"
            "[dim]Ejecuta: pip install openpyxl[/dim]"
        )
        return None


def deduplicate(results: list[dict]) -> list[dict]:
    """Elimina resultados duplicados por ruta."""
    seen = set()
    unique = []
    for r in results:
        key = r.get("ruta", "")
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


# --- Ventana de consola de Windows ---------------------------------------
#
# El .exe se compila como aplicacion de CONSOLA para que el modo texto siga
# funcionando al doble clic. El precio es que, al abrir la interfaz grafica,
# quedaria una ventana negra de cmd detras. En vez de renunciar al modo texto
# compilando en modo "windowed", se esconde esa ventana mientras la GUI esta
# abierta y se vuelve a mostrar al salir.

SW_HIDE = 0
SW_SHOW = 5


def _consola_hwnd():
    """Handle de la ventana de consola, o None si no aplica (no-Windows)."""
    try:
        return ctypes.windll.kernel32.GetConsoleWindow()
    except (AttributeError, OSError):
        return None


def ocultar_consola() -> bool:
    """Esconde la ventana negra de consola. Devuelve True si lo logro."""
    hwnd = _consola_hwnd()
    if not hwnd:
        return False
    try:
        ctypes.windll.user32.ShowWindow(hwnd, SW_HIDE)
        return True
    except (AttributeError, OSError):
        return False


def mostrar_consola() -> bool:
    """Vuelve a mostrar la ventana de consola escondida."""
    hwnd = _consola_hwnd()
    if not hwnd:
        return False
    try:
        ctypes.windll.user32.ShowWindow(hwnd, SW_SHOW)
        return True
    except (AttributeError, OSError):
        return False
