"""Recuperador de contrasenas WiFi guardadas en Windows."""

import subprocess

from rich.prompt import Prompt
from rich.table import Table
from utils import console



def _mask(password: str) -> str:
    """Enmascara una contrasena mostrando solo el primer y ultimo caracter."""
    if len(password) <= 2:
        return "*" * len(password)
    return password[0] + "*" * (len(password) - 2) + password[-1]


def get_wifi_passwords() -> list[dict]:
    """Obtiene las redes WiFi guardadas y sus contrasenas."""
    results = []

    try:
        # Listar perfiles WiFi
        output = subprocess.run(
            ["netsh", "wlan", "show", "profiles"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if output.returncode != 0:
            return results

        profiles = []
        for line in output.stdout.splitlines():
            # Soporte espanol e ingles
            if "All User Profile" in line or "Perfil de todos los usuarios" in line:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    profiles.append(parts[1].strip())

        for profile in profiles:
            info = {"red": profile, "contrasena": "", "seguridad": ""}
            try:
                detail = subprocess.run(
                    ["netsh", "wlan", "show", "profile", profile, "key=clear"],
                    capture_output=True, text=True, timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                for line in detail.stdout.splitlines():
                    line_stripped = line.strip()
                    # Contrasena (espanol / ingles)
                    if "Key Content" in line_stripped or "Contenido de la clave" in line_stripped:
                        parts = line_stripped.split(":", 1)
                        if len(parts) > 1:
                            info["contrasena"] = parts[1].strip()
                    # Tipo de seguridad
                    if ("Authentication" in line_stripped and "open" not in line_stripped.lower()) or \
                       "Autenticacion" in line_stripped:
                        parts = line_stripped.split(":", 1)
                        if len(parts) > 1 and not info["seguridad"]:
                            info["seguridad"] = parts[1].strip()
            except (subprocess.TimeoutExpired, OSError):
                info["contrasena"] = "Error al obtener"

            results.append(info)

    except (subprocess.TimeoutExpired, OSError):
        pass

    return results


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
            display = pwd
        else:
            display = _mask(pwd)
        table.add_row(str(i), net["red"], display, net["seguridad"])

    console.print()
    console.print(table)
