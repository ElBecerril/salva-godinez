"""Reset de cola de impresion de Windows."""

import os
import subprocess


from tools import is_admin
from utils import console


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
            encoding="utf-8", errors="replace",
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
    failed_removals = []
    if os.path.isdir(SPOOL_PATH):
        for fname in os.listdir(SPOOL_PATH):
            filepath = os.path.join(SPOOL_PATH, fname)
            try:
                os.remove(filepath)
                removed += 1
            except OSError as e:
                failed_removals.append((fname, str(e)))

    console.print("[bold yellow]Reiniciando servicio de impresion...[/bold yellow]")
    try:
        result = subprocess.run(
            ["net", "start", "spooler"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        start_failed = result.returncode != 0
        if start_failed:
            console.print(f"[red]No se pudo reiniciar el spooler: {result.stderr.strip()}[/red]")
    except (subprocess.TimeoutExpired, OSError) as e:
        console.print(f"[red]Error al reiniciar spooler: {e}[/red]")
        start_failed = True

    # Verificar el estado real del servicio en vez de confiar solo en el
    # returncode de 'net start' (puede devolver 0 sin que el servicio haya
    # terminado de arrancar, o el propio comando puede fallar por otra razon).
    running = False
    try:
        query = subprocess.run(
            ["sc", "query", "spooler"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        running = query.returncode == 0 and "RUNNING" in query.stdout.upper()
    except (subprocess.TimeoutExpired, OSError) as e:
        console.print(f"[yellow]No se pudo verificar el estado del servicio: {e}[/yellow]")

    if not running:
        console.print("[bold red]El servicio de impresion no quedo corriendo.[/bold red]")
        console.print("[dim]Intenta reiniciar el servicio 'Print Spooler' manualmente (services.msc).[/dim]")
        if removed:
            console.print(f"[yellow]Se eliminaron {removed} archivo(s) de la cola antes de la falla.[/yellow]")
        if failed_removals:
            console.print(
                f"[yellow]{len(failed_removals)} archivo(s) de la cola no se pudieron eliminar.[/yellow]"
            )
        return

    if failed_removals:
        console.print(
            f"[yellow]Spooler reiniciado, pero {len(failed_removals)} archivo(s) de la cola "
            "no se pudieron eliminar (pueden seguir en la lista de impresion).[/yellow]"
        )
        for fname, err in failed_removals:
            console.print(f"  [dim]- {fname}: {err}[/dim]")
    elif removed:
        console.print(f"[bold green]Cola limpiada: {removed} archivo(s) eliminado(s). Spooler reiniciado correctamente.[/bold green]")
    else:
        console.print("[green]Spooler reiniciado correctamente. La cola ya estaba vacia.[/green]")
