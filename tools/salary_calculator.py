"""Calculadora de Sueldo Neto (ISR/IMSS)."""

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich import box

from config import ISR_MONTHLY_TABLE, IMSS_EMPLOYEE_RATES, UMA_DAILY

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


def calculate_imss_deductions(monthly_gross: float) -> dict:
    """Calcula las cuotas obrero IMSS mensuales.

    Se usa el SBC (Salario Base de Cotizacion) = salario bruto mensual.
    El excedente de Enf. y Mat. se calcula sobre lo que exceda 3 UMA mensuales.
    """
    three_uma_monthly = UMA_DAILY * 3 * 30.4

    deductions = {}

    # Enfermedad y Maternidad excedente 3 UMA
    excess = max(0, monthly_gross - three_uma_monthly)
    deductions["Enf. y Mat. (excedente 3 UMA)"] = excess * IMSS_EMPLOYEE_RATES["enf_mat_excedente"]

    # Las demas se calculan sobre el SBC completo
    deductions["Enf. y Mat. (dinero)"] = monthly_gross * IMSS_EMPLOYEE_RATES["enf_mat_dinero"]
    deductions["Gastos medicos pensionados"] = monthly_gross * IMSS_EMPLOYEE_RATES["gastos_medicos"]
    deductions["Invalidez y vida"] = monthly_gross * IMSS_EMPLOYEE_RATES["invalidez_vida"]
    deductions["Cesantia y vejez"] = monthly_gross * IMSS_EMPLOYEE_RATES["cesantia_vejez"]

    return deductions


def calculate_isr(taxable_base: float) -> dict:
    """Calcula el ISR mensual segun Art. 96 LISR.

    Returns:
        dict con limite_inferior, excedente, tasa, impuesto_marginal, cuota_fija, isr_total
    """
    bracket = _find_bracket(taxable_base, ISR_MONTHLY_TABLE)
    if bracket is None:
        return {"isr_total": 0}

    lim_inf, _, cuota_fija, tasa = bracket
    excedente = taxable_base - lim_inf
    impuesto_marginal = excedente * tasa

    return {
        "limite_inferior": lim_inf,
        "excedente": excedente,
        "tasa": tasa,
        "impuesto_marginal": impuesto_marginal,
        "cuota_fija": cuota_fija,
        "isr_total": impuesto_marginal + cuota_fija,
    }


def salary_calculator_menu() -> None:
    """Calculadora de sueldo neto mensual."""
    console.print("\n[bold cyan]Calculadora de Sueldo Neto[/bold cyan]\n")

    monthly_gross = _ask_float("[bold]Salario bruto mensual[/bold]")
    if not monthly_gross:
        return

    # 1. Calcular IMSS
    imss = calculate_imss_deductions(monthly_gross)
    total_imss = sum(imss.values())

    # 2. Base gravable = bruto - IMSS
    taxable_base = monthly_gross - total_imss

    # 3. Calcular ISR
    isr = calculate_isr(taxable_base)
    isr_total = isr.get("isr_total", 0)

    # 4. Sueldo neto
    net_salary = monthly_gross - total_imss - isr_total

    # Mostrar tabla desglosada
    table = Table(title="Desglose de Sueldo Neto", box=box.SIMPLE_HEAVY)
    table.add_column("Concepto", style="bold")
    table.add_column("Monto", justify="right")

    table.add_row("[bold]Salario bruto[/bold]", f"[bold]{_fmt(monthly_gross)}[/bold]")
    table.add_row("", "")

    # Desglose IMSS
    table.add_row("[yellow]Deducciones IMSS[/yellow]", "")
    for concept, amount in imss.items():
        table.add_row(f"  {concept}", f"[red]-{_fmt(amount)}[/red]")
    table.add_row("  [bold]Total IMSS[/bold]", f"[red]-{_fmt(total_imss)}[/red]")
    table.add_row("", "")

    # Desglose ISR
    table.add_row("[yellow]ISR Art. 96[/yellow]", "")
    table.add_row("  Base gravable", _fmt(taxable_base))
    if "tasa" in isr:
        table.add_row("  Limite inferior", _fmt(isr["limite_inferior"]))
        table.add_row("  Excedente", _fmt(isr["excedente"]))
        table.add_row(f"  Tasa ({isr['tasa']:.2%})", f"[red]-{_fmt(isr['impuesto_marginal'])}[/red]")
        table.add_row("  Cuota fija", f"[red]-{_fmt(isr['cuota_fija'])}[/red]")
    table.add_row("  [bold]Total ISR[/bold]", f"[red]-{_fmt(isr_total)}[/red]")
    table.add_row("", "")

    table.add_row(
        "[bold green]Sueldo neto[/bold green]",
        f"[bold green]{_fmt(net_salary)}[/bold green]",
    )

    console.print(table)
    console.print(DISCLAIMER)
