"""Liberador de espacio: limpia temporales, cache y descargas antiguas."""

import ctypes
import os
import time

from rich.prompt import Prompt
from rich.table import Table

from tools import format_size, is_admin
from config import TEMP_CLEAN_PATHS, WINDOWS_UPDATE_CACHE, DOWNLOADS_PATH, OLD_DOWNLOAD_DAYS, SECONDS_PER_DAY
from utils import console



def _scan_dir(path: str) -> tuple[int, int]:
    """Escanea un directorio y retorna (tamano_total, num_archivos)."""
    total = 0
    count = 0
    if not os.path.isdir(path):
        return 0, 0
    for dirpath, _, filenames in os.walk(path):
        for fname in filenames:
            filepath = os.path.join(dirpath, fname)
            try:
                total += os.path.getsize(filepath)
                count += 1
            except OSError:
                continue
    return total, count


def _scan_temp_files() -> tuple[int, int, list[str]]:
    """Escanea archivos temporales."""
    total = 0
    count = 0
    paths = []
    for temp_path in TEMP_CLEAN_PATHS:
        if not temp_path or not os.path.isdir(temp_path):
            continue
        size, files = _scan_dir(temp_path)
        total += size
        count += files
        if size > 0:
            paths.append(temp_path)
    return total, count, paths


def _scan_update_cache() -> tuple[int, int]:
    """Escanea cache de Windows Update (requiere admin)."""
    if not is_admin():
        return 0, 0
    return _scan_dir(WINDOWS_UPDATE_CACHE)


def _scan_old_downloads(days: int = OLD_DOWNLOAD_DAYS) -> tuple[int, int, list[str]]:
    """Escanea descargas antiguas."""
    if not os.path.isdir(DOWNLOADS_PATH):
        return 0, 0, []

    cutoff = time.time() - (days * SECONDS_PER_DAY)
    total = 0
    count = 0
    files = []

    for fname in os.listdir(DOWNLOADS_PATH):
        filepath = os.path.join(DOWNLOADS_PATH, fname)
        if not os.path.isfile(filepath):
            continue
        try:
            stat = os.stat(filepath)
            if stat.st_mtime < cutoff:
                total += stat.st_size
                count += 1
                files.append(filepath)
        except OSError:
            continue

    return total, count, files


def _clean_dir(path: str) -> tuple[int, int]:
    """Elimina archivos de un directorio. Retorna (bytes_liberados, archivos_eliminados)."""
    freed = 0
    removed = 0
    if not os.path.isdir(path):
        return 0, 0
    for dirpath, _, filenames in os.walk(path, topdown=False):
        for fname in filenames:
            filepath = os.path.join(dirpath, fname)
            try:
                size = os.path.getsize(filepath)
                os.remove(filepath)
                freed += size
                removed += 1
            except OSError:
                continue
        # Intentar eliminar directorios vacios
        try:
            if dirpath != path:
                os.rmdir(dirpath)
        except OSError:
            pass
    return freed, removed


def _clean_files(file_list: list[str]) -> tuple[int, int]:
    """Elimina archivos especificos de una lista."""
    freed = 0
    removed = 0
    for filepath in file_list:
        try:
            size = os.path.getsize(filepath)
            os.remove(filepath)
            freed += size
            removed += 1
        except OSError:
            continue
    return freed, removed


def _empty_recycle_bin() -> bool:
    """Vacia la papelera de reciclaje."""
    try:
        # SHEmptyRecycleBinW(hwnd, pszRootPath, dwFlags)
        # SHERB_NOCONFIRMATION=1 | SHERB_NOPROGRESSUI=2 | SHERB_NOSOUND=4
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x07)
        return result == 0 or result == -2147418113  # S_OK or already empty
    except (AttributeError, OSError):
        return False


def disk_cleaner_menu() -> None:
    """Menu del liberador de espacio."""
    console.print("\n[bold cyan]Liberador de Espacio[/bold cyan]\n")

    # Escanear categorias
    with console.status("[bold green]Escaneando archivos temporales..."):
        temp_size, temp_count, temp_paths = _scan_temp_files()

    with console.status("[bold green]Escaneando cache de Windows Update..."):
        update_size, update_count = _scan_update_cache()

    with console.status("[bold green]Escaneando descargas antiguas..."):
        dl_size, dl_count, dl_files = _scan_old_downloads()

    # Tabla resumen
    table = Table(title="Espacio recuperable")
    table.add_column("#", style="bold cyan", width=4, justify="right")
    table.add_column("Categoria", style="bold")
    table.add_column("Archivos", justify="right")
    table.add_column("Tamano", justify="right", style="yellow")

    categories = []

    if temp_count > 0:
        categories.append(("Archivos temporales", temp_count, temp_size, "temp"))
        table.add_row(str(len(categories)), "Archivos temporales", str(temp_count), format_size(temp_size))

    if update_count > 0:
        categories.append(("Cache de Windows Update", update_count, update_size, "update"))
        table.add_row(str(len(categories)), "Cache de Windows Update", str(update_count), format_size(update_size))
    elif not is_admin():
        table.add_row("-", "Cache de Windows Update", "-", "[dim](requiere admin)[/dim]")

    if dl_count > 0:
        categories.append((f"Descargas antiguas (>{OLD_DOWNLOAD_DAYS} dias)", dl_count, dl_size, "downloads"))
        table.add_row(str(len(categories)), f"Descargas antiguas (>{OLD_DOWNLOAD_DAYS} dias)", str(dl_count), format_size(dl_size))

    categories.append(("Papelera de reciclaje", 0, 0, "recycle"))
    table.add_row(str(len(categories)), "Papelera de reciclaje", "-", "-")

    console.print(table)

    total = temp_size + update_size + dl_size
    if total == 0 and not categories:
        console.print("\n[bold green]No hay archivos para limpiar.[/bold green]")
        return

    console.print(f"\n[bold]Total estimado (sin papelera): {format_size(total)}[/bold]")

    # Preguntar cuales limpiar
    to_clean = Prompt.ask(
        "[bold]Numeros a limpiar (separados por coma, o 'todos')[/bold]",
        default="todos",
    ).strip().lower()

    if to_clean == "todos":
        selected = set(range(len(categories)))
    else:
        try:
            selected = {int(x.strip()) - 1 for x in to_clean.split(",")}
        except ValueError:
            console.print("[red]Entrada invalida.[/red]")
            return

    total_freed = 0
    total_removed = 0

    for idx in sorted(selected):
        if idx < 0 or idx >= len(categories):
            continue
        name, _, _, cat_type = categories[idx]
        console.print(f"\n[bold yellow]Limpiando: {name}...[/bold yellow]")

        if cat_type == "temp":
            for path in temp_paths:
                freed, removed = _clean_dir(path)
                total_freed += freed
                total_removed += removed
        elif cat_type == "update":
            freed, removed = _clean_dir(WINDOWS_UPDATE_CACHE)
            total_freed += freed
            total_removed += removed
        elif cat_type == "downloads":
            freed, removed = _clean_files(dl_files)
            total_freed += freed
            total_removed += removed
        elif cat_type == "recycle":
            if _empty_recycle_bin():
                console.print("  [green]Papelera vaciada.[/green]")
            else:
                console.print("  [dim]La papelera ya estaba vacia o no se pudo vaciar.[/dim]")

    console.print(f"\n[bold green]Limpieza completada![/bold green]")
    console.print(f"  Archivos eliminados: [bold]{total_removed}[/bold]")
    console.print(f"  Espacio liberado: [bold]{format_size(total_freed)}[/bold]")
