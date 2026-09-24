"""Busqueda de archivos Office por nombre en todos los discos."""

import os
import time
from datetime import datetime

from config import OFFICE_EXTENSIONS, RECENT_DAYS, SECONDS_PER_DAY, SKIP_DIRS
from utils import format_size as _format_size, get_drives as _get_drives


# Antes, un error de permisos en os.walk (onerror=lambda e: None) se tragaba
# en silencio: la busqueda devolvia 0 y el usuario concluia "no hay nada"
# cuando en realidad NO SE PUDO revisar esa carpeta. Mismo pecado que
# shadow_copies.py antes de v2.9.0, mismo remedio en espiritu: avisar via
# `ultimo_motivo()`. Pero AQUI el criterio no puede ser "contar cuantas
# carpetas fallaron": en un Windows real, un os.walk sobre C:\ SIEMPRE topa
# con decenas de carpetas con acceso denegado aunque el disco este sano —
# perfiles de OTROS usuarios, C:\Program Files\WindowsApps, subcarpetas de
# ProgramData\Microsoft, y las junctions de compatibilidad de cada perfil
# ("Datos de programa", "Menu Inicio", "Cookies", "Plantillas"...) que
# tienen un ACL de DENEGAR listado para Everyone, INCLUSO para
# administrador. Con un umbral (o con "0 resultados + >0 errores") el aviso
# saldria en practicamente toda busqueda, y el consejo "abre como
# administrador" seria FALSO para esas carpetas (admin no las desbloquea) —
# eso le ensena al usuario a ignorar el aviso, que es peor que no avisar.
#
# El unico caso en que de verdad "no se pudo buscar" (y donde abrir como
# administrador, o desbloquear la unidad, SI puede arreglarlo) es que no se
# pudiera listar la RAIZ de una unidad completa: BitLocker bloqueado, disco
# con permisos rotos, unidad de red caida. Ahi la unidad ENTERA queda sin
# revisar, a diferencia de una subcarpeta puntual bloqueada por ACL. Por eso
# `_al_fallar` compara la ruta que fallo contra la raiz de la unidad que se
# esta recorriendo, y el motivo/aviso dependen SOLO de esas fallas de raiz.
_MOTIVO_OK = ""
_MOTIVO_SIN_PERMISOS = "sin_permisos"

_ultimo_motivo = _MOTIVO_OK
_dirs_sin_acceso = 0
_unidades_sin_acceso: list[str] = []


def ultimo_motivo() -> str:
    """Motivo de la ultima corrida: "" (bien) o "sin_permisos"."""
    return _ultimo_motivo


def dirs_sin_acceso() -> int:
    """Cuantas carpetas (de cualquier tipo, no solo raices de unidad) no se
    pudieron revisar por falta de permiso en la ultima corrida. Informativo
    nada mas: NO decide `ultimo_motivo()` (ver comentario de arriba)."""
    return _dirs_sin_acceso


def unidades_sin_acceso() -> list[str]:
    """Unidades cuya RAIZ no se pudo listar en la ultima corrida (la unidad
    completa quedo sin revisar). Esto es lo que de verdad decide
    `ultimo_motivo() == "sin_permisos"`."""
    return list(_unidades_sin_acceso)


def _file_info(filepath: str) -> dict | None:
    try:
        stat = os.stat(filepath)
        return {
            "nombre": os.path.basename(filepath),
            "ruta": filepath,
            "tamano": _format_size(stat.st_size),
            "fecha": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "tamano_bytes": stat.st_size,
            "mtime": stat.st_mtime,
        }
    except OSError:
        return None


def search_by_name(name_filter: str, progress_callback=None) -> list[dict]:
    """Busca archivos Office por nombre parcial en todos los discos.

    Args:
        name_filter: Texto parcial del nombre del archivo (sin extension).
        progress_callback: Funcion opcional que recibe el directorio actual.

    Returns:
        Lista de resultados con nombre, ruta, tamano, fecha.
    """
    global _ultimo_motivo, _dirs_sin_acceso, _unidades_sin_acceso
    _ultimo_motivo = _MOTIVO_OK
    sin_acceso = 0
    unidades_fallidas: list[str] = []

    name_lower = name_filter.lower()
    results = []
    drives = _get_drives()

    for drive in drives:
        raiz_norm = os.path.normcase(os.path.normpath(drive))

        def _al_fallar(err: OSError, _drive=drive, _raiz_norm=raiz_norm) -> None:
            nonlocal sin_acceso
            # winerror 5 = "Acceso denegado" en Windows; PermissionError cubre el
            # resto (incluye el equivalente en Linux, util para las pruebas).
            if not (isinstance(err, PermissionError) or getattr(err, "winerror", None) == 5):
                return
            sin_acceso += 1
            # os.walk pasa como filename la carpeta que fallo al listar; si
            # es la RAIZ de esta unidad, la unidad entera quedo sin revisar
            # (a diferencia de una subcarpeta puntual bloqueada por ACL).
            fallo_norm = os.path.normcase(os.path.normpath(getattr(err, "filename", "") or ""))
            if fallo_norm == _raiz_norm and _drive not in unidades_fallidas:
                unidades_fallidas.append(_drive)

        for dirpath, dirnames, filenames in os.walk(drive, topdown=True,
                                                     onerror=_al_fallar):
            # Saltar directorios del sistema que causan problemas
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            try:
                if progress_callback:
                    progress_callback(dirpath)

                for fname in filenames:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in OFFICE_EXTENSIONS:
                        continue
                    if name_lower and name_lower not in fname.lower():
                        continue
                    filepath = os.path.join(dirpath, fname)
                    info = _file_info(filepath)
                    if info:
                        info["origen"] = f"Disco ({drive.rstrip(os.sep)})"
                        results.append(info)
            except (PermissionError, OSError):
                continue

    _dirs_sin_acceso = sin_acceso
    _unidades_sin_acceso = unidades_fallidas
    if unidades_fallidas:
        _ultimo_motivo = _MOTIVO_SIN_PERMISOS

    return results


def search_recent_excel(days: int = RECENT_DAYS, progress_callback=None) -> list[dict]:
    """Busca todos los archivos Office modificados en los ultimos N dias.

    Args:
        days: Numero de dias hacia atras para buscar.
        progress_callback: Funcion opcional que recibe el directorio actual.

    Returns:
        Lista de resultados.
    """
    global _ultimo_motivo, _dirs_sin_acceso, _unidades_sin_acceso
    _ultimo_motivo = _MOTIVO_OK
    sin_acceso = 0
    unidades_fallidas: list[str] = []

    cutoff = time.time() - (days * SECONDS_PER_DAY)
    results = []
    drives = _get_drives()

    for drive in drives:
        raiz_norm = os.path.normcase(os.path.normpath(drive))

        def _al_fallar(err: OSError, _drive=drive, _raiz_norm=raiz_norm) -> None:
            nonlocal sin_acceso
            if not (isinstance(err, PermissionError) or getattr(err, "winerror", None) == 5):
                return
            sin_acceso += 1
            fallo_norm = os.path.normcase(os.path.normpath(getattr(err, "filename", "") or ""))
            if fallo_norm == _raiz_norm and _drive not in unidades_fallidas:
                unidades_fallidas.append(_drive)

        for dirpath, dirnames, filenames in os.walk(drive, topdown=True,
                                                     onerror=_al_fallar):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            try:
                if progress_callback:
                    progress_callback(dirpath)

                for fname in filenames:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in OFFICE_EXTENSIONS:
                        continue
                    filepath = os.path.join(dirpath, fname)
                    info = _file_info(filepath)
                    if info and info["mtime"] >= cutoff:
                        info["origen"] = f"Disco ({drive.rstrip(os.sep)})"
                        results.append(info)
            except (PermissionError, OSError):
                continue

    _dirs_sin_acceso = sin_acceso
    _unidades_sin_acceso = unidades_fallidas
    if unidades_fallidas:
        _ultimo_motivo = _MOTIVO_SIN_PERMISOS

    # Ordenar por fecha de modificacion, mas reciente primero
    results.sort(key=lambda x: x["mtime"], reverse=True)
    return results
