"""Verificador de conexion: ping y prueba de puertos."""

import socket
import subprocess

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

console = Console()


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
            low = line.strip().lower()
            # Paquetes enviados (espanol / ingles)
            if "recibidos" in low or "received" in low:
                parts = low.replace("=", " ").replace(",", " ").split()
                nums = [p for p in parts if p.isdigit()]
                if len(nums) >= 3:
                    info["sent"] = int(nums[0])
                    info["received"] = int(nums[1])
                    info["lost"] = int(nums[2])
            # Tiempos (espanol / ingles)
            if ("nimo" in low or "minimum" in low) and "ms" in low:
                parts = low.replace("=", " ").replace(",", " ").replace("ms", " ").split()
                nums = [p for p in parts if p.replace(".", "").isdigit()]
                if len(nums) >= 3:
                    info["min_ms"] = nums[0]
                    info["max_ms"] = nums[1]
                    info["avg_ms"] = nums[2]

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
