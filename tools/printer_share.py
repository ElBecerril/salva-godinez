"""Compartir impresora en red: ver, compartir y dejar de compartir."""

import json
import subprocess

from rich.markup import escape
from rich.prompt import Prompt
from rich.table import Table

from tools import is_admin
from utils import ps_escape, console


# --- Logica (sin UI) ---


class PrinterQueryError(Exception):
    """Error real al consultar impresoras (no confundir con 'sin impresoras')."""


def _get_printers() -> list[dict]:
    """Obtiene la lista de impresoras instaladas via PowerShell.

    Devuelve una lista vacia tanto si el comando tuvo exito y no hay
    impresoras instaladas, como si la salida no pudo parsearse como JSON
    (por ejemplo, stdout vacio cuando Get-Printer no devuelve nada). Un
    fallo real de ejecucion (returncode != 0, timeout, error de SO) se
    señala levantando PrinterQueryError para que el llamador pueda
    distinguir "no tienes impresoras" de "ocurrio un error".
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Printer | Select-Object Name, DriverName, PortName, Shared, ShareName "
             "| ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        raise PrinterQueryError(str(e)) from e

    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip() or f"returncode {result.returncode}"
        raise PrinterQueryError(error)

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        # Stdout vacio (u otro contenido no-JSON) cuando el sistema no
        # tiene ninguna impresora instalada: no es un error, es "sin datos".
        return []

    if isinstance(data, dict):
        data = [data]
    return data


def _filter_unshared(printers: list[dict]) -> list[dict]:
    """Devuelve solo las impresoras que NO estan compartidas."""
    return [p for p in printers if not p.get("Shared", False)]


def _filter_shared(printers: list[dict]) -> list[dict]:
    """Devuelve solo las impresoras que SI estan compartidas."""
    return [p for p in printers if p.get("Shared", False)]


def _set_printer_shared(name: str, shared: bool, share_name: str = "") -> dict:
    """Comparte o deja de compartir una impresora via PowerShell.

    Devuelve un dict {"ok": bool, "error_kind": str, "message": str}.
    error_kind es uno de: "", "timeout", "os", "cmd" (comando fallo con
    returncode != 0). No imprime nada; el llamador decide como mostrarlo.
    """
    if shared:
        cmd = (f'Set-Printer -Name "{ps_escape(name)}" -Shared $true '
               f'-ShareName "{ps_escape(share_name)}"')
    else:
        cmd = f'Set-Printer -Name "{ps_escape(name)}" -Shared $false'

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error_kind": "timeout", "message": ""}
    except OSError as e:
        return {"ok": False, "error_kind": "os", "message": str(e)}

    if result.returncode == 0:
        return {"ok": True, "error_kind": "", "message": ""}

    error = result.stderr.strip() or result.stdout.strip()
    return {"ok": False, "error_kind": "cmd", "message": error}


# --- Interfaz de consola ---


def _show_shared_printers() -> None:
    """Muestra todas las impresoras con su estado de comparticion."""
    console.print("\n[bold cyan]Impresoras Instaladas[/bold cyan]\n")

    try:
        with console.status("[bold green]Obteniendo lista de impresoras..."):
            printers = _get_printers()
    except PrinterQueryError as e:
        console.print(f"[red]Error al obtener las impresoras del sistema: {escape(str(e))}[/red]")
        return

    if not printers:
        console.print("[yellow]No tienes impresoras instaladas en este equipo.[/yellow]")
        return

    table = Table()
    table.add_column("#", style="bold cyan", width=4, justify="right")
    table.add_column("Nombre", style="white")
    table.add_column("Controlador", style="dim")
    table.add_column("Compartida", justify="center")
    table.add_column("Nombre en Red", style="cyan")

    for i, p in enumerate(printers, 1):
        shared = p.get("Shared", False)
        shared_text = "[green]Si[/green]" if shared else "[dim]No[/dim]"
        share_name = p.get("ShareName", "") or ""
        table.add_row(
            str(i),
            escape(p.get("Name", "")),
            escape(p.get("DriverName", "")),
            shared_text,
            escape(share_name),
        )

    console.print(table)


def _share_printer() -> None:
    """Comparte una impresora en la red local."""
    console.print("\n[bold cyan]Compartir Impresora en Red[/bold cyan]\n")

    if not is_admin():
        console.print("[red]Se requieren permisos de administrador para compartir impresoras.[/red]")
        return

    try:
        with console.status("[bold green]Obteniendo lista de impresoras..."):
            printers = _get_printers()
    except PrinterQueryError as e:
        console.print(f"[red]Error al obtener las impresoras del sistema: {escape(str(e))}[/red]")
        return

    if not printers:
        console.print("[yellow]No tienes impresoras instaladas en este equipo.[/yellow]")
        return

    # Filtrar impresoras no compartidas
    unshared = _filter_unshared(printers)
    if not unshared:
        console.print("[yellow]Todas las impresoras ya estan compartidas.[/yellow]")
        return

    console.print("[bold]Impresoras disponibles para compartir:[/bold]")
    for i, p in enumerate(unshared, 1):
        console.print(f"  [cyan]{i}[/cyan] - {escape(p.get('Name', ''))}")

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

    with console.status("[bold green]Compartiendo impresora..."):
        result = _set_printer_shared(name, True, share_name)

    if result["ok"]:
        console.print(
            f"\n[bold green]Impresora '{escape(name)}' compartida como "
            f"'{escape(share_name)}'.[/bold green]"
        )
    elif result["error_kind"] == "timeout":
        console.print("[red]Timeout al intentar compartir la impresora.[/red]")
    elif result["error_kind"] == "os":
        console.print(f"[red]Error del sistema: {escape(result['message'])}[/red]")
    else:
        console.print(f"[red]Error al compartir: {escape(result['message'])}[/red]")


def _unshare_printer() -> None:
    """Deja de compartir una impresora en la red."""
    console.print("\n[bold cyan]Dejar de Compartir Impresora[/bold cyan]\n")

    if not is_admin():
        console.print("[red]Se requieren permisos de administrador para modificar impresoras.[/red]")
        return

    try:
        with console.status("[bold green]Obteniendo lista de impresoras..."):
            printers = _get_printers()
    except PrinterQueryError as e:
        console.print(f"[red]Error al obtener las impresoras del sistema: {escape(str(e))}[/red]")
        return

    if not printers:
        console.print("[yellow]No tienes impresoras instaladas en este equipo.[/yellow]")
        return

    # Filtrar impresoras compartidas
    shared = _filter_shared(printers)
    if not shared:
        console.print("[yellow]No hay impresoras compartidas.[/yellow]")
        return

    console.print("[bold]Impresoras compartidas:[/bold]")
    for i, p in enumerate(shared, 1):
        share_name = p.get("ShareName", "")
        console.print(f"  [cyan]{i}[/cyan] - {escape(p.get('Name', ''))} (Red: {escape(share_name)})")

    choice = Prompt.ask(
        "\n[bold]Selecciona la impresora[/bold]",
        choices=[str(i) for i in range(1, len(shared) + 1)],
    )
    printer = shared[int(choice) - 1]
    name = printer.get("Name", "")

    confirm = Prompt.ask(
        f"[bold]Dejar de compartir '{escape(name)}'?[/bold]",
        choices=["s", "n"], default="n",
    )
    if confirm != "s":
        console.print("[dim]Operacion cancelada.[/dim]")
        return

    with console.status("[bold green]Quitando comparticion..."):
        result = _set_printer_shared(name, False)

    if result["ok"]:
        console.print(f"\n[bold green]Impresora '{escape(name)}' ya no esta compartida.[/bold green]")
    elif result["error_kind"] == "timeout":
        console.print("[red]Timeout al intentar modificar la impresora.[/red]")
    elif result["error_kind"] == "os":
        console.print(f"[red]Error del sistema: {escape(result['message'])}[/red]")
    else:
        console.print(f"[red]Error: {escape(result['message'])}[/red]")


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
