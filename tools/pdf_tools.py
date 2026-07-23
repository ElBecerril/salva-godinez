"""Herramientas PDF: unir, dividir, rotar, eliminar, reordenar, extraer texto, convertir y mas."""

import getpass
import os

from rich.markup import escape
from rich.prompt import Prompt
from utils import console
from tools.image_converter import _safe_output_path as _safe_output_path_parts


# ============================================================
# --- Logica (sin UI) ---
# ============================================================
#
# Funciones puras: reciben todo por parametro y devuelven datos
# (dict/list/tuple). No imprimen nada, no preguntan nada. Los
# errores se devuelven como dato ({"ok": False, "error": "..."})
# o se dejan propagar como excepcion. Pueden tocar disco, eso es
# trabajo real, no interfaz.


def _safe_output_path(path: str) -> str:
    """Evita sobrescribir un archivo existente agregando un sufijo numerico.

    Reutiliza la logica de image_converter._safe_output_path, adaptando
    una ruta completa (directorio + nombre + extension) al formato que
    espera esa funcion (directorio, nombre base, extension).
    """
    directory = os.path.dirname(path) or "."
    base_name, ext = os.path.splitext(os.path.basename(path))
    return _safe_output_path_parts(directory, base_name, ext)


def _import_pypdf():
    """Import lazy de pypdf. Retorna el modulo o None (sin imprimir nada)."""
    try:
        import pypdf
        return pypdf
    except ImportError:
        return None


def _import_pillow():
    """Import lazy de Pillow. Retorna Image o None (sin imprimir nada)."""
    try:
        from PIL import Image
        return Image
    except ImportError:
        return None


def _import_pymupdf():
    """Import lazy de PyMuPDF (opcional). Retorna fitz o None (sin imprimir nada)."""
    try:
        import fitz
        return fitz
    except ImportError:
        return None


def _import_docx():
    """Import lazy de python-docx. Retorna la clase Document o None."""
    try:
        from docx import Document
        return Document
    except ImportError:
        return None


def pdf_to_word_do(fitz, Document, path, output, overwrite=False):
    """Convierte un PDF a Word (.docx) extrayendo el texto por bloques.

    Es extraccion de TEXTO simple (parrafos editables): NO reconstruye tablas ni
    columnas complejas (eso requeriria pdf2docx + opencv, que pesa mucho). Cada
    bloque de texto del PDF se agrega como un parrafo, en orden de lectura, con
    un salto de pagina entre paginas.

    Si overwrite=True (la interfaz ya confirmo reemplazar, p.ej. el dialogo
    nativo), se escribe en la ruta exacta; si no, se evita sobrescribir con un
    sufijo (_safe_output_path).

    Retorna dict {"ok": True, "output", "pages", "empty"(bool)} o
    {"ok": False, "error": "open_error"|"encrypted"|"convert_error", "detail"}.
    """
    try:
        doc = fitz.open(path)
    except Exception as e:  # noqa: BLE001 - archivo corrupto/invalido
        return {"ok": False, "error": "open_error", "detail": str(e)}

    # PDF cifrado: intentar con password vacio; si sigue cifrado, abortar.
    if doc.is_encrypted and not doc.authenticate(""):
        doc.close()
        return {"ok": False, "error": "encrypted"}

    try:
        word = Document()
        n_pages = doc.page_count
        con_texto = False
        for i in range(n_pages):
            page = doc.load_page(i)
            # (x0, y0, x1, y1, texto, block_no, block_type); block_type 1 = imagen.
            bloques = page.get_text("blocks")
            # Orden de lectura: arriba->abajo, luego izquierda->derecha.
            bloques.sort(key=lambda b: (round(b[1]), round(b[0])))
            for b in bloques:
                if len(b) >= 7 and b[6] != 0:
                    continue  # bloque de imagen, no de texto
                texto = (b[4] or "").strip()
                if texto:
                    word.add_paragraph(texto)
                    con_texto = True
            if i < n_pages - 1:
                word.add_page_break()

        if not overwrite:
            output = _safe_output_path(output)
        word.save(output)
        return {"ok": True, "output": output, "pages": n_pages, "empty": not con_texto}
    except Exception as e:  # noqa: BLE001 - error al leer paginas o guardar
        return {"ok": False, "error": "convert_error", "detail": str(e)}
    finally:
        doc.close()


def open_pdf(path):
    """Abre un PdfReader manejando corrupcion y cifrado (password vacio).

    Retorna dict:
      {"ok": True, "pypdf": pypdf, "reader": reader}
      {"ok": False, "error": "no_pypdf" | "not_found" | "corrupt" | "encrypted", "detail": opcional}
    """
    pypdf = _import_pypdf()
    if not pypdf:
        return {"ok": False, "error": "no_pypdf"}
    if not os.path.isfile(path):
        return {"ok": False, "error": "not_found"}
    try:
        reader = pypdf.PdfReader(path)
    except (pypdf.errors.PdfReadError, pypdf.errors.PdfStreamError, OSError) as e:
        return {"ok": False, "error": "corrupt", "detail": str(e)}

    # Un PDF cifrado no falla al abrir con PdfReader, pero tumba la app al
    # acceder a .pages. Intentamos descifrar con password vacio (comun en
    # PDFs "protegidos" solo para edicion) y si sigue cifrado, abortamos.
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            pass
        if reader.is_encrypted:
            return {"ok": False, "error": "encrypted"}

    return {"ok": True, "pypdf": pypdf, "reader": reader}


def read_pdf_total(path):
    """Abre un PDF y retorna su total de paginas (maneja cifrado como open_pdf).

    Retorna dict {"ok": True, "pypdf", "reader", "total"} o
    {"ok": False, "error": "no_pypdf"|"not_found"|"corrupt"|"encrypted", "detail": opcional}.
    """
    pypdf = _import_pypdf()
    if not pypdf:
        return {"ok": False, "error": "no_pypdf"}
    if not os.path.isfile(path):
        return {"ok": False, "error": "not_found"}
    try:
        reader = pypdf.PdfReader(path)
    except (pypdf.errors.PdfReadError, pypdf.errors.PdfStreamError, OSError) as e:
        return {"ok": False, "error": "corrupt", "detail": str(e)}

    # Igual que open_pdf: un PDF cifrado no falla al abrir con PdfReader, pero
    # tumba len(reader.pages) con FileNotDecryptedError. Intentamos descifrar
    # con password vacio antes de reportar "corrupto" (mensaje falso).
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            pass
        if reader.is_encrypted:
            return {"ok": False, "error": "encrypted"}

    try:
        total = len(reader.pages)
    except Exception as e:
        return {"ok": False, "error": "corrupt", "detail": str(e)}
    return {"ok": True, "pypdf": pypdf, "reader": reader, "total": total}


def read_pdf_for_protect(path):
    """Abre un PDF sin manejo de cifrado, para el flujo proteger/desproteger.

    Retorna dict {"ok": True, "pypdf", "reader"} o
    {"ok": False, "error": "no_pypdf"|"not_found"|"read_error", "detail": opcional}.
    """
    pypdf = _import_pypdf()
    if not pypdf:
        return {"ok": False, "error": "no_pypdf"}
    if not os.path.isfile(path):
        return {"ok": False, "error": "not_found"}
    try:
        reader = pypdf.PdfReader(path)
    except (pypdf.errors.PdfReadError, pypdf.errors.PdfStreamError, OSError) as e:
        return {"ok": False, "error": "read_error", "detail": str(e)}
    return {"ok": True, "pypdf": pypdf, "reader": reader}


def parse_page_selection(selection: str, total: int):
    """Parsea seleccion de paginas tipo '1,3,5' o '2-4' o '1,3-5,8'.

    Retorna (indices, error): indices es un set 0-based si tuvo exito
    (error es None), o None si hubo error (error trae el mensaje).
    """
    indices = set()
    parts = selection.replace(" ", "").split(",")
    for part in parts:
        if "-" in part:
            try:
                start, end = part.split("-")
                start, end = int(start), int(end)
                if start < 1 or end > total or start > end:
                    return None, f"Rango invalido: {part}. El PDF tiene paginas 1-{total}."
                indices.update(range(start - 1, end))
            except ValueError:
                return None, f"Formato invalido: {part}. Usa: inicio-fin (ej: 2-4)"
        else:
            try:
                num = int(part)
                if num < 1 or num > total:
                    return None, f"Pagina {num} fuera de rango. El PDF tiene paginas 1-{total}."
                indices.add(num - 1)
            except ValueError:
                return None, f"Formato invalido: {part}. Usa numeros separados por comas."
    return indices, None


def parse_reorder(order_str: str, total: int):
    """Parsea el nuevo orden de paginas (ej: '3,1,2,5,4').

    Retorna (new_order, error): new_order es lista de ints 1-based si tuvo
    exito, o None si hubo error (error trae el mensaje).
    """
    try:
        new_order = [int(x.strip()) for x in order_str.split(",")]
    except ValueError:
        return None, "Formato invalido. Usa numeros separados por comas."
    if sorted(new_order) != list(range(1, total + 1)):
        return None, f"Debes incluir todas las paginas (1-{total}) exactamente una vez."
    return new_order, None


def parse_dpi(dpi_str: str):
    """Valida el DPI ingresado. Retorna (dpi, error)."""
    try:
        dpi = int(dpi_str)
        if dpi < 72 or dpi > 600:
            return None, "DPI debe estar entre 72 y 600."
    except ValueError:
        return None, "DPI invalido."
    return dpi, None


def get_pdf_metadata_fields(meta):
    """Extrae los campos con valor de un objeto metadata de pypdf.

    Retorna una lista de tuplas (label, value) solo con los campos
    que tienen valor.
    """
    fields = [
        ("Titulo", meta.title),
        ("Autor", meta.author),
        ("Asunto", meta.subject),
        ("Creador", meta.creator),
        ("Productor", meta.producer),
        ("Fecha creacion", str(meta.creation_date) if meta.creation_date else None),
        ("Fecha modificacion", str(meta.modification_date) if meta.modification_date else None),
    ]
    return [(label, value) for label, value in fields if value]


def merge_pdfs_do(paths, output, overwrite=False):
    """Une multiples PDFs (paths) en un solo archivo (output).

    Si overwrite=True (la interfaz YA confirmo reemplazar, p.ej. el dialogo
    nativo de Windows pregunto "el archivo existe, reemplazar?"), se escribe en
    la ruta exacta en vez de renombrar a "_1". El guard "no pisar un PDF de
    entrada" (same_as_input) SIEMPRE se respeta, con o sin overwrite.

    Retorna dict {"ok": True, "output", "total_pages", "warnings"} o
    {"ok": False, "error": "no_pypdf"|"same_as_input"|"no_pages"|"write_error",
     "detail": opcional, "warnings": [...]}.
    """
    pypdf = _import_pypdf()
    if not pypdf:
        return {"ok": False, "error": "no_pypdf"}

    input_abspaths = {os.path.abspath(p) for p in paths}
    if os.path.abspath(output) in input_abspaths:
        return {"ok": False, "error": "same_as_input"}

    if not overwrite:
        output = _safe_output_path(output)

    warnings = []
    try:
        writer = pypdf.PdfWriter()
        for path in paths:
            try:
                reader = pypdf.PdfReader(path)
                if reader.is_encrypted:
                    reader.decrypt("")
                for page in reader.pages:
                    writer.add_page(page)
            except Exception as e:
                warnings.append(f"PDF corrupto, cifrado o invalido: {os.path.basename(path)} — {e}")
                continue

        if len(writer.pages) == 0:
            return {"ok": False, "error": "no_pages", "warnings": warnings}

        with open(output, "wb") as f:
            writer.write(f)

        return {"ok": True, "output": output, "total_pages": len(writer.pages), "warnings": warnings}
    except (pypdf.errors.PdfReadError, OSError) as e:
        return {"ok": False, "error": "write_error", "detail": str(e), "warnings": warnings}


def split_pdf_do(pypdf, reader, path, output_dir, mode, rango=None):
    """Ejecuta la division de un PDF ya abierto (individual o por rango)."""
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        return {"ok": False, "error": "write_error", "detail": str(e)}
    base_name = os.path.splitext(os.path.basename(path))[0]
    total = len(reader.pages)

    if mode == "individual":
        try:
            for i, page in enumerate(reader.pages, 1):
                writer = pypdf.PdfWriter()
                writer.add_page(page)
                out_path = _safe_output_path(os.path.join(output_dir, f"{base_name}_pag{i}.pdf"))
                with open(out_path, "wb") as f:
                    writer.write(f)
        except OSError as e:
            return {"ok": False, "error": "write_error", "detail": str(e)}
        return {"ok": True, "mode": "individual", "total": total, "output_dir": output_dir}

    # modo rango
    try:
        start, end = rango.split("-")
        start, end = int(start), int(end)
        if start < 1 or end > total or start > end:
            return {"ok": False, "error": "invalid_range", "total": total}
    except ValueError:
        return {"ok": False, "error": "invalid_format"}

    try:
        writer = pypdf.PdfWriter()
        for i in range(start - 1, end):
            writer.add_page(reader.pages[i])

        out_path = _safe_output_path(os.path.join(output_dir, f"{base_name}_pag{start}-{end}.pdf"))
        with open(out_path, "wb") as f:
            writer.write(f)
    except OSError as e:
        return {"ok": False, "error": "write_error", "detail": str(e)}
    except Exception as e:
        # Una pagina corrupta al copiarla puede lanzar errores de pypdf fuera
        # de OSError; que no tumbe la app (mismo criterio que rotate/delete/...).
        return {"ok": False, "error": "write_error", "detail": str(e)}
    return {"ok": True, "mode": "rango", "output": out_path, "pages": end - start + 1}


def rotate_pages_do(pypdf, reader, path, angle, indices):
    """Rota las paginas en `indices` (0-based) por `angle` grados y guarda copia."""
    try:
        writer = pypdf.PdfWriter()
        for i, page in enumerate(reader.pages):
            if i in indices:
                page.rotate(angle)
            writer.add_page(page)

        base_name = os.path.splitext(path)[0]
        output = _safe_output_path(f"{base_name}_rotado.pdf")
        with open(output, "wb") as f:
            writer.write(f)

        return {"ok": True, "output": output, "rotated_count": len(indices)}
    except (pypdf.errors.PdfReadError, OSError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def delete_pages_do(pypdf, reader, path, indices):
    """Elimina las paginas en `indices` (0-based) y guarda copia."""
    try:
        total = len(reader.pages)
        writer = pypdf.PdfWriter()
        for i, page in enumerate(reader.pages):
            if i not in indices:
                writer.add_page(page)

        base_name = os.path.splitext(path)[0]
        output = _safe_output_path(f"{base_name}_editado.pdf")
        with open(output, "wb") as f:
            writer.write(f)

        remaining = total - len(indices)
        return {"ok": True, "output": output, "deleted": len(indices), "remaining": remaining}
    except (pypdf.errors.PdfReadError, OSError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def reorder_pages_do(pypdf, reader, path, new_order):
    """Reordena las paginas segun `new_order` (lista 1-based) y guarda copia."""
    try:
        writer = pypdf.PdfWriter()
        for num in new_order:
            writer.add_page(reader.pages[num - 1])

        base_name = os.path.splitext(path)[0]
        output = _safe_output_path(f"{base_name}_reordenado.pdf")
        with open(output, "wb") as f:
            writer.write(f)

        return {"ok": True, "output": output}
    except (pypdf.errors.PdfReadError, OSError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def extract_text_do(pypdf, reader, path):
    """Extrae el texto de todas las paginas y lo guarda en un .txt."""
    try:
        text_parts = []
        for i, page in enumerate(reader.pages, 1):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"--- Pagina {i} ---\n{page_text}")

        if not text_parts:
            return {"ok": False, "error": "no_text"}

        full_text = "\n\n".join(text_parts)

        base_name = os.path.splitext(path)[0]
        output = _safe_output_path(f"{base_name}.txt")
        with open(output, "w", encoding="utf-8") as f:
            f.write(full_text)

        return {"ok": True, "output": output, "chars": len(full_text)}
    except (pypdf.errors.PdfReadError, OSError) as e:
        return {"ok": False, "error": "extract_error", "detail": str(e)}
    except Exception as e:
        return {"ok": False, "error": "extract_error", "detail": str(e)}


def images_to_pdf_do(Image, paths, output):
    """Convierte una lista de imagenes a un solo PDF."""
    images = []
    try:
        for p in paths:
            img = Image.open(p)
            # RGBA/P/LA → RGB para compatibilidad con PDF
            if img.mode in ("RGBA", "P", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                img.close()
                img = background
            elif img.mode != "RGB":
                converted = img.convert("RGB")
                img.close()
                img = converted
            images.append(img)

        if len(images) == 1:
            images[0].save(output, "PDF")
        else:
            images[0].save(output, "PDF", save_all=True, append_images=images[1:])

        return {"ok": True, "output": output, "count": len(images)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        for img in images:
            try:
                img.close()
            except Exception:
                pass


def pdf_to_images_do(fitz, path, fmt, dpi, output_dir):
    """Convierte cada pagina de un PDF a imagen."""
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        return {"ok": False, "error": "write_error", "detail": str(e)}
    try:
        doc = fitz.open(path)
        base_name = os.path.splitext(os.path.basename(path))[0]
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)

        page_count = len(doc)
        for i, page in enumerate(doc, 1):
            pix = page.get_pixmap(matrix=matrix)
            ext = "png" if fmt == "png" else "jpg"
            out_path = _safe_output_path(os.path.join(output_dir, f"{base_name}_pag{i}.{ext}"))
            if fmt == "jpg":
                pix.save(out_path, jpg_quality=95)
            else:
                pix.save(out_path)

        doc.close()
        return {"ok": True, "output_dir": output_dir, "count": page_count, "dpi": dpi}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def unprotect_pdf_do(pypdf, reader, password, base_name):
    """Quita la proteccion de un PDF ya abierto (cifrado) con `password`."""
    try:
        if not reader.decrypt(password):
            return {"ok": False, "error": "wrong_password"}
    except Exception:
        return {"ok": False, "error": "wrong_password_or_corrupt"}

    try:
        writer = pypdf.PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        output = _safe_output_path(f"{base_name}_desprotegido.pdf")
        with open(output, "wb") as f:
            writer.write(f)
    except OSError as e:
        return {"ok": False, "error": "write_error", "detail": str(e)}
    except Exception as e:
        return {"ok": False, "error": "write_error", "detail": str(e)}

    return {"ok": True, "output": output}


def protect_pdf_do(pypdf, reader, password, base_name):
    """Agrega proteccion con `password` a un PDF ya abierto (sin cifrar)."""
    try:
        writer = pypdf.PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)

        output = _safe_output_path(f"{base_name}_protegido.pdf")
        with open(output, "wb") as f:
            writer.write(f)
    except OSError as e:
        return {"ok": False, "error": "write_error", "detail": str(e)}
    except Exception as e:
        return {"ok": False, "error": "write_error", "detail": str(e)}

    return {"ok": True, "output": output}


def clean_metadata_do(pypdf, reader, path):
    """Reescribe el PDF sin metadatos."""
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
        output = _safe_output_path(f"{base_name}_limpio.pdf")
        with open(output, "wb") as f:
            writer.write(f)

        return {"ok": True, "output": output}
    except (pypdf.errors.PdfReadError, OSError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# --- Interfaz de consola ---
# ============================================================
#
# Adaptadores: preguntan al usuario (Prompt/Confirm/getpass), llaman a la
# logica de arriba y muestran resultados. Ninguna decision de negocio vive
# aca, solo el dialogo con el usuario.


def _get_pypdf():
    """Import lazy de pypdf para no crashear si no esta instalado."""
    pypdf = _import_pypdf()
    if not pypdf:
        console.print(
            "[bold red]pypdf no esta instalado.[/bold red]\n"
            "[dim]Ejecuta: pip install pypdf[/dim]"
        )
    return pypdf


def _get_pillow():
    """Import lazy de Pillow para no crashear si no esta instalado."""
    Image = _import_pillow()
    if not Image:
        console.print(
            "[bold red]Pillow no esta instalado.[/bold red]\n"
            "[dim]Ejecuta: pip install Pillow[/dim]"
        )
    return Image


def _get_pymupdf():
    """Import lazy de PyMuPDF (opcional, para PDF a imagenes)."""
    fitz = _import_pymupdf()
    if not fitz:
        console.print(
            "[bold red]PyMuPDF no esta instalado.[/bold red]\n"
            "[dim]Ejecuta: pip install PyMuPDF[/dim]\n"
            "[dim]Esta dependencia es opcional y solo se necesita para 'PDF a Imagenes'.[/dim]"
        )
    return fitz


def _open_pdf_reader(prompt_text="[bold]Ruta del PDF[/bold]"):
    """Pide ruta al usuario, valida y abre PdfReader.

    Retorna (pypdf, reader, path) o None si falla.
    """
    pypdf = _get_pypdf()
    if not pypdf:
        return None

    path = Prompt.ask(prompt_text).strip().strip('"')
    result = open_pdf(path)
    if not result["ok"]:
        if result["error"] == "not_found":
            console.print("[red]Archivo no encontrado.[/red]")
        elif result["error"] == "corrupt":
            console.print(f"[red]Error al leer PDF (archivo corrupto o invalido): {escape(str(result['detail']))}[/red]")
        elif result["error"] == "encrypted":
            console.print("[red]El PDF esta protegido con contrasena y no se puede procesar.[/red]")
        return None

    return result["pypdf"], result["reader"], path


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
            console.print(f"  [red]Archivo no encontrado: {escape(path)}[/red]")
            continue
        paths.append(path)

    if len(paths) < 2:
        console.print("[yellow]Se necesitan al menos 2 PDFs para unir.[/yellow]")
        return

    output = Prompt.ask(
        "[bold]Ruta del PDF de salida[/bold]",
        default=os.path.join(os.path.dirname(paths[0]), "unido.pdf"),
    ).strip().strip('"')

    result = merge_pdfs_do(paths, output)

    for w in result.get("warnings", []):
        console.print(f"  [red]{escape(w)}[/red]")

    if not result["ok"]:
        if result["error"] == "same_as_input":
            console.print(
                "[red]La ruta de salida no puede ser igual a uno de los PDFs de entrada "
                "(se perderia el original). Elige otra ruta.[/red]"
            )
        elif result["error"] == "no_pages":
            console.print("[red]No se pudieron leer paginas de ninguno de los PDFs.[/red]")
        elif result["error"] == "write_error":
            console.print(f"[red]Error al unir PDFs: {escape(str(result['detail']))}[/red]")
        return

    console.print(f"\n[bold green]PDF unido creado: {escape(result['output'])} ({result['total_pages']} paginas)[/bold green]")


def split_pdf() -> None:
    """Divide un PDF en paginas individuales o por rango."""
    pypdf = _get_pypdf()
    if not pypdf:
        return

    console.print("\n[bold cyan]Dividir PDF[/bold cyan]")
    console.print("[dim]Separa un PDF en paginas individuales o extrae un rango especifico.[/dim]")

    path = Prompt.ask("[bold]Ruta del PDF a dividir[/bold]").strip().strip('"')

    open_result = read_pdf_total(path)
    if not open_result["ok"]:
        if open_result["error"] == "not_found":
            console.print("[red]Archivo no encontrado.[/red]")
        elif open_result["error"] == "corrupt":
            console.print(f"[red]Error al leer PDF (archivo corrupto o invalido): {escape(str(open_result['detail']))}[/red]")
        elif open_result["error"] == "encrypted":
            console.print(
                "[red]El PDF esta protegido con contrasena. Usa primero la opcion "
                "'Proteger/Desproteger PDF' para quitarle la proteccion.[/red]"
            )
        return

    pypdf, reader, total = open_result["pypdf"], open_result["reader"], open_result["total"]
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

    if mode == "individual":
        exec_result = split_pdf_do(pypdf, reader, path, output_dir, mode)
    else:
        rango = Prompt.ask("[bold]Rango (ej: 1-5)[/bold]").strip()
        exec_result = split_pdf_do(pypdf, reader, path, output_dir, mode, rango)

    if not exec_result["ok"]:
        if exec_result["error"] == "write_error":
            console.print(f"[red]Error al escribir archivo (revisa permisos o espacio en disco): {escape(str(exec_result['detail']))}[/red]")
        elif exec_result["error"] == "invalid_range":
            console.print(f"[red]Rango invalido. El PDF tiene paginas 1-{total}.[/red]")
        elif exec_result["error"] == "invalid_format":
            console.print("[red]Formato invalido. Usa: inicio-fin (ej: 1-5)[/red]")
        return

    if exec_result["mode"] == "individual":
        console.print(f"\n[bold green]{exec_result['total']} archivos creados en: {escape(exec_result['output_dir'])}[/bold green]")
    else:
        console.print(f"\n[bold green]PDF creado: {escape(exec_result['output'])} ({exec_result['pages']} paginas)[/bold green]")


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
        indices, error = parse_page_selection(scope, total)
        if indices is None:
            console.print(f"[red]{escape(str(error))}[/red]")
            return

    exec_result = rotate_pages_do(pypdf, reader, path, angle, indices)
    if not exec_result["ok"]:
        console.print(f"[red]Error al rotar PDF: {escape(str(exec_result['error']))}[/red]")
        return

    console.print(
        f"\n[bold green]PDF rotado creado: {escape(exec_result['output'])} "
        f"({exec_result['rotated_count']} paginas rotadas {angle}°)[/bold green]"
    )


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

    indices, error = parse_page_selection(selection, total)
    if indices is None:
        console.print(f"[red]{escape(str(error))}[/red]")
        return

    if len(indices) >= total:
        console.print("[red]No puedes eliminar todas las paginas del PDF.[/red]")
        return

    exec_result = delete_pages_do(pypdf, reader, path, indices)
    if not exec_result["ok"]:
        console.print(f"[red]Error al editar PDF: {escape(str(exec_result['error']))}[/red]")
        return

    console.print(
        f"\n[bold green]PDF creado: {escape(exec_result['output'])} "
        f"({exec_result['deleted']} paginas eliminadas, {exec_result['remaining']} restantes)[/bold green]"
    )


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

    new_order, error = parse_reorder(order_str, total)
    if new_order is None:
        console.print(f"[red]{escape(str(error))}[/red]")
        return

    exec_result = reorder_pages_do(pypdf, reader, path, new_order)
    if not exec_result["ok"]:
        console.print(f"[red]Error al reordenar PDF: {escape(str(exec_result['error']))}[/red]")
        return

    console.print(f"\n[bold green]PDF reordenado creado: {escape(exec_result['output'])}[/bold green]")


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

    exec_result = extract_text_do(pypdf, reader, path)
    if not exec_result["ok"]:
        if exec_result["error"] == "no_text":
            console.print("[yellow]No se pudo extraer texto del PDF (puede ser un PDF escaneado/imagen).[/yellow]")
        elif exec_result["error"] == "extract_error":
            console.print(f"[red]Error al extraer texto: {escape(str(exec_result['detail']))}[/red]")
        return

    console.print(f"\n[bold green]Texto extraido: {escape(exec_result['output'])} ({exec_result['chars']:,} caracteres)[/bold green]")


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
            console.print(f"  [red]Archivo no encontrado: {escape(path)}[/red]")
            continue
        ext = os.path.splitext(path)[1].lower()
        if ext not in valid_exts:
            console.print(f"  [red]Formato no soportado: {escape(ext)}. Usa JPG, PNG, BMP o WEBP.[/red]")
            continue
        paths.append(path)

    if not paths:
        console.print("[yellow]No se agregaron imagenes.[/yellow]")
        return

    output = Prompt.ask(
        "[bold]Ruta del PDF de salida[/bold]",
        default=os.path.join(os.path.dirname(paths[0]), "imagenes.pdf"),
    ).strip().strip('"')
    output = _safe_output_path(output)

    exec_result = images_to_pdf_do(Image, paths, output)
    if not exec_result["ok"]:
        console.print(f"[red]Error al crear PDF (posible imagen invalida o demasiado grande): {escape(str(exec_result['error']))}[/red]")
        return

    console.print(f"\n[bold green]PDF creado: {escape(exec_result['output'])} ({exec_result['count']} imagenes)[/bold green]")


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
    dpi, error = parse_dpi(dpi_str)
    if dpi is None:
        console.print(f"[red]{escape(str(error))}[/red]")
        return

    output_dir = Prompt.ask(
        "[bold]Carpeta de salida[/bold]",
        default=os.path.join(os.path.dirname(path), "pdf_imagenes"),
    ).strip().strip('"')

    exec_result = pdf_to_images_do(fitz, path, fmt, dpi, output_dir)
    if not exec_result["ok"]:
        console.print(f"[red]Error al convertir PDF a imagenes: {escape(str(exec_result['error']))}[/red]")
        return

    console.print(
        f"\n[bold green]{exec_result['count']} imagenes creadas en: {escape(exec_result['output_dir'])} "
        f"({exec_result['dpi']} DPI)[/bold green]"
    )


def pdf_to_word() -> None:
    """Convierte un PDF a Word (.docx) extrayendo su texto."""
    fitz = _get_pymupdf()
    if not fitz:
        return
    Document = _import_docx()
    if not Document:
        console.print(
            "[red]Esta version no incluye python-docx, necesario para crear el "
            "archivo Word.[/red]"
        )
        return

    console.print("\n[bold cyan]PDF a Word[/bold cyan]")
    console.print(
        "[dim]Extrae el texto del PDF a un .docx editable. Es texto simple: no "
        "reconstruye tablas ni columnas complejas.[/dim]"
    )

    path = Prompt.ask("[bold]Ruta del PDF[/bold]").strip().strip('"')
    if not os.path.isfile(path):
        console.print("[red]Archivo no encontrado.[/red]")
        return

    output = Prompt.ask(
        "[bold]Ruta del Word de salida[/bold]",
        default=os.path.splitext(path)[0] + ".docx",
    ).strip().strip('"')

    exec_result = pdf_to_word_do(fitz, Document, path, output)
    if not exec_result["ok"]:
        if exec_result["error"] == "encrypted":
            console.print(
                "[red]El PDF esta protegido con password. Desprotegelo primero "
                "(opcion Proteger/Desproteger PDF).[/red]"
            )
        else:
            console.print(
                f"[red]No se pudo convertir el PDF a Word: "
                f"{escape(str(exec_result.get('detail', exec_result['error'])))}[/red]"
            )
        return

    if exec_result.get("empty"):
        console.print(
            "[yellow]El PDF no tenia texto seleccionable (puede ser un escaneo o "
            "imagen); el Word quedo vacio.[/yellow]"
        )
    console.print(
        f"\n[bold green]Word creado: {escape(exec_result['output'])} "
        f"({exec_result['pages']} paginas)[/bold green]"
    )


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

    open_result = read_pdf_for_protect(path)
    if not open_result["ok"]:
        console.print(f"[red]Error al leer PDF: {escape(str(open_result.get('detail', '')))}[/red]")
        return
    pypdf, reader = open_result["pypdf"], open_result["reader"]

    base_name = os.path.splitext(path)[0]

    if reader.is_encrypted:
        # Desproteger
        console.print("[dim]El PDF esta protegido con password.[/dim]")
        password = getpass.getpass("Password actual: ")

        exec_result = unprotect_pdf_do(pypdf, reader, password, base_name)
        if not exec_result["ok"]:
            if exec_result["error"] == "wrong_password":
                console.print("[red]Password incorrecto.[/red]")
            elif exec_result["error"] == "wrong_password_or_corrupt":
                console.print("[red]Password incorrecto o PDF corrupto.[/red]")
            elif exec_result["error"] == "write_error":
                console.print(f"[red]Error al guardar PDF (revisa permisos o espacio en disco): {escape(str(exec_result['detail']))}[/red]")
            return

        console.print(f"\n[bold green]PDF desprotegido creado: {escape(exec_result['output'])}[/bold green]")
    else:
        # Proteger
        console.print("[dim]El PDF no tiene proteccion.[/dim]")
        password = getpass.getpass("Nueva password: ")
        if not password:
            console.print("[yellow]Password vacio, operacion cancelada.[/yellow]")
            return

        confirm = getpass.getpass("Confirmar password: ")
        if password != confirm:
            console.print("[red]Las passwords no coinciden.[/red]")
            return

        exec_result = protect_pdf_do(pypdf, reader, password, base_name)
        if not exec_result["ok"]:
            console.print(f"[red]Error al guardar PDF (revisa permisos o espacio en disco): {escape(str(exec_result['detail']))}[/red]")
            return

        console.print(f"\n[bold green]PDF protegido creado: {escape(exec_result['output'])}[/bold green]")


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
        fields = get_pdf_metadata_fields(meta)
        if fields:
            for label, value in fields:
                console.print(f"  {label}: {escape(str(value))}")
        else:
            console.print("  [dim]No hay metadatos adicionales.[/dim]")
    else:
        console.print("  [dim]No hay metadatos.[/dim]")

    action = Prompt.ask(
        "\n[bold]Limpiar metadatos?[/bold]",
        choices=["si", "no"],
        default="no",
    )

    if action == "si":
        exec_result = clean_metadata_do(pypdf, reader, path)
        if not exec_result["ok"]:
            console.print(f"[red]Error al limpiar metadatos: {escape(str(exec_result['error']))}[/red]")
            return
        console.print(f"\n[bold green]PDF sin metadatos creado: {escape(exec_result['output'])}[/bold green]")


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
            "  [bold]11[/bold] - PDF a Word\n"
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
        elif choice == "11":
            pdf_to_word()
        elif choice == "0":
            break
        else:
            console.print("[red]Opcion no valida.[/red]")
