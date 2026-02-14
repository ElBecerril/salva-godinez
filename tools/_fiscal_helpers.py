"""Funciones compartidas entre los modulos fiscales (salario, retenciones, prestaciones)."""

from rich.prompt import Prompt
from utils import console


DISCLAIMER = (
    "[dim italic]Este calculo es un estimado con fines informativos. "
    "Consulta con un contador para cifras exactas.[/dim italic]"
)


def ask_float(prompt: str) -> float | None:
    """Pide un numero flotante positivo al usuario."""
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


def fmt(amount: float) -> str:
    """Formatea un monto como moneda: $1,234.56"""
    return f"${amount:,.2f}"


def find_bracket(income: float, table: list[tuple]) -> tuple | None:
    """Busca el rango correspondiente en una tabla progresiva."""
    for row in table:
        if row[0] <= income <= row[1]:
            return row
    return None
