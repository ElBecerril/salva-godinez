"""Consolidador de libros Excel: unir archivos o unir hojas."""

import os
import zipfile

from rich.prompt import Prompt
from rich.panel import Panel
from rich import box

from utils import get_openpyxl as _get_openpyxl, console


# --- Logica (sin UI) ---


def _safe_output_path(path: str) -> str:
    """Evita sobrescribir un archivo existente agregando un sufijo numerico.

    Normaliza los separadores: el nombre de salida suele armarse uniendo un
    directorio de dialogo (barras /) con un nombre por os.path.join (barra \\),
    y la ruta cruda queda mezclada. normpath la deja en un solo estilo.
    """
    if not os.path.exists(path):
        return os.path.normpath(path)

    base, ext = os.path.splitext(path)
    counter = 1
    while True:
        candidate = f"{base}_{counter}{ext}"
        if not os.path.exists(candidate):
            return os.path.normpath(candidate)
        counter += 1


def _merge_files(paths: list[str], output: str) -> dict:
    """Modo 1: Unir archivos — cada archivo aporta sus hojas al workbook final.

    Returns:
        dict con: ok, sheets, output, open_errors (lista de (nombre, error)),
        forced_xlsx, output_conflict, save_error.
    """
    openpyxl = _get_openpyxl()
    if not openpyxl:
        return {
            "ok": False, "sheets": 0, "output": None, "open_errors": [],
            "forced_xlsx": False, "output_conflict": False, "save_error": None,
        }

    from copy import copy

    dest_wb = openpyxl.Workbook()
    dest_wb.remove(dest_wb.active)
    total_sheets = 0
    open_errors: list[tuple[str, str]] = []

    for path in paths:
        try:
            src_wb = openpyxl.load_workbook(path, data_only=True)
        except (OSError, KeyError, zipfile.BadZipFile) as e:
            open_errors.append((os.path.basename(path), str(e)))
            continue
        base = os.path.splitext(os.path.basename(path))[0]

        for ws in src_wb.worksheets:
            # Nombre unico para la hoja (max 31 chars, limite de Excel)
            sheet_name = f"{base}_{ws.title}"[:31]
            existing = {s.title for s in dest_wb.worksheets}
            if sheet_name in existing:
                # Agregar sufijo numerico si el nombre truncado ya existe
                for n in range(2, 100):
                    suffix = f"_{n}"
                    candidate = f"{base}_{ws.title}"[:31 - len(suffix)] + suffix
                    if candidate not in existing:
                        sheet_name = candidate
                        break
            dest_ws = dest_wb.create_sheet(title=sheet_name)

            for row in ws.iter_rows():
                for cell in row:
                    dest_cell = dest_ws.cell(row=cell.row, column=cell.column, value=cell.value)
                    if cell.has_style:
                        dest_cell.font = copy(cell.font)
                        dest_cell.fill = copy(cell.fill)
                        dest_cell.number_format = cell.number_format
                        dest_cell.alignment = copy(cell.alignment)

            # Copiar anchos de columna
            for col_letter, dim in ws.column_dimensions.items():
                dest_ws.column_dimensions[col_letter].width = dim.width

            total_sheets += 1

        src_wb.close()

    # .xlsm de salida sin macros VBA reales queda corrupto: si el usuario
    # pidio .xlsm pero ninguna hoja de origen trajo VBA, forzamos .xlsx.
    forced_xlsx = False
    if output.lower().endswith(".xlsm") and not getattr(dest_wb, "vba_archive", None):
        forced_xlsx = True
        output = os.path.splitext(output)[0] + ".xlsx"

    input_abspaths = {os.path.abspath(p) for p in paths}
    if os.path.abspath(output) in input_abspaths:
        dest_wb.close()
        return {
            "ok": False, "sheets": 0, "output": None, "open_errors": open_errors,
            "forced_xlsx": forced_xlsx, "output_conflict": True, "save_error": None,
        }
    output = _safe_output_path(output)

    try:
        dest_wb.save(output)
    except OSError as e:
        dest_wb.close()
        return {
            "ok": False, "sheets": 0, "output": None, "open_errors": open_errors,
            "forced_xlsx": forced_xlsx, "output_conflict": False, "save_error": str(e),
        }
    dest_wb.close()
    return {
        "ok": True, "sheets": total_sheets, "output": output, "open_errors": open_errors,
        "forced_xlsx": forced_xlsx, "output_conflict": False, "save_error": None,
    }


def _merge_sheets(filepath: str, output: str, skip_header: bool = True) -> dict:
    """Modo 2: Unir hojas — stack vertical de hojas en una sola.

    Args:
        skip_header: si True (default), se descarta la primera fila de las
            hojas 2+ asumiendo que traen encabezado repetido. Si False, se
            conservan todas las filas de todas las hojas.

    Returns:
        dict con: ok, rows, output, open_error, input_conflict, forced_xlsx, save_error.
    """
    openpyxl = _get_openpyxl()
    if not openpyxl:
        return {
            "ok": False, "rows": 0, "output": None, "open_error": None,
            "input_conflict": False, "forced_xlsx": False, "save_error": None,
        }

    try:
        src_wb = openpyxl.load_workbook(filepath, data_only=True)
    except (OSError, KeyError, zipfile.BadZipFile) as e:
        return {
            "ok": False, "rows": 0, "output": None, "open_error": str(e),
            "input_conflict": False, "forced_xlsx": False, "save_error": None,
        }

    if os.path.abspath(output) == os.path.abspath(filepath):
        src_wb.close()
        return {
            "ok": False, "rows": 0, "output": None, "open_error": None,
            "input_conflict": True, "forced_xlsx": False, "save_error": None,
        }

    dest_wb = openpyxl.Workbook()
    dest_ws = dest_wb.active
    dest_ws.title = "Consolidado"

    current_row = 1
    for idx, ws in enumerate(src_wb.worksheets):
        for row_num, row in enumerate(ws.iter_rows(values_only=True), 1):
            # Skip header en hojas 2+ (fila 1), solo si el usuario confirmo
            # que todas las hojas traen encabezado.
            if skip_header and idx > 0 and row_num == 1:
                continue
            for col, value in enumerate(row, 1):
                dest_ws.cell(row=current_row, column=col, value=value)
            current_row += 1

    src_wb.close()

    forced_xlsx = False
    if output.lower().endswith(".xlsm") and not getattr(dest_wb, "vba_archive", None):
        forced_xlsx = True
        output = os.path.splitext(output)[0] + ".xlsx"
    output = _safe_output_path(output)

    try:
        dest_wb.save(output)
    except OSError as e:
        dest_wb.close()
        return {
            "ok": False, "rows": 0, "output": None, "open_error": None,
            "input_conflict": False, "forced_xlsx": forced_xlsx, "save_error": str(e),
        }
    dest_wb.close()
    return {
        "ok": True, "rows": current_row - 1, "output": output, "open_error": None,
        "input_conflict": False, "forced_xlsx": forced_xlsx, "save_error": None,
    }


# --- Interfaz de consola ---


def consolidator_menu() -> None:
    """Menu del consolidador de libros Excel."""
    console.print(
        Panel(
            "[bold]1[/bold] - Unir archivos (varios .xlsx → un workbook)\n"
            "[bold]2[/bold] - Unir hojas (hojas de un archivo → una sola hoja)\n"
            "[bold]0[/bold] - Volver",
            title="[bold yellow]Unir Varios Excel en Uno[/bold yellow]",
            box=box.ROUNDED,
        )
    )
    mode = Prompt.ask("[bold cyan]Opcion[/bold cyan]", default="0")

    if mode == "1":
        console.print("\n[bold cyan]Unir archivos Excel[/bold cyan]")
        console.print("[dim]Ingresa las rutas de los archivos (vacio para terminar):[/dim]\n")

        paths = []
        while True:
            path = Prompt.ask(
                f"  [bold]Archivo {len(paths) + 1}[/bold] (vacio para terminar)",
                default="",
            ).strip().strip('"')
            if not path:
                break
            if not os.path.isfile(path):
                console.print(f"  [red]Archivo no encontrado: {path}[/red]")
                continue
            if not path.lower().endswith((".xlsx", ".xlsm")):
                console.print("  [red]Solo se soportan archivos .xlsx y .xlsm[/red]")
                continue
            paths.append(path)

        if len(paths) < 2:
            console.print("[yellow]Se necesitan al menos 2 archivos.[/yellow]")
            return

        output = Prompt.ask(
            "[bold]Ruta del archivo de salida[/bold]",
            default=os.path.join(os.path.dirname(paths[0]), "consolidado.xlsx"),
        ).strip().strip('"')

        console.print(
            "[yellow]Aviso:[/yellow] las formulas de los archivos de origen se convierten "
            "a sus valores actuales. Si algun archivo no fue abierto/recalculado en Excel "
            "antes de esto, esas celdas pueden llegar vacias."
        )

        with console.status("[bold green]Consolidando archivos..."):
            result = _merge_files(paths, output)

        for basename, err in result["open_errors"]:
            console.print(f"  [red]No se pudo abrir {basename}: {err}[/red]")

        if result["forced_xlsx"]:
            console.print(
                "[yellow]El archivo de salida se genero como .xlsx: ninguno de los archivos "
                "de origen tenia macros VBA, un .xlsm sin macros queda corrupto.[/yellow]"
            )

        if result["output_conflict"]:
            console.print(
                "[red]La ruta de salida no puede ser igual a uno de los archivos de entrada "
                "(se perderia el original). Elige otra ruta.[/red]"
            )

        if result["save_error"]:
            console.print(
                f"[red]Error al guardar archivo (revisa que no este abierto o el espacio en disco): {result['save_error']}[/red]"
            )

        if result["sheets"]:
            console.print(f"\n[bold green]Consolidado creado: {result['output']} ({result['sheets']} hojas)[/bold green]")

    elif mode == "2":
        console.print("\n[bold cyan]Unir hojas en una sola[/bold cyan]\n")

        filepath = Prompt.ask("[bold]Ruta del archivo Excel[/bold]").strip().strip('"')
        if not os.path.isfile(filepath):
            console.print("[red]Archivo no encontrado.[/red]")
            return

        base, ext = os.path.splitext(filepath)
        output = Prompt.ask(
            "[bold]Ruta del archivo de salida[/bold]",
            default=f"{base}_consolidado{ext}",
        ).strip().strip('"')

        console.print(
            "\n[yellow]Aviso:[/yellow] por defecto se asume que [bold]todas[/bold] las hojas "
            "tienen encabezado, y se descartara la primera fila de la hoja 2 en adelante "
            "(la de la primera hoja se conserva completa). Si alguna hoja NO trae encabezado, "
            "esa fila de datos se perderia."
        )
        console.print(
            "[yellow]Aviso:[/yellow] las formulas se convierten a sus valores actuales. Si el "
            "archivo no fue abierto/recalculado en Excel antes de esto, esas celdas pueden "
            "llegar vacias."
        )
        has_header = Prompt.ask(
            "[bold]Todas las hojas tienen fila de encabezado?[/bold]",
            choices=["s", "n"], default="s",
        )
        if has_header == "n":
            console.print("[dim]Se conservaran todas las filas de todas las hojas.[/dim]")
        confirm = Prompt.ask(
            "[bold]Continuar con la union de hojas?[/bold]",
            choices=["s", "n"], default="s",
        )
        if confirm != "s":
            console.print("[dim]Operacion cancelada.[/dim]")
            return

        with console.status("[bold green]Uniendo hojas..."):
            result = _merge_sheets(filepath, output, skip_header=(has_header == "s"))

        if result["open_error"]:
            console.print(f"  [red]No se pudo abrir el archivo: {result['open_error']}[/red]")

        if result["input_conflict"]:
            console.print(
                "[red]La ruta de salida no puede ser igual al archivo de entrada "
                "(se perderia el original). Elige otra ruta.[/red]"
            )

        if result["forced_xlsx"]:
            console.print(
                "[yellow]El archivo de salida se genero como .xlsx: el resultado no tiene "
                "macros VBA, un .xlsm sin macros queda corrupto.[/yellow]"
            )

        if result["save_error"]:
            console.print(
                f"[red]Error al guardar archivo (revisa que no este abierto o el espacio en disco): {result['save_error']}[/red]"
            )

        if result["rows"]:
            console.print(f"\n[bold green]Archivo creado: {result['output']} ({result['rows']} filas)[/bold green]")

    elif mode == "0":
        return
    else:
        console.print("[red]Opcion no valida.[/red]")
