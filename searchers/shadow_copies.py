"""Busqueda de archivos Office en Shadow Copies (VSS) de Windows."""

import os
import re
import subprocess

from config import OFFICE_EXTENSIONS
from utils import format_size as _format_size


# Por que la ultima corrida no encontro copias de seguridad. La UI lo consulta
# con `ultimo_motivo()` para no repetir el pecado de v2.8.2 en el desinfectante
# de USB: devolver una lista vacia sin decir POR QUE. Un usuario que no abrio la
# app como administrador merece leer "necesitas administrador", no un
# "no encontre nada" que suena a que no habia respaldo.
_MOTIVO_OK = ""
_MOTIVO_SIN_PERMISOS = "sin_permisos"
_MOTIVO_SIN_COPIAS = "sin_copias"
_MOTIVO_ERROR = "error"

_ultimo_motivo = _MOTIVO_OK


def ultimo_motivo() -> str:
    """Motivo de la ultima corrida: "" (bien), sin_permisos, sin_copias, error."""
    return _ultimo_motivo


def _list_shadow_copies() -> list[dict]:
    """Lista las shadow copies disponibles usando vssadmin."""
    global _ultimo_motivo
    _ultimo_motivo = _MOTIVO_OK
    try:
        result = subprocess.run(
            ["vssadmin", "list", "shadows"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            # vssadmin exige elevacion; sin ella imprime "No tiene los permisos
            # adecuados..." y sale con codigo != 0. Verificado en la VM (Win11
            # es-MX): sin admin la etapa entera moria en silencio y el usuario
            # concluia que no habia respaldos.
            salida = ((result.stdout or "") + (result.stderr or "")).lower()
            if (
                "permis" in salida            # ES: "permisos"; EN: "permission"
                or "elevad" in salida         # ES: "privilegios elevados"
                or "administrat" in salida    # EN: "administrator"
                or "denied" in salida
                or "denegado" in salida
            ):
                _ultimo_motivo = _MOTIVO_SIN_PERMISOS
            else:
                _ultimo_motivo = _MOTIVO_ERROR
            return []

        shadows = []
        current = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            # El parseo se ancla al CONTENIDO, no a las etiquetas: vssadmin
            # traduce los rotulos al idioma de Windows ("Shadow Copy Volume" ->
            # "Volumen de instantaneas", "Original Volume" -> "Volumen
            # original"), pero la ruta \\?\GLOBALROOT\... y el "(C:)" salen
            # igual en cualquier idioma.
            #
            # Anclarse a la etiqueta inglesa fue justo el bug: en Windows en
            # espanol —o sea el de TODO el publico de esta app— la linea de la
            # ruta nunca matcheaba, "path" jamas se seteaba y la condicion de
            # guardado de abajo nunca se cumplia, asi que el rescate por
            # Copias de seguridad devolvia [] en silencio. v2.8.1 arreglo el
            # regex de la unidad, pero esta mitad seguia rota; se cazo
            # corriendo vssadmin de verdad en la VM en es-MX.
            match_path = re.search(
                r"(\\\\[?]\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy\d+)", line
            )
            match_drive = re.search(r"\(([A-Za-z]):\)", line)
            if match_path:
                current["path"] = match_path.group(1)
            elif match_drive:
                current["drive"] = match_drive.group(1)
            elif (
                "creation time" in line.lower()
                or "creation date" in line.lower()
                or "creación" in line.lower()
                or "creacion" in line.lower()
            ):
                # EN: "...at creation time: <fecha>"
                # ES: "Contenia N instantaneas en el momento de su creacion: <fecha>"
                parts = line.split(":", 1)
                if len(parts) > 1:
                    current["date"] = parts[1].strip()

            # Cuando tenemos un shadow copy completo, guardarlo
            if "path" in current and "drive" in current:
                shadows.append(current)
                current = {}

        if not shadows:
            _ultimo_motivo = _MOTIVO_SIN_COPIAS
        return shadows
    except (subprocess.TimeoutExpired, OSError):
        _ultimo_motivo = _MOTIVO_ERROR
        return []


def search_shadow_copies(name_filter: str, original_path: str = "") -> list[dict]:
    """Busca un archivo Office en las shadow copies disponibles.

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
            # Si la shadow copy es de otra unidad, no aplica: evita
            # reportar como "copia de seguridad" un archivo de otro volumen
            # que por casualidad tiene la misma ruta relativa.
            shadow_drive = shadow.get("drive", "").strip(":").upper()
            if len(original_path) > 1 and original_path[1] == ":" and shadow_drive:
                if original_path[0].upper() != shadow_drive:
                    continue

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
                        "origen": "Copia de seguridad de Windows",
                    })
                except OSError:
                    pass
        else:
            # Busqueda por nombre - intentar en rutas comunes
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
                            if ext not in OFFICE_EXTENSIONS:
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
                                    "origen": "Copia de seguridad de Windows",
                                })
                            except OSError:
                                continue
                except OSError:
                    continue

    return results
