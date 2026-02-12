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
        subprocess.run(
            ["net", "stop", "spooler"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
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
        subprocess.run(
            ["net", "start", "spooler"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        console.print(f"[red]Error al reiniciar spooler: {e}[/red]")
        return

    if removed:
        console.print(f"[bold green]Cola limpiada: {removed} archivo(s) eliminado(s).[/bold green]")
    else:
        console.print("[green]Spooler reiniciado. La cola ya estaba vacia.[/green]")
