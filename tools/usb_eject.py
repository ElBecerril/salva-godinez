"""Expulsion segura de unidades USB."""

import ctypes
import time

from rich.prompt import Prompt

from tools import get_removable_drives
from utils import console


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
    """Expulsa una unidad USB de forma segura via DeviceIoControl.

    Sigue la secuencia canonica de Windows (KB165721): abrir el volumen,
    bloquearlo (LOCK), desmontarlo (DISMOUNT), permitir la remocion del medio
    y expulsarlo (EJECT). Es fiable y no depende de verbos localizados del
    Shell (InvokeVerb("Eject") abria la carpeta en Windows en espanol en vez
    de expulsar).
    """
    # Normalizar: solo la letra con ':'
    drive = drive_letter.rstrip("\\")

    try:
        kernel32 = ctypes.windll.kernel32
    except (AttributeError, OSError):
        console.print("[red]La expulsion segura solo esta disponible en Windows.[/red]")
        return

    # HANDLE es de 64 bits; sin esto ctypes lo trunca a int y rompe la
    # comparacion con INVALID_HANDLE_VALUE.
    kernel32.CreateFileW.restype = ctypes.c_void_p
    invalid_handle = ctypes.c_void_p(-1).value

    # Constantes Win32
    generic_rw = 0xC0000000          # GENERIC_READ | GENERIC_WRITE
    share_rw = 0x00000003            # FILE_SHARE_READ | FILE_SHARE_WRITE
    open_existing = 3
    FSCTL_LOCK_VOLUME = 0x00090018
    FSCTL_DISMOUNT_VOLUME = 0x00090020
    IOCTL_STORAGE_MEDIA_REMOVAL = 0x002D4804
    IOCTL_STORAGE_EJECT_MEDIA = 0x002D4808

    try:
        volume_path = "\\\\.\\" + drive  # \\.\G:
        handle = kernel32.CreateFileW(
            volume_path, generic_rw, share_rw, None, open_existing, 0, None
        )
    except OSError as e:
        console.print(f"[red]Error del sistema al abrir {drive}: {e}[/red]")
        return

    if not handle or handle == invalid_handle:
        console.print(
            f"[red]No se pudo acceder a {drive} para expulsarla.[/red]\n"
            "[dim]Puede requerir permisos de administrador.[/dim]"
        )
        return

    try:
        bytes_returned = ctypes.c_uint32(0)

        # 1. Bloquear el volumen. Falla si hay archivos/programas usandolo;
        #    reintentar da tiempo a que se liberen.
        locked = False
        for _ in range(10):
            if kernel32.DeviceIoControl(
                handle, FSCTL_LOCK_VOLUME, None, 0, None, 0,
                ctypes.byref(bytes_returned), None,
            ):
                locked = True
                break
            time.sleep(0.3)

        if not locked:
            console.print(
                f"[red]No se pudo expulsar {drive}: la unidad esta en uso.[/red]\n"
                "[dim]Cierra los archivos o programas que la usen e intenta de nuevo.[/dim]"
            )
            return

        # 2. Desmontar el sistema de archivos.
        kernel32.DeviceIoControl(
            handle, FSCTL_DISMOUNT_VOLUME, None, 0, None, 0,
            ctypes.byref(bytes_returned), None,
        )

        # 3. Permitir la remocion del medio (PreventMediaRemoval = FALSE).
        prevent_removal = ctypes.c_byte(0)
        kernel32.DeviceIoControl(
            handle, IOCTL_STORAGE_MEDIA_REMOVAL,
            ctypes.byref(prevent_removal), ctypes.sizeof(prevent_removal),
            None, 0, ctypes.byref(bytes_returned), None,
        )

        # 4. Expulsar.
        kernel32.DeviceIoControl(
            handle, IOCTL_STORAGE_EJECT_MEDIA, None, 0, None, 0,
            ctypes.byref(bytes_returned), None,
        )
    finally:
        kernel32.CloseHandle(handle)

    # Verificar activamente que la unidad ya no este presente.
    ejected_confirmed = False
    verification_failed = False
    for _ in range(10):
        time.sleep(0.4)
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
            f"\n[yellow]Se expulso {drive}, pero no fue posible verificar en este "
            "sistema si la unidad realmente se solto. Verifica manualmente (p. ej. "
            "en el explorador de archivos) antes de retirar el dispositivo.[/yellow]"
        )
    else:
        console.print(
            f"\n[yellow]Se envio el comando de expulsion para {drive}, pero la unidad "
            "todavia aparece en el sistema. Puede que siga en uso. No la retires "
            "todavia; verifica manualmente.[/yellow]"
        )


def usb_eject_menu() -> None:
    """Menu de expulsion segura de USB."""
    console.print("\n[bold cyan]Expulsar USB con Seguridad[/bold cyan]\n")

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
        choices=["s", "n"], default="n",
    )
    if confirm != "s":
        console.print("[dim]Operacion cancelada.[/dim]")
        return

    with console.status(f"[bold green]Expulsando {drive}..."):
        _eject_drive(drive)
