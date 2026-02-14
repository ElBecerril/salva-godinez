"""Limpiador de celdas Excel: elimina espacios dobles, invisibles y NBSP."""

import os
import re

from rich.prompt import Prompt
from rich.table import Table

from utils import get_openpyxl as _get_openpyxl, console



# Caracteres invisibles a limpiar
_INVISIBLE = re.compile(
    "[\u00a0"     # NBSP
    "\u200b"      # Zero-width space
    "\u200c"      # Zero-width non-joiner
    "\u200d"      # Zero-width joiner
    "\ufeff"      # BOM
    "\u2060"      # Word joiner
    "]"
)


def _clean_cell_value(value: str) -> str:
    """Limpia una cadena: strip, doble espacio, caracteres invisibles."""
    cleaned = _INVISIBLE.sub(" ", value)
    cleaned = re.sub(r" {2,}", " ", cleaned)
    cleaned = cleaned.strip()
    return cleaned


def clean_file(filepath: str) -> dict:
    """Limpia celdas de texto en un archivo Excel.

    Returns:
        dict con total_cells, cleaned_cells, changes (lista de diffs)
    """
    openpyxl = _get_openpyxl()
    if not openpyxl:
        return {"total_cells": 0, "cleaned_cells": 0, "changes": []}

    wb = openpyxl.load_workbook(filepath)
    total = 0
    cleaned = 0
    changes = []

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    total += 1
                    new_val = _clean_cell_value(cell.value)
                    if new_val != cell.value:
                        changes.append({
                            "hoja": ws.title,
                            "celda": cell.coordinate,
                            "antes": repr(cell.value),
                            "despues": repr(new_val),
                        })
                        cell.value = new_val
                        cleaned += 1

    return {"total_cells": total, "cleaned_cells": cleaned,
            "changes": changes, "_wb": wb}


def cell_cleaner_menu() -> None:
    """Menu del limpiador de celdas."""
    console.print("\n[bold cyan]Limpiador de Celdas Excel[/bold cyan]\n")

    filepath = Prompt.ask("[bold]Ruta del archivo Excel[/bold]").strip().strip('"')
    if not filepath or not os.path.isfile(filepath):
        console.print("[red]Archivo no encontrado.[/red]")
        return

    if not filepath.lower().endswith((".xlsx", ".xlsm")):
        console.print("[red]Solo se soportan archivos .xlsx y .xlsm[/red]")
        return

    with console.status("[bold green]Analizando celdas..."):
        result = clean_file(filepath)

    wb = result.pop("_wb", None)
    console.print(f"\n  Celdas de texto analizadas: [bold]{result['total_cells']}[/bold]")
    console.print(f"  Celdas con cambios: [bold]{result['cleaned_cells']}[/bold]")

    if not result["changes"]:
        console.print("\n[bold green]No se encontraron celdas por limpiar.[/bold green]")
        if wb:
            wb.close()
        return

    # Preview de cambios
    table = Table(title="Cambios detectados")
    table.add_column("Hoja", style="cyan")
    table.add_column("Celda", style="bold")
    table.add_column("Antes", style="red")
    table.add_column("Despues", style="green")

    for change in result["changes"][:20]:
        table.add_row(change["hoja"], change["celda"], change["antes"], change["despues"])

    if len(result["changes"]) > 20:
        table.add_row("...", f"+{len(result['changes']) - 20} mas", "", "")

    console.print(table)

    confirm = Prompt.ask(
        "\n[bold]Guardar archivo limpio?[/bold]",
        choices=["s", "n"], default="s",
    )
    if confirm != "s" or not wb:
        if wb:
            wb.close()
        return

    base, ext = os.path.splitext(filepath)
    output = f"{base}_limpio{ext}"
    try:
        wb.save(output)
        console.print(f"\n[bold green]Archivo guardado: {output}[/bold green]")
    finally:
        wb.close()
