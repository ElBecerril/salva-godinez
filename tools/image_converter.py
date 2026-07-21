"""Conversor de imagenes: PNG, JPG, BMP, WEBP, ICO."""

import os

from rich.progress import Progress, BarColumn, TextColumn
from rich.prompt import Prompt
from utils import console


SUPPORTED_FORMATS = {
    "png": ".png",
    "jpg": ".jpg",
    "bmp": ".bmp",
    "webp": ".webp",
    "ico": ".ico",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".ico", ".tiff", ".tif", ".gif"}


# --- Logica (sin UI) ---


def _get_pillow():
    """Import lazy de Pillow. Devuelve el modulo Image, o None si no esta instalado."""
    try:
        from PIL import Image
        return Image
    except ImportError:
        return None


def _collect_images(path: str) -> dict:
    """Recolecta archivos de imagen de un archivo o directorio.

    Returns:
        dict con: images (lista de rutas), error (mensaje de error o None).
    """
    path = path.strip().strip('"')

    if os.path.isfile(path):
        ext = os.path.splitext(path)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            return {"images": [path], "error": None}
        return {"images": [], "error": f"El archivo no es una imagen soportada: {ext}"}

    if os.path.isdir(path):
        images = []
        for fname in sorted(os.listdir(path)):
            ext = os.path.splitext(fname)[1].lower()
            if ext in IMAGE_EXTENSIONS:
                images.append(os.path.join(path, fname))
        return {"images": images, "error": None}

    return {"images": [], "error": "Ruta no encontrada."}


def _safe_output_path(output_dir: str, base_name: str, ext: str) -> str:
    """Genera ruta de salida con sufijo numerico si ya existe.

    El directorio suele venir de un dialogo de tkinter (barras /) y el nombre
    se une con os.path.join (barra \\ en Windows), asi que la ruta cruda queda
    con separadores mezclados: "C:/Users/...\\archivo.pdf". Se normaliza para
    que el mensaje que ve el usuario y el archivo real usen un solo estilo.
    """
    out_path = os.path.join(output_dir, f"{base_name}{ext}")
    if not os.path.exists(out_path):
        return os.path.normpath(out_path)

    counter = 1
    while True:
        out_path = os.path.join(output_dir, f"{base_name}_{counter}{ext}")
        if not os.path.exists(out_path):
            return os.path.normpath(out_path)
        counter += 1


def _convert_image(Image, src: str, target_ext: str, output_dir: str) -> dict:
    """Convierte una imagen al formato destino.

    Returns:
        dict con: ok, output (ruta creada o None), multiframe (n_frames si >1,
        si no None), error (mensaje o None).
    """
    base_name = os.path.splitext(os.path.basename(src))[0]
    out_path = _safe_output_path(output_dir, base_name, target_ext)
    multiframe = None

    try:
        from PIL import ImageOps

        img = Image.open(src)

        # Imagenes multipagina/animadas (GIF, TIFF): solo se convierte el
        # primer frame, avisamos al usuario para que no se sorprenda.
        if getattr(img, "n_frames", 1) > 1:
            multiframe = img.n_frames

        # Respeta la orientacion EXIF (fotos de celular vienen rotadas por
        # metadata, no por los pixeles reales).
        img = ImageOps.exif_transpose(img)

        # RGBA → RGB para formatos que no soportan transparencia
        if target_ext in (".jpg", ".bmp") and img.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
            img = background

        # ICO tiene tamano maximo de 256x256
        if target_ext == ".ico":
            max_size = 256
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        # Guardar
        save_kwargs = {}
        if target_ext == ".jpg":
            save_kwargs["quality"] = 90
        elif target_ext == ".webp":
            save_kwargs["quality"] = 85
        elif target_ext == ".ico":
            save_kwargs["sizes"] = [(img.width, img.height)]

        img.save(out_path, **save_kwargs)
        return {"ok": True, "output": out_path, "multiframe": multiframe, "error": None}

    except Exception as e:
        return {"ok": False, "output": None, "multiframe": multiframe, "error": str(e)}


# --- Interfaz de consola ---


def image_converter_menu() -> None:
    """Menu del conversor de imagenes."""
    Image = _get_pillow()
    if not Image:
        console.print(
            "[bold red]Pillow no esta instalado.[/bold red]\n"
            "[dim]Ejecuta: pip install Pillow[/dim]"
        )
        return

    console.print("\n[bold cyan]Convertir Imagenes[/bold cyan]\n")
    console.print("[dim]Formatos soportados: PNG, JPG, BMP, WEBP, ICO[/dim]\n")

    path = Prompt.ask("[bold]Ruta del archivo o carpeta[/bold]").strip().strip('"')
    collected = _collect_images(path)
    images = collected["images"]

    if collected["error"]:
        console.print(f"[red]{collected['error']}[/red]")

    if not images:
        console.print("[yellow]No se encontraron imagenes para convertir.[/yellow]")
        return

    console.print(f"[dim]{len(images)} imagen(es) encontrada(s).[/dim]\n")

    format_list = ", ".join(SUPPORTED_FORMATS.keys())
    target = Prompt.ask(
        f"[bold]Formato destino[/bold] ({format_list})",
        choices=list(SUPPORTED_FORMATS.keys()),
    ).lower()
    target_ext = SUPPORTED_FORMATS[target]

    # Carpeta de salida
    if os.path.isfile(path):
        default_out = os.path.dirname(path) or "."
    else:
        default_out = os.path.join(path, f"convertido_{target}")

    output_dir = Prompt.ask(
        "[bold]Carpeta de salida[/bold]",
        default=default_out,
    ).strip().strip('"')
    os.makedirs(output_dir, exist_ok=True)

    # Convertir con barra de progreso
    converted = 0
    failed = 0

    with Progress(
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("[dim]{task.completed}/{task.total}[/dim]"),
        console=console,
    ) as progress:
        task = progress.add_task("Convirtiendo...", total=len(images))

        for src in images:
            result = _convert_image(Image, src, target_ext, output_dir)
            if result["multiframe"]:
                console.print(
                    f"  [yellow]{os.path.basename(src)} tiene {result['multiframe']} frames/paginas; "
                    "solo se convertira el primero.[/yellow]"
                )
            if result["ok"]:
                converted += 1
            else:
                console.print(f"  [red]Error con {os.path.basename(src)}: {result['error']}[/red]")
                failed += 1
            progress.advance(task)

    console.print(f"\n[bold green]Conversion completada![/bold green]")
    console.print(f"  Convertidos: [bold]{converted}[/bold]")
    if failed:
        console.print(f"  Fallidos: [red]{failed}[/red]")
    console.print(f"  Carpeta: [bold]{output_dir}[/bold]")
