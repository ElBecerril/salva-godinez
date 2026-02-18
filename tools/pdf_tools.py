"""Herramientas PDF: unir, dividir, rotar, eliminar, reordenar, extraer texto, convertir y mas."""

import os

from rich.prompt import Prompt
from utils import console



def _get_pypdf():
    """Import lazy de pypdf para no crashear si no esta instalado."""
    try:
        import pypdf
        return pypdf
    except ImportError:
        console.print(
            "[bold red]pypdf no esta instalado.[/bold red]\n"
            "[dim]Ejecuta: pip install pypdf[/dim]"
        )
        return None


def _get_pillow():
    """Import lazy de Pillow para no crashear si no esta instalado."""
    try:
        from PIL import Image
        return Image
    except ImportError:
        console.print(
            "[bold red]Pillow no esta instalado.[/bold red]\n"
            "[dim]Ejecuta: pip install Pillow[/dim]"
        )
        return None


def _get_pymupdf():
    """Import lazy de PyMuPDF (opcional, para PDF a imagenes)."""
    try:
        import fitz
        return fitz
    except ImportError:
        console.print(
            "[bold red]PyMuPDF no esta instalado.[/bold red]\n"
            "[dim]Ejecuta: pip install PyMuPDF[/dim]\n"
            "[dim]Esta dependencia es opcional y solo se necesita para 'PDF a Imagenes'.[/dim]"
        )
        return None


def _open_pdf_reader(prompt_text="[bold]Ruta del PDF[/bold]"):
    """Pide ruta al usuario, valida y abre PdfReader.

    Retorna (pypdf, reader, path) o None si falla.
    """
    pypdf = _get_pypdf()
    if not pypdf:
        return None

    path = Prompt.ask(prompt_text).strip().strip('"')
    if not os.path.isfile(path):
        console.print("[red]Archivo no encontrado.[/red]")
        return None

    try:
        reader = pypdf.PdfReader(path)
        return pypdf, reader, path
    except (pypdf.errors.PdfReadError, pypdf.errors.PdfStreamError, OSError) as e:
        console.print(f"[red]Error al leer PDF (archivo corrupto o invalido): {e}[/red]")
        return None


def merge_pdfs() -> None:
    """Une multiples archivos PDF en uno solo."""
    pypdf = _get_pypdf()
    if not pypdf:
        return

    console.print("\n[bold cyan]Unir PDFs[/bold cyan]")
    console.print("[dim]Agrega todos los PDFs que necesites, no hay limite.[/dim]")
    console.print("[dim]Ingresa las rutas una por linea (linea vacia para terminar):[/dim]\n")

    paths = []
    while True:
        path = Prompt.ask(f"  [bold]PDF {len(paths) + 1}[/bold] (vacio para terminar)", default="").strip().strip('"')
        if not path:
            break
        if not os.path.isfile(path):
            console.print(f"  [red]Archivo no encontrado: {path}[/red]")
            continue
        paths.append(path)

    if len(paths) < 2:
        console.print("[yellow]Se necesitan al menos 2 PDFs para unir.[/yellow]")
        return

    output = Prompt.ask(
        "[bold]Ruta del PDF de salida[/bold]",
        default=os.path.join(os.path.dirname(paths[0]), "unido.pdf"),
    ).strip().strip('"')

    try:
        writer = pypdf.PdfWriter()
        for path in paths:
            try:
                reader = pypdf.PdfReader(path)
            except (pypdf.errors.PdfReadError, pypdf.errors.PdfStreamError) as e:
                console.print(f"  [red]PDF corrupto o invalido: {os.path.basename(path)} — {e}[/red]")
                continue
            for page in reader.pages:
                writer.add_page(page)

        if len(writer.pages) == 0:
            console.print("[red]No se pudieron leer paginas de ninguno de los PDFs.[/red]")
            return

        with open(output, "wb") as f:
            writer.write(f)

        total_pages = len(writer.pages)
        console.print(f"\n[bold green]PDF unido creado: {output} ({total_pages} paginas)[/bold green]")
    except (pypdf.errors.PdfReadError, OSError) as e:
        console.print(f"[red]Error al unir PDFs: {e}[/red]")


def split_pdf() -> None:
    """Divide un PDF en paginas individuales o por rango."""
    pypdf = _get_pypdf()
    if not pypdf:
        return

    console.print("\n[bold cyan]Dividir PDF[/bold cyan]")
    console.print("[dim]Separa un PDF en paginas individuales o extrae un rango especifico.[/dim]")

    path = Prompt.ask("[bold]Ruta del PDF a dividir[/bold]").strip().strip('"')
    if not os.path.isfile(path):
        console.print("[red]Archivo no encontrado.[/red]")
        return

    try:
        reader = pypdf.PdfReader(path)
        total = len(reader.pages)
    except (pypdf.errors.PdfReadError, pypdf.errors.PdfStreamError, OSError) as e:
        console.print(f"[red]Error al leer PDF (archivo corrupto o invalido): {e}[/red]")
        return

    console.print(f"[dim]El PDF tiene {total} paginas.[/dim]")

    mode = Prompt.ask(
        "[bold]Modo[/bold]",
        choices=["individual", "rango"],
        default="individual",
    )

    output_dir = Prompt.ask(
        "[bold]Carpeta de salida[/bold]",
        default=os.path.join(os.path.dirname(path), "pdf_dividido"),
    ).strip().strip('"')
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(path))[0]

    if mode == "individual":
        for i, page in enumerate(reader.pages, 1):
            writer = pypdf.PdfWriter()
            writer.add_page(page)
            out_path = os.path.join(output_dir, f"{base_name}_pag{i}.pdf")
            with open(out_path, "wb") as f:
                writer.write(f)
        console.print(f"\n[bold green]{total} archivos creados en: {output_dir}[/bold green]")
    else:
        rango = Prompt.ask("[bold]Rango (ej: 1-5)[/bold]").strip()
        try:
            start, end = rango.split("-")
            start, end = int(start), int(end)
            if start < 1 or end > total or start > end:
                console.print(f"[red]Rango invalido. El PDF tiene paginas 1-{total}.[/red]")
                return
        except ValueError:
            console.print("[red]Formato invalido. Usa: inicio-fin (ej: 1-5)[/red]")
            return

        writer = pypdf.PdfWriter()
        for i in range(start - 1, end):
            writer.add_page(reader.pages[i])

        out_path = os.path.join(output_dir, f"{base_name}_pag{start}-{end}.pdf")
        with open(out_path, "wb") as f:
            writer.write(f)
        console.print(f"\n[bold green]PDF creado: {out_path} ({end - start + 1} paginas)[/bold green]")


def rotate_pages() -> None:
    """Rota paginas de un PDF (90, 180 o 270 grados)."""
    console.print("\n[bold cyan]Rotar Paginas[/bold cyan]")
    console.print("[dim]Rota todas o algunas paginas de un PDF.[/dim]")

    result = _open_pdf_reader("[bold]Ruta del PDF a rotar[/bold]")
    if not result:
        return
    pypdf, reader, path = result

    total = len(reader.pages)
    console.print(f"[dim]El PDF tiene {total} paginas.[/dim]")

    angle = Prompt.ask(
        "[bold]Angulo de rotacion[/bold]",
        choices=["90", "180", "270"],
        default="90",
    )
    angle = int(angle)

    scope = Prompt.ask(
        "[bold]Paginas a rotar[/bold] (todas / rango ej: 1,3,5 o 2-4)",
        default="todas",
    ).strip()

    # Determinar indices de paginas a rotar
    if scope.lower() == "todas":
        indices = list(range(total))
    else:
        indices = _parse_page_selection(scope, total)
        if indices is None:
            return

    try:
        writer = pypdf.PdfWriter()
        for i, page in enumerate(reader.pages):
            if i in indices:
                page.rotate(angle)
            writer.add_page(page)

        base_name = os.path.splitext(path)[0]
        output = f"{base_name}_rotado.pdf"
        with open(output, "wb") as f:
            writer.write(f)

        rotated_count = len(indices)
        console.print(f"\n[bold green]PDF rotado creado: {output} ({rotated_count} paginas rotadas {angle}°)[/bold green]")
    except (pypdf.errors.PdfReadError, OSError) as e:
        console.print(f"[red]Error al rotar PDF: {e}[/red]")


def _parse_page_selection(selection: str, total: int):
    """Parsea seleccion de paginas tipo '1,3,5' o '2-4' o '1,3-5,8'.

    Retorna set de indices (0-based) o None si hay error.
    """
    indices = set()
    parts = selection.replace(" ", "").split(",")
    for part in parts:
        if "-" in part:
            try:
                start, end = part.split("-")
                start, end = int(start), int(end)
                if start < 1 or end > total or start > end:
                    console.print(f"[red]Rango invalido: {part}. El PDF tiene paginas 1-{total}.[/red]")
                    return None
                indices.update(range(start - 1, end))
            except ValueError:
                console.print(f"[red]Formato invalido: {part}. Usa: inicio-fin (ej: 2-4)[/red]")
                return None
        else:
            try:
                num = int(part)
                if num < 1 or num > total:
                    console.print(f"[red]Pagina {num} fuera de rango. El PDF tiene paginas 1-{total}.[/red]")
                    return None
                indices.add(num - 1)
            except ValueError:
                console.print(f"[red]Formato invalido: {part}. Usa numeros separados por comas.[/red]")
                return None
    return indices


def delete_pages() -> None:
    """Elimina paginas especificas de un PDF."""
    console.print("\n[bold cyan]Eliminar Paginas[/bold cyan]")
    console.print("[dim]Elimina paginas especificas de un PDF.[/dim]")

    result = _open_pdf_reader("[bold]Ruta del PDF[/bold]")
    if not result:
        return
    pypdf, reader, path = result

    total = len(reader.pages)
    console.print(f"[dim]El PDF tiene {total} paginas.[/dim]")

    selection = Prompt.ask(
        "[bold]Paginas a eliminar[/bold] (ej: 1,3,5 o 2-4)",
    ).strip()

    indices = _parse_page_selection(selection, total)
    if indices is None:
        return

    if len(indices) >= total:
        console.print("[red]No puedes eliminar todas las paginas del PDF.[/red]")
        return

    try:
        writer = pypdf.PdfWriter()
        for i, page in enumerate(reader.pages):
            if i not in indices:
                writer.add_page(page)

        base_name = os.path.splitext(path)[0]
        output = f"{base_name}_editado.pdf"
        with open(output, "wb") as f:
            writer.write(f)

        remaining = total - len(indices)
        console.print(
            f"\n[bold green]PDF creado: {output} "
            f"({len(indices)} paginas eliminadas, {remaining} restantes)[/bold green]"
        )
    except (pypdf.errors.PdfReadError, OSError) as e:
        console.print(f"[red]Error al editar PDF: {e}[/red]")


def reorder_pages() -> None:
    """Reordena las paginas de un PDF."""
    console.print("\n[bold cyan]Reordenar Paginas[/bold cyan]")
    console.print("[dim]Cambia el orden de las paginas de un PDF.[/dim]")

    result = _open_pdf_reader("[bold]Ruta del PDF[/bold]")
    if not result:
        return
    pypdf, reader, path = result

    total = len(reader.pages)
    console.print(f"[dim]El PDF tiene {total} paginas. Orden actual: {','.join(str(i) for i in range(1, total + 1))}[/dim]")

    order_str = Prompt.ask(
        f"[bold]Nuevo orden[/bold] (ej: 3,1,2,5,4 — debe incluir las {total} paginas)",
    ).strip()

    try:
        new_order = [int(x.strip()) for x in order_str.split(",")]
    except ValueError:
        console.print("[red]Formato invalido. Usa numeros separados por comas.[/red]")
        return

    if sorted(new_order) != list(range(1, total + 1)):
        console.print(f"[red]Debes incluir todas las paginas (1-{total}) exactamente una vez.[/red]")
        return

    try:
        writer = pypdf.PdfWriter()
        for num in new_order:
            writer.add_page(reader.pages[num - 1])

        base_name = os.path.splitext(path)[0]
        output = f"{base_name}_reordenado.pdf"
        with open(output, "wb") as f:
            writer.write(f)

        console.print(f"\n[bold green]PDF reordenado creado: {output}[/bold green]")
    except (pypdf.errors.PdfReadError, OSError) as e:
        console.print(f"[red]Error al reordenar PDF: {e}[/red]")


def extract_text() -> None:
    """Extrae el texto de un PDF a un archivo .txt."""
    console.print("\n[bold cyan]Extraer Texto[/bold cyan]")
    console.print("[dim]Extrae todo el texto de un PDF a un archivo de texto.[/dim]")

    result = _open_pdf_reader("[bold]Ruta del PDF[/bold]")
    if not result:
        return
    pypdf, reader, path = result

    total = len(reader.pages)
    console.print(f"[dim]El PDF tiene {total} paginas.[/dim]")

    try:
        text_parts = []
        for i, page in enumerate(reader.pages, 1):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"--- Pagina {i} ---\n{page_text}")

        if not text_parts:
            console.print("[yellow]No se pudo extraer texto del PDF (puede ser un PDF escaneado/imagen).[/yellow]")
            return

        full_text = "\n\n".join(text_parts)

        base_name = os.path.splitext(path)[0]
        output = f"{base_name}.txt"
        with open(output, "w", encoding="utf-8") as f:
            f.write(full_text)

        console.print(f"\n[bold green]Texto extraido: {output} ({len(full_text):,} caracteres)[/bold green]")
    except (pypdf.errors.PdfReadError, OSError) as e:
        console.print(f"[red]Error al extraer texto: {e}[/red]")


def images_to_pdf() -> None:
    """Convierte imagenes (JPG/PNG/BMP/WEBP) a un PDF."""
    Image = _get_pillow()
    if not Image:
        return

    console.print("\n[bold cyan]Imagenes a PDF[/bold cyan]")
    console.print("[dim]Convierte imagenes a un solo PDF. Formatos: JPG, PNG, BMP, WEBP.[/dim]")
    console.print("[dim]Ingresa las rutas una por linea (linea vacia para terminar):[/dim]\n")

    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    paths = []
    while True:
        path = Prompt.ask(f"  [bold]Imagen {len(paths) + 1}[/bold] (vacio para terminar)", default="").strip().strip('"')
        if not path:
            break
        if not os.path.isfile(path):
            console.print(f"  [red]Archivo no encontrado: {path}[/red]")
            continue
        ext = os.path.splitext(path)[1].lower()
        if ext not in valid_exts:
            console.print(f"  [red]Formato no soportado: {ext}. Usa JPG, PNG, BMP o WEBP.[/red]")
            continue
        paths.append(path)

    if not paths:
        console.print("[yellow]No se agregaron imagenes.[/yellow]")
        return

    output = Prompt.ask(
        "[bold]Ruta del PDF de salida[/bold]",
        default=os.path.join(os.path.dirname(paths[0]), "imagenes.pdf"),
    ).strip().strip('"')

    try:
        images = []
        for p in paths:
            img = Image.open(p)
            # RGBA/P/LA → RGB para compatibilidad con PDF
            if img.mode in ("RGBA", "P", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)

        if len(images) == 1:
            images[0].save(output, "PDF")
        else:
            images[0].save(output, "PDF", save_all=True, append_images=images[1:])

        console.print(f"\n[bold green]PDF creado: {output} ({len(images)} imagenes)[/bold green]")
    except (OSError, ValueError) as e:
        console.print(f"[red]Error al crear PDF: {e}[/red]")


def pdf_to_images() -> None:
    """Convierte cada pagina de un PDF a imagen (PNG/JPG)."""
    fitz = _get_pymupdf()
    if not fitz:
        return

    console.print("\n[bold cyan]PDF a Imagenes[/bold cyan]")
    console.print("[dim]Convierte cada pagina de un PDF a imagen PNG o JPG.[/dim]")

    path = Prompt.ask("[bold]Ruta del PDF[/bold]").strip().strip('"')
    if not os.path.isfile(path):
        console.print("[red]Archivo no encontrado.[/red]")
        return

    fmt = Prompt.ask(
        "[bold]Formato de salida[/bold]",
        choices=["png", "jpg"],
        default="png",
    )

    dpi_str = Prompt.ask("[bold]DPI[/bold] (resolucion)", default="150").strip()
    try:
        dpi = int(dpi_str)
        if dpi < 72 or dpi > 600:
            console.print("[red]DPI debe estar entre 72 y 600.[/red]")
            return
    except ValueError:
        console.print("[red]DPI invalido.[/red]")
        return

    output_dir = Prompt.ask(
        "[bold]Carpeta de salida[/bold]",
        default=os.path.join(os.path.dirname(path), "pdf_imagenes"),
    ).strip().strip('"')
    os.makedirs(output_dir, exist_ok=True)

    try:
        doc = fitz.open(path)
        base_name = os.path.splitext(os.path.basename(path))[0]
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)

        page_count = len(doc)
        for i, page in enumerate(doc, 1):
            pix = page.get_pixmap(matrix=matrix)
            ext = "png" if fmt == "png" else "jpg"
            out_path = os.path.join(output_dir, f"{base_name}_pag{i}.{ext}")
            if fmt == "jpg":
                pix.save(out_path, jpg_quality=95)
            else:
                pix.save(out_path)

        doc.close()
        console.print(f"\n[bold green]{page_count} imagenes creadas en: {output_dir} ({dpi} DPI)[/bold green]")
    except Exception as e:
        console.print(f"[red]Error al convertir PDF a imagenes: {e}[/red]")


def protect_pdf() -> None:
    """Protege o desprotege un PDF con password."""
    console.print("\n[bold cyan]Proteger/Desproteger PDF[/bold cyan]")
    console.print("[dim]Agrega o quita proteccion con password a un PDF.[/dim]")

    pypdf = _get_pypdf()
    if not pypdf:
        return

    path = Prompt.ask("[bold]Ruta del PDF[/bold]").strip().strip('"')
    if not os.path.isfile(path):
        console.print("[red]Archivo no encontrado.[/red]")
        return

    try:
        reader = pypdf.PdfReader(path)
    except (pypdf.errors.PdfReadError, pypdf.errors.PdfStreamError, OSError) as e:
        console.print(f"[red]Error al leer PDF: {e}[/red]")
        return

    base_name = os.path.splitext(path)[0]

    if reader.is_encrypted:
        # Desproteger
        console.print("[dim]El PDF esta protegido con password.[/dim]")
        password = Prompt.ask("[bold]Password actual[/bold]").strip()
        try:
            if not reader.decrypt(password):
                console.print("[red]Password incorrecto.[/red]")
                return
        except Exception:
            console.print("[red]Password incorrecto o PDF corrupto.[/red]")
            return

        writer = pypdf.PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        output = f"{base_name}_desprotegido.pdf"
        with open(output, "wb") as f:
            writer.write(f)

        console.print(f"\n[bold green]PDF desprotegido creado: {output}[/bold green]")
    else:
        # Proteger
        console.print("[dim]El PDF no tiene proteccion.[/dim]")
        password = Prompt.ask("[bold]Nueva password[/bold]").strip()
        if not password:
            console.print("[yellow]Password vacio, operacion cancelada.[/yellow]")
            return

        confirm = Prompt.ask("[bold]Confirmar password[/bold]").strip()
        if password != confirm:
            console.print("[red]Las passwords no coinciden.[/red]")
            return

        writer = pypdf.PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)

        output = f"{base_name}_protegido.pdf"
        with open(output, "wb") as f:
            writer.write(f)

        console.print(f"\n[bold green]PDF protegido creado: {output}[/bold green]")


def pdf_metadata() -> None:
    """Muestra y permite limpiar los metadatos de un PDF."""
    console.print("\n[bold cyan]Ver/Limpiar Metadatos[/bold cyan]")
    console.print("[dim]Muestra informacion del PDF y permite limpiar metadatos.[/dim]")

    result = _open_pdf_reader("[bold]Ruta del PDF[/bold]")
    if not result:
        return
    pypdf, reader, path = result

    total = len(reader.pages)
    meta = reader.metadata

    console.print(f"\n[bold]Informacion del PDF:[/bold]")
    console.print(f"  Paginas: {total}")

    if meta:
        fields = [
            ("Titulo", meta.title),
            ("Autor", meta.author),
            ("Asunto", meta.subject),
            ("Creador", meta.creator),
            ("Productor", meta.producer),
            ("Fecha creacion", str(meta.creation_date) if meta.creation_date else None),
            ("Fecha modificacion", str(meta.modification_date) if meta.modification_date else None),
        ]
        has_data = False
        for label, value in fields:
            if value:
                console.print(f"  {label}: {value}")
                has_data = True
        if not has_data:
            console.print("  [dim]No hay metadatos adicionales.[/dim]")
    else:
        console.print("  [dim]No hay metadatos.[/dim]")

    action = Prompt.ask(
        "\n[bold]Limpiar metadatos?[/bold]",
        choices=["si", "no"],
        default="no",
    )

    if action == "si":
        try:
            writer = pypdf.PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.add_metadata({
                "/Title": "",
                "/Author": "",
                "/Subject": "",
                "/Creator": "",
                "/Producer": "",
            })

            base_name = os.path.splitext(path)[0]
            output = f"{base_name}_limpio.pdf"
            with open(output, "wb") as f:
                writer.write(f)

            console.print(f"\n[bold green]PDF sin metadatos creado: {output}[/bold green]")
        except (pypdf.errors.PdfReadError, OSError) as e:
            console.print(f"[red]Error al limpiar metadatos: {e}[/red]")


def pdf_menu() -> None:
    """Sub-menu de herramientas PDF."""
    while True:
        console.print(
            "\n[bold cyan]Herramientas PDF[/bold cyan]\n"
            "  [bold]1[/bold]  - Unir PDFs\n"
            "  [bold]2[/bold]  - Dividir PDF\n"
            "  [bold]3[/bold]  - Rotar Paginas\n"
            "  [bold]4[/bold]  - Eliminar Paginas\n"
            "  [bold]5[/bold]  - Reordenar Paginas\n"
            "  [bold]6[/bold]  - Extraer Texto\n"
            "  [bold]7[/bold]  - Imagenes a PDF\n"
            "  [bold]8[/bold]  - PDF a Imagenes\n"
            "  [bold]9[/bold]  - Proteger/Desproteger PDF\n"
            "  [bold]10[/bold] - Ver/Limpiar Metadatos\n"
            "  [bold]0[/bold]  - Volver"
        )
        choice = Prompt.ask("[bold cyan]Opcion[/bold cyan]", default="0")

        if choice == "1":
            merge_pdfs()
        elif choice == "2":
            split_pdf()
        elif choice == "3":
            rotate_pages()
        elif choice == "4":
            delete_pages()
        elif choice == "5":
            reorder_pages()
        elif choice == "6":
            extract_text()
        elif choice == "7":
            images_to_pdf()
        elif choice == "8":
            pdf_to_images()
        elif choice == "9":
            protect_pdf()
        elif choice == "10":
            pdf_metadata()
        elif choice == "0":
            break
        else:
            console.print("[red]Opcion no valida.[/red]")
