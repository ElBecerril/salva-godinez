"""Simulador de prestaciones laborales Mexico."""

from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box

from config import (
    AGUINALDO_MIN_DAYS,
    SALARIO_MINIMO_DAILY,
    UMA_DAILY,
    VACATION_DAYS_RANGES_20PLUS,
    VACATION_DAYS_TABLE,
)
from tools._fiscal_helpers import DISCLAIMER, ask_float as _ask_float, fmt as _fmt
from utils import console




# --- Logica (sin UI) ---

def _get_vacation_days(years: float) -> int:
    """Dias de vacaciones segun antiguedad (LFT Art. 76, reforma "vacaciones
    dignas" 2023+).

    El derecho a vacaciones sube por anio CUMPLIDO, asi que se usa la parte
    entera de la antiguedad (aunque `years` venga con decimales para el calculo
    proporcional de prima de antiguedad / 20 dias)."""
    years = int(years)
    if years <= 0:
        return 0
    if years <= 20:
        return VACATION_DAYS_TABLE.get(years, 20)

    for lo, hi, days in VACATION_DAYS_RANGES_20PLUS:
        if lo <= years <= hi:
            return days

    # Mas alla del ultimo rango explicito de la tabla: seguir sumando 2 dias
    # cada 5 anos adicionales a partir del ultimo tramo conocido.
    last_lo, last_hi, last_days = VACATION_DAYS_RANGES_20PLUS[-1]
    extra_blocks = (years - last_hi + 4) // 5
    return last_days + extra_blocks * 2


def calculate_aguinaldo(daily_salary: float, days_worked: int) -> dict:
    """Calcula aguinaldo proporcional.

    Returns:
        dict con bruto, exento (30 UMA), gravado
    """
    days_worked = min(days_worked, 365)
    proportional = (days_worked / 365) * AGUINALDO_MIN_DAYS * daily_salary
    exempt = UMA_DAILY * 30  # 30 dias de UMA exentos
    taxable = max(0, proportional - exempt)
    return {"bruto": proportional, "exento": min(proportional, exempt), "gravado": taxable}


def calculate_vacaciones(daily_salary: float, years: float, days_worked: int) -> dict:
    """Calcula prima vacacional proporcional (25%).

    Returns:
        dict con dias, prima_bruta, prima_exenta (15 UMA)
    """
    # Topar a 365 igual que el aguinaldo: sin esto, un dato erroneo (>365 dias)
    # infla la prima proporcional por encima del derecho de un anio completo,
    # y contamina finiquito/liquidacion que llaman a esta funcion.
    days_worked = min(days_worked, 365)
    vac_days = _get_vacation_days(years)
    prop_days = (days_worked / 365) * vac_days
    prima = prop_days * daily_salary * 0.25
    exempt = UMA_DAILY * 15  # 15 dias de UMA exentos
    return {
        "dias": prop_days,
        "prima_bruta": prima,
        "prima_exenta": min(prima, exempt),
        "prima_gravada": max(0, prima - exempt),
    }


def calculate_finiquito(daily_salary: float, years: float, days_worked: int) -> dict:
    """Calcula finiquito (renuncia voluntaria).

    Incluye: aguinaldo proporcional + vacaciones proporcionales + prima vacacional.
    Si la antiguedad es >= 15 anos, incluye ademas prima de antiguedad
    (Art. 162-III LFT: la renuncia voluntaria solo genera este derecho a
    partir de 15 anos de servicio).

    `years` acepta decimales: la prima de antiguedad se paga tambien por la
    fraccion de anio (Art. 162-I LFT), asi que 5.5 anos rinde 5.5 x 12 dias.
    """
    ag = calculate_aguinaldo(daily_salary, days_worked)
    vac = calculate_vacaciones(daily_salary, years, days_worked)
    vac_salary = vac["dias"] * daily_salary

    # Prima de antiguedad: 12 dias por ano (proporcional por fraccion, Art.
    # 162-I LFT), tope de 2 veces el SALARIO MINIMO general diario (Art.
    # 162/486 LFT) — NO 2 veces la UMA.
    seniority_daily = min(daily_salary, SALARIO_MINIMO_DAILY * 2)
    seniority = seniority_daily * 12 * years if years >= 15 else 0.0

    total = ag["bruto"] + vac_salary + vac["prima_bruta"] + seniority
    return {
        "aguinaldo": ag["bruto"],
        "vacaciones_dias": vac["dias"],
        "vacaciones_pago": vac_salary,
        "prima_vacacional": vac["prima_bruta"],
        "prima_antiguedad": seniority,
        "total": total,
    }


def calculate_liquidacion(daily_salary: float, years: float, days_worked: int) -> dict:
    """Calcula liquidacion (despido injustificado).

    Incluye: finiquito + 3 meses constitucional + 20 dias/ano + prima antiguedad.
    """
    fin = calculate_finiquito(daily_salary, years, days_worked)

    # SDI (Salario Diario Integrado, Art. 89 LFT) con factor de integracion
    # minimo, usado para la indemnizacion (3 meses y 20 dias/ano).
    sdi = daily_salary * (365 + AGUINALDO_MIN_DAYS + _get_vacation_days(years) * 0.25) / 365

    # Los 3 meses constitucionales se calculan con SDI, igual que el 20 dias/ano
    # (Art. 89 LFT: las indemnizaciones se pagan con el salario INTEGRADO). Es
    # el criterio dominante de la SCJN para toda indemnizacion por despido.
    three_months = sdi * 90
    twenty_per_year = sdi * 20 * years

    # Prima de antiguedad: 12 dias por ano (proporcional por fraccion, Art.
    # 162-I LFT), tope de 2 veces el SALARIO MINIMO general diario (Art.
    # 162/486 LFT) — NO 2 veces la UMA. En despido (a diferencia de la
    # renuncia) se paga sin importar la antiguedad, por lo que aqui se
    # recalcula en vez de reusar la de calculate_finiquito (que solo aplica
    # desde 15 anos) para no perderla ni duplicarla.
    seniority_daily = min(daily_salary, SALARIO_MINIMO_DAILY * 2)
    seniority = seniority_daily * 12 * years

    total = (
        fin["total"] - fin["prima_antiguedad"] + three_months + twenty_per_year + seniority
    )
    return {
        **fin,
        "tres_meses": three_months,
        "veinte_por_ano": twenty_per_year,
        "prima_antiguedad": seniority,
        "total_liquidacion": total,
    }


# --- Interfaz de consola ---

def _ask_int(prompt: str) -> int | None:
    val = Prompt.ask(prompt).strip()
    try:
        result = int(val)
        if result < 0:
            console.print("[red]El valor no puede ser negativo.[/red]")
            return None
        return result
    except ValueError:
        console.print("[red]Valor numerico invalido.[/red]")
        return None


def _ask_years(prompt: str) -> float | None:
    """Pide anos de antiguedad: acepta decimales (la prima de antiguedad y los
    20 dias/ano se pagan tambien por la fraccion de anio) y permite 0."""
    val = Prompt.ask(prompt).strip().replace(",", ".")
    try:
        result = float(val)
        if result < 0:
            console.print("[red]El valor no puede ser negativo.[/red]")
            return None
        return result
    except ValueError:
        console.print("[red]Valor numerico invalido.[/red]")
        return None


def _option_aguinaldo() -> None:
    console.print("\n[bold cyan]Calculo de Aguinaldo[/bold cyan]\n")
    salary = _ask_float("[bold]Salario diario[/bold]")
    if not salary:
        return
    days = _ask_int("[bold]Dias trabajados en el ano[/bold]")
    if days is None:
        return

    result = calculate_aguinaldo(salary, days)

    table = Table(title="Aguinaldo", box=box.SIMPLE_HEAVY)
    table.add_column("Concepto", style="bold")
    table.add_column("Monto", justify="right")
    table.add_row("Aguinaldo bruto", _fmt(result["bruto"]))
    table.add_row("Exento (30 UMA)", _fmt(result["exento"]))
    table.add_row("Gravado", _fmt(result["gravado"]))
    console.print(table)
    console.print(DISCLAIMER)


def _option_vacaciones() -> None:
    console.print("\n[bold cyan]Calculo de Vacaciones y Prima[/bold cyan]\n")
    salary = _ask_float("[bold]Salario diario[/bold]")
    if not salary:
        return
    years = _ask_years("[bold]Anos de antiguedad[/bold] (acepta decimales, ej: 5.5)")
    if years is None:
        return
    days = _ask_int("[bold]Dias trabajados en el ano[/bold]")
    if days is None:
        return

    result = calculate_vacaciones(salary, years, days)

    table = Table(title="Vacaciones", box=box.SIMPLE_HEAVY)
    table.add_column("Concepto", style="bold")
    table.add_column("Valor", justify="right")
    table.add_row("Dias de vacaciones", f"{result['dias']:.1f}")
    table.add_row("Prima vacacional bruta", _fmt(result["prima_bruta"]))
    table.add_row("Prima exenta (15 UMA)", _fmt(result["prima_exenta"]))
    table.add_row("Prima gravada", _fmt(result["prima_gravada"]))
    console.print(table)
    console.print(DISCLAIMER)


def _option_finiquito() -> None:
    console.print("\n[bold cyan]Calculo de Finiquito (Renuncia)[/bold cyan]\n")
    salary = _ask_float("[bold]Salario diario[/bold]")
    if not salary:
        return
    years = _ask_years("[bold]Anos de antiguedad[/bold] (acepta decimales, ej: 5.5)")
    if years is None:
        return
    days = _ask_int("[bold]Dias trabajados en el ano actual[/bold]")
    if days is None:
        return

    result = calculate_finiquito(salary, years, days)

    table = Table(title="Finiquito", box=box.SIMPLE_HEAVY)
    table.add_column("Concepto", style="bold")
    table.add_column("Monto", justify="right")
    table.add_row("Aguinaldo proporcional", _fmt(result["aguinaldo"]))
    table.add_row(f"Vacaciones ({result['vacaciones_dias']:.1f} dias)", _fmt(result["vacaciones_pago"]))
    table.add_row("Prima vacacional", _fmt(result["prima_vacacional"]))
    if result["prima_antiguedad"] > 0:
        table.add_row("Prima de antiguedad (>=15 anos)", _fmt(result["prima_antiguedad"]))
    table.add_row("[bold]Total finiquito[/bold]", f"[bold]{_fmt(result['total'])}[/bold]")
    console.print(table)
    console.print(DISCLAIMER)


def _option_liquidacion() -> None:
    console.print("\n[bold cyan]Calculo de Liquidacion (Despido)[/bold cyan]\n")
    salary = _ask_float("[bold]Salario diario[/bold]")
    if not salary:
        return
    years = _ask_years("[bold]Anos de antiguedad[/bold] (acepta decimales, ej: 5.5)")
    if years is None:
        return
    days = _ask_int("[bold]Dias trabajados en el ano actual[/bold]")
    if days is None:
        return

    result = calculate_liquidacion(salary, years, days)

    table = Table(title="Liquidacion", box=box.SIMPLE_HEAVY)
    table.add_column("Concepto", style="bold")
    table.add_column("Monto", justify="right")
    table.add_row("Aguinaldo proporcional", _fmt(result["aguinaldo"]))
    table.add_row(f"Vacaciones ({result['vacaciones_dias']:.1f} dias)", _fmt(result["vacaciones_pago"]))
    table.add_row("Prima vacacional", _fmt(result["prima_vacacional"]))
    table.add_row("3 meses (constitucional)", _fmt(result["tres_meses"]))
    table.add_row("20 dias por ano", _fmt(result["veinte_por_ano"]))
    table.add_row("Prima de antiguedad", _fmt(result["prima_antiguedad"]))
    table.add_row("[bold]Total liquidacion[/bold]", f"[bold]{_fmt(result['total_liquidacion'])}[/bold]")
    console.print(table)
    console.print(DISCLAIMER)


def prestaciones_menu() -> None:
    """Sub-menu del simulador de prestaciones."""
    while True:
        console.print(
            Panel(
                "[bold]1[/bold] - Aguinaldo\n"
                "[bold]2[/bold] - Vacaciones y Prima\n"
                "[bold]3[/bold] - Finiquito (renuncia)\n"
                "[bold]4[/bold] - Liquidacion (despido)\n"
                "[bold]0[/bold] - Volver",
                title="[bold yellow]Simulador de Prestaciones[/bold yellow]",
                box=box.ROUNDED,
            )
        )
        choice = Prompt.ask("[bold cyan]Opcion[/bold cyan]", default="0")

        if choice == "1":
            _option_aguinaldo()
        elif choice == "2":
            _option_vacaciones()
        elif choice == "3":
            _option_finiquito()
        elif choice == "4":
            _option_liquidacion()
        elif choice == "0":
            break
        else:
            console.print("[red]Opcion no valida.[/red]")

        if choice in ("1", "2", "3", "4"):
            Prompt.ask("\n[dim]Presiona Enter para continuar[/dim]", default="")
