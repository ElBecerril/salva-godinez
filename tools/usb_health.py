"""Verificador de USB: diagnostico de estado, velocidad y autenticidad."""

import errno
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

from rich.markup import escape
from rich.prompt import Prompt
from rich.table import Table

from tools import get_removable_drives, format_size
from utils import console


# --- Logica (sin UI) ---


def _get_usb_info(drive: str) -> dict:
    """Obtiene informacion de la unidad via PowerShell Get-Volume."""
    letter = drive[0].upper()
    if not letter.isalpha():
        return {"label": "Desconocido", "filesystem": "Desconocido",
                "size": 0, "free": 0, "health": "Desconocido"}
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-Volume -DriveLetter {letter} | Select-Object "
             f"FileSystemLabel, FileSystem, Size, SizeRemaining, HealthStatus "
             f"| ConvertTo-Json -Compress"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
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


# chkdsk en un disco SANO siempre imprime una linea como
# "0 KB in bad sectors." (o su equivalente en espanol), por lo que
# buscar la palabra suelta "bad" genera un falso positivo permanente.
# En vez de eso, se parsea la cantidad reportada y solo se considera
# un problema real si esa cantidad es mayor a cero.
_BAD_SECTORS_RE = re.compile(
    r"(\d+)\s*kb\s+(?:in bad sectors|en sectores (?:dañados|defectuosos))",
    re.IGNORECASE,
)


_PROBLEM_KEYWORD_RE = re.compile(r"\b(errores?|corrupt\w*|problemas?|incorrecto\w*)\b")

# El mensaje de un disco SANO tipicamente incluye la propia palabra clave en
# forma NEGADA (ej. "no encontro problemas", "no errors found"), asi que
# buscar "problema"/"error" como substring suelto da el mismo falso positivo
# permanente que "bad" (ver _BAD_SECTORS_RE arriba). Se descarta un match si
# esta precedido de cerca por una negacion tipica.
_NEGATION_MARKERS = ("no ", "sin ", "ningun", "ningún", "ninguna", "not ", "0 ")


def _chkdsk_output_has_errors(output: str) -> bool:
    """Analiza el output crudo de chkdsk buscando errores reales (EN/ES)."""
    lower = output.lower()

    for match in _BAD_SECTORS_RE.finditer(lower):
        if int(match.group(1)) > 0:
            return True

    for match in _PROBLEM_KEYWORD_RE.finditer(lower):
        context_before = lower[max(0, match.start() - 20):match.start()]
        if any(neg in context_before for neg in _NEGATION_MARKERS):
            continue
        return True

    return False


def _check_filesystem(drive: str) -> dict:
    """Ejecuta chkdsk en modo solo lectura y parsea resultados."""
    try:
        result = subprocess.run(
            ["chkdsk", drive.rstrip("\\")],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        output = result.stdout + result.stderr
        has_errors = _chkdsk_output_has_errors(output)
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


def _select_offsets(test_size: int, chunk_size: int, max_points: int = 4) -> list[int]:
    """Elige hasta `max_points` offsets distribuidos sobre `test_size`,
    garantizando una separacion minima de `chunk_size` entre offsets
    consecutivos para que los chunks de prueba nunca se solapen (ver
    docstring de `_detect_fake_usb`). Si `test_size` no alcanza para
    separar varios puntos, cae a los que si quepan (minimo 1: el offset 0).
    """
    if test_size <= chunk_size:
        return [0]
    rango_util = test_size - chunk_size
    # cuantos puntos caben sin que sus chunks se solapen
    puntos = min(max_points, rango_util // chunk_size + 1)
    if puntos <= 1:
        return [0]
    return [int(rango_util * i / (puntos - 1)) for i in range(puntos)]


def _detect_fake_usb(drive: str, reported_size: int = 0) -> dict:
    """Prueba rapida (NO concluyente) de posible capacidad USB falsificada.

    LIMITACION IMPORTANTE: una memoria USB con capacidad falsificada
    (chip real mas chico reportando un tamano mayor) tipicamente falla
    solo al escribir MAS ALLA de su capacidad fisica real, no en el
    primer MB — por eso probar solo el inicio de la unidad (como hacia
    esta funcion antes) siempre "pasaba" incluso en USBs falsas. Una
    prueba realmente concluyente requeriria escribir y verificar datos
    a lo largo de TODA la capacidad reportada (puede ser cientos de GB
    en USBs grandes), lo cual es lento y desgasta la memoria flash, asi
    que no es viable en un diagnostico rapido.

    Como mejora sobre la version anterior, se escribe y verifica un
    patron distinto en hasta 4 puntos distribuidos (inicio, ~10%, ~50%,
    ~90%) de la capacidad reportada, acotados a un tamano maximo de prueba
    (_FAKE_TEST_CAP) para mantener el chequeo rapido. La cantidad real de
    puntos se ajusta segun quepan sin solaparse (ver `_select_offsets`). Si
    la unidad "falsea" mas capacidad de la que este limite cubre, esta
    prueba no lo detectara — por eso el resultado se reporta como "sin
    indicios de falsificacion" y NO como "autentica".
    """
    _FAKE_TEST_CAP = 256 * 1024 * 1024  # limite de prueba: 256 MB
    chunk_size = 256 * 1024  # 256 KB por punto verificado
    _FREE_SPACE_MARGIN = 8 * 1024 * 1024  # margen de seguridad: 8 MB

    test_size = min(reported_size, _FAKE_TEST_CAP) if reported_size else 0

    # Si la USB esta casi llena, escribir test_size bytes puede fallar con
    # OSError (sin espacio) y antes eso se reportaba como "posible USB
    # falsa", lo cual es enganoso. Se acota la prueba al espacio libre
    # real, dejando un margen de seguridad.
    try:
        free_space = shutil.disk_usage(drive).free
    except OSError:
        free_space = None

    if free_space is not None:
        usable = max(free_space - _FREE_SPACE_MARGIN, 0)
        test_size = min(test_size, usable) if test_size else 0
        if usable < chunk_size:
            return {
                "authentic": None,
                "detail": "No se pudo completar la prueba por falta de espacio libre en la unidad",
            }

    test_size = max(test_size, chunk_size)

    # Los offsets se calculaban antes como fracciones fijas (0%, 10%, 50%,
    # 90%) de (test_size - chunk_size). Si test_size era chico (entre
    # ~512 KB y ~2.8 MB, algo comun en una USB legitima casi llena), esas
    # fracciones quedaban tan juntas que el chunk escrito en un offset
    # pisaba la cola del chunk anterior; al releer no coincidia el patron
    # y la funcion reportaba "posible USB falsa" siendo mentira. Ahora se
    # eligen offsets espaciados por AL MENOS chunk_size entre si, y si no
    # caben los 4 puntos se usan los que si quepan sin solaparse (minimo
    # 1, el offset 0).
    offsets = _select_offsets(test_size, chunk_size)

    def _pattern_for(offset: int) -> bytes:
        seed = (offset % 251) + 1
        return bytes((seed + i) % 256 for i in range(chunk_size))

    test_file = os.path.join(drive, ".salva_faketest.tmp")

    try:
        with open(test_file, "wb") as f:
            for offset in offsets:
                f.seek(offset)
                f.write(_pattern_for(offset))
            f.flush()
            os.fsync(f.fileno())

        all_match = True
        with open(test_file, "rb") as f:
            for offset in offsets:
                f.seek(offset)
                read_back = f.read(chunk_size)
                if read_back != _pattern_for(offset):
                    all_match = False
                    break

        if all_match:
            return {
                "authentic": True,
                "detail": (
                    f"Sin indicios de falsificacion en la prueba rapida "
                    f"({len(offsets)} punto(s) verificado(s) — no concluyente)"
                ),
            }
        else:
            return {
                "authentic": False,
                "detail": "Los datos leidos no coinciden en uno o mas puntos — posible USB falsa",
            }
    except OSError as e:
        if e.errno == errno.ENOSPC:
            return {
                "authentic": None,
                "detail": "No se pudo completar la prueba por falta de espacio libre en la unidad",
            }
        return {"authentic": False, "detail": f"Error durante la prueba: {e}"}
    finally:
        try:
            os.remove(test_file)
        except OSError:
            pass


# --- Interfaz de consola ---


def usb_health_menu() -> None:
    """Menu del verificador de USB."""
    console.print("\n[bold cyan]Revisar Estado de la USB[/bold cyan]\n")

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
    table.add_row("Etiqueta", escape(info["label"]))
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

    # Deteccion de USB falsa (prueba rapida, no concluyente — ver docstring)
    console.print("\n[bold yellow]Verificacion de autenticidad (prueba rapida, no concluyente)...[/bold yellow]")
    with console.status("[bold green]Verificando integridad de datos..."):
        fake = _detect_fake_usb(drive, reported_size=info["size"])

    if fake["authentic"] is None:
        console.print(f"  [bold yellow]Aviso:[/bold yellow] {fake['detail']}")
    elif fake["authentic"]:
        console.print(f"  [bold green]OK:[/bold green] {fake['detail']}")
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
            console.print(f"[dim]{escape(chk['output'][:500])}[/dim]")
