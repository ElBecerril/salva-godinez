"""Reset de cola de impresion de Windows."""

import os
import subprocess

from rich.console import Console

from tools import is_admin

console = Console()

SPOOL_PATH = os.path.join(os.environ.get("SYSTEMROOT", r"C:\Windows"),
                          "System32", "spool", "PRINTERS")


def reset_spooler() -> None:
    """Detiene el spooler, limpia la cola y lo reinicia."""
    if not is_admin():
        console.print(
            "[bold red]Se requieren permisos de administrador.[/bold red]\n"
            "[dim]Ejecuta el programa como administrador e intenta de nuevo.[/dim]"
        )
        return

    console.print("[bold yellow]Deteniendo servicio de impresion...[/bold yellow]")
    try:
        result = subprocess.run(
            ["net", "stop", "spooler"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            # returncode 2 = servicio ya estaba detenido, no es error real
            if "3521" not in result.stderr and "already" not in result.stderr.lower() \
                    and "ya" not in result.stderr.lower():
                console.print(f"[yellow]Advertencia al detener spooler: {result.stderr.strip()}[/yellow]")
    except (subprocess.TimeoutExpired, OSError) as e:
        console.print(f"[red]Error al detener spooler: {e}[/red]")
        return

    # Limpiar archivos de la cola
    removed = 0
    if os.path.isdir(SPOOL_PATH):
        for fname in os.listdir(SPOOL_PATH):
            filepath = os.path.join(SPOOL_PATH, fname)
            try:
                os.remove(filepath)
                removed += 1
            except OSError:
                pass

    console.print("[bold yellow]Reiniciando servicio de impresion...[/bold yellow]")
    try:
        result = subprocess.run(
            ["net", "start", "spooler"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            console.print(f"[red]No se pudo reiniciar el spooler: {result.stderr.strip()}[/red]")
            console.print("[dim]Intenta reiniciar el servicio 'Print Spooler' manualmente.[/dim]")
            return
    except (subprocess.TimeoutExpired, OSError) as e:
        console.print(f"[red]Error al reiniciar spooler: {e}[/red]")
        return

    if removed:
        console.print(f"[bold green]Cola limpiada: {removed} archivo(s) eliminado(s).[/bold green]")
    else:
        console.print("[green]Spooler reiniciado. La cola ya estaba vacia.[/green]")
