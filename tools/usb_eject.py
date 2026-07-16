"""Expulsion segura de unidades USB."""

import ctypes
import subprocess
import time

from rich.prompt import Prompt

from tools import get_removable_drives
from utils import ps_escape, console


def _drive_still_present(drive: str) -> bool | None:
    """Verifica si la unidad sigue presente en el sistema.

    Returns:
        True si sigue apareciendo como unidad removible, False si ya no esta
        presente, None si no se pudo determinar (p. ej. no disponible en esta
        plataforma).
    """
    try:
        letter = drive.rstrip("\\") + "\\"
        drive_type = ctypes.windll.kernel32.GetDriveTypeW(letter)
        return drive_type == 2  # DRIVE_REMOVABLE
    except (AttributeError, OSError):
        return None


def _eject_drive(drive_letter: str) -> None:
    """Expulsa una unidad USB usando el Shell de Windows.

    Usa el mismo mecanismo que el explorador de Windows:
    Shell.Application.Namespace(17).ParseName("X:").InvokeVerb("Eject")
    """
    # Normalizar: solo la letra con ':'
    drive = drive_letter.rstrip("\\")

    ps_script = (
        f'$shell = New-Object -ComObject Shell.Application; '
        f'$item = $shell.Namespace(17).ParseName("{ps_escape(drive)}"); '
        f'if ($item) {{ $item.InvokeVerb("Eject") }} '
        f'else {{ exit 1 }}'
    )

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if stderr:
                console.print(f"[red]Error al expulsar: {stderr}[/red]")
            else:
                console.print(f"[red]No se pudo expulsar {drive}. Verifica que no haya archivos abiertos.[/red]")
            return

        # InvokeVerb("Eject") via COM es "fire-and-forget": el comando puede
        # devolver returncode 0 aunque la expulsion real no se haya completado
        # (p. ej. archivos abiertos). Verificar activamente antes de afirmar
        # exito.
        ejected_confirmed = False
        verification_failed = False
        for _ in range(10):
            time.sleep(0.5)
            present = _drive_still_present(drive)
            if present is None:
                verification_failed = True
                break
            if not present:
                ejected_confirmed = True
                break

        if ejected_confirmed:
            console.print(f"\n[bold green]Unidad {drive} expulsada correctamente.[/bold green]")
            console.print("[dim]Ya puedes retirar el dispositivo de forma segura.[/dim]")
        elif verification_failed:
            console.print(
                f"\n[yellow]Se envio el comando de expulsion para {drive}, pero no fue "
                "posible verificar en este sistema si la unidad realmente se expulso. "
                "Verifica manualmente (p. ej. en el explorador de archivos) antes de "
                "retirar el dispositivo.[/yellow]"
            )
        else:
            console.print(
                f"\n[yellow]Se envio el comando de expulsion para {drive}, pero la unidad "
                "todavia aparece en el sistema. Puede que siga en uso o que la expulsion "
                "no se haya completado. No la retires todavia; verifica manualmente.[/yellow]"
            )

    except subprocess.TimeoutExpired:
        console.print(
            f"[red]Timeout al intentar expulsar {drive}.[/red]\n"
            "[dim]Puede haber archivos abiertos en la unidad. Cierralos e intenta de nuevo.[/dim]"
        )
    except OSError as e:
        console.print(f"[red]Error del sistema: {e}[/red]")


def usb_eject_menu() -> None:
    """Menu de expulsion segura de USB."""
    console.print("\n[bold cyan]Expulsion Segura de USB[/bold cyan]\n")

    drives = get_removable_drives()
    if not drives:
        console.print("[yellow]No se detectaron unidades USB conectadas.[/yellow]")
        return

    console.print("[bold]Unidades USB detectadas:[/bold]")
    for i, drive in enumerate(drives, 1):
        console.print(f"  [cyan]{i}[/cyan] - {drive}")

    if len(drives) == 1:
        drive = drives[0]
        console.print(f"\n[dim]Solo hay una unidad: {drive}[/dim]")
    else:
        choice = Prompt.ask(
            "\n[bold]Selecciona la unidad a expulsar[/bold]",
            choices=[str(i) for i in range(1, len(drives) + 1)],
        )
        drive = drives[int(choice) - 1]

    confirm = Prompt.ask(
        f"[bold]Expulsar {drive} ?[/bold]",
        choices=["s", "n"], default="s",
    )
    if confirm != "s":
        console.print("[dim]Operacion cancelada.[/dim]")
        return

    with console.status(f"[bold green]Expulsando {drive}..."):
        _eject_drive(drive)
