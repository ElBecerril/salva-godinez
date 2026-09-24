"""Calculadora de Sueldo Neto (ISR/IMSS)."""

from rich.table import Table
from rich import box

from config import (
    ISR_MONTHLY_TABLE,
    IMSS_EMPLOYEE_RATES,
    SALARIO_MINIMO_DAILY,
    UMA_DAILY,
    AGUINALDO_MIN_DAYS,
    VACATION_DAYS_TABLE,
)
from tools._fiscal_helpers import DISCLAIMER, ask_float as _ask_float, fmt as _fmt, find_bracket as _find_bracket
from utils import console


# --- Logica (sin UI) ---

# Tope legal de cotizacion IMSS: 25 UMA mensuales (Art. 28 LSS, reformado 2021).
# Se usa el mismo factor mensual (30.4) que ya usa el resto de este archivo
# para convertir el UMA diario a UMA mensual.
SBC_MONTHLY_CAP = UMA_DAILY * 25 * 30.4

# Factor de integracion MINIMO del SBC (Art. 27 LSS): el salario base de
# cotizacion integra la parte proporcional de aguinaldo (15 dias) y prima
# vacacional (25% de las vacaciones). Factor = 1 + 15/365 + (12 x 25%)/365,
# usando las vacaciones del PRIMER anio (12 dias, reforma 2023). Es el piso
# legal: crece con la antiguedad, pero esta calculadora no pide antiguedad,
# asi que aplica el minimo (antes se usaba el bruto sin integrar, que
# subestimaba las cuotas IMSS ~4.5%).
FACTOR_INTEGRACION_SBC_MINIMO = 1 + (AGUINALDO_MIN_DAYS + VACATION_DAYS_TABLE[1] * 0.25) / 365

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

# Mensualizacion del salario minimo (mismo factor 30.4 que el resto del
# archivo) para detectar a quien gana justo el minimo: Art. 96 LISR (tercer
# parrafo) exime de retencion de ISR a quien en el mes unicamente percibe un
# salario minimo general, y el Art. 36 LSS pone la cuota obrero del IMSS a
# cargo del PATRON para ese mismo caso. +0.01 de tolerancia por redondeo (el
# bruto capturado puede venir ya redondeado a centavos).
SALARIO_MINIMO_MONTHLY = SALARIO_MINIMO_DAILY * 30.4


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

    Se usa el SBC (Salario Base de Cotizacion) = salario bruto mensual por el
    factor de integracion minimo (integra aguinaldo y prima vacacional, Art.
    27 LSS), topado a 25 UMA mensuales (tope legal de cotizacion, Art. 28 LSS).
    El excedente de Enf. y Mat. se calcula sobre lo que exceda 3 UMA mensuales.
    """
    sbc = min(monthly_gross * FACTOR_INTEGRACION_SBC_MINIMO, SBC_MONTHLY_CAP)
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


def calculate_neto(monthly_gross: float) -> dict:
    """Compone bruto -> IMSS -> ISR -> subsidio -> neto mensual.

    Punto unico de esta composicion: la consola (salary_calculator_menu) y el
    panel de GUI (gui/panels/sueldo.py) llaman a esta funcion en vez de
    reimplementarla, para no tener dos calculos que se puedan desincronizar.

    Caso especial salario minimo (Art. 96 LISR 3er parrafo + Art. 36 LSS): a
    quien en el mes solo percibe un salario minimo general no se le retiene
    ISR, y la cuota obrero del IMSS la paga el patron. En ese caso el neto es
    el bruto completo; `salario_minimo=True` le indica a la UI que muestre la
    nota legal en vez de (o ademas de) el desglose normal.
    """
    imss = calculate_imss_deductions(monthly_gross)
    total_imss = sum(imss.values())

    # Base gravable = bruto (las cuotas obrero IMSS no son deducibles de la
    # base del ISR de sueldos, Art. 96 LISR; el IMSS solo se resta al
    # calcular el neto).
    taxable_base = monthly_gross

    isr = calculate_isr(taxable_base)
    isr_total = isr.get("isr_total", 0)

    # Subsidio al empleo (beneficia a sueldos bajos, se resta del ISR a cargo
    # sin poder hacer el ISR negativo; bajo el esquema 2026 de monto unico, si
    # el subsidio excede el ISR el excedente NO se entrega en efectivo al
    # trabajador, simplemente el ISR neto queda en cero).
    subsidio_empleo = calculate_subsidio_empleo(monthly_gross)
    isr_neto = max(isr_total - subsidio_empleo, 0)

    salario_minimo = monthly_gross <= SALARIO_MINIMO_MONTHLY + 0.01
    if salario_minimo:
        total_imss = 0.0  # Art. 36 LSS: la cuota obrero la paga el patron
        isr_neto = 0.0  # Art. 96 LISR: no hay retencion
        net_salary = monthly_gross
    else:
        net_salary = monthly_gross - total_imss - isr_neto

    return {
        "imss": imss,
        "total_imss": total_imss,
        "taxable_base": taxable_base,
        "isr": isr,
        "isr_total": isr_total,
        "subsidio_empleo": subsidio_empleo,
        "isr_neto": isr_neto,
        "net_salary": net_salary,
        "salario_minimo": salario_minimo,
    }


# --- Interfaz de consola ---

_NOTA_SALARIO_MINIMO = (
    "Ganas el salario minimo: por ley no se te retiene ISR (Art. 96 LISR) y "
    "tu cuota del IMSS la paga el patron (Art. 36 LSS)."
)


def salary_calculator_menu() -> None:
    """Calculadora de sueldo neto mensual."""
    console.print("\n[bold cyan]Calculadora de Sueldo Neto[/bold cyan]\n")

    monthly_gross = _ask_float("[bold]Salario bruto mensual[/bold]")
    if not monthly_gross:
        return

    resultado = calculate_neto(monthly_gross)
    isr = resultado["isr"]
    if "error" in isr:
        console.print(f"[red]No se pudo calcular el ISR: {isr['error']}[/red]")

    imss = resultado["imss"]
    total_imss = resultado["total_imss"]
    taxable_base = resultado["taxable_base"]
    isr_total = resultado["isr_total"]
    subsidio_empleo = resultado["subsidio_empleo"]
    isr_neto = resultado["isr_neto"]
    net_salary = resultado["net_salary"]

    # Mostrar tabla desglosada
    table = Table(title="Desglose de Sueldo Neto", box=box.SIMPLE_HEAVY)
    table.add_column("Concepto", style="bold")
    table.add_column("Monto", justify="right")

    table.add_row("[bold]Salario bruto[/bold]", f"[bold]{_fmt(monthly_gross)}[/bold]")
    table.add_row("", "")

    if resultado["salario_minimo"]:
        console.print(f"[yellow]{_NOTA_SALARIO_MINIMO}[/yellow]\n")
        table.add_row("  IMSS a cargo del trabajador", f"[red]-{_fmt(0)}[/red]")
        table.add_row("  ISR a cargo del trabajador", f"[red]-{_fmt(0)}[/red]")
        table.add_row("", "")
    else:
        # Desglose IMSS
        table.add_row("[yellow]Deducciones IMSS (SBC integrado)[/yellow]", "")
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
