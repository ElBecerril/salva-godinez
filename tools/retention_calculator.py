"""Calculadora de Retenciones (Honorarios / RESICO)."""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box

from config import RESICO_MONTHLY_TABLE

console = Console()

DISCLAIMER = (
    "[dim italic]Este calculo es un estimado con fines informativos. "
    "Consulta con un contador para cifras exactas.[/dim italic]"
)


def _ask_float(prompt: str) -> float | None:
    val = Prompt.ask(prompt).strip()
    try:
        result = float(val.replace(",", ""))
        if result <= 0:
            console.print("[red]El valor debe ser mayor a cero.[/red]")
            return None
        return result
    except ValueError:
        console.print("[red]Valor numerico invalido.[/red]")
        return None


def _fmt(amount: float) -> str:
    return f"${amount:,.2f}"


def _find_bracket(income: float, table: list[tuple]) -> tuple | None:
    """Busca el rango correspondiente en una tabla progresiva."""
    for row in table:
        if row[0] <= income <= row[1]:
            return row
    return None


def _option_honorarios() -> None:
    """Calculo de retenciones para pagos por Honorarios (persona fisica)."""
    console.print("\n[bold cyan]Retenciones por Honorarios[/bold cyan]\n")

    subtotal = _ask_float("[bold]Subtotal (monto antes de impuestos)[/bold]")
    if not subtotal:
        return

    iva = subtotal * 0.16
    isr_retenido = subtotal * 0.10
    iva_retenido = iva * (2 / 3)
    total = subtotal + iva - isr_retenido - iva_retenido

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
    """Calculo de ISR para RESICO personas fisicas."""
    console.print("\n[bold cyan]ISR RESICO Personas Fisicas[/bold cyan]\n")

    income = _ask_float("[bold]Ingreso mensual[/bold]")
    if not income:
        return

    bracket = _find_bracket(income, RESICO_MONTHLY_TABLE)
    if bracket is None:
        console.print("[red]No se encontro el rango fiscal para ese monto.[/red]")
        return

    lim_inf, _, cuota_fija, tasa = bracket
    excedente = income - lim_inf
    impuesto_marginal = excedente * tasa
    isr_total = cuota_fija + impuesto_marginal
    tasa_efectiva = (isr_total / income) * 100 if income > 0 else 0
    neto = income - isr_total

    table = Table(title="RESICO - Desglose ISR", box=box.SIMPLE_HEAVY)
    table.add_column("Concepto", style="bold")
    table.add_column("Valor", justify="right")

    table.add_row("Ingreso mensual", _fmt(income))
    table.add_row("Limite inferior", _fmt(lim_inf))
    table.add_row("Excedente", _fmt(excedente))
    table.add_row(f"Tasa sobre excedente ({tasa:.2%})", _fmt(impuesto_marginal))
    table.add_row("Cuota fija", _fmt(cuota_fija))
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
                title="[bold yellow]Calculadora de Retenciones[/bold yellow]",
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
