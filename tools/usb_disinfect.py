"""Desinfectante de USB: detecta y limpia amenazas comunes."""

import os
import subprocess

from rich.markup import escape
from rich.prompt import Prompt
from rich.table import Table

from tools import get_removable_drives
from utils import read_lnk_target as _read_lnk_target, console, ps_escape


# Nombres sospechosos comunes en USBs infectados
SUSPICIOUS_FILES = {"autorun.inf", "desktop.ini.exe", "recycler.exe", "ravmon.exe"}
SUSPICIOUS_EXTENSIONS = {".exe", ".scr", ".bat", ".cmd", ".vbs", ".wsf", ".pif", ".com"}

# Atributos de Windows (WinNT.h) para detectar entradas ocultas/sistema.
FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_SYSTEM = 0x4


# --- Logica (sin UI) ---


def _is_suspicious_lnk(lnk_path: str) -> bool:
    """Verifica si un .lnk apunta a un ejecutable (patron de virus USB)."""
    target = _read_lnk_target(lnk_path)
    if not target:
        return False
    ext = os.path.splitext(target)[1].lower()
    return ext in SUSPICIOUS_EXTENSIONS


def scan_usb(drive: str, max_depth: int = 3) -> list[dict]:
    """Escanea una USB en busca de amenazas comunes.

    Recorre recursivamente hasta `max_depth` niveles bajo la raiz: el malware
    de USB no siempre se copia solo en la raiz, y escanear unicamente ahi da
    una falsa sensacion de seguridad.
    """
    threats = []
    base_depth = drive.rstrip("\\/").count(os.sep)
    try:
        for dirpath, dirnames, filenames in os.walk(drive):
            depth = dirpath.rstrip("\\/").count(os.sep) - base_depth
            if depth >= max_depth:
                dirnames[:] = []
                continue

            for entry in filenames:
                filepath = os.path.join(dirpath, entry)
                lower = entry.lower()

                # autorun.inf
                if lower == "autorun.inf":
                    threats.append({"archivo": filepath, "tipo": "Autorun.inf",
                                    "riesgo": "Alto"})
                    continue

                # Nombres conocidos de malware (heuristica de alta confianza)
                if lower in SUSPICIOUS_FILES:
                    threats.append({"archivo": filepath, "tipo": "Archivo sospechoso",
                                    "riesgo": "Alto"})
                    continue

                # Ejecutables sueltos: tener una extension comun (.exe/.bat/etc.)
                # no es por si sola prueba de infeccion, asi que se marca como
                # riesgo medio y nunca se borra sin confirmacion explicita.
                ext = os.path.splitext(lower)[1]
                if ext in SUSPICIOUS_EXTENSIONS:
                    threats.append({"archivo": filepath, "tipo": "Ejecutable sospechoso",
                                    "riesgo": "Medio"})
                    continue

                # .lnk que apuntan a ejecutables
                if lower.endswith(".lnk"):
                    if _is_suspicious_lnk(filepath):
                        threats.append({"archivo": filepath, "tipo": "Acceso directo malicioso",
                                        "riesgo": "Medio"})
    except OSError:
        pass
    return threats


def clean_usb(drive: str, threats: list[dict]) -> list[dict]:
    """Elimina las amenazas detectadas con confirmacion.

    Solo borra las de riesgo Alto (autorun.inf, nombres de malware
    conocidos): son heuristicas de alta confianza. Las de riesgo Medio
    (ejecutables sueltos, accesos directos sospechosos) NO se borran
    aqui — un .exe legitimo del usuario tiene la misma extension que uno
    malicioso, asi que borrarlas en bloque es demasiado agresivo. Esas
    quedan para revision manual (ver usb_disinfect_menu).

    Retorna la lista de resultados por archivo:
    [{"archivo": ruta, "ok": True}, {"archivo": ruta, "ok": False, "error": ...}, ...]
    """
    results = []
    for threat in threats:
        if threat.get("riesgo") != "Alto":
            continue
        filepath = threat["archivo"]
        try:
            os.remove(filepath)
            results.append({"archivo": filepath, "ok": True})
        except OSError as e:
            results.append({"archivo": filepath, "ok": False, "error": str(e)})
    return results


def check_fs_health(drive: str) -> dict:
    """Consulta el estado del sistema de archivos de la unidad via Get-Volume.

    Sirve para distinguir "USB con virus" (atributos ocultos, recuperable con
    attrib) de "USB con el sistema de archivos DANADO" (corrupcion de la tabla
    de archivos), donde attrib no ayuda y formatear/reparar solo empeora las
    chances de recuperar los datos.

    Retorna {"healthy": True}; {"healthy": False, "status": str} si Windows lo
    reporta danado; o {"unknown": True} si no se pudo consultar (fail-safe: el
    llamador sigue como si estuviera sano).
    """
    letter = drive.rstrip(":\\/")  # "F:\\" -> "F"
    if not letter:
        return {"unknown": True}
    ps = (
        f'$v = Get-Volume -DriveLetter "{ps_escape(letter[0])}" -ErrorAction Stop; '
        'Write-Output ($v.HealthStatus.ToString() + "|" + $v.OperationalStatus)'
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except (subprocess.TimeoutExpired, OSError):
        return {"unknown": True}

    out = (result.stdout or "").strip()
    if result.returncode != 0 or not out:
        return {"unknown": True}

    parts = out.split("|", 1)
    health = parts[0].strip().lower()
    oper = (parts[1] if len(parts) > 1 else "").strip().lower()
    # "Full Repair Needed" / "Spot Fix Needed" / "Scan Needed" en OperationalStatus,
    # o HealthStatus "Unhealthy", indican un volumen danado.
    damaged = health == "unhealthy" or "repair" in oper or "needed" in oper
    if damaged:
        return {"healthy": False, "status": out}
    return {"healthy": True}


def _count_hidden(drive: str, max_depth: int = 3) -> tuple[int, int]:
    """Cuenta entradas con atributo Oculto/Sistema hasta `max_depth` niveles.

    Retorna (ocultas, errores). `errores` > 0 (sin poder leer casi nada) delata
    un directorio danado. Usa scandir, que en Windows ya trae los atributos de
    la enumeracion, asi que entry.stat() no cuesta syscalls extra.
    """
    hidden = 0
    errors = 0

    def walk(path: str, depth: int) -> None:
        nonlocal hidden, errors
        if depth > max_depth:
            return
        try:
            with os.scandir(path) as it:
                for entry in it:
                    try:
                        attrs = getattr(
                            entry.stat(follow_symlinks=False), "st_file_attributes", 0
                        )
                        is_dir = entry.is_dir(follow_symlinks=False)
                    except OSError:
                        errors += 1
                        continue
                    if attrs & (FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM):
                        hidden += 1
                    if is_dir:
                        walk(entry.path, depth + 1)
        except OSError:
            errors += 1

    walk(drive, 1)
    return hidden, errors


def unhide_folders(drive: str) -> dict:
    """Restaura carpetas ocultas por malware usando attrib, reportando lo que
    REALMENTE cambio.

    attrib devuelve codigo 0 aunque no toque nada (unidad sin nada oculto) o
    aunque falle archivo por archivo ("Acceso denegado" va a stdout y aun asi
    sale con 0). Confiar en ese returncode hacia que la app cantara "carpetas
    restauradas" sin haber restaurado nada. Aqui se verifica el efecto real
    contando lo oculto antes/despues, y se detecta el caso de USB danada.

    Retorna uno de:
      {"ok": True, "changed": N}                       -> N entradas quedaron
          visibles (N puede ser 0: no habia nada oculto que restaurar).
      {"ok": False, "fs_damaged": True, "status": str} -> el sistema de archivos
          de la unidad esta danado (no es virus); attrib no aplica.
      {"ok": False, "returncode": int, "detail": str, "remaining": R}
          -> attrib fallo o quedaron R entradas ocultas sin poder restaurar.
      {"ok": False, "error": str}                      -> no se pudo ejecutar attrib.
    """
    # 1) Si el volumen esta danado, attrib no ayuda: reportar la verdad en vez
    #    de mentir "restaurado".
    health = check_fs_health(drive)
    if health.get("healthy") is False:
        return {"ok": False, "fs_damaged": True, "status": health.get("status", "")}

    # 2) Cuanto habia oculto ANTES. Si ni siquiera se puede leer el directorio
    #    (errores y cero entradas), es probable corrupcion.
    hidden_before, errors_before = _count_hidden(drive)
    if errors_before and hidden_before == 0:
        return {"ok": False, "fs_damaged": True, "status": "directorio ilegible"}

    # 3) Ejecutar attrib.
    try:
        result = subprocess.run(
            ["attrib", "-h", "-s", "-r", "/s", "/d", f"{drive}*.*"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"ok": False, "error": str(e)}

    # 4) Verificar el efecto real.
    hidden_after, _ = _count_hidden(drive)
    changed = max(0, hidden_before - hidden_after)
    detail = (result.stderr or result.stdout or "").strip()

    if result.returncode != 0:
        return {"ok": False, "returncode": result.returncode, "detail": detail,
                "remaining": hidden_after}
    if hidden_after > 0:
        # attrib salio 0 pero quedaron entradas ocultas: no es exito real.
        return {"ok": False, "returncode": 0, "detail": detail,
                "remaining": hidden_after}
    return {"ok": True, "changed": changed}


# --- Interfaz de consola ---


def usb_disinfect_menu() -> None:
    """Interfaz principal del desinfectante de USB."""
    console.print("\n[bold cyan]Quitar Virus de la USB[/bold cyan]\n")

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

    # Escanear
    with console.status(f"[bold green]Escaneando {drive}..."):
        threats = scan_usb(drive)

    if not threats:
        console.print(f"\n[bold green]No se encontraron amenazas en {drive}[/bold green]")
    else:
        table = Table(title=f"Amenazas encontradas en {drive}")
        table.add_column("#", style="bold cyan", width=4, justify="right")
        table.add_column("Archivo", style="white", max_width=40)
        table.add_column("Tipo", style="yellow")
        table.add_column("Riesgo", style="red")

        for i, t in enumerate(threats, 1):
            table.add_row(str(i), escape(os.path.basename(t["archivo"])), t["tipo"], t["riesgo"])

        console.print()
        console.print(table)

        high_risk = [t for t in threats if t["riesgo"] == "Alto"]
        medium_risk = [t for t in threats if t["riesgo"] != "Alto"]

        if high_risk:
            console.print(
                f"\n[bold]{len(high_risk)} amenaza(s) de riesgo Alto[/bold] "
                "(autorun.inf / nombres de malware conocidos)."
            )
            confirm = Prompt.ask(
                "[bold]Eliminar solo las de riesgo Alto?[/bold]", choices=["s", "n"], default="n"
            )
            if confirm == "s":
                clean_results = clean_usb(drive, threats)
                removed = 0
                for r in clean_results:
                    if r["ok"]:
                        console.print(f"  [green]Eliminado:[/green] {escape(os.path.basename(r['archivo']))}")
                        removed += 1
                    else:
                        console.print(f"  [red]No se pudo eliminar {escape(os.path.basename(r['archivo']))}: {escape(r['error'])}[/red]")
                console.print(f"\n[bold green]{removed} amenaza(s) eliminada(s).[/bold green]")

        if medium_risk:
            console.print(
                f"\n[yellow]{len(medium_risk)} archivo(s) sospechoso(s) de riesgo Medio "
                "(ejecutables sueltos / accesos directos) — NO se borran automaticamente. "
                "Revisalos manualmente:[/yellow]"
            )
            for t in medium_risk:
                console.print(f"  - {escape(t['archivo'])} ({t['tipo']})")

    # Ofrecer restaurar carpetas ocultas
    restore = Prompt.ask(
        "[bold]Restaurar carpetas ocultas?[/bold]", choices=["s", "n"], default="n"
    )
    if restore == "s":
        console.print(f"[bold yellow]Restaurando carpetas ocultas en {drive}...[/bold yellow]")
        result = unhide_folders(drive)
        if result["ok"]:
            changed = result.get("changed", 0)
            if changed > 0:
                console.print(
                    f"[green]Listo: {changed} carpeta(s)/archivo(s) oculto(s) "
                    "por el virus quedaron visibles de nuevo.[/green]"
                )
            else:
                console.print(
                    "[yellow]No habia carpetas ocultas por virus en esta USB, "
                    "asi que no hubo nada que restaurar.[/yellow]"
                )
        elif result.get("fs_damaged"):
            console.print(
                "[bold red]Esta USB parece tener el sistema de archivos DANADO "
                "(no es un virus).[/bold red]"
            )
            console.print(
                "[yellow]NO la formatees ni la 'repares': los archivos suelen "
                "poder recuperarse con una herramienta de recuperacion, pero "
                "formatear o reparar reduce las posibilidades.[/yellow]"
            )
            if result.get("status"):
                console.print(f"[dim]Estado del volumen: {escape(result['status'])}[/dim]")
        elif "error" in result:
            console.print(f"[red]Error al restaurar atributos: {escape(result['error'])}[/red]")
        else:
            remaining = result.get("remaining", 0)
            console.print(
                f"[red]No se pudieron restaurar {remaining} elemento(s). Es "
                "posible que necesiten permisos de administrador o que la "
                "unidad tenga daño.[/red]"
            )
            if result.get("detail"):
                console.print(f"[dim]{escape(result['detail'])}[/dim]")
