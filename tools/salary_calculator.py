"""Calculadora de Sueldo Neto (ISR/IMSS)."""

from rich.table import Table
from rich import box

from config import ISR_MONTHLY_TABLE, IMSS_EMPLOYEE_RATES, UMA_DAILY
from tools._fiscal_helpers import DISCLAIMER, ask_float as _ask_float, fmt as _fmt, find_bracket as _find_bracket
from utils import console


# --- Logica (sin UI) ---

# Tope legal de cotizacion IMSS: 25 UMA mensuales (Art. 28 LSS, reformado 2021).
# Se usa el mismo factor mensual (30.4) que ya usa el resto de este archivo
# para convertir el UMA diario a UMA mensual.
SBC_MONTHLY_CAP = UMA_DAILY * 25 * 30.4

# Subsidio para el empleo 2026 — Decreto DOF 31/12/2025, que sustituye la
# tabla por rangos vigente hasta 2025 (Decreto 26/12/2013) por un MONTO UNICO
# mensual para quien no exceda el limite de ingresos, en vez de un monto
# escalonado segun el nivel de ingreso.
#
# El decreto NO fija un monto en pesos: define una FORMULA — el subsidio es el
# valor mensual de la UMA multiplicado por 15.02%. Por eso se calcula aqui a
# partir de UMA_DAILY en vez de hardcodear pesos: cuando el INEGI publique la
# UMA de 2027 y se actualice config.py, el subsidio se mueve solo.
#   UMA mensual 2026 = 117.31 x 30.4 = $3,566.22
#   Subsidio (feb-dic 2026) = 3,566.22 x 15.02% = $535.65
#
# Transitorio SOLO enero 2026: el decreto manda usar 15.59% porque en enero
# seguia vigente la UMA de 2025 ($113.14 diaria = $3,439.46 mensual), ya que la
# UMA nueva entra en vigor el 1 de febrero. Eso daba $536.21 — un caso pasado y
# distinto por $0.56, que esta calculadora no modela: siempre usa el general.
SUBSIDIO_EMPLEO_FACTOR_UMA = 0.1502
SUBSIDIO_EMPLEO_MENSUAL = round(UMA_DAILY * 30.4 * SUBSIDIO_EMPLEO_FACTOR_UMA, 2)
SUBSIDIO_EMPLEO_LIMITE_INGRESO = 11_492.66


def calculate_subsidio_empleo(monthly_gross: float) -> float:
    """Calcula el subsidio al empleo mensual aplicable a sueldos bajos.

    Fuente: Decreto DOF 31/12/2025 (subsidio 2026): monto unico de
    SUBSIDIO_EMPLEO_MENSUAL para ingresos mensuales base ISR que no excedan
    SUBSIDIO_EMPLEO_LIMITE_INGRESO; fuera de ese limite, el subsidio es cero.
    """
    if monthly_gross <= SUBSIDIO_EMPLEO_LIMITE_INGRESO:
        return SUBSIDIO_EMPLEO_MENSUAL
    return 0.0


def calculate_imss_deductions(monthly_gross: float) -> dict:
    """Calcula las cuotas obrero IMSS mensuales.

    Se usa el SBC (Salario Base de Cotizacion) = salario bruto mensual,
    topado a 25 UMA mensuales (tope legal de cotizacion, Art. 28 LSS).
    El excedente de Enf. y Mat. se calcula sobre lo que exceda 3 UMA mensuales.
    """
    sbc = min(monthly_gross, SBC_MONTHLY_CAP)
    three_uma_monthly = UMA_DAILY * 3 * 30.4

    deductions = {}

    # Enfermedad y Maternidad excedente 3 UMA
    excess = max(0, sbc - three_uma_monthly)
    deductions["Enf. y Mat. (excedente 3 UMA)"] = excess * IMSS_EMPLOYEE_RATES["enf_mat_excedente"]

    # Las demas se calculan sobre el SBC completo (topado)
    deductions["Enf. y Mat. (dinero)"] = sbc * IMSS_EMPLOYEE_RATES["enf_mat_dinero"]
    deductions["Gastos medicos pensionados"] = sbc * IMSS_EMPLOYEE_RATES["gastos_medicos"]
    deductions["Invalidez y vida"] = sbc * IMSS_EMPLOYEE_RATES["invalidez_vida"]
    deductions["Cesantia y vejez"] = sbc * IMSS_EMPLOYEE_RATES["cesantia_vejez"]

    return deductions


def calculate_isr(taxable_base: float) -> dict:
    """Calcula el ISR mensual segun Art. 96 LISR.

    Returns:
        dict con limite_inferior, excedente, tasa, impuesto_marginal, cuota_fija, isr_total
        (o {"isr_total": 0, "error": "..."} si no se encontro un bracket).
    """
    try:
        bracket = _find_bracket(taxable_base, ISR_MONTHLY_TABLE)
    except ValueError as e:
        return {"isr_total": 0, "error": str(e)}

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


# --- Interfaz de consola ---

def salary_calculator_menu() -> None:
    """Calculadora de sueldo neto mensual."""
    console.print("\n[bold cyan]Calculadora de Sueldo Neto[/bold cyan]\n")

    monthly_gross = _ask_float("[bold]Salario bruto mensual[/bold]")
    if not monthly_gross:
        return

    # 1. Calcular IMSS
    imss = calculate_imss_deductions(monthly_gross)
    total_imss = sum(imss.values())

    # 2. Base gravable = bruto (las cuotas obrero IMSS no son deducibles de
    # la base del ISR de sueldos, Art. 96 LISR; el IMSS solo se resta al
    # calcular el neto, ver punto 4)
    taxable_base = monthly_gross

    # 3. Calcular ISR
    isr = calculate_isr(taxable_base)
    if "error" in isr:
        console.print(f"[red]No se pudo calcular el ISR: {isr['error']}[/red]")
    isr_total = isr.get("isr_total", 0)

    # 3b. Subsidio al empleo (beneficia a sueldos bajos, se resta del ISR a cargo
    # sin poder hacer el ISR negativo; bajo el esquema 2026 de monto unico, si
    # el subsidio excede el ISR el excedente NO se entrega en efectivo al
    # trabajador, simplemente el ISR neto queda en cero)
    subsidio_empleo = calculate_subsidio_empleo(monthly_gross)
    isr_neto = max(isr_total - subsidio_empleo, 0)

    # 4. Sueldo neto
    net_salary = monthly_gross - total_imss - isr_neto

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
    if subsidio_empleo:
        table.add_row("  Subsidio al empleo", f"[green]+{_fmt(subsidio_empleo)}[/green]")
        table.add_row("  [bold]ISR neto a cargo[/bold]", f"[red]-{_fmt(max(isr_neto, 0))}[/red]")
    table.add_row("", "")

    table.add_row(
        "[bold green]Sueldo neto[/bold green]",
        f"[bold green]{_fmt(net_salary)}[/bold green]",
    )

    console.print(table)
    console.print(DISCLAIMER)
