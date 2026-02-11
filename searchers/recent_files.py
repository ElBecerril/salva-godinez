"""Busqueda de archivos Excel en el historial reciente de Windows (.lnk)."""

import os
import struct
from datetime import datetime

from config import EXCEL_EXTENSIONS, RECENT_PATH


def _read_lnk_target(lnk_path: str) -> str | None:
    """Lee la ruta destino de un archivo .lnk (shortcut de Windows).

    Implementacion simplificada que extrae la ruta del LocalBasePath
    del formato Shell Link Binary (.lnk).
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
            if offset + 4 > len(content):
                return None
            link_info_size = struct.unpack_from("<I", content, offset)[0]
            link_info_start = offset

            if offset + 16 > len(content):
                return None
            # LocalBasePathOffset esta en offset+12 dentro de LinkInfo
            local_base_path_offset = struct.unpack_from("<I", content, offset + 16)[0]

            path_start = link_info_start + local_base_path_offset
            if path_start >= len(content):
                return None

            # Leer string null-terminated
            end = content.index(b"\x00", path_start)
            path = content[path_start:end].decode("ascii", errors="replace")
            if path and os.path.splitext(path)[1]:
                return path

        return None
    except (OSError, struct.error, ValueError):
        return None


def search_recent_files(name_filter: str = "") -> list[dict]:
    """Busca archivos Excel en el historial reciente de Windows.

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
            if ext not in EXCEL_EXTENSIONS:
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


def _format_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
