"""Desbloquear archivos en uso: detecta procesos y ofrece cerrarlos."""

import ctypes
import ctypes.wintypes
import os
import subprocess

from rich.markup import escape
from rich.prompt import Prompt
from rich.table import Table

from utils import ps_escape, console


# --- Logica (sin UI) ---


def _find_locking_processes(filepath: str) -> dict:
    """Detecta procesos que tienen abierto un archivo usando Restart Manager API.

    Retorna {"procesos": [...], "certero": bool}. Restart Manager es una
    API confiable para esto, asi que su resultado (incluyendo una lista
    vacia) se marca como certero=True. Si falla y se usa el fallback de
    PowerShell, certero=False porque ese metodo no ve archivos de datos
    abiertos (ver docstring de _fallback_find_locking).
    """
    processes = []

    try:
        # Cargar rstrtmgr.dll
        rstrtmgr = ctypes.WinDLL("rstrtmgr.dll")

        # RmStartSession
        session_handle = ctypes.wintypes.DWORD()
        session_key = ctypes.create_unicode_buffer(256)

        ret = rstrtmgr.RmStartSession(
            ctypes.byref(session_handle), 0, session_key
        )
        if ret != 0:
            return _fallback_find_locking(filepath)

        try:
            # RmRegisterResources
            filepath_w = ctypes.c_wchar_p(os.path.abspath(filepath))
            ret = rstrtmgr.RmRegisterResources(
                session_handle, 1, ctypes.byref(filepath_w),
                0, None, 0, None
            )
            if ret != 0:
                return _fallback_find_locking(filepath)

            # RmGetList
            n_proc_info_needed = ctypes.wintypes.UINT(0)
            n_proc_info = ctypes.wintypes.UINT(0)
            reboot_reasons = ctypes.wintypes.DWORD(0)

            ret = rstrtmgr.RmGetList(
                session_handle,
                ctypes.byref(n_proc_info_needed),
                ctypes.byref(n_proc_info),
                None,
                ctypes.byref(reboot_reasons),
            )

            if n_proc_info_needed.value == 0:
                return {"procesos": [], "certero": True}

            # Definir RM_PROCESS_INFO
            class FILETIME(ctypes.Structure):
                _fields_ = [("dwLowDateTime", ctypes.wintypes.DWORD),
                            ("dwHighDateTime", ctypes.wintypes.DWORD)]

            class RM_UNIQUE_PROCESS(ctypes.Structure):
                _fields_ = [("dwProcessId", ctypes.wintypes.DWORD),
                            ("ProcessStartTime", FILETIME)]

            class RM_PROCESS_INFO(ctypes.Structure):
                _fields_ = [
                    ("Process", RM_UNIQUE_PROCESS),
                    ("strAppName", ctypes.c_wchar * 256),
                    ("strServiceShortName", ctypes.c_wchar * 64),
                    ("ApplicationType", ctypes.wintypes.UINT),
                    ("AppStatus", ctypes.wintypes.ULONG),
                    ("TSSessionId", ctypes.wintypes.DWORD),
                    ("bRestartable", ctypes.wintypes.BOOL),
                ]

            n = n_proc_info_needed.value
            proc_info_arr = (RM_PROCESS_INFO * n)()
            n_proc_info.value = n

            ret = rstrtmgr.RmGetList(
                session_handle,
                ctypes.byref(n_proc_info_needed),
                ctypes.byref(n_proc_info),
                proc_info_arr,
                ctypes.byref(reboot_reasons),
            )

            if ret == 0:
                for i in range(n_proc_info.value):
                    info = proc_info_arr[i]
                    processes.append({
                        "pid": info.Process.dwProcessId,
                        "nombre": info.strAppName.strip() or "Desconocido",
                    })

        finally:
            rstrtmgr.RmEndSession(session_handle)

    except (OSError, AttributeError):
        return _fallback_find_locking(filepath)

    return {"procesos": processes, "certero": True}


def _fallback_find_locking(filepath: str) -> dict:
    """Fallback usando PowerShell si Restart Manager falla.

    LIMITACION IMPORTANTE: este fallback busca en `$_.Modules.FileName`,
    que solo contiene los EXE/DLL que un proceso tiene cargados en
    memoria, NO los archivos de datos que tiene abiertos (ej. un .xlsx
    abierto en Excel jamas aparece en Modules). Por eso, cuando esta
    busqueda no encuentra nada, NO significa que el archivo este libre:
    solo significa que este metodo no pudo determinarlo. Se devuelve un
    dict con esa distincion explicita en vez de una simple lista vacia,
    para que el llamador no reporte "archivo libre" cuando en realidad
    no se sabe.
    """
    import json

    try:
        abs_path = ps_escape(os.path.abspath(filepath))
        cmd = (
            f'Get-Process | Where-Object {{ $_.Modules.FileName -contains "{abs_path}" }} '
            f"| Select-Object Id, ProcessName | ConvertTo-Json -Compress"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]
            procesos = [{"pid": p["Id"], "nombre": p["ProcessName"]} for p in data]
            return {"procesos": procesos, "certero": False}
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError, KeyError, TypeError):
        pass
    return {"procesos": [], "certero": False}


def _kill_process(pid: int) -> bool:
    """Termina un proceso por PID usando taskkill."""
    try:
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


# --- Interfaz de consola ---


def file_unlocker_menu() -> None:
    """Menu para desbloquear archivos en uso."""
    console.print("\n[bold cyan]Desbloquear Archivo en Uso[/bold cyan]\n")

    filepath = Prompt.ask("[bold]Ruta del archivo bloqueado[/bold]").strip().strip('"')
    if not filepath or not os.path.exists(filepath):
        console.print("[red]Archivo no encontrado.[/red]")
        return

    with console.status("[bold green]Buscando procesos que bloquean el archivo..."):
        resultado = _find_locking_processes(filepath)

    processes = resultado["procesos"]
    certero = resultado["certero"]

    if not processes:
        if certero:
            console.print("\n[bold green]No se detectaron procesos bloqueando el archivo.[/bold green]")
        else:
            # El fallback de PowerShell no ve archivos de datos abiertos
            # (solo EXE/DLL cargados), asi que una lista vacia aca NO es
            # prueba de que el archivo este libre.
            console.print("\n[bold yellow]No se pudo determinar que proceso bloquea el archivo.[/bold yellow]")
            console.print(
                "[dim]El metodo de deteccion disponible no alcanza a ver archivos de datos "
                "abiertos (ej. documentos en Word/Excel). El archivo puede seguir bloqueado "
                "aunque no se haya detectado ningun proceso.[/dim]"
            )
        return

    table = Table(title=f"Procesos usando: {escape(os.path.basename(filepath))}")
    table.add_column("#", style="bold cyan", width=4, justify="right")
    table.add_column("PID", style="bold")
    table.add_column("Proceso", style="yellow")

    for i, p in enumerate(processes, 1):
        table.add_row(str(i), str(p["pid"]), escape(p["nombre"]))

    console.print(table)

    confirm = Prompt.ask(
        "\n[bold]Cerrar proceso(s)?[/bold]",
        choices=["s", "n"], default="n",
    )
    if confirm != "s":
        return

    killed = 0
    for p in processes:
        if _kill_process(p["pid"]):
            console.print(f"  [green]Cerrado:[/green] {escape(p['nombre'])} (PID {p['pid']})")
            killed += 1
        else:
            console.print(f"  [red]No se pudo cerrar:[/red] {escape(p['nombre'])} (PID {p['pid']})")

    console.print(f"\n[bold green]{killed} proceso(s) cerrado(s).[/bold green]")
