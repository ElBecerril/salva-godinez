"""Reporte de resultados en consola usando Rich y acciones de restauracion."""

import os
import shutil

from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markup import escape
from utils import console



def show_results(results: list[dict], title: str = "Resultados") -> None:
    """Muestra los resultados en una tabla Rich.

    Args:
        results: Lista de dicts con nombre, ruta, tamano, fecha, origen.
        title: Titulo de la tabla.
    """
    if not results:
        console.print(
            Panel("[yellow]No se encontraron archivos.[/yellow]", title=title)
        )
        return

    table = Table(title=title, show_lines=True)
    table.add_column("#", style="bold cyan", width=4, justify="right")
    table.add_column("Nombre", style="bold white", max_width=40)
    table.add_column("Ruta", style="dim", max_width=60)
    table.add_column("Tamano", justify="right", style="green")
    table.add_column("Fecha", style="yellow")
    table.add_column("Origen", style="magenta")

    for i, r in enumerate(results, 1):
        table.add_row(
            str(i),
            escape(str(r.get("nombre", "?"))),
            escape(str(r.get("ruta", "?"))),
            escape(str(r.get("tamano", "?"))),
            escape(str(r.get("fecha", "?"))),
            escape(str(r.get("origen", "?"))),
        )

    console.print(table)
    console.print(f"\n  [bold]Total: {len(results)} archivo(s) encontrado(s)[/bold]\n")


def offer_restore(results: list[dict]) -> None:
    """Ofrece copiar/restaurar un archivo encontrado a una ubicacion elegida.

    Args:
        results: Lista de resultados mostrados previamente.
    """
    if not results:
        return

    console.print(
        "[bold cyan]Puedes copiar un archivo encontrado a otra ubicacion.[/bold cyan]"
    )
    choice = Prompt.ask(
        "Numero del archivo a copiar (0 para omitir)", default="0"
    )

    try:
        idx = int(choice)
    except ValueError:
        return

    if idx < 1 or idx > len(results):
        return

    selected = results[idx - 1]
    nombre = selected.get("nombre")
    # Para los archivos de la papelera, la ruta que se muestra es la ORIGINAL
    # (de donde se borro) y ahi ya no hay nada: el archivo vive renombrado
    # dentro de $Recycle.Bin. "ruta_fisica" es de donde si se puede copiar.
    source = selected.get("ruta_fisica") or selected.get("ruta")

    if not source or not nombre:
        console.print(
            "[red]El resultado seleccionado no tiene ruta o nombre validos.[/red]"
        )
        return

    if not os.path.isfile(source):
        console.print(
            f"[red]Ya no se puede recuperar este archivo.[/red] "
            f"Puede que se haya vaciado la papelera o que ya no este en: "
            f"{escape(str(selected.get('ruta', source)))}"
        )
        return

    dest_dir = Prompt.ask(
        "Carpeta destino (ej: C:\\Users\\TuUsuario\\Desktop)",
        default=os.path.join(os.path.expanduser("~"), "Desktop"),
    )

    if not os.path.isdir(dest_dir):
        console.print(f"[red]La carpeta no existe:[/red] {escape(str(dest_dir))}")
        return

    dest_path = os.path.join(dest_dir, nombre)

    # Evitar sobreescribir
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(nombre)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(dest_dir, f"{base}_recuperado{counter}{ext}")
            counter += 1

    try:
        shutil.copy2(source, dest_path)
        console.print(
            f"\n[bold green]Archivo copiado exitosamente a:[/bold green] {escape(str(dest_path))}\n"
        )
    except OSError as e:
        console.print(f"[red]Error al copiar:[/red] {escape(str(e))}")
