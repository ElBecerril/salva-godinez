"""Herramientas PDF: unir y dividir archivos PDF."""

import os

from rich.console import Console
from rich.prompt import Prompt

console = Console()


def _get_pypdf():
    """Import lazy de pypdf para no crashear si no esta instalado."""
    try:
        import pypdf
        return pypdf
    except ImportError:
        console.print(
            "[bold red]pypdf no esta instalado.[/bold red]\n"
            "[dim]Ejecuta: pip install pypdf[/dim]"
        )
        return None


def merge_pdfs() -> None:
    """Une multiples archivos PDF en uno solo."""
    pypdf = _get_pypdf()
    if not pypdf:
        return

    console.print("\n[bold cyan]Unir PDFs[/bold cyan]")
    console.print("[dim]Ingresa las rutas de los PDFs a unir (una por linea, linea vacia para terminar):[/dim]\n")

    paths = []
    while True:
        path = Prompt.ask(f"  [bold]PDF {len(paths) + 1}[/bold] (vacio para terminar)", default="").strip().strip('"')
        if not path:
            break
        if not os.path.isfile(path):
            console.print(f"  [red]Archivo no encontrado: {path}[/red]")
            continue
        paths.append(path)

    if len(paths) < 2:
        console.print("[yellow]Se necesitan al menos 2 PDFs para unir.[/yellow]")
        return

    output = Prompt.ask(
        "[bold]Ruta del PDF de salida[/bold]",
        default=os.path.join(os.path.dirname(paths[0]), "unido.pdf"),
    ).strip().strip('"')

    try:
        writer = pypdf.PdfWriter()
        for path in paths:
            try:
                reader = pypdf.PdfReader(path)
            except (pypdf.errors.PdfReadError, pypdf.errors.PdfStreamError) as e:
                console.print(f"  [red]PDF corrupto o invalido: {os.path.basename(path)} — {e}[/red]")
                continue
            for page in reader.pages:
                writer.add_page(page)

        if len(writer.pages) == 0:
            console.print("[red]No se pudieron leer paginas de ninguno de los PDFs.[/red]")
            return

        with open(output, "wb") as f:
            writer.write(f)

        total_pages = len(writer.pages)
        console.print(f"\n[bold green]PDF unido creado: {output} ({total_pages} paginas)[/bold green]")
    except (pypdf.errors.PdfReadError, OSError) as e:
        console.print(f"[red]Error al unir PDFs: {e}[/red]")


def split_pdf() -> None:
    """Divide un PDF en paginas individuales o por rango."""
    pypdf = _get_pypdf()
    if not pypdf:
        return

    console.print("\n[bold cyan]Dividir PDF[/bold cyan]")

    path = Prompt.ask("[bold]Ruta del PDF a dividir[/bold]").strip().strip('"')
    if not os.path.isfile(path):
        console.print("[red]Archivo no encontrado.[/red]")
        return

    try:
        reader = pypdf.PdfReader(path)
        total = len(reader.pages)
    except (pypdf.errors.PdfReadError, pypdf.errors.PdfStreamError, OSError) as e:
        console.print(f"[red]Error al leer PDF (archivo corrupto o invalido): {e}[/red]")
        return

    console.print(f"[dim]El PDF tiene {total} paginas.[/dim]")

    mode = Prompt.ask(
        "[bold]Modo[/bold]",
        choices=["individual", "rango"],
        default="individual",
    )

    output_dir = Prompt.ask(
        "[bold]Carpeta de salida[/bold]",
        default=os.path.join(os.path.dirname(path), "pdf_dividido"),
    ).strip().strip('"')
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(path))[0]

    if mode == "individual":
        for i, page in enumerate(reader.pages, 1):
            writer = pypdf.PdfWriter()
            writer.add_page(page)
            out_path = os.path.join(output_dir, f"{base_name}_pag{i}.pdf")
            with open(out_path, "wb") as f:
                writer.write(f)
        console.print(f"\n[bold green]{total} archivos creados en: {output_dir}[/bold green]")
    else:
        rango = Prompt.ask("[bold]Rango (ej: 1-5)[/bold]").strip()
        try:
            start, end = rango.split("-")
            start, end = int(start), int(end)
            if start < 1 or end > total or start > end:
                console.print(f"[red]Rango invalido. El PDF tiene paginas 1-{total}.[/red]")
                return
        except ValueError:
            console.print("[red]Formato invalido. Usa: inicio-fin (ej: 1-5)[/red]")
            return

        writer = pypdf.PdfWriter()
        for i in range(start - 1, end):
            writer.add_page(reader.pages[i])

        out_path = os.path.join(output_dir, f"{base_name}_pag{start}-{end}.pdf")
        with open(out_path, "wb") as f:
            writer.write(f)
        console.print(f"\n[bold green]PDF creado: {out_path} ({end - start + 1} paginas)[/bold green]")


def pdf_menu() -> None:
    """Sub-menu de herramientas PDF."""
    while True:
        console.print(
            "\n[bold cyan]Herramientas PDF[/bold cyan]\n"
            "  [bold]1[/bold] - Unir PDFs\n"
            "  [bold]2[/bold] - Dividir PDF\n"
            "  [bold]0[/bold] - Volver"
        )
        choice = Prompt.ask("[bold cyan]Opcion[/bold cyan]", default="0")

        if choice == "1":
            merge_pdfs()
        elif choice == "2":
            split_pdf()
        elif choice == "0":
            break
        else:
            console.print("[red]Opcion no valida.[/red]")
