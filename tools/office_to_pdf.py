"""Convertir documentos de Office (Word/Excel/PowerPoint) a PDF.

Usa la automatizacion COM del Office INSTALADO en la maquina, manejada desde
PowerShell. Se eligio este camino sobre las librerias de Python por dos
razones:

1. Cero dependencias nuevas: `pywin32` habria sumado varios MB al .exe, y las
   librerias que renderizan Office sin Office (LibreOffice headless, docx2pdf
   con su propio motor) pesan decenas de MB o requieren instalar otro programa.
   El proyecto ya habla PowerShell en media docena de modulos.
2. Fidelidad: el PDF lo genera el mismo Word/Excel que creo el archivo, asi que
   respeta fuentes, encabezados, saltos de pagina y formato tal cual los ve el
   usuario. Una reimplementacion nunca queda igual, y aqui el resultado suele
   ir a un jefe o a un cliente.

El costo es la dependencia dura de Office instalado: si no esta, se avisa con
claridad en vez de intentar un render pobre.

Notas de implementacion (por que el script de PowerShell se ve asi):
- Los archivos se abren en modo SOLO LECTURA: convertir NUNCA debe modificar
  el original.
- A los archivos protegidos se les pasa una contrasena basura a proposito. Si
  no, Word/Excel abren un dialogo modal INVISIBLE (la app corre sin ventana) y
  el proceso se queda colgado hasta el timeout. Con una contrasena incorrecta
  tiran error de inmediato y se reporta "protegido con contrasena".
- Siempre hay un `finally` que hace Quit: un COM huerfano deja un WINWORD.EXE
  invisible comiendo memoria y despues bloquea el archivo del usuario.
"""

import os
import subprocess

from rich.markup import escape
from rich.prompt import Prompt

from utils import console, ps_escape
from tools.pdf_tools import _safe_output_path


# Extensiones soportadas por aplicacion de Office.
WORD_EXTS = {".doc", ".docx", ".docm", ".rtf", ".odt", ".txt"}
EXCEL_EXTS = {".xls", ".xlsx", ".xlsm", ".xlsb", ".csv", ".ods"}
POWERPOINT_EXTS = {".ppt", ".pptx", ".pptm", ".odp"}
SUPPORTED_EXTS = WORD_EXTS | EXCEL_EXTS | POWERPOINT_EXTS

# Timeout por archivo. Office puede tardar en arrancar en frio (primera
# conversion de la sesion, equipo de oficina lento), de ahi que sea generoso.
CONVERT_TIMEOUT = 300

# Contrasena basura para que un archivo protegido falle rapido en vez de
# colgarse en un dialogo invisible (ver docstring del modulo).
_BOGUS_PASSWORD = "SG-no-abrir-x9"


def get_app_for_extension(ext: str) -> str | None:
    """Retorna 'word' | 'excel' | 'powerpoint' para la extension, o None."""
    ext = ext.lower()
    if ext in WORD_EXTS:
        return "word"
    if ext in EXCEL_EXTS:
        return "excel"
    if ext in POWERPOINT_EXTS:
        return "powerpoint"
    return None


def _build_ps_script(app: str, in_path: str, out_path: str) -> str:
    """Arma el script de PowerShell que maneja el COM de Office.

    Todo dato externo (las dos rutas) pasa por `ps_escape`. El script imprime
    'SG_OK' en exito o 'SG_ERR:<mensaje>' en error, y siempre cierra la
    aplicacion de Office en el `finally`.
    """
    src = ps_escape(in_path)
    dst = ps_escape(out_path)
    pwd = ps_escape(_BOGUS_PASSWORD)

    if app == "word":
        # wdFormatPDF = 17. Documents.Open(FileName, ConfirmConversions,
        # ReadOnly, AddToRecentFiles, PasswordDocument).
        cuerpo = f"""
$app = New-Object -ComObject Word.Application
$app.Visible = $false
$app.DisplayAlerts = 0
try {{
    $doc = $app.Documents.Open("{src}", $false, $true, $false, "{pwd}")
    try {{
        $doc.SaveAs([ref]"{dst}", [ref]17)
    }} finally {{
        $doc.Close(0)
    }}
}} finally {{
    $app.Quit(0)
}}
"""
    elif app == "excel":
        # xlTypePDF = 0. Workbooks.Open(Filename, UpdateLinks, ReadOnly,
        # Format, Password).
        cuerpo = f"""
$app = New-Object -ComObject Excel.Application
$app.Visible = $false
$app.DisplayAlerts = $false
try {{
    $wb = $app.Workbooks.Open("{src}", 0, $true, 5, "{pwd}")
    try {{
        $wb.ExportAsFixedFormat(0, "{dst}")
    }} finally {{
        $wb.Close($false)
    }}
}} finally {{
    $app.Quit()
}}
"""
    else:  # powerpoint
        # ppSaveAsPDF = 32. PowerPoint no puede correr totalmente invisible;
        # se abre sin ventana (WithWindow = $false), que es lo mas cerca.
        cuerpo = f"""
$app = New-Object -ComObject PowerPoint.Application
try {{
    $pres = $app.Presentations.Open("{src}", $true, $false, $false)
    try {{
        $pres.SaveAs("{dst}", 32)
    }} finally {{
        $pres.Close()
    }}
}} finally {{
    $app.Quit()
}}
"""

    # El try/catch exterior convierte cualquier excepcion COM en una linea
    # 'SG_ERR:' legible, en vez de un volcado de PowerShell de 20 lineas.
    return (
        "$ErrorActionPreference = 'Stop'\n"
        "try {\n"
        f"{cuerpo}\n"
        "    Write-Output 'SG_OK'\n"
        "} catch {\n"
        "    Write-Output ('SG_ERR:' + $_.Exception.Message)\n"
        "}\n"
    )


def _classify_error(mensaje: str, app: str) -> str:
    """Traduce el error crudo de COM a una razon estable del dominio."""
    m = (mensaje or "").lower()
    if "no se puede crear" in m or "cannot create" in m or "80040154" in m or "invalid class string" in m:
        return "no_office"
    if "contrasen" in m or "password" in m or "protected" in m or "protegid" in m:
        return "password"
    if "no se encuentra" in m or "not found" in m or "does not exist" in m:
        return "not_found"
    if "en uso" in m or "in use" in m or "locked" in m or "being used" in m:
        return "in_use"
    return "convert_error"


def office_to_pdf_do(path: str, output: str | None = None, overwrite: bool = False) -> dict:
    """Convierte UN documento de Office a PDF. Funcion pura de logica (sin UI).

    `output` por defecto es el mismo nombre con extension .pdf, junto al
    original. Si overwrite=False (lo normal) se evita pisar un archivo
    existente agregando un sufijo numerico.

    Retorna {"ok": True, "output": ruta} o
    {"ok": False, "error": razon, "detail": mensaje}, donde razon es una de:
    unsupported | not_found | not_windows | no_office | password | in_use |
    timeout | convert_error.
    """
    ext = os.path.splitext(path)[1].lower()
    app = get_app_for_extension(ext)
    if not app:
        return {"ok": False, "error": "unsupported", "detail": ext}

    if not os.path.isfile(path):
        return {"ok": False, "error": "not_found", "detail": path}

    if os.name != "nt":
        # La automatizacion COM de Office solo existe en Windows. En desarrollo
        # (Linux) se corta aqui con un error de dato, no con una excepcion.
        return {"ok": False, "error": "not_windows", "detail": os.name}

    in_path = os.path.abspath(path)
    if not output:
        output = os.path.splitext(in_path)[0] + ".pdf"
    output = os.path.abspath(output)

    if not overwrite:
        output = _safe_output_path(output)

    # Office escribe el PDF el solo; si el directorio no existe, falla con un
    # error COM opaco. Mejor detectarlo aqui.
    out_dir = os.path.dirname(output)
    if out_dir and not os.path.isdir(out_dir):
        return {"ok": False, "error": "convert_error", "detail": f"No existe la carpeta {out_dir}"}

    ps = _build_ps_script(app, in_path, output)

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=CONVERT_TIMEOUT, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "detail": str(CONVERT_TIMEOUT)}
    except OSError as e:
        return {"ok": False, "error": "convert_error", "detail": str(e)}

    salida = (result.stdout or "").strip()

    if "SG_OK" in salida:
        # Confiar en el codigo de salida no basta: Office puede reportar exito
        # y no haber escrito nada (p.ej. si SaveAs fue cancelado por una
        # politica). Se verifica el efecto REAL, igual que unhide_folders.
        if os.path.isfile(output) and os.path.getsize(output) > 0:
            return {"ok": True, "output": output}
        return {
            "ok": False, "error": "convert_error",
            "detail": "Office reporto exito pero no se genero el PDF",
        }

    for linea in salida.splitlines():
        if linea.startswith("SG_ERR:"):
            detalle = linea[len("SG_ERR:"):].strip()
            return {"ok": False, "error": _classify_error(detalle, app), "detail": detalle}

    detalle = salida or (result.stderr or "").strip() or "PowerShell no devolvio nada"
    return {"ok": False, "error": _classify_error(detalle, app), "detail": detalle}


# ============================================================
# --- Interfaz de consola ---
# ============================================================


ERROR_MENSAJES = {
    "unsupported": "Ese tipo de archivo no se puede convertir. Sirve para Word "
                   "(.doc/.docx/.rtf/.odt), Excel (.xls/.xlsx/.csv) y "
                   "PowerPoint (.ppt/.pptx).",
    "not_found": "No encontre ese archivo. Revisa la ruta.",
    "not_windows": "Esta funcion necesita Windows con Office instalado.",
    "no_office": "No encontre Microsoft Office instalado en esta computadora. "
                 "Esta funcion usa el Word/Excel/PowerPoint que ya tienes para "
                 "generar el PDF con el formato exacto.",
    "password": "El archivo esta protegido con contrasena. Abrelo en Office, "
                "quitale la proteccion y vuelve a intentar.",
    "in_use": "El archivo esta abierto en otro programa. Cierralo y vuelve a "
              "intentar.",
    "timeout": "Office tardo demasiado y se cancelo la conversion. Si el "
               "documento es muy grande, intenta cerrando otros programas.",
    "convert_error": "No se pudo convertir el archivo.",
}


def _print_error(res: dict) -> None:
    """Imprime el error de una conversion en lenguaje de oficina."""
    razon = res.get("error", "convert_error")
    console.print(f"\n[bold red]{ERROR_MENSAJES.get(razon, ERROR_MENSAJES['convert_error'])}[/bold red]")
    detalle = res.get("detail", "")
    # El detalle crudo se muestra atenuado: al usuario no le dice nada, pero
    # sirve si reporta el problema. escape() porque viene de Office/PowerShell.
    if detalle and razon in ("convert_error", "no_office", "timeout"):
        console.print(f"[dim]Detalle: {escape(str(detalle))}[/dim]")


def office_to_pdf_menu() -> None:
    """Interfaz de consola: convertir documentos de Office a PDF."""
    console.print("\n[bold cyan]Convertir Word/Excel/PowerPoint a PDF[/bold cyan]\n")
    console.print(
        "[dim]Usa el Office instalado en esta computadora, asi que el PDF "
        "queda con el formato exacto del documento.[/dim]\n"
    )

    entrada = Prompt.ask("[bold]Ruta del archivo (o Enter para cancelar)[/bold]", default="").strip()
    if not entrada:
        console.print("[yellow]Cancelado.[/yellow]")
        return

    # Comillas: la gente pega rutas con comillas desde el Explorador.
    path = entrada.strip('"').strip("'")

    ext = os.path.splitext(path)[1].lower()
    if not get_app_for_extension(ext):
        console.print(f"\n[bold red]{ERROR_MENSAJES['unsupported']}[/bold red]")
        return

    if not os.path.isfile(path):
        console.print(f"\n[bold red]{ERROR_MENSAJES['not_found']}[/bold red]")
        return

    with console.status("[bold green]Convirtiendo con Office (puede tardar la primera vez)..."):
        res = office_to_pdf_do(path)

    if res["ok"]:
        console.print(f"\n[bold green]Listo. PDF creado:[/bold green] {escape(res['output'])}")
    else:
        _print_error(res)
