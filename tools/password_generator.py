"""Generador de contrasenas seguras."""

import secrets
import string
import subprocess

from rich.console import Console
from rich.prompt import Prompt

console = Console()


def generate_password(length: int = 16, use_symbols: bool = True) -> str:
    """Genera una contrasena segura usando el modulo secrets."""
    chars = string.ascii_letters + string.digits
    if use_symbols:
        chars += "!@#$%&*+-_=?"
    # Garantizar al menos un caracter de cada tipo
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
    ]
    if use_symbols:
        password.append(secrets.choice("!@#$%&*+-_=?"))
    remaining = length - len(password)
    password.extend(secrets.choice(chars) for _ in range(remaining))
    # Mezclar para que los caracteres garantizados no esten siempre al inicio
    result = list(password)
    secrets.SystemRandom().shuffle(result)
    return "".join(result)


def copy_to_clipboard(text: str) -> bool:
    """Copia texto al portapapeles usando clip.exe (Windows builtin)."""
    try:
        process = subprocess.run(
            ["clip.exe"],
            input=text,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return process.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def password_generator_menu() -> None:
    """Interfaz interactiva para generar contrasenas."""
    console.print("\n[bold cyan]Generador de Contrasenas Seguras[/bold cyan]\n")

    length_str = Prompt.ask(
        "[bold]Longitud de la contrasena[/bold]", default="16"
    )
    try:
        length = int(length_str)
        if length < 8:
            console.print("[yellow]Longitud minima: 8 caracteres.[/yellow]")
            length = 8
        elif length > 128:
            console.print("[yellow]Longitud maxima: 128 caracteres.[/yellow]")
            length = 128
    except ValueError:
        console.print("[yellow]Valor invalido, usando 16.[/yellow]")
        length = 16

    use_symbols = Prompt.ask(
        "[bold]Incluir simbolos (!@#$%&*)?[/bold]", choices=["s", "n"], default="s"
    ) == "s"

    password = generate_password(length, use_symbols)
    console.print(f"\n[bold green]Contrasena generada:[/bold green] [white on black] {password} [/white on black]")

    if copy_to_clipboard(password):
        console.print("[dim]Copiada al portapapeles.[/dim]")
    else:
        console.print("[dim yellow]No se pudo copiar al portapapeles.[/dim yellow]")
