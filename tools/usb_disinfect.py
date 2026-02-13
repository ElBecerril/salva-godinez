"""Desinfectante de USB: detecta y limpia amenazas comunes."""

import os
import subprocess

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from tools import get_removable_drives
from utils import read_lnk_target as _read_lnk_target

console = Console()

# Nombres sospechosos comunes en USBs infectados
SUSPICIOUS_FILES = {"autorun.inf", "desktop.ini.exe", "recycler.exe", "ravmon.exe"}
SUSPICIOUS_EXTENSIONS = {".exe", ".scr", ".bat", ".cmd", ".vbs", ".wsf", ".pif", ".com"}


def _is_suspicious_lnk(lnk_path: str, drive: str) -> bool:
    """Verifica si un .lnk apunta a un ejecutable (patron de virus USB)."""
    target = _read_lnk_target(lnk_path)
    if not target:
        return False
    ext = os.path.splitext(target)[1].lower()
    return ext in SUSPICIOUS_EXTENSIONS


def scan_usb(drive: str) -> list[dict]:
    """Escanea una USB en busca de amenazas comunes."""
    threats = []
    try:
        for entry in os.listdir(drive):
            filepath = os.path.join(drive, entry)
            lower = entry.lower()

            # autorun.inf
            if lower == "autorun.inf":
                threats.append({"archivo": filepath, "tipo": "Autorun.inf",
                                "riesgo": "Alto"})
                continue

            # Ejecutables ocultos en la raiz
            ext = os.path.splitext(lower)[1]
            if ext in SUSPICIOUS_EXTENSIONS and os.path.isfile(filepath):
                threats.append({"archivo": filepath, "tipo": "Ejecutable sospechoso",
                                "riesgo": "Alto"})
                continue

            # Nombres conocidos de malware
            if lower in SUSPICIOUS_FILES:
                threats.append({"archivo": filepath, "tipo": "Archivo sospechoso",
                                "riesgo": "Alto"})
                continue

            # .lnk que apuntan a ejecutables
            if lower.endswith(".lnk") and os.path.isfile(filepath):
                if _is_suspicious_lnk(filepath, drive):
                    threats.append({"archivo": filepath, "tipo": "Acceso directo malicioso",
                                    "riesgo": "Medio"})
    except OSError:
        pass
    return threats


def clean_usb(drive: str, threats: list[dict]) -> int:
    """Elimina las amenazas detectadas con confirmacion."""
    removed = 0
    for threat in threats:
        filepath = threat["archivo"]
        try:
            os.remove(filepath)
            console.print(f"  [green]Eliminado:[/green] {os.path.basename(filepath)}")
            removed += 1
        except OSError as e:
            console.print(f"  [red]No se pudo eliminar {os.path.basename(filepath)}: {e}[/red]")
    return removed


def unhide_folders(drive: str) -> None:
    """Restaura carpetas ocultas por malware usando attrib."""
    console.print(f"[bold yellow]Restaurando carpetas ocultas en {drive}...[/bold yellow]")
    try:
        subprocess.run(
            ["attrib", "-h", "-s", "-r", "/s", "/d", f"{drive}*.*"],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        console.print("[green]Atributos restaurados.[/green]")
    except (subprocess.TimeoutExpired, OSError) as e:
        console.print(f"[red]Error al restaurar atributos: {e}[/red]")


def usb_disinfect_menu() -> None:
    """Interfaz principal del desinfectante de USB."""
    console.print("\n[bold cyan]Desinfectante de USB[/bold cyan]\n")

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
            "[bold]Selecciona la unidad[/bold]",
            choices=[str(i) for i in range(1, len(drives) + 1)],
        )
        drive = drives[int(choice) - 1]

    # Escanear
    with console.status(f"[bold green]Escaneando {drive}..."):
        threats = scan_usb(drive)

    if not threats:
        console.print(f"\n[bold green]No se encontraron amenazas en {drive}[/bold green]")
    else:
        table = Table(title=f"Amenazas encontradas en {drive}")
        table.add_column("#", style="bold cyan", width=4, justify="right")
        table.add_column("Archivo", style="white", max_width=40)
        table.add_column("Tipo", style="yellow")
        table.add_column("Riesgo", style="red")

        for i, t in enumerate(threats, 1):
            table.add_row(str(i), os.path.basename(t["archivo"]), t["tipo"], t["riesgo"])

        console.print()
        console.print(table)

        confirm = Prompt.ask(
            "\n[bold]Eliminar amenazas?[/bold]", choices=["s", "n"], default="s"
        )
        if confirm == "s":
            removed = clean_usb(drive, threats)
            console.print(f"\n[bold green]{removed} amenaza(s) eliminada(s).[/bold green]")

    # Ofrecer restaurar carpetas ocultas
    restore = Prompt.ask(
        "[bold]Restaurar carpetas ocultas?[/bold]", choices=["s", "n"], default="s"
    )
    if restore == "s":
        unhide_folders(drive)
