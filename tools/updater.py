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

# Limite maximo razonable para el .exe del updater (evita descargas
# descontroladas o respuestas maliciosas con Content-Length falso/ausente).
MAX_DOWNLOAD_SIZE = 200 * 1024 * 1024  # 200 MB



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
    # Primero el patron que ata el hash al filename del asset (mas
    # especifico): <hex>  <filename>. Se intenta antes del patron generico
    # para no agarrar el hash de otro asset cuando el body lista varios.
    match = re.search(rf"([0-9a-fA-F]{{64}})\s+\S*{re.escape(filename)}", body)
    if match:
        return match.group(1).lower()
    # Fallback generico: SHA-256: <hex> o SHA256: <hex>
    match = re.search(r"SHA-?256\s*:\s*([0-9a-fA-F]{64})", body)
    if match:
        return match.group(1).lower()
    return None


def _download_exe(url: str, filename: str, expected_sha256: str | None = None) -> bool:
    """Descarga un archivo a una ubicacion temporal con barra de progreso Rich.

    El orden es deliberado por seguridad: se descarga primero a un archivo
    temporal (el Escritorio no se toca todavia), se verifica el SHA-256 y
    SOLO si la verificacion es exitosa (o no hay hash de referencia) se
    mueve el archivo temporal a su ubicacion final en el Escritorio. Solo
    despues de confirmar que ese move fue exitoso se borran las versiones
    anteriores del Escritorio; asi, si el move falla, las versiones viejas
    siguen intactas.

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

        if total > MAX_DOWNLOAD_SIZE:
            console.print(
                f"[bold red]La descarga excede el tamano maximo permitido "
                f"({MAX_DOWNLOAD_SIZE // (1024 * 1024)} MB segun Content-Length). "
                "Se aborta por seguridad. El Escritorio no fue modificado.[/bold red]"
            )
            return False

        sha256 = hashlib.sha256()
        written = 0

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
                    written += len(chunk)
                    if written > MAX_DOWNLOAD_SIZE:
                        console.print(
                            f"[bold red]La descarga supero el tamano maximo permitido "
                            f"({MAX_DOWNLOAD_SIZE // (1024 * 1024)} MB). "
                            "Se aborta por seguridad. El Escritorio no fue modificado.[/bold red]"
                        )
                        return False
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
            if total > 0 and written != total:
                console.print(
                    f"[bold red]La descarga quedo incompleta: se esperaban {total} bytes "
                    f"(Content-Length) y se recibieron {written}. Sin hash de referencia "
                    "para verificar, se descarta por seguridad. El Escritorio no fue "
                    "modificado.[/bold red]"
                )
                return False
            console.print(
                f"[yellow]SHA-256: {actual_hash} (sin hash de referencia en el Release "
                "para verificar; se procede con precaucion)[/yellow]"
            )

        # Solo ahora, con la descarga ya verificada, es seguro tocar el Escritorio.
        # Primero se mueve el archivo temporal a su destino final; solo si el
        # move fue exitoso se procede a borrar versiones anteriores del
        # Escritorio. Asi, si el move falla, las versiones viejas siguen ahi.
        shutil.move(tmp_path, dest)
        console.print(f"[bold green]Guardado en:[/bold green] {dest}")

        current_exe = os.path.abspath(sys.executable) if getattr(sys, "frozen", False) else ""
        dest_abs = os.path.abspath(dest)
        for old in glob.glob(os.path.join(desktop, "SalvaGodinez*.exe")):
            old_abs = os.path.abspath(old)
            if old_abs != current_exe and old_abs != dest_abs:
                try:
                    os.remove(old)
                except OSError as e:
                    console.print(f"[yellow]No se pudo eliminar version anterior {old}: {e}[/yellow]")

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
        # hash, mueve el archivo final al Escritorio y solo tras confirmar
        # ese move borra versiones anteriores. Reporta sus propios errores;
        # no los silencia.
        filename = f"SalvaGodinez_{remote_tag}.exe"
        _download_exe(exe_asset["browser_download_url"], filename, expected_hash)

    except Exception as e:
        # Esto solo cubre la verificacion de si hay una version nueva
        # (llamada a la API de GitHub): sin internet, timeout, API error, etc.
        # No cubre la descarga en si, que reporta sus propios errores arriba.
        console.print(f"[dim]No se pudo verificar actualizaciones: {e}[/dim]")
        return
