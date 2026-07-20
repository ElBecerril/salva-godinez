"""Calculadora de Retenciones (Honorarios / RESICO)."""

from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box

from config import RESICO_MONTHLY_TABLE, IVA_RATE, ISR_RETENTION_RATE, IVA_RETENTION_FRACTION
from tools._fiscal_helpers import DISCLAIMER, ask_float as _ask_float, fmt as _fmt, find_bracket as _find_bracket
from utils import console



# --- Logica (sin UI) ---

def calculate_honorarios(subtotal: float) -> dict:
    """Calcula retenciones para pagos por Honorarios (persona fisica).

    Returns:
        dict con subtotal, iva, isr_retenido, iva_retenido, total
    """
    iva = subtotal * IVA_RATE
    isr_retenido = subtotal * ISR_RETENTION_RATE
    iva_retenido = iva * IVA_RETENTION_FRACTION
    total = subtotal + iva - isr_retenido - iva_retenido
    return {
        "subtotal": subtotal,
        "iva": iva,
        "isr_retenido": isr_retenido,
        "iva_retenido": iva_retenido,
        "total": total,
    }


def calculate_resico(income: float) -> dict:
    """Calcula ISR para RESICO personas fisicas.

    RESICO PF (Art. 113-E LISR) NO es un calculo marginal: se aplica una
    TASA FIJA sobre el INGRESO TOTAL segun el rango en el que cae, no una
    cuota fija mas un porcentaje sobre el excedente.

    Returns:
        dict con lim_inf, lim_sup, tasa, isr_total, tasa_efectiva, neto
        (o {"error": "..."} si no se encontro el rango).
    """
    try:
        bracket = _find_bracket(income, RESICO_MONTHLY_TABLE)
    except ValueError as e:
        return {"error": str(e)}

    lim_inf, lim_sup, _cuota_fija_no_usada, tasa = bracket
    isr_total = income * tasa
    tasa_efectiva = (isr_total / income) * 100 if income > 0 else 0
    neto = income - isr_total

    return {
        "lim_inf": lim_inf,
        "lim_sup": lim_sup,
        "tasa": tasa,
        "isr_total": isr_total,
        "tasa_efectiva": tasa_efectiva,
        "neto": neto,
    }


# --- Interfaz de consola ---

def _option_honorarios() -> None:
    """Calculo de retenciones para pagos por Honorarios (persona fisica)."""
    console.print("\n[bold cyan]Retenciones por Honorarios[/bold cyan]\n")

    subtotal = _ask_float("[bold]Subtotal (monto antes de impuestos)[/bold]")
    if not subtotal:
        return

    result = calculate_honorarios(subtotal)
    iva = result["iva"]
    isr_retenido = result["isr_retenido"]
    iva_retenido = result["iva_retenido"]
    total = result["total"]

    table = Table(title="Honorarios - Desglose", box=box.SIMPLE_HEAVY)
    table.add_column("Concepto", style="bold")
    table.add_column("Monto", justify="right")

    table.add_row("Subtotal", _fmt(subtotal))
    table.add_row("IVA (16%)", f"[green]+{_fmt(iva)}[/green]")
    table.add_row("ISR retenido (10%)", f"[red]-{_fmt(isr_retenido)}[/red]")
    table.add_row("IVA retenido (2/3)", f"[red]-{_fmt(iva_retenido)}[/red]")
    table.add_row("", "")
    table.add_row("[bold]Total a recibir[/bold]", f"[bold]{_fmt(total)}[/bold]")
    table.add_row("[dim]Total en factura (subtotal + IVA)[/dim]", f"[dim]{_fmt(subtotal + iva)}[/dim]")

    console.print(table)
    console.print(DISCLAIMER)


def _option_resico() -> None:
    """Calculo de ISR para RESICO personas fisicas.

    RESICO PF (Art. 113-E LISR) NO es un calculo marginal: se aplica una
    TASA FIJA sobre el INGRESO TOTAL segun el rango en el que cae, no una
    cuota fija mas un porcentaje sobre el excedente.
    """
    console.print("\n[bold cyan]ISR RESICO Personas Fisicas[/bold cyan]\n")

    income = _ask_float("[bold]Ingreso mensual[/bold]")
    if not income:
        return

    result = calculate_resico(income)
    if "error" in result:
        console.print(f"[red]No se encontro el rango fiscal para ese monto: {result['error']}[/red]")
        return

    lim_inf = result["lim_inf"]
    lim_sup = result["lim_sup"]
    tasa = result["tasa"]
    isr_total = result["isr_total"]
    tasa_efectiva = result["tasa_efectiva"]
    neto = result["neto"]

    rango_sup = "en adelante" if lim_sup == float("inf") else _fmt(lim_sup)

    table = Table(title="RESICO - Desglose ISR", box=box.SIMPLE_HEAVY)
    table.add_column("Concepto", style="bold")
    table.add_column("Valor", justify="right")

    table.add_row("Ingreso mensual", _fmt(income))
    table.add_row("Rango aplicable", f"{_fmt(lim_inf)} - {rango_sup}")
    table.add_row(f"Tasa fija del rango ({tasa:.2%})", _fmt(isr_total))
    table.add_row("", "")
    table.add_row("[bold]ISR a pagar[/bold]", f"[red]{_fmt(isr_total)}[/red]")
    table.add_row("Tasa efectiva", f"{tasa_efectiva:.2f}%")
    table.add_row("[bold green]Neto despues de ISR[/bold green]", f"[bold green]{_fmt(neto)}[/bold green]")

    console.print(table)
    console.print(DISCLAIMER)


def retention_calculator_menu() -> None:
    """Sub-menu de calculadora de retenciones."""
    while True:
        console.print(
            Panel(
                "[bold]1[/bold] - Honorarios (persona fisica)\n"
                "[bold]2[/bold] - RESICO (personas fisicas)\n"
                "[bold]0[/bold] - Volver",
                title="[bold yellow]Retenciones de Honorarios[/bold yellow]",
                box=box.ROUNDED,
            )
        )
        choice = Prompt.ask("[bold cyan]Opcion[/bold cyan]", default="0")

        if choice == "1":
            _option_honorarios()
        elif choice == "2":
            _option_resico()
        elif choice == "0":
            break
        else:
            console.print("[red]Opcion no valida.[/red]")

        if choice in ("1", "2"):
            Prompt.ask("\n[dim]Presiona Enter para continuar[/dim]", default="")
