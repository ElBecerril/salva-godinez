"""Respaldo rapido a USB: copia Desktop y Documents con progreso."""

import os
import platform
import shutil
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TransferSpeedColumn
from rich.prompt import Prompt
from rich.table import Table

from tools import get_removable_drives, format_size
from config import BACKUP_SOURCES

console = Console()


def _calculate_backup_size(sources: list[str]) -> tuple[int, int]:
    """Calcula tamano total y numero de archivos a respaldar.

    Returns:
        (total_bytes, file_count)
    """
    total = 0
    count = 0
    for source in sources:
        if not os.path.isdir(source):
            continue
        for dirpath, _, filenames in os.walk(source):
            for fname in filenames:
                filepath = os.path.join(dirpath, fname)
                try:
                    total += os.path.getsize(filepath)
                    count += 1
                except OSError:
                    continue
    return total, count


def _copy_with_progress(sources: list[str], dest_base: str) -> tuple[int, int]:
    """Copia archivos con barra de progreso Rich.

    Returns:
        (files_copied, files_skipped)
    """
    copied = 0
    skipped = 0

    # Contar total para progreso
    total_size, total_files = _calculate_backup_size(sources)

    with Progress(
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TransferSpeedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Copiando...", total=total_size)

        for source in sources:
            if not os.path.isdir(source):
                continue
            source_name = os.path.basename(source)

            for dirpath, _, filenames in os.walk(source):
                rel_dir = os.path.relpath(dirpath, source)
                dest_dir = os.path.join(dest_base, source_name, rel_dir)
                os.makedirs(dest_dir, exist_ok=True)

                for fname in filenames:
                    src_file = os.path.join(dirpath, fname)
                    dst_file = os.path.join(dest_dir, fname)

                    try:
                        src_size = os.path.getsize(src_file)

                        # Skip si es identico (mismo tamano y fecha)
                        if os.path.exists(dst_file):
                            dst_stat = os.stat(dst_file)
                            src_stat = os.stat(src_file)
                            if (dst_stat.st_size == src_stat.st_size and
                                    abs(dst_stat.st_mtime - src_stat.st_mtime) < 2):
                                skipped += 1
                                progress.advance(task, src_size)
                                continue

                        shutil.copy2(src_file, dst_file)
                        copied += 1
                        progress.advance(task, src_size)
                    except OSError:
                        progress.advance(task, 0)
                        continue

    return copied, skipped


def usb_backup_menu() -> None:
    """Menu de respaldo rapido a USB."""
    console.print("\n[bold cyan]Respaldo Rapido a USB[/bold cyan]\n")

    drives = get_removable_drives()
    if not drives:
        console.print("[yellow]No se detectaron unidades USB conectadas.[/yellow]")
        return

    console.print("[bold]Unidades USB detectadas:[/bold]")
    for i, drive in enumerate(drives, 1):
        console.print(f"  [cyan]{i}[/cyan] - {drive}")

    if len(drives) == 1:
        drive = drives[0]
    else:
        choice = Prompt.ask(
            "[bold]Selecciona la unidad destino[/bold]",
            choices=[str(i) for i in range(1, len(drives) + 1)],
        )
        drive = drives[int(choice) - 1]

    # Calcular tamano
    valid_sources = [s for s in BACKUP_SOURCES if os.path.isdir(s)]
    if not valid_sources:
        console.print("[red]No se encontraron las carpetas de origen (Desktop, Documents).[/red]")
        return

    with console.status("[bold green]Calculando tamano del respaldo..."):
        total_bytes, file_count = _calculate_backup_size(valid_sources)

    # Verificar espacio disponible
    try:
        free = shutil.disk_usage(drive).free
    except OSError:
        free = 0

    # Resumen
    table = Table(title="Resumen del respaldo")
    table.add_column("", style="bold")
    table.add_column("")
    table.add_row("Carpetas de origen", ", ".join(os.path.basename(s) for s in valid_sources))
    table.add_row("Archivos a copiar", str(file_count))
    table.add_row("Tamano total", format_size(total_bytes))
    table.add_row("Espacio libre en USB", format_size(free))
    console.print(table)

    if total_bytes > free:
        console.print("\n[bold red]No hay suficiente espacio en la USB.[/bold red]")
        return

    # Destino
    hostname = platform.node()
    date_str = datetime.now().strftime("%Y%m%d")
    dest_base = os.path.join(drive, f"Respaldo_{hostname}_{date_str}")

    console.print(f"\n[dim]Destino: {dest_base}[/dim]")

    confirm = Prompt.ask(
        "[bold]Iniciar respaldo?[/bold]",
        choices=["s", "n"], default="s",
    )
    if confirm != "s":
        return

    copied, skipped = _copy_with_progress(valid_sources, dest_base)

    console.print(f"\n[bold green]Respaldo completado![/bold green]")
    console.print(f"  Archivos copiados: [bold]{copied}[/bold]")
    if skipped:
        console.print(f"  Archivos sin cambios (omitidos): [dim]{skipped}[/dim]")
    console.print(f"  Ubicacion: [bold]{dest_base}[/bold]")
