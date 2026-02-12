"""Simulador de prestaciones laborales Mexico."""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box

from config import AGUINALDO_MIN_DAYS, UMA_DAILY, VACATION_DAYS_TABLE

console = Console()

DISCLAIMER = (
    "[dim italic]Este calculo es un estimado con fines informativos. "
    "Consulta con un contador o abogado laboral para cifras exactas.[/dim italic]"
)


def _get_vacation_days(years: int) -> int:
    """Dias de vacaciones segun antiguedad (LFT 2023+)."""
    if years <= 0:
        return 0
    if years <= 20:
        return VACATION_DAYS_TABLE.get(years, 20)
    # Despues de 20 anos: +2 dias por cada 5 anos adicionales
    extra = ((years - 20) // 5) * 2
    return 26 + extra


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


def _fmt(amount: float) -> str:
    return f"${amount:,.2f}"


def calculate_aguinaldo(daily_salary: float, days_worked: int) -> dict:
    """Calcula aguinaldo proporcional.

    Returns:
        dict con bruto, exento (30 UMA), gravado
    """
    proportional = (days_worked / 365) * AGUINALDO_MIN_DAYS * daily_salary
    exempt = UMA_DAILY * 30  # 30 dias de UMA exentos
    taxable = max(0, proportional - exempt)
    return {"bruto": proportional, "exento": min(proportional, exempt), "gravado": taxable}


def calculate_vacaciones(daily_salary: float, years: int, days_worked: int) -> dict:
    """Calcula prima vacacional proporcional (25%).

    Returns:
        dict con dias, prima_bruta, prima_exenta (15 UMA)
    """
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


def calculate_finiquito(daily_salary: float, years: int, days_worked: int) -> dict:
    """Calcula finiquito (renuncia voluntaria).

    Incluye: aguinaldo proporcional + vacaciones proporcionales + prima vacacional.
    """
    ag = calculate_aguinaldo(daily_salary, days_worked)
    vac = calculate_vacaciones(daily_salary, years, days_worked)
    vac_salary = vac["dias"] * daily_salary

    total = ag["bruto"] + vac_salary + vac["prima_bruta"]
    return {
        "aguinaldo": ag["bruto"],
        "vacaciones_dias": vac["dias"],
        "vacaciones_pago": vac_salary,
        "prima_vacacional": vac["prima_bruta"],
        "total": total,
    }


def calculate_liquidacion(daily_salary: float, years: int, days_worked: int) -> dict:
    """Calcula liquidacion (despido injustificado).

    Incluye: finiquito + 3 meses constitucional + 20 dias/ano + prima antiguedad.
    """
    fin = calculate_finiquito(daily_salary, years, days_worked)

    three_months = daily_salary * 90
    twenty_per_year = daily_salary * 20 * years

    # Prima de antiguedad: 12 dias por ano, tope de 2 UMA diarios
    seniority_daily = min(daily_salary, UMA_DAILY * 2)
    seniority = seniority_daily * 12 * years

    total = fin["total"] + three_months + twenty_per_year + seniority
    return {
        **fin,
        "tres_meses": three_months,
        "veinte_por_ano": twenty_per_year,
        "prima_antiguedad": seniority,
        "total_liquidacion": total,
    }


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
    years = _ask_int("[bold]Anos de antiguedad[/bold]")
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
    years = _ask_int("[bold]Anos de antiguedad[/bold]")
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
    table.add_row("[bold]Total finiquito[/bold]", f"[bold]{_fmt(result['total'])}[/bold]")
    console.print(table)
    console.print(DISCLAIMER)


def _option_liquidacion() -> None:
    console.print("\n[bold cyan]Calculo de Liquidacion (Despido)[/bold cyan]\n")
    salary = _ask_float("[bold]Salario diario[/bold]")
    if not salary:
        return
    years = _ask_int("[bold]Anos de antiguedad[/bold]")
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
