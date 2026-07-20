"""Reset de cola de impresion de Windows."""

import os
import subprocess

from rich.prompt import Confirm

from tools import is_admin
from utils import console


SPOOL_PATH = os.path.join(os.environ.get("SYSTEMROOT", r"C:\Windows"),
                          "System32", "spool", "PRINTERS")


# --- Logica (sin UI) ---


def _count_pending_jobs() -> int:
    """Cuenta los archivos en la cola de impresion."""
    if not os.path.isdir(SPOOL_PATH):
        return 0
    try:
        return sum(1 for _ in os.listdir(SPOOL_PATH))
    except OSError:
        return 0


def _stop_spooler_service() -> dict:
    """Detiene el servicio de impresion via 'net stop spooler'.

    Retorna {"ok": True, "returncode": int, "stderr": str, "already_stopped": bool}
    si el subprocess corrio, o {"ok": False, "error": str} si no se pudo ejecutar.
    """
    try:
        result = subprocess.run(
            ["net", "stop", "spooler"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        already_stopped = False
        if result.returncode != 0:
            # returncode distinto de 0 puede ser porque el servicio ya
            # estaba detenido, no es error real.
            stderr_lower = result.stderr.lower()
            already_stopped = (
                "3521" in result.stderr
                or "already" in stderr_lower
                or "ya" in stderr_lower
            )
        return {
            "ok": True,
            "returncode": result.returncode,
            "stderr": result.stderr,
            "already_stopped": already_stopped,
        }
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"ok": False, "error": str(e)}


def _clear_spool_queue() -> dict:
    """Elimina los archivos de la cola de impresion.

    Retorna {"removed": int, "failed": [(nombre, error), ...]}.
    """
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
    return {"removed": removed, "failed": failed_removals}


def _start_spooler_service() -> dict:
    """Inicia el servicio de impresion via 'net start spooler'.

    Retorna {"ok": bool, "stderr": str} si corrio, o
    {"ok": False, "error": str} si no se pudo ejecutar.
    """
    try:
        result = subprocess.run(
            ["net", "start", "spooler"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return {"ok": result.returncode == 0, "stderr": result.stderr}
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"ok": False, "error": str(e)}


def _check_spooler_running() -> dict:
    """Verifica el estado real del servicio con 'sc query spooler'.

    Retorna {"running": bool} o {"running": False, "error": str} si la
    consulta fallo.
    """
    try:
        query = subprocess.run(
            ["sc", "query", "spooler"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        running = query.returncode == 0 and "RUNNING" in query.stdout.upper()
        return {"running": running}
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"running": False, "error": str(e)}


# --- Interfaz de consola ---


def reset_spooler() -> None:
    """Detiene el spooler, limpia la cola y lo reinicia."""
    if not is_admin():
        console.print(
            "[bold red]Se requieren permisos de administrador.[/bold red]\n"
            "[dim]Ejecuta el programa como administrador e intenta de nuevo.[/dim]"
        )
        return

    # Contar los trabajos en cola para advertir antes de borrarlos: limpiar la
    # cola cancela impresiones pendientes de TODOS los usuarios de la PC y es
    # irreversible, asi que exige una confirmacion explicita.
    pending = _count_pending_jobs()

    if pending:
        console.print(
            f"\n[bold red]La cola de impresion tiene {pending} archivo(s) pendiente(s).[/bold red]"
        )
        console.print(
            "[red]Limpiarla cancela las impresiones en espera de TODOS los usuarios de "
            "esta PC y no se puede deshacer.[/red]"
        )
        if not Confirm.ask(
            "[bold red]Continuar y limpiar la cola de impresion?[/bold red]",
            default=False,
        ):
            console.print("[dim]Operacion cancelada. No se toco la cola.[/dim]")
            return

    console.print("[bold yellow]Deteniendo servicio de impresion...[/bold yellow]")
    stop_result = _stop_spooler_service()
    if not stop_result["ok"]:
        console.print(f"[red]Error al detener spooler: {stop_result['error']}[/red]")
        return
    if stop_result["returncode"] != 0 and not stop_result["already_stopped"]:
        console.print(f"[yellow]Advertencia al detener spooler: {stop_result['stderr'].strip()}[/yellow]")

    # Limpiar archivos de la cola
    clear_result = _clear_spool_queue()
    removed = clear_result["removed"]
    failed_removals = clear_result["failed"]

    console.print("[bold yellow]Reiniciando servicio de impresion...[/bold yellow]")
    start_result = _start_spooler_service()
    if not start_result["ok"] and "error" in start_result:
        console.print(f"[red]Error al reiniciar spooler: {start_result['error']}[/red]")
        start_failed = True
    else:
        start_failed = not start_result["ok"]
        if start_failed:
            console.print(f"[red]No se pudo reiniciar el spooler: {start_result['stderr'].strip()}[/red]")

    # Verificar el estado real del servicio en vez de confiar solo en el
    # returncode de 'net start' (puede devolver 0 sin que el servicio haya
    # terminado de arrancar, o el propio comando puede fallar por otra razon).
    running_result = _check_spooler_running()
    running = running_result["running"]
    if "error" in running_result:
        console.print(f"[yellow]No se pudo verificar el estado del servicio: {running_result['error']}[/yellow]")

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
