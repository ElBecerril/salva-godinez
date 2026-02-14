"""Verificador de conexion: ping y prueba de puertos."""

import re
import socket
import subprocess

from rich.prompt import Prompt
from rich.table import Table
from utils import console


# Regex para la linea de estadisticas de paquetes (funciona en cualquier locale)
# Busca 3 numeros que representan enviados, recibidos, perdidos
_PKT_REGEX = re.compile(
    r"(\d+).*?(\d+).*?(\d+).*?(?:%|perdidos|lost)",
    re.IGNORECASE,
)

# Regex para la linea de tiempos min/max/avg (funciona en cualquier locale)
# Busca 3 valores numericos seguidos de "ms"
_TIME_REGEX = re.compile(
    r"(\d+)\s*ms.*?(\d+)\s*ms.*?(\d+)\s*ms",
    re.IGNORECASE,
)


def ping_host(host: str, count: int = 4) -> dict:
    """Ejecuta ping y parsea el resultado.

    Returns:
        dict con llaves: ok, sent, received, lost, min_ms, max_ms, avg_ms, output
    """
    try:
        result = subprocess.run(
            ["ping", "-n", str(count), host],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        output = result.stdout + result.stderr
        info: dict = {"ok": result.returncode == 0, "output": output,
                      "sent": count, "received": 0, "lost": count,
                      "min_ms": "-", "max_ms": "-", "avg_ms": "-"}

        for line in output.splitlines():
            # Paquetes: busca linea con 3 numeros + "perdidos"/"lost"/%
            m = _PKT_REGEX.search(line)
            if m:
                info["sent"] = int(m.group(1))
                info["received"] = int(m.group(2))
                info["lost"] = int(m.group(3))
            # Tiempos: busca linea con 3 valores en ms
            m = _TIME_REGEX.search(line)
            if m:
                info["min_ms"] = m.group(1)
                info["max_ms"] = m.group(2)
                info["avg_ms"] = m.group(3)

        return info
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "Timeout", "sent": count,
                "received": 0, "lost": count,
                "min_ms": "-", "max_ms": "-", "avg_ms": "-"}
    except OSError as e:
        return {"ok": False, "output": str(e), "sent": 0,
                "received": 0, "lost": 0,
                "min_ms": "-", "max_ms": "-", "avg_ms": "-"}


def check_port(host: str, port: int, timeout: int = 3) -> bool:
    """Verifica si un puerto esta abierto."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def ping_checker_menu() -> None:
    """Menu del verificador de conexion."""
    console.print("\n[bold cyan]Verificador de Conexion[/bold cyan]\n")

    host = Prompt.ask("[bold]IP o nombre del equipo[/bold]").strip()
    if not host:
        console.print("[red]Debes ingresar una IP o nombre.[/red]")
        return

    with console.status(f"[bold green]Haciendo ping a {host}..."):
        info = ping_host(host)

    if info["ok"]:
        console.print(f"\n[bold green]Respuesta de {host}[/bold green]")
    else:
        console.print(f"\n[bold red]Sin respuesta de {host}[/bold red]")

    table = Table()
    table.add_column("Metrica", style="bold")
    table.add_column("Valor")
    table.add_row("Enviados", str(info["sent"]))
    table.add_row("Recibidos", str(info["received"]))
    table.add_row("Perdidos", str(info["lost"]))
    table.add_row("Min (ms)", str(info["min_ms"]))
    table.add_row("Max (ms)", str(info["max_ms"]))
    table.add_row("Promedio (ms)", str(info["avg_ms"]))
    console.print(table)

    # Ofrecer verificar puertos de impresora
    check_ports = Prompt.ask(
        "\n[bold]Verificar puertos de impresora?[/bold]",
        choices=["s", "n"], default="n",
    )
    if check_ports == "s":
        printer_ports = [(9100, "RAW/JetDirect"), (631, "IPP/CUPS"), (515, "LPD")]
        console.print()
        for port, desc in printer_ports:
            with console.status(f"[bold green]Probando puerto {port}..."):
                ok = check_port(host, port)
            status = "[green]Abierto[/green]" if ok else "[red]Cerrado[/red]"
            console.print(f"  Puerto {port} ({desc}): {status}")
