"""Limpiador de impresoras fantasma (duplicadas / inactivas)."""

import json
import re
import subprocess

from rich.prompt import Prompt
from rich.table import Table

from tools import is_admin
from utils import ps_escape, console



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
             "Get-Printer | Select-Object Name, DriverName, PortName, Shared, PrinterStatus "
             "| ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=30,
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

    # PowerShell devuelve un objeto si solo hay una impresora
    if isinstance(data, dict):
        data = [data]
    return data


# Patrones de deteccion de impresoras "fantasma":
#   1. "Copia N" / "Copy N" al final del nombre (con o sin parentesis),
#      p.ej. "HP LaserJet Copia 2", "Epson L3150 (Copy 3)".
#   2. Sufijo numerico entre parentesis al final SIN la palabra "copia",
#      p.ej. "HP LaserJet (2)", "Epson L3150(3)". Se exige que el numero
#      vaya entre parentesis para evitar falsos positivos con nombres de
#      impresora legitimos que terminan en un numero de modelo
#      (ej. "HP LaserJet 4050", "Epson L3150").
#   3. Impresoras redirigidas de sesion RDP / Terminal Services, cuyo
#      nombre incluye "redirected" o "redirigid[oa]" (con o sin "s" de
#      plural), p.ej. "HP LaserJet (redirected 2)", "Epson (redirigida)".
#
# Limitaciones conocidas (fuera de alcance para evitar falsos positivos):
#   - Duplicados renombrados sin ningun marcador reconocible (p.ej. el
#     usuario le puso "HP LaserJet 2" manualmente, sin parentesis).
#   - Otras palabras de "copia" en otros idiomas distintos de ES/EN.
#   - Nombres con "duplicado"/"clon"/"backup" u otras convenciones no
#     estandar no se detectan como fantasma.
_GHOST_COPY_PATTERN = re.compile(r"[\s\(]*(?:copia|copy)\s+\d+\s*\)?$", re.IGNORECASE)
_GHOST_BARE_SUFFIX_PATTERN = re.compile(r"\(\s*\d+\s*\)\s*$")
_GHOST_REDIRECTED_PATTERN = re.compile(r"redirect(?:ed)?|redirigid[oa]s?", re.IGNORECASE)


def _identify_ghosts(printers: list[dict]) -> list[dict]:
    """Identifica impresoras fantasma (copias duplicadas o redirigidas)."""
    ghosts = []
    for p in printers:
        name = p.get("Name", "")
        if _GHOST_COPY_PATTERN.search(name):
            p["_ghost_reason"] = "Copia duplicada"
            ghosts.append(p)
        elif _GHOST_BARE_SUFFIX_PATTERN.search(name):
            p["_ghost_reason"] = "Sufijo numerico entre parentesis (posible duplicado)"
            ghosts.append(p)
        elif _GHOST_REDIRECTED_PATTERN.search(name):
            p["_ghost_reason"] = "Impresora redirigida (sesion RDP/Terminal Services)"
            ghosts.append(p)
    return ghosts


def _remove_printer(name: str) -> bool:
    """Elimina una impresora por nombre (requiere admin)."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f'Remove-Printer -Name "{ps_escape(name)}"'],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def ghost_printers_menu() -> None:
    """Menu del limpiador de impresoras fantasma."""
    console.print("\n[bold cyan]Limpiador de Impresoras Fantasma[/bold cyan]\n")

    try:
        with console.status("[bold green]Obteniendo lista de impresoras..."):
            printers = _get_printers()
    except PrinterQueryError as e:
        console.print(f"[red]Error al obtener las impresoras del sistema: {e}[/red]")
        return

    if not printers:
        console.print("[yellow]No tienes impresoras instaladas en este equipo.[/yellow]")
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
