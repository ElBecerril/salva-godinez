"""Compartir impresora en red: ver, compartir y dejar de compartir."""

import json
import subprocess

from rich.prompt import Prompt
from rich.table import Table

from tools import is_admin
from utils import ps_escape, console



def _get_printers() -> list[dict]:
    """Obtiene la lista de impresoras instaladas via PowerShell."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Printer | Select-Object Name, DriverName, PortName, Shared, ShareName "
             "| ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]
        return data
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
        return []


def _show_shared_printers() -> None:
    """Muestra todas las impresoras con su estado de comparticion."""
    console.print("\n[bold cyan]Impresoras Instaladas[/bold cyan]\n")

    with console.status("[bold green]Obteniendo lista de impresoras..."):
        printers = _get_printers()

    if not printers:
        console.print("[yellow]No se pudieron obtener las impresoras del sistema.[/yellow]")
        return

    table = Table()
    table.add_column("#", style="bold cyan", width=4, justify="right")
    table.add_column("Nombre", style="white")
    table.add_column("Driver", style="dim")
    table.add_column("Compartida", justify="center")
    table.add_column("Nombre en Red", style="cyan")

    for i, p in enumerate(printers, 1):
        shared = p.get("Shared", False)
        shared_text = "[green]Si[/green]" if shared else "[dim]No[/dim]"
        share_name = p.get("ShareName", "") or ""
        table.add_row(
            str(i),
            p.get("Name", ""),
            p.get("DriverName", ""),
            shared_text,
            share_name,
        )

    console.print(table)


def _share_printer() -> None:
    """Comparte una impresora en la red local."""
    console.print("\n[bold cyan]Compartir Impresora en Red[/bold cyan]\n")

    if not is_admin():
        console.print("[red]Se requieren permisos de administrador para compartir impresoras.[/red]")
        return

    with console.status("[bold green]Obteniendo lista de impresoras..."):
        printers = _get_printers()

    if not printers:
        console.print("[yellow]No se pudieron obtener las impresoras del sistema.[/yellow]")
        return

    # Filtrar impresoras no compartidas
    unshared = [p for p in printers if not p.get("Shared", False)]
    if not unshared:
        console.print("[yellow]Todas las impresoras ya estan compartidas.[/yellow]")
        return

    console.print("[bold]Impresoras disponibles para compartir:[/bold]")
    for i, p in enumerate(unshared, 1):
        console.print(f"  [cyan]{i}[/cyan] - {p.get('Name', '')}")

    choice = Prompt.ask(
        "\n[bold]Selecciona la impresora[/bold]",
        choices=[str(i) for i in range(1, len(unshared) + 1)],
    )
    printer = unshared[int(choice) - 1]
    name = printer.get("Name", "")

    share_name = Prompt.ask(
        "[bold]Nombre para compartir en red[/bold]",
        default=name.replace(" ", "_")[:20],
    ).strip()
    if not share_name:
        console.print("[red]Nombre de red invalido.[/red]")
        return

    try:
        with console.status("[bold green]Compartiendo impresora..."):
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f'Set-Printer -Name "{ps_escape(name)}" -Shared $true -ShareName "{ps_escape(share_name)}"'],
                capture_output=True, text=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

        if result.returncode == 0:
            console.print(
                f"\n[bold green]Impresora '{name}' compartida como '{share_name}'.[/bold green]"
            )
        else:
            error = result.stderr.strip() or result.stdout.strip()
            console.print(f"[red]Error al compartir: {error}[/red]")
    except subprocess.TimeoutExpired:
        console.print("[red]Timeout al intentar compartir la impresora.[/red]")
    except OSError as e:
        console.print(f"[red]Error del sistema: {e}[/red]")


def _unshare_printer() -> None:
    """Deja de compartir una impresora en la red."""
    console.print("\n[bold cyan]Dejar de Compartir Impresora[/bold cyan]\n")

    if not is_admin():
        console.print("[red]Se requieren permisos de administrador para modificar impresoras.[/red]")
        return

    with console.status("[bold green]Obteniendo lista de impresoras..."):
        printers = _get_printers()

    if not printers:
        console.print("[yellow]No se pudieron obtener las impresoras del sistema.[/yellow]")
        return

    # Filtrar impresoras compartidas
    shared = [p for p in printers if p.get("Shared", False)]
    if not shared:
        console.print("[yellow]No hay impresoras compartidas.[/yellow]")
        return

    console.print("[bold]Impresoras compartidas:[/bold]")
    for i, p in enumerate(shared, 1):
        share_name = p.get("ShareName", "")
        console.print(f"  [cyan]{i}[/cyan] - {p.get('Name', '')} (Red: {share_name})")

    choice = Prompt.ask(
        "\n[bold]Selecciona la impresora[/bold]",
        choices=[str(i) for i in range(1, len(shared) + 1)],
    )
    printer = shared[int(choice) - 1]
    name = printer.get("Name", "")

    confirm = Prompt.ask(
        f"[bold]Dejar de compartir '{name}'?[/bold]",
        choices=["s", "n"], default="n",
    )
    if confirm != "s":
        console.print("[dim]Operacion cancelada.[/dim]")
        return

    try:
        with console.status("[bold green]Quitando comparticion..."):
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f'Set-Printer -Name "{ps_escape(name)}" -Shared $false'],
                capture_output=True, text=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

        if result.returncode == 0:
            console.print(f"\n[bold green]Impresora '{name}' ya no esta compartida.[/bold green]")
        else:
            error = result.stderr.strip() or result.stdout.strip()
            console.print(f"[red]Error: {error}[/red]")
    except subprocess.TimeoutExpired:
        console.print("[red]Timeout al intentar modificar la impresora.[/red]")
    except OSError as e:
        console.print(f"[red]Error del sistema: {e}[/red]")


def printer_share_menu() -> None:
    """Sub-menu de comparticion de impresoras en red."""
    while True:
        console.print(
            "\n[bold cyan]Compartir Impresora en Red[/bold cyan]\n"
            "  [bold]1[/bold] - Ver impresoras\n"
            "  [bold]2[/bold] - Compartir impresora\n"
            "  [bold]3[/bold] - Dejar de compartir\n"
            "  [bold]0[/bold] - Volver"
        )
        choice = Prompt.ask("[bold cyan]Opcion[/bold cyan]", default="0")

        if choice == "1":
            _show_shared_printers()
        elif choice == "2":
            _share_printer()
        elif choice == "3":
            _unshare_printer()
        elif choice == "0":
            break
        else:
            console.print("[red]Opcion no valida.[/red]")
