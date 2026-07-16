"""
Auto-updater: verifica GitHub Releases y ofrece descargar nueva version.
"""

import glob
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.request

from rich.panel import Panel
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn
from rich.prompt import Confirm
from utils import console

REPO = "ElBecerril/salva-godinez"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"



def _parse_version(tag: str) -> tuple:
    """'v3.0.0' -> (3, 0, 0)"""
    return tuple(int(x) for x in tag.lstrip("vV").split("."))


def _extract_sha256(body: str, filename: str) -> str | None:
    """Extrae hash SHA-256 del body del Release.

    Busca patrones como:
        SHA-256: abc123...
        `abc123...` SalvaGodinez.exe
        abc123...  SalvaGodinez.exe
    """
    if not body:
        return None
    # Patron: SHA-256: <hex> o SHA256: <hex>
    match = re.search(r"SHA-?256\s*:\s*([0-9a-fA-F]{64})", body)
    if match:
        return match.group(1).lower()
    # Patron estilo checksum file: <hex>  <filename>
    match = re.search(rf"([0-9a-fA-F]{{64}})\s+\S*{re.escape(filename)}", body)
    if match:
        return match.group(1).lower()
    return None


def _download_exe(url: str, filename: str, expected_sha256: str | None = None) -> bool:
    """Descarga un archivo a una ubicacion temporal con barra de progreso Rich.

    El orden es deliberado por seguridad: se descarga primero a un archivo
    temporal (el Escritorio no se toca todavia), se verifica el SHA-256 y
    SOLO si la verificacion es exitosa (o no hay hash de referencia) se
    borran las versiones anteriores del Escritorio y se mueve el archivo
    temporal a su ubicacion final.

    Returns:
        True si la descarga se completo y quedo instalada en el Escritorio,
        False si algo fallo (descarga, verificacion de hash, etc.). En ese
        caso el Escritorio no se modifica.
    """
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    dest = os.path.join(desktop, filename)

    tmp_fd, tmp_path = tempfile.mkstemp(prefix="salvagodinez_update_", suffix=".tmp")
    os.close(tmp_fd)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SalvaGodinez-Updater"})
        resp = urllib.request.urlopen(req, timeout=30)
        total = int(resp.headers.get("Content-Length", 0))

        sha256 = hashlib.sha256()

        with Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
        ) as progress:
            task = progress.add_task("Descargando...", total=total or None)
            with open(tmp_path, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    sha256.update(chunk)
                    progress.advance(task, len(chunk))

        actual_hash = sha256.hexdigest()

        if expected_sha256:
            if actual_hash != expected_sha256:
                console.print(
                    f"[bold red]Verificacion SHA-256 fallida![/bold red]\n"
                    f"[red]Esperado: {expected_sha256}[/red]\n"
                    f"[red]Obtenido: {actual_hash}[/red]\n"
                    f"[red]La descarga se descarto por seguridad. El Escritorio no fue modificado.[/red]"
                )
                return False
            console.print("[green]SHA-256 verificado correctamente.[/green]")
        else:
            console.print(
                f"[yellow]SHA-256: {actual_hash} (sin hash de referencia en el Release "
                "para verificar; se procede con precaucion)[/yellow]"
            )

        # Solo ahora, con la descarga ya verificada, es seguro tocar el Escritorio.
        current_exe = os.path.abspath(sys.executable) if getattr(sys, "frozen", False) else ""
        for old in glob.glob(os.path.join(desktop, "SalvaGodinez*.exe")):
            if os.path.abspath(old) != current_exe:
                try:
                    os.remove(old)
                except OSError as e:
                    console.print(f"[yellow]No se pudo eliminar version anterior {old}: {e}[/yellow]")

        shutil.move(tmp_path, dest)
        console.print(f"[bold green]Guardado en:[/bold green] {dest}")
        return True

    except Exception as e:
        console.print(f"[bold red]Error al descargar la actualizacion: {e}[/bold red]")
        return False
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def check_for_updates(current_version: str) -> None:
    """Verifica si hay una version nueva en GitHub Releases."""
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"User-Agent": "SalvaGodinez-Updater"},
        )
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read().decode("utf-8"))

        remote_tag = data.get("tag_name", "")
        if not remote_tag:
            return

        local_tuple = _parse_version(current_version)
        remote_tuple = _parse_version(remote_tag)

        if remote_tuple <= local_tuple:
            return

        console.print(
            Panel(
                f"[bold]Nueva version disponible:[/bold] {remote_tag}\n"
                f"[dim]Tu version actual: v{current_version}[/dim]",
                title="[bold yellow]Actualizacion disponible[/bold yellow]",
                border_style="yellow",
            )
        )

        if not Confirm.ask("[yellow]Deseas descargar la nueva version?[/yellow]", default=False):
            return

        assets = data.get("assets", [])
        exe_asset = next((a for a in assets if a["name"].endswith(".exe")), None)

        if not exe_asset:
            console.print("[red]No se encontro archivo .exe en el Release.[/red]")
            return

        # Extraer hash SHA-256 del body del Release (si el autor lo incluyo)
        release_body = data.get("body", "")
        expected_hash = _extract_sha256(release_body, exe_asset["name"])

        # Nota: _download_exe() descarga primero a un temporal, verifica el
        # hash y solo entonces borra versiones anteriores del Escritorio y
        # mueve el archivo final. Reporta sus propios errores; no los
        # silencia.
        filename = f"SalvaGodinez_{remote_tag}.exe"
        _download_exe(exe_asset["browser_download_url"], filename, expected_hash)

    except Exception as e:
        # Esto solo cubre la verificacion de si hay una version nueva
        # (llamada a la API de GitHub): sin internet, timeout, API error, etc.
        # No cubre la descarga en si, que reporta sus propios errores arriba.
        console.print(f"[dim]No se pudo verificar actualizaciones: {e}[/dim]")
        return
