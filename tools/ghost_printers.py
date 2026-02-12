"""Limpiador de impresoras fantasma (duplicadas / inactivas)."""

import json
import re
import subprocess

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from tools import is_admin

console = Console()


def _get_printers() -> list[dict]:
    """Obtiene la lista de impresoras instaladas via PowerShell."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Printer | Select-Object Name, DriverName, PortName, Shared, PrinterStatus "
             "| ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        # PowerShell devuelve un objeto si solo hay una impresora
        if isinstance(data, dict):
            data = [data]
        return data
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
        return []


def _identify_ghosts(printers: list[dict]) -> list[dict]:
    """Identifica impresoras fantasma (copias duplicadas)."""
    ghost_pattern = re.compile(r"[\s\(]*(Copia\s+\d+|Copy\s+\d+)\s*\)?$", re.IGNORECASE)
    ghosts = []
    for p in printers:
        name = p.get("Name", "")
        if ghost_pattern.search(name):
            p["_ghost_reason"] = "Copia duplicada"
            ghosts.append(p)
    return ghosts


def _remove_printer(name: str) -> bool:
    """Elimina una impresora por nombre (requiere admin)."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f'Remove-Printer -Name "{name}"'],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def ghost_printers_menu() -> None:
    """Menu del limpiador de impresoras fantasma."""
    console.print("\n[bold cyan]Limpiador de Impresoras Fantasma[/bold cyan]\n")

    with console.status("[bold green]Obteniendo lista de impresoras..."):
        printers = _get_printers()

    if not printers:
        console.print("[yellow]No se pudieron obtener las impresoras del sistema.[/yellow]")
        return

    # Mostrar todas las impresoras
    table = Table(title="Impresoras instaladas")
    table.add_column("#", style="bold cyan", width=4, justify="right")
    table.add_column("Nombre", style="white")
    table.add_column("Driver", style="dim")
    table.add_column("Puerto", style="dim")
    table.add_column("Estado", style="yellow")

    ghosts = _identify_ghosts(printers)
    ghost_names = {g.get("Name", "") for g in ghosts}

    for i, p in enumerate(printers, 1):
        name = p.get("Name", "")
        marker = " [red](Fantasma)[/red]" if name in ghost_names else ""
        table.add_row(
            str(i),
            name + marker,
            p.get("DriverName", ""),
            p.get("PortName", ""),
            str(p.get("PrinterStatus", "")),
        )

    console.print(table)

    if not ghosts:
        console.print("\n[bold green]No se detectaron impresoras fantasma.[/bold green]")
        return

    console.print(f"\n[bold yellow]Se detectaron {len(ghosts)} impresora(s) fantasma.[/bold yellow]")

    if not is_admin():
        console.print("[red]Se requieren permisos de administrador para eliminar impresoras.[/red]")
        return

    confirm = Prompt.ask(
        "[bold]Eliminar impresoras fantasma?[/bold]",
        choices=["s", "n"], default="n",
    )
    if confirm != "s":
        return

    removed = 0
    for g in ghosts:
        name = g.get("Name", "")
        if _remove_printer(name):
            console.print(f"  [green]Eliminada:[/green] {name}")
            removed += 1
        else:
            console.print(f"  [red]No se pudo eliminar:[/red] {name}")

    console.print(f"\n[bold green]{removed} impresora(s) eliminada(s).[/bold green]")
