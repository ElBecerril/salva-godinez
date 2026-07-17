"""Desinfectante de USB: detecta y limpia amenazas comunes."""

import os
import subprocess

from rich.prompt import Prompt
from rich.table import Table

from tools import get_removable_drives
from utils import read_lnk_target as _read_lnk_target, console


# Nombres sospechosos comunes en USBs infectados
SUSPICIOUS_FILES = {"autorun.inf", "desktop.ini.exe", "recycler.exe", "ravmon.exe"}
SUSPICIOUS_EXTENSIONS = {".exe", ".scr", ".bat", ".cmd", ".vbs", ".wsf", ".pif", ".com"}


def _is_suspicious_lnk(lnk_path: str) -> bool:
    """Verifica si un .lnk apunta a un ejecutable (patron de virus USB)."""
    target = _read_lnk_target(lnk_path)
    if not target:
        return False
    ext = os.path.splitext(target)[1].lower()
    return ext in SUSPICIOUS_EXTENSIONS


def scan_usb(drive: str, max_depth: int = 3) -> list[dict]:
    """Escanea una USB en busca de amenazas comunes.

    Recorre recursivamente hasta `max_depth` niveles bajo la raiz: el malware
    de USB no siempre se copia solo en la raiz, y escanear unicamente ahi da
    una falsa sensacion de seguridad.
    """
    threats = []
    base_depth = drive.rstrip("\\/").count(os.sep)
    try:
        for dirpath, dirnames, filenames in os.walk(drive):
            depth = dirpath.rstrip("\\/").count(os.sep) - base_depth
            if depth >= max_depth:
                dirnames[:] = []
                continue

            for entry in filenames:
                filepath = os.path.join(dirpath, entry)
                lower = entry.lower()

                # autorun.inf
                if lower == "autorun.inf":
                    threats.append({"archivo": filepath, "tipo": "Autorun.inf",
                                    "riesgo": "Alto"})
                    continue

                # Nombres conocidos de malware (heuristica de alta confianza)
                if lower in SUSPICIOUS_FILES:
                    threats.append({"archivo": filepath, "tipo": "Archivo sospechoso",
                                    "riesgo": "Alto"})
                    continue

                # Ejecutables sueltos: tener una extension comun (.exe/.bat/etc.)
                # no es por si sola prueba de infeccion, asi que se marca como
                # riesgo medio y nunca se borra sin confirmacion explicita.
                ext = os.path.splitext(lower)[1]
                if ext in SUSPICIOUS_EXTENSIONS:
                    threats.append({"archivo": filepath, "tipo": "Ejecutable sospechoso",
                                    "riesgo": "Medio"})
                    continue

                # .lnk que apuntan a ejecutables
                if lower.endswith(".lnk"):
                    if _is_suspicious_lnk(filepath):
                        threats.append({"archivo": filepath, "tipo": "Acceso directo malicioso",
                                        "riesgo": "Medio"})
    except OSError:
        pass
    return threats


def clean_usb(drive: str, threats: list[dict]) -> int:
    """Elimina las amenazas detectadas con confirmacion.

    Solo borra las de riesgo Alto (autorun.inf, nombres de malware
    conocidos): son heuristicas de alta confianza. Las de riesgo Medio
    (ejecutables sueltos, accesos directos sospechosos) NO se borran
    aqui — un .exe legitimo del usuario tiene la misma extension que uno
    malicioso, asi que borrarlas en bloque es demasiado agresivo. Esas
    quedan para revision manual (ver usb_disinfect_menu).
    """
    removed = 0
    for threat in threats:
        if threat.get("riesgo") != "Alto":
            continue
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
        result = subprocess.run(
            ["attrib", "-h", "-s", "-r", "/s", "/d", f"{drive}*.*"],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            console.print("[green]Atributos restaurados correctamente.[/green]")
        else:
            detail = (result.stderr or result.stdout or "").strip()
            console.print(
                f"[red]attrib devolvio un error (codigo {result.returncode}). "
                "Es posible que no todas las carpetas/archivos se hayan restaurado.[/red]"
            )
            if detail:
                console.print(f"[dim]{detail}[/dim]")
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

        high_risk = [t for t in threats if t["riesgo"] == "Alto"]
        medium_risk = [t for t in threats if t["riesgo"] != "Alto"]

        if high_risk:
            console.print(
                f"\n[bold]{len(high_risk)} amenaza(s) de riesgo Alto[/bold] "
                "(autorun.inf / nombres de malware conocidos)."
            )
            confirm = Prompt.ask(
                "[bold]Eliminar solo las de riesgo Alto?[/bold]", choices=["s", "n"], default="n"
            )
            if confirm == "s":
                removed = clean_usb(drive, threats)
                console.print(f"\n[bold green]{removed} amenaza(s) eliminada(s).[/bold green]")

        if medium_risk:
            console.print(
                f"\n[yellow]{len(medium_risk)} archivo(s) sospechoso(s) de riesgo Medio "
                "(ejecutables sueltos / accesos directos) — NO se borran automaticamente. "
                "Revisalos manualmente:[/yellow]"
            )
            for t in medium_risk:
                console.print(f"  - {t['archivo']} ({t['tipo']})")

    # Ofrecer restaurar carpetas ocultas
    restore = Prompt.ask(
        "[bold]Restaurar carpetas ocultas?[/bold]", choices=["s", "n"], default="n"
    )
    if restore == "s":
        unhide_folders(drive)
