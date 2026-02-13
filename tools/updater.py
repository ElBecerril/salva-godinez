"""
Auto-updater: verifica GitHub Releases y ofrece descargar nueva version.
"""

import json
import os
import urllib.request

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn
from rich.prompt import Confirm

REPO = "ElBecerril/salva-godinez"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"

console = Console()


def _parse_version(tag: str) -> tuple:
    """'v3.0.0' -> (3, 0, 0)"""
    return tuple(int(x) for x in tag.lstrip("vV").split("."))


def _download_exe(url: str, filename: str) -> None:
    """Descarga un archivo al Escritorio con barra de progreso Rich."""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    dest = os.path.join(desktop, filename)

    req = urllib.request.Request(url, headers={"User-Agent": "SalvaGodinez-Updater"})
    resp = urllib.request.urlopen(req, timeout=30)
    total = int(resp.headers.get("Content-Length", 0))

    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
    ) as progress:
        task = progress.add_task("Descargando...", total=total or None)
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                progress.advance(task, len(chunk))

    console.print(f"\n[bold green]Guardado en:[/bold green] {dest}")


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

        filename = f"SalvaGodinez_{remote_tag}.exe"
        _download_exe(exe_asset["browser_download_url"], filename)

    except Exception:
        # Sin internet, timeout, API error, etc. — seguir sin molestar
        return
