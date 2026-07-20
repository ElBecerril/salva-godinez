"""Funciones compartidas entre los modulos fiscales (salario, retenciones, prestaciones)."""

from rich.prompt import Prompt
from utils import console


# --- Logica (sin UI) ---

def fmt(amount: float) -> str:
    """Formatea un monto como moneda: $1,234.56"""
    return f"${amount:,.2f}"


def find_bracket(income: float, table: list[tuple]) -> tuple:
    """Busca el rango correspondiente en una tabla progresiva.

    Usa un intervalo semi-abierto [limite_inferior, siguiente_limite_inferior)
    en vez de [limite_inferior, limite_superior] declarado en la tabla: los
    limites superior/inferior de renglones consecutivos en las tablas del SAT
    no son exactamente contiguos (ej. 844.59 vs 844.60), y comparar contra el
    limite superior declarado puede dejar huecos por errores de punto
    flotante donde ningun rango calza y la funcion devolveria None
    silenciosamente (ISR de $0 sin aviso). Con el limite inferior del
    siguiente renglon como corte, no quedan huecos.
    """
    if income < table[0][0]:
        raise ValueError(
            f"Ingreso {income} por debajo del primer limite inferior de la tabla ({table[0][0]})."
        )

    for idx, row in enumerate(table):
        lim_inf = row[0]
        upper_bound = table[idx + 1][0] if idx + 1 < len(table) else float("inf")
        if lim_inf <= income < upper_bound:
            return row

    # No deberia llegarse aqui si la tabla cubre hasta infinito, pero se deja
    # un error explicito en vez de un 0 silencioso por si la tabla esta mal
    # construida.
    raise ValueError(f"No se encontro un bracket para el ingreso {income} en la tabla proporcionada.")


# --- Interfaz de consola ---

DISCLAIMER = (
    "[yellow]Esto es una ESTIMACION informativa, NO es lo que legalmente te "
    "deben ni una asesoria oficial.[/yellow]\n"
    "[dim]No considera casos especiales (comisiones, salario variable, bonos, "
    "convenios de empresa, antiguedad interrumpida u otros). Para tu caso real, "
    "gratis y oficial:\n"
    "  - Laboral (finiquito, liquidacion, despido): PROFEDET - profedet.gob.mx\n"
    "  - Impuestos (ISR, RESICO, retenciones): SAT - sat.gob.mx[/dim]"
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
