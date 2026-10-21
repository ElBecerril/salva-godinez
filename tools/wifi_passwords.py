"""Recuperador de contrasenas WiFi guardadas en Windows."""

import ctypes
import subprocess
import unicodedata

from rich.markup import escape
from rich.prompt import Prompt
from rich.table import Table
from utils import console


# --- Logica (sin UI) ---


def _mask(password: str) -> str:
    """Enmascara una contrasena con un placeholder de longitud fija.

    No revela ningun caracter real (ni el primero ni el ultimo).
    """
    return "*" * 8


def _oem_encoding() -> str:
    """Pagina de codigos con la que netsh escribe su salida (cp850 en Windows
    en espanol, cp437 en ingles...). NO es UTF-8: decodificarla como UTF-8
    convertia 'Autenticacion' (con tilde) en 'Autenticaci?n' y los nombres de
    red con n con tilde o acentos quedaban corruptos."""
    try:
        return f"cp{ctypes.windll.kernel32.GetOEMCP()}"
    except (AttributeError, OSError):
        return "utf-8"


def _plain(texto: str) -> str:
    """Minusculas y sin acentos, para comparar etiquetas de netsh en cualquier
    idioma ('Autenticacion' y 'Autenticacion' con tilde son lo mismo)."""
    sin_acentos = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_acentos if not unicodedata.combining(c)).lower()


def _run_netsh(args: list[str]):
    """Corre netsh y devuelve un objeto con returncode y stdout YA decodificado
    con la pagina de codigos del sistema."""
    crudo = subprocess.run(
        ["netsh"] + args,
        capture_output=True, timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        texto = (crudo.stdout or b"").decode(_oem_encoding(), errors="replace")
    except LookupError:
        texto = (crudo.stdout or b"").decode("utf-8", errors="replace")

    class _Salida:
        returncode = crudo.returncode
        stdout = texto

    return _Salida


def get_wifi_passwords() -> list[dict]:
    """Obtiene las redes WiFi guardadas y sus contrasenas."""
    results = []

    try:
        # Listar perfiles WiFi
        output = _run_netsh(["wlan", "show", "profiles"])
        if output.returncode != 0:
            return results

        profiles = []
        for line in output.stdout.splitlines():
            # Soporte espanol e ingles
            etiqueta = _plain(line)
            if "all user profile" in etiqueta or "perfil de todos los usuarios" in etiqueta:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    profiles.append(parts[1].strip())

        for profile in profiles:
            info = {"red": profile, "contrasena": "", "seguridad": ""}
            try:
                detail = _run_netsh(["wlan", "show", "profile", profile, "key=clear"])
                for line in detail.stdout.splitlines():
                    line_stripped = line.strip()
                    etiqueta = _plain(line_stripped)
                    # Contrasena (espanol / ingles)
                    if "key content" in etiqueta or "contenido de la clave" in etiqueta:
                        parts = line_stripped.split(":", 1)
                        if len(parts) > 1:
                            info["contrasena"] = parts[1].strip()
                    # Tipo de seguridad
                    if ("authentication" in etiqueta and "open" not in etiqueta) or \
                       "autenticacion" in etiqueta:
                        parts = line_stripped.split(":", 1)
                        if len(parts) > 1 and not info["seguridad"]:
                            info["seguridad"] = parts[1].strip()
            except (subprocess.TimeoutExpired, OSError):
                info["contrasena"] = "Error al obtener"

            results.append(info)

    except (subprocess.TimeoutExpired, OSError):
        pass

    return results


# --- Interfaz de consola ---


def show_wifi_passwords() -> None:
    """Muestra las redes WiFi y contrasenas en una tabla Rich."""
    with console.status("[bold green]Obteniendo redes WiFi guardadas..."):
        networks = get_wifi_passwords()

    if not networks:
        console.print("[yellow]No se encontraron redes WiFi guardadas.[/yellow]")
        return

    reveal = Prompt.ask(
        "[bold]Mostrar contrasenas en texto plano?[/bold]",
        choices=["s", "n"], default="n",
    )
    show_plain = reveal == "s"

    table = Table(title=f"Redes WiFi guardadas ({len(networks)})")
    table.add_column("#", style="bold cyan", width=4, justify="right")
    table.add_column("Red", style="bold white", max_width=30)
    table.add_column("Contrasena", style="green", max_width=30)
    table.add_column("Seguridad", style="yellow", max_width=20)

    for i, net in enumerate(networks, 1):
        pwd = net["contrasena"]
        if not pwd:
            display = "[dim]Sin contrasena[/dim]"
        elif show_plain:
            display = escape(pwd)
        else:
            display = _mask(pwd)
        table.add_row(str(i), escape(net["red"]), display, escape(net["seguridad"]))

    console.print()
    console.print(table)
