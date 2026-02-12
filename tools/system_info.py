"""Informacion del sistema: hostname, IP, MAC, Windows, usuario."""

import os
import platform
import socket
import uuid

from rich.console import Console
from rich.table import Table

console = Console()


def get_system_info() -> dict:
    """Recopila informacion basica del sistema."""
    info = {}
    info["hostname"] = socket.gethostname()
    try:
        info["ip"] = socket.gethostbyname(info["hostname"])
    except socket.gaierror:
        info["ip"] = "No disponible"
    info["mac"] = ":".join(
        f"{(uuid.getnode() >> i) & 0xFF:02x}" for i in range(40, -1, -8)
    )
    info["sistema"] = f"{platform.system()} {platform.release()}"
    info["version"] = platform.version()
    info["arquitectura"] = platform.machine()
    info["procesador"] = platform.processor() or "No disponible"
    info["usuario"] = os.environ.get("USERNAME", os.environ.get("USER", "Desconocido"))
    info["dominio"] = os.environ.get("USERDOMAIN", "N/A")
    return info


def show_system_info() -> None:
    """Muestra la informacion del sistema en una tabla Rich."""
    with console.status("[bold green]Recopilando informacion del sistema..."):
        info = get_system_info()

    table = Table(title="Informacion del Sistema", show_header=False, padding=(0, 2))
    table.add_column("Campo", style="bold cyan", width=16)
    table.add_column("Valor", style="white")

    labels = {
        "hostname": "Hostname",
        "ip": "IP Local",
        "mac": "MAC Address",
        "sistema": "Sistema",
        "version": "Version",
        "arquitectura": "Arquitectura",
        "procesador": "Procesador",
        "usuario": "Usuario",
        "dominio": "Dominio",
    }

    for key, label in labels.items():
        table.add_row(label, info.get(key, "?"))

    console.print()
    console.print(table)
