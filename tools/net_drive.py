"""Mapeo de unidades de red: ver, conectar y desconectar."""

import subprocess

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

console = Console()


def _run_net_use(args: list[str]) -> subprocess.CompletedProcess:
    """Ejecuta 'net use' con los argumentos dados."""
    return subprocess.run(
        ["net", "use"] + args,
        capture_output=True, text=True, timeout=30,
    )


def _parse_net_use_output() -> list[dict]:
    """Parsea la salida de 'net use' y devuelve lista de unidades mapeadas.

    Usa parseo posicional para funcionar en cualquier locale de Windows.
    """
    try:
        result = _run_net_use([])
    except (subprocess.TimeoutExpired, OSError) as e:
        console.print(f"[red]Error al ejecutar net use: {e}[/red]")
        return []

    if result.returncode != 0:
        return []

    drives = []
    lines = result.stdout.splitlines()

    for line in lines:
        # Las lineas de unidades mapeadas empiezan con OK, Disconnected, Unavailable, etc.
        stripped = line.strip()
        if not stripped:
            continue

        # Buscar lineas que contengan una letra de unidad seguida de ':'
        # y una ruta UNC (\\)
        parts = stripped.split()
        if len(parts) < 3:
            continue

        # Detectar patron: STATUS LETRA: \\ruta o LETRA: \\ruta
        drive_letter = None
        remote_path = None
        status = ""

        for i, part in enumerate(parts):
            if len(part) == 2 and part[0].isalpha() and part[1] == ":":
                drive_letter = part.upper()
                status = " ".join(parts[:i]) if i > 0 else ""
                # Buscar la ruta UNC despues de la letra
                for j in range(i + 1, len(parts)):
                    if parts[j].startswith("\\\\"):
                        remote_path = parts[j]
                        break
                break

        if drive_letter and remote_path:
            drives.append({
                "status": status,
                "letter": drive_letter,
                "remote": remote_path,
            })

    return drives


def _show_mapped_drives() -> None:
    """Muestra las unidades de red mapeadas en una tabla."""
    console.print("\n[bold cyan]Unidades de Red Mapeadas[/bold cyan]\n")

    drives = _parse_net_use_output()
    if not drives:
        console.print("[yellow]No hay unidades de red mapeadas.[/yellow]")
        return

    table = Table()
    table.add_column("Letra", style="bold cyan")
    table.add_column("Ruta remota")
    table.add_column("Estado")

    for d in drives:
        status_style = "green" if d["status"].upper() == "OK" else "yellow"
        table.add_row(d["letter"], d["remote"], f"[{status_style}]{d['status']}[/{status_style}]")

    console.print(table)


def _map_new_drive() -> None:
    """Mapea una nueva unidad de red."""
    console.print("\n[bold cyan]Mapear Nueva Unidad de Red[/bold cyan]\n")

    letter = Prompt.ask("[bold]Letra de unidad[/bold] (ej: Z)").strip().upper()
    if not letter or not letter[0].isalpha():
        console.print("[red]Letra de unidad invalida.[/red]")
        return
    letter = letter[0] + ":"

    remote = Prompt.ask("[bold]Ruta UNC[/bold] (ej: \\\\servidor\\carpeta)").strip()
    if not remote.startswith("\\\\"):
        console.print("[red]La ruta debe ser UNC (empezar con \\\\).[/red]")
        return

    use_creds = Prompt.ask(
        "[bold]Requiere credenciales?[/bold]",
        choices=["s", "n"], default="n",
    )

    args = [letter, remote, "/persistent:yes"]

    if use_creds == "s":
        user = Prompt.ask("[bold]Usuario[/bold] (ej: DOMINIO\\usuario)").strip()
        password = Prompt.ask("[bold]Contrasena[/bold]", password=True)
        args.extend([f"/user:{user}", password])

    try:
        with console.status("[bold green]Conectando..."):
            result = _run_net_use(args)

        if result.returncode == 0:
            console.print(f"\n[bold green]Unidad {letter} mapeada a {remote}[/bold green]")
        else:
            error = result.stderr.strip() or result.stdout.strip()
            console.print(f"[red]Error al mapear: {error}[/red]")
    except subprocess.TimeoutExpired:
        console.print("[red]Timeout al intentar conectar. El servidor puede no estar accesible.[/red]")
    except OSError as e:
        console.print(f"[red]Error del sistema: {e}[/red]")


def _disconnect_drive() -> None:
    """Desconecta una unidad de red mapeada."""
    console.print("\n[bold cyan]Desconectar Unidad de Red[/bold cyan]\n")

    drives = _parse_net_use_output()
    if not drives:
        console.print("[yellow]No hay unidades de red mapeadas para desconectar.[/yellow]")
        return

    console.print("[bold]Unidades mapeadas:[/bold]")
    for i, d in enumerate(drives, 1):
        console.print(f"  [cyan]{i}[/cyan] - {d['letter']} -> {d['remote']}")

    choice = Prompt.ask(
        "\n[bold]Selecciona la unidad a desconectar[/bold]",
        choices=[str(i) for i in range(1, len(drives) + 1)],
    )
    drive = drives[int(choice) - 1]

    confirm = Prompt.ask(
        f"[bold]Desconectar {drive['letter']} ({drive['remote']}) ?[/bold]",
        choices=["s", "n"], default="s",
    )
    if confirm != "s":
        console.print("[dim]Operacion cancelada.[/dim]")
        return

    try:
        with console.status("[bold green]Desconectando..."):
            result = _run_net_use([drive["letter"], "/delete"])

        if result.returncode == 0:
            console.print(f"\n[bold green]Unidad {drive['letter']} desconectada.[/bold green]")
        else:
            error = result.stderr.strip() or result.stdout.strip()
            console.print(f"[red]Error al desconectar: {error}[/red]")
    except subprocess.TimeoutExpired:
        console.print("[red]Timeout al intentar desconectar.[/red]")
    except OSError as e:
        console.print(f"[red]Error del sistema: {e}[/red]")


def net_drive_menu() -> None:
    """Sub-menu de mapeo de unidades de red."""
    while True:
        console.print(
            "\n[bold cyan]Unidades de Red[/bold cyan]\n"
            "  [bold]1[/bold] - Ver unidades mapeadas\n"
            "  [bold]2[/bold] - Mapear nueva unidad\n"
            "  [bold]3[/bold] - Desconectar unidad\n"
            "  [bold]0[/bold] - Volver"
        )
        choice = Prompt.ask("[bold cyan]Opcion[/bold cyan]", default="0")

        if choice == "1":
            _show_mapped_drives()
        elif choice == "2":
            _map_new_drive()
        elif choice == "3":
            _disconnect_drive()
        elif choice == "0":
            break
        else:
            console.print("[red]Opcion no valida.[/red]")
