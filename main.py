"""
Buscador de Archivos Excel Perdidos
by El_Becerril

Script interactivo para buscar y recuperar archivos Excel perdidos
en el disco local usando multiples estrategias.
"""

import sys
import os

# Agregar el directorio del script al path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box

from searchers.recycle_bin import search_recycle_bin
from searchers.disk_search import search_by_name, search_recent_excel
from searchers.temp_files import search_temp_files
from searchers.recent_files import search_recent_files
from searchers.shadow_copies import search_shadow_copies
from reporting.console_report import show_results, offer_restore

console = Console()

BANNER = r"""
[bold cyan]
 ____                           _
| __ ) _   _ ___  ___ __ _ ___| | ___  _ __
|  _ \| | | / __|/ __/ _` / __| |/ _ \| '__|
| |_) | |_| \__ \ (_| (_| \__ \ | (_) | |
|____/ \__,_|___/\___\__,_|___/_|\___/|_|

  [bold white]Buscador de Archivos Excel Perdidos[/bold white]
  [dim]by El_Becerril[/dim]
[/bold cyan]"""


def show_menu() -> str:
    console.print(BANNER)
    console.print(
        Panel(
            "[bold]1[/bold] - Buscar por nombre de archivo\n"
            "[bold]2[/bold] - Buscar todos los Excel recientes (ultimos 30 dias)\n"
            "[bold]3[/bold] - Revisar papelera de reciclaje\n"
            "[bold]4[/bold] - Revisar archivos temporales / autorecuperacion de Excel\n"
            "[bold]5[/bold] - Revisar archivos recientes de Windows\n"
            "[bold]6[/bold] - Busqueda completa (todas las opciones)\n"
            "[bold]0[/bold] - Salir",
            title="[bold yellow]Menu Principal[/bold yellow]",
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

    # 1. Papelera
    with console.status("[bold green]Buscando en papelera de reciclaje..."):
        results = search_recycle_bin(name)
        all_results.extend(results)

    # 2. Archivos temporales
    with console.status("[bold green]Buscando en archivos temporales / autorecuperacion..."):
        results = search_temp_files(name)
        all_results.extend(results)

    # 3. Archivos recientes
    with console.status("[bold green]Revisando archivos recientes de Windows..."):
        results = search_recent_files(name)
        all_results.extend(results)

    # 4. Busqueda en disco (la mas lenta)
    console.print("[bold yellow]Buscando en todos los discos (esto puede tardar)...[/bold yellow]")
    with console.status("[bold green]Escaneando discos...") as status:
        def progress(path):
            # Truncar para que quepa en la linea
            display = path if len(path) < 60 else "..." + path[-57:]
            status.update(f"[bold green]Escaneando:[/bold green] {display}")

        results = search_by_name(name, progress_callback=progress)
        all_results.extend(results)

    # 5. Shadow copies
    with console.status("[bold green]Revisando shadow copies (VSS)..."):
        results = search_shadow_copies(name)
        all_results.extend(results)

    # Eliminar duplicados por ruta
    all_results = _deduplicate(all_results)

    show_results(all_results, title=f"Resultados para '{name}'")
    offer_restore(all_results)


def option_recent_excel() -> None:
    console.print("[bold yellow]Buscando archivos Excel de los ultimos 30 dias...[/bold yellow]")
    with console.status("[bold green]Escaneando discos...") as status:
        def progress(path):
            display = path if len(path) < 60 else "..." + path[-57:]
            status.update(f"[bold green]Escaneando:[/bold green] {display}")

        results = search_recent_excel(progress_callback=progress)

    show_results(results, title="Archivos Excel recientes (ultimos 30 dias)")
    offer_restore(results)


def option_recycle_bin() -> None:
    name = Prompt.ask(
        "[bold]Filtrar por nombre (dejar vacio para ver todos)[/bold]",
        default="",
    )
    with console.status("[bold green]Revisando papelera de reciclaje..."):
        results = search_recycle_bin(name)

    show_results(results, title="Archivos Excel en la Papelera")
    offer_restore(results)


def option_temp_files() -> None:
    name = Prompt.ask(
        "[bold]Filtrar por nombre (dejar vacio para ver todos)[/bold]",
        default="",
    )
    with console.status("[bold green]Buscando archivos temporales y de autorecuperacion..."):
        results = search_temp_files(name)

    show_results(results, title="Archivos Temporales / Autorecuperacion")
    offer_restore(results)


def option_recent_windows() -> None:
    name = Prompt.ask(
        "[bold]Filtrar por nombre (dejar vacio para ver todos)[/bold]",
        default="",
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

    # Disco completo
    console.print("[bold yellow]Escaneando todos los discos...[/bold yellow]")
    with console.status("[bold green]Escaneando discos...") as status:
        def progress(path):
            display = path if len(path) < 60 else "..." + path[-57:]
            status.update(f"[bold green]Escaneando:[/bold green] {display}")

        results = search_by_name(name, progress_callback=progress)
        all_results.extend(results)
        if results:
            console.print(f"  [green]+{len(results)}[/green] encontrado(s) en discos")

    # Shadow copies
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


def main() -> None:
    try:
        while True:
            choice = show_menu()

            if choice == "1":
                option_search_by_name()
            elif choice == "2":
                option_recent_excel()
            elif choice == "3":
                option_recycle_bin()
            elif choice == "4":
                option_temp_files()
            elif choice == "5":
                option_recent_windows()
            elif choice == "6":
                option_full_search()
            elif choice == "0":
                console.print("[bold cyan]Hasta luego![/bold cyan]")
                break
            else:
                console.print("[red]Opcion no valida.[/red]")

            Prompt.ask("\n[dim]Presiona Enter para volver al menu[/dim]", default="")
    except KeyboardInterrupt:
        console.print("\n[bold cyan]Hasta luego![/bold cyan]")


if __name__ == "__main__":
    main()
