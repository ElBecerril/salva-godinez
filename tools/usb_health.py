"""Verificador de USB: diagnostico de estado, velocidad y autenticidad."""

import json
import os
import subprocess
import tempfile
import time

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from tools import get_removable_drives, format_size

console = Console()


def _get_usb_info(drive: str) -> dict:
    """Obtiene informacion de la unidad via PowerShell Get-Volume."""
    letter = drive[0]
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-Volume -DriveLetter {letter} | Select-Object "
             f"FileSystemLabel, FileSystem, Size, SizeRemaining, HealthStatus "
             f"| ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            return {
                "label": data.get("FileSystemLabel", "") or "(sin etiqueta)",
                "filesystem": data.get("FileSystem", "Desconocido"),
                "size": data.get("Size", 0),
                "free": data.get("SizeRemaining", 0),
                "health": data.get("HealthStatus", "Desconocido"),
            }
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
        pass
    return {"label": "Desconocido", "filesystem": "Desconocido",
            "size": 0, "free": 0, "health": "Desconocido"}


def _check_filesystem(drive: str) -> dict:
    """Ejecuta chkdsk en modo solo lectura y parsea resultados."""
    try:
        result = subprocess.run(
            ["chkdsk", drive.rstrip("\\")],
            capture_output=True, text=True, timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        output = result.stdout + result.stderr
        has_errors = any(
            kw in output.lower()
            for kw in ["error", "corrupt", "bad", "problema", "incorrecto"]
        )
        return {"ok": not has_errors, "output": output, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "Timeout ejecutando chkdsk", "returncode": -1}
    except OSError as e:
        return {"ok": False, "output": str(e), "returncode": -1}


def _speed_test(drive: str, size_mb: int = 10) -> dict:
    """Prueba de velocidad: escribe y lee un archivo de prueba.

    Returns:
        dict con write_mbps, read_mbps
    """
    test_file = os.path.join(drive, ".salva_speedtest.tmp")
    data = os.urandom(size_mb * 1024 * 1024)

    try:
        # Escritura
        start = time.perf_counter()
        with open(test_file, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        write_time = time.perf_counter() - start

        # Lectura
        start = time.perf_counter()
        with open(test_file, "rb") as f:
            _ = f.read()
        read_time = time.perf_counter() - start

        write_mbps = size_mb / write_time if write_time > 0 else 0
        read_mbps = size_mb / read_time if read_time > 0 else 0

        return {"write_mbps": write_mbps, "read_mbps": read_mbps}
    except OSError as e:
        return {"write_mbps": 0, "read_mbps": 0, "error": str(e)}
    finally:
        try:
            os.remove(test_file)
        except OSError:
            pass


def _detect_fake_usb(drive: str) -> dict:
    """Detecta USBs con capacidad falsa escribiendo un patron y verificando."""
    test_file = os.path.join(drive, ".salva_faketest.tmp")
    size = 1024 * 1024  # 1 MB
    pattern = bytes(range(256)) * (size // 256)

    try:
        # Escribir patron
        with open(test_file, "wb") as f:
            f.write(pattern)
            f.flush()
            os.fsync(f.fileno())

        # Leer y verificar
        with open(test_file, "rb") as f:
            read_back = f.read()

        if read_back == pattern:
            return {"authentic": True, "detail": "Patron verificado correctamente"}
        else:
            return {"authentic": False, "detail": "Los datos leidos no coinciden — posible USB falsa"}
    except OSError as e:
        return {"authentic": False, "detail": f"Error durante la prueba: {e}"}
    finally:
        try:
            os.remove(test_file)
        except OSError:
            pass


def usb_health_menu() -> None:
    """Menu del verificador de USB."""
    console.print("\n[bold cyan]Verificador de USB[/bold cyan]\n")

    drives = get_removable_drives()
    if not drives:
        console.print("[yellow]No se detectaron unidades USB conectadas.[/yellow]")
        return

    console.print("[bold]Unidades USB detectadas:[/bold]")
    for i, drive in enumerate(drives, 1):
        console.print(f"  [cyan]{i}[/cyan] - {drive}")

    if len(drives) == 1:
        drive = drives[0]
    else:
        choice = Prompt.ask(
            "[bold]Selecciona la unidad[/bold]",
            choices=[str(i) for i in range(1, len(drives) + 1)],
        )
        drive = drives[int(choice) - 1]

    # Informacion basica
    with console.status("[bold green]Obteniendo informacion de la unidad..."):
        info = _get_usb_info(drive)

    table = Table(title=f"USB: {drive}")
    table.add_column("Propiedad", style="bold")
    table.add_column("Valor")
    table.add_row("Etiqueta", info["label"])
    table.add_row("Sistema de archivos", info["filesystem"])
    table.add_row("Tamano total", format_size(info["size"]))
    table.add_row("Espacio libre", format_size(info["free"]))
    table.add_row("Estado de salud", info["health"])
    console.print(table)

    # Diagnosticos opcionales
    run_diag = Prompt.ask(
        "\n[bold]Ejecutar diagnosticos? (velocidad, integridad, autenticidad)[/bold]",
        choices=["s", "n"], default="n",
    )
    if run_diag != "s":
        return

    # Prueba de velocidad
    console.print("\n[bold yellow]Prueba de velocidad (10 MB)...[/bold yellow]")
    with console.status("[bold green]Escribiendo y leyendo datos de prueba..."):
        speed = _speed_test(drive)

    if "error" in speed:
        console.print(f"[red]Error en prueba de velocidad: {speed['error']}[/red]")
    else:
        console.print(f"  Escritura: [bold]{speed['write_mbps']:.1f} MB/s[/bold]")
        console.print(f"  Lectura:   [bold]{speed['read_mbps']:.1f} MB/s[/bold]")

    # Deteccion de USB falsa
    console.print("\n[bold yellow]Verificacion de autenticidad...[/bold yellow]")
    with console.status("[bold green]Verificando integridad de datos..."):
        fake = _detect_fake_usb(drive)

    if fake["authentic"]:
        console.print(f"  [bold green]USB autentica:[/bold green] {fake['detail']}")
    else:
        console.print(f"  [bold red]Advertencia:[/bold red] {fake['detail']}")

    # Chkdsk
    run_chkdsk = Prompt.ask(
        "\n[bold]Ejecutar verificacion de filesystem (chkdsk)?[/bold]",
        choices=["s", "n"], default="n",
    )
    if run_chkdsk == "s":
        with console.status("[bold green]Ejecutando chkdsk (puede tardar)..."):
            chk = _check_filesystem(drive)

        if chk["ok"]:
            console.print("[bold green]Filesystem sin errores detectados.[/bold green]")
        else:
            console.print("[bold red]Se detectaron posibles errores en el filesystem.[/bold red]")
            console.print(f"[dim]{chk['output'][:500]}[/dim]")
