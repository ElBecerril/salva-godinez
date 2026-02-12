"""
Salva Godinez — Navaja suiza para oficinistas
by El_Becerril

Toolkit multi-modulo para rescate de archivos, mantenimiento
de impresoras, diagnostico del sistema y mas.
"""

import sys
import os

# Agregar el directorio del script al path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box

# Searchers (modulo de rescate de archivos Office)
from searchers.recycle_bin import search_recycle_bin
from searchers.disk_search import search_by_name, search_recent_excel
from searchers.temp_files import search_temp_files
from searchers.recent_files import search_recent_files
from searchers.shadow_copies import search_shadow_copies
from reporting.console_report import show_results, offer_restore

# Tools
from tools.spooler import reset_spooler
from tools.system_info import show_system_info
from tools.usb_disinfect import usb_disinfect_menu
from tools.pdf_tools import pdf_menu
from tools.wifi_passwords import show_wifi_passwords
from tools.password_generator import password_generator_menu

console = Console()

BANNER = r"""[bold cyan]
              ( (
               ) )
            .-------.
            |       |]
            \       /
             `-----'

  ____        _              ____          _ _
 / ___|  __ _| |_   ____ _  / ___| ___   __| (_)_ __   ___ ____
 \___ \ / _` | \ \ / / _` || |  _ / _ \ / _` | | '_ \ / _ \_  /
  ___) | (_| | |\ V / (_| || |_| | (_) | (_| | | | | |  __// /
 |____/ \__,_|_| \_/ \__,_| \____|\___/ \__,_|_|_| |_|\___/___|

  [bold white]La navaja suiza para sobrevivir la oficina[/bold white]
  [dim]by El_Becerril[/dim]
[/bold cyan]"""


# ─── Menu principal ───────────────────────────────────────────

def show_main_menu() -> str:
    console.print(BANNER)
    console.print(
        Panel(
            "[bold]1[/bold] - Rescatista de Archivos Office\n"
            "[bold]2[/bold] - Reset de Spooler (cola de impresion)\n"
            "[bold]3[/bold] - Info del Sistema\n"
            "[bold]4[/bold] - Desinfectante de USB\n"
            "[bold]5[/bold] - Editor de PDF\n"
            "[bold]6[/bold] - Recuperador de WiFi\n"
            "[bold]7[/bold] - Generador de Contrasenas\n"
            "[bold]0[/bold] - Salir",
            title="[bold yellow]Menu Principal[/bold yellow]",
            box=box.ROUNDED,
        )
    )
    return Prompt.ask("\n[bold cyan]Selecciona una opcion[/bold cyan]", default="0")


# ─── Sub-menu: Rescatista de Archivos Office ──────────────────

def show_office_menu() -> str:
    console.print(
        Panel(
            "[bold]1[/bold] - Buscar por nombre de archivo\n"
            "[bold]2[/bold] - Buscar todos los Office recientes (ultimos 30 dias)\n"
            "[bold]3[/bold] - Revisar papelera de reciclaje\n"
            "[bold]4[/bold] - Revisar archivos temporales / autorecuperacion\n"
            "[bold]5[/bold] - Revisar archivos recientes de Windows\n"
            "[bold]6[/bold] - Busqueda completa (todas las opciones)\n"
            "[bold]0[/bold] - Volver al menu principal",
            title="[bold yellow]Rescatista de Archivos Office[/bold yellow]",
            box=box.ROUNDED,
        )
    )
    return Prompt.ask("\n[bold cyan]Selecciona una opcion[/bold cyan]", default="0")


def ask_name() -> str:
    return Prompt.ask(
        "[bold]Nombre (o parte del nombre) del archivo[/bold]"
    ).strip()


def option_search_by_name() -> None:
    name = ask_name()
    if not name:
        console.print("[red]Debes ingresar un nombre.[/red]")
        return

    all_results = []

    with console.status("[bold green]Buscando en papelera de reciclaje..."):
        all_results.extend(search_recycle_bin(name))

    with console.status("[bold green]Buscando en archivos temporales / autorecuperacion..."):
        all_results.extend(search_temp_files(name))

    with console.status("[bold green]Revisando archivos recientes de Windows..."):
        all_results.extend(search_recent_files(name))

    console.print("[bold yellow]Buscando en todos los discos (esto puede tardar)...[/bold yellow]")
    with console.status("[bold green]Escaneando discos...") as status:
        def progress(path):
            display = path if len(path) < 60 else "..." + path[-57:]
            status.update(f"[bold green]Escaneando:[/bold green] {display}")
        all_results.extend(search_by_name(name, progress_callback=progress))

    with console.status("[bold green]Revisando shadow copies (VSS)..."):
        all_results.extend(search_shadow_copies(name))

    all_results = _deduplicate(all_results)
    show_results(all_results, title=f"Resultados para '{name}'")
    offer_restore(all_results)


def option_recent_office() -> None:
    console.print("[bold yellow]Buscando archivos Office de los ultimos 30 dias...[/bold yellow]")
    with console.status("[bold green]Escaneando discos...") as status:
        def progress(path):
            display = path if len(path) < 60 else "..." + path[-57:]
            status.update(f"[bold green]Escaneando:[/bold green] {display}")
        results = search_recent_excel(progress_callback=progress)

    show_results(results, title="Archivos Office recientes (ultimos 30 dias)")
    offer_restore(results)


def option_recycle_bin() -> None:
    name = Prompt.ask(
        "[bold]Filtrar por nombre (dejar vacio para ver todos)[/bold]", default=""
    )
    with console.status("[bold green]Revisando papelera de reciclaje..."):
        results = search_recycle_bin(name)
    show_results(results, title="Archivos Office en la Papelera")
    offer_restore(results)


def option_temp_files() -> None:
    name = Prompt.ask(
        "[bold]Filtrar por nombre (dejar vacio para ver todos)[/bold]", default=""
    )
    with console.status("[bold green]Buscando archivos temporales y de autorecuperacion..."):
        results = search_temp_files(name)
    show_results(results, title="Archivos Temporales / Autorecuperacion")
    offer_restore(results)


def option_recent_windows() -> None:
    name = Prompt.ask(
        "[bold]Filtrar por nombre (dejar vacio para ver todos)[/bold]", default=""
    )
    with console.status("[bold green]Revisando archivos recientes de Windows..."):
        results = search_recent_files(name)
    show_results(results, title="Archivos Recientes de Windows")
    offer_restore(results)


def option_full_search() -> None:
    name = ask_name()
    if not name:
        console.print("[red]Debes ingresar un nombre.[/red]")
        return

    all_results = []

    steps = [
        ("Papelera de reciclaje", lambda: search_recycle_bin(name)),
        ("Archivos temporales / autorecuperacion", lambda: search_temp_files(name)),
        ("Archivos recientes de Windows", lambda: search_recent_files(name)),
    ]

    for label, searcher in steps:
        with console.status(f"[bold green]Buscando en {label}..."):
            results = searcher()
            all_results.extend(results)
            if results:
                console.print(
                    f"  [green]+{len(results)}[/green] encontrado(s) en {label}"
                )

    console.print("[bold yellow]Escaneando todos los discos...[/bold yellow]")
    with console.status("[bold green]Escaneando discos...") as status:
        def progress(path):
            display = path if len(path) < 60 else "..." + path[-57:]
            status.update(f"[bold green]Escaneando:[/bold green] {display}")
        results = search_by_name(name, progress_callback=progress)
        all_results.extend(results)
        if results:
            console.print(f"  [green]+{len(results)}[/green] encontrado(s) en discos")

    with console.status("[bold green]Revisando shadow copies (VSS)..."):
        results = search_shadow_copies(name)
        all_results.extend(results)
        if results:
            console.print(
                f"  [green]+{len(results)}[/green] encontrado(s) en Shadow Copies"
            )

    all_results = _deduplicate(all_results)
    console.print()
    show_results(all_results, title=f"Busqueda completa para '{name}'")
    offer_restore(all_results)


def _deduplicate(results: list[dict]) -> list[dict]:
    """Elimina resultados duplicados por ruta."""
    seen = set()
    unique = []
    for r in results:
        key = r.get("ruta", "")
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def office_rescue_menu() -> None:
    """Sub-menu de rescate de archivos Office."""
    while True:
        choice = show_office_menu()

        if choice == "1":
            option_search_by_name()
        elif choice == "2":
            option_recent_office()
        elif choice == "3":
            option_recycle_bin()
        elif choice == "4":
            option_temp_files()
        elif choice == "5":
            option_recent_windows()
        elif choice == "6":
            option_full_search()
        elif choice == "0":
            break
        else:
            console.print("[red]Opcion no valida.[/red]")

        Prompt.ask("\n[dim]Presiona Enter para continuar[/dim]", default="")


# ─── Main ─────────────────────────────────────────────────────

def main() -> None:
    try:
        while True:
            choice = show_main_menu()

            if choice == "1":
                office_rescue_menu()
            elif choice == "2":
                reset_spooler()
            elif choice == "3":
                show_system_info()
            elif choice == "4":
                usb_disinfect_menu()
            elif choice == "5":
                pdf_menu()
            elif choice == "6":
                show_wifi_passwords()
            elif choice == "7":
                password_generator_menu()
            elif choice == "0":
                console.print("[bold cyan]Hasta luego![/bold cyan]")
                break
            else:
                console.print("[red]Opcion no valida.[/red]")

            if choice != "1":
                Prompt.ask("\n[dim]Presiona Enter para volver al menu[/dim]", default="")
    except KeyboardInterrupt:
        console.print("\n[bold cyan]Hasta luego![/bold cyan]")


if __name__ == "__main__":
    main()
