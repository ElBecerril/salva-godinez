"""Liberador de espacio: limpia temporales, cache y descargas antiguas."""

import ctypes
import os
import time

from rich.markup import escape
from rich.prompt import Confirm, Prompt
from rich.table import Table

from tools import format_size, is_admin
from config import (
    TEMP_CLEAN_PATHS,
    WINDOWS_UPDATE_CACHE,
    DOWNLOADS_PATH,
    OLD_DOWNLOAD_DAYS,
    SECONDS_PER_DAY,
    TEMP_PREFIXES,
    RECOVERY_EXTENSIONS,
)
from utils import console


# --- Logica (sin UI) ---


def _scan_dir(path: str, proteger_rescatables: bool = False) -> tuple[int, int]:
    """Escanea un directorio y retorna (tamano_total, num_archivos).

    Con proteger_rescatables=True se excluyen los autorecuperados de Office,
    para que el tamano estimado coincida con lo que _clean_dir de verdad borra
    (que tambien los salta) y no se le prometa al usuario liberar algo que se
    va a conservar.
    """
    total = 0
    count = 0
    if not os.path.isdir(path):
        return 0, 0
    for dirpath, _, filenames in os.walk(path):
        for fname in filenames:
            if proteger_rescatables and _es_rescatable(fname):
                continue
            filepath = os.path.join(dirpath, fname)
            try:
                total += os.path.getsize(filepath)
                count += 1
            except OSError:
                continue
    return total, count


def _scan_temp_files() -> tuple[int, int, list[str]]:
    """Escanea archivos temporales."""
    total = 0
    count = 0
    paths = []
    for temp_path in TEMP_CLEAN_PATHS:
        if not temp_path or not os.path.isdir(temp_path):
            continue
        size, files = _scan_dir(temp_path, proteger_rescatables=True)
        total += size
        count += files
        if size > 0:
            paths.append(temp_path)
    return total, count, paths


def _scan_update_cache() -> tuple[int, int]:
    """Escanea cache de Windows Update (requiere admin)."""
    if not is_admin():
        return 0, 0
    return _scan_dir(WINDOWS_UPDATE_CACHE)


def _scan_old_downloads(days: int = OLD_DOWNLOAD_DAYS) -> tuple[int, int, list[str]]:
    """Escanea descargas antiguas."""
    if not os.path.isdir(DOWNLOADS_PATH):
        return 0, 0, []

    cutoff = time.time() - (days * SECONDS_PER_DAY)
    total = 0
    count = 0
    files = []

    for fname in os.listdir(DOWNLOADS_PATH):
        filepath = os.path.join(DOWNLOADS_PATH, fname)
        if not os.path.isfile(filepath):
            continue
        try:
            stat = os.stat(filepath)
            if stat.st_mtime < cutoff:
                total += stat.st_size
                count += 1
                files.append(filepath)
        except OSError:
            continue

    return total, count, files


def _es_rescatable(fname: str) -> bool:
    """True si el nombre tiene patron de autorecuperado/temporal de Office.

    Mismos patrones que usa el RESCATE (searchers/temp_files._has_temp_signature):
    prefijos ~$/~ o una extension de config.RECOVERY_EXTENSIONS. Se comparte la
    fuente de verdad para que la limpieza no borre lo que el rescate recupera.
    """
    lower = fname.lower()
    if any(lower.startswith(p) for p in TEMP_PREFIXES):
        return True
    return os.path.splitext(lower)[1] in RECOVERY_EXTENSIONS


def _clean_dir(path: str, proteger_rescatables: bool = False) -> tuple[int, int]:
    """Elimina archivos de un directorio. Retorna (bytes_liberados, archivos_eliminados).

    Si proteger_rescatables=True (se usa al limpiar %TEMP% y demas rutas
    temporales), se SALTAN los archivos con patron de autorecuperacion de
    Office: un .asd/.tmp/~$ de un Word/Excel crasheado vive en %TEMP% y es
    justo lo que la herramienta de rescate del producto recuperaria. Borrarlos
    aqui destruiria para siempre lo que "Recuperar archivos" promete salvar.
    """
    freed = 0
    removed = 0
    if not os.path.isdir(path):
        return 0, 0
    for dirpath, _, filenames in os.walk(path, topdown=False):
        for fname in filenames:
            if proteger_rescatables and _es_rescatable(fname):
                continue
            filepath = os.path.join(dirpath, fname)
            try:
                size = os.path.getsize(filepath)
                os.remove(filepath)
                freed += size
                removed += 1
            except OSError:
                continue
        # Intentar eliminar directorios vacios
        try:
            if dirpath != path:
                os.rmdir(dirpath)
        except OSError:
            pass
    return freed, removed


class _SHFILEOPSTRUCTW(ctypes.Structure):
    """Estructura de SHFileOperationW (shell32).

    Los tipos son los de MSDN: fFlags es WORD (no DWORD). La alineacion por
    defecto de ctypes coincide con la del struct real en Win32 y Win64, asi
    que NO hay que forzar _pack_.
    """

    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("wFunc", ctypes.c_uint),
        ("pFrom", ctypes.c_wchar_p),
        ("pTo", ctypes.c_wchar_p),
        ("fFlags", ctypes.c_ushort),
        ("fAnyOperationsAborted", ctypes.c_int),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", ctypes.c_wchar_p),
    ]


def _send_to_recycle_bin(file_list: list[str]) -> tuple[int, int]:
    """Manda archivos a la Papelera de reciclaje (recuperables).

    Usa SHFileOperationW con FOF_ALLOWUNDO, que es lo mismo que hace el
    Explorador de Windows al borrar con la tecla Supr. A diferencia de
    os.remove, el usuario puede recuperar el archivo despues.

    IMPORTANTE: si algo falla NO se cae de vuelta a un borrado permanente.
    Preferimos no liberar espacio antes que borrar algo sin vuelta atras.

    Returns:
        (bytes_liberados, archivos_movidos). (0, 0) si la operacion fallo.
    """
    if not file_list:
        return 0, 0

    # pFrom es una lista de rutas separadas por \0 y terminada en DOBLE \0.
    paths = [p for p in file_list if os.path.exists(p)]
    if not paths:
        return 0, 0

    freed = 0
    for filepath in paths:
        try:
            freed += os.path.getsize(filepath)
        except OSError:
            continue

    FO_DELETE = 0x0003
    FOF_SILENT = 0x0004
    FOF_NOCONFIRMATION = 0x0010
    FOF_ALLOWUNDO = 0x0040
    FOF_NOERRORUI = 0x0400

    try:
        op = _SHFILEOPSTRUCTW()
        op.hwnd = None
        op.wFunc = FO_DELETE
        op.pFrom = "\0".join(paths) + "\0\0"
        op.pTo = None
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
        if result != 0 or op.fAnyOperationsAborted:
            return 0, 0
        return freed, len(paths)
    except (AttributeError, OSError, ValueError):
        return 0, 0


def _empty_recycle_bin() -> bool:
    """Vacia la papelera de reciclaje."""
    try:
        # SHEmptyRecycleBinW(hwnd, pszRootPath, dwFlags)
        # SHERB_NOCONFIRMATION=1 | SHERB_NOPROGRESSUI=2 | SHERB_NOSOUND=4
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x07)
        return result == 0 or result == -2147418113  # S_OK or already empty
    except (AttributeError, OSError):
        return False


class _SHQUERYRBINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint32),
        ("i64Size", ctypes.c_int64),
        ("i64NumItems", ctypes.c_int64),
    ]


def _query_recycle_bin() -> tuple[int, int]:
    """Consulta (bytes, num_archivos) de la papelera SIN vaciarla.

    Usa SHQueryRecycleBinW con pszRootPath=None (consulta todas las unidades).
    Retorna (0, 0) si esta vacia o si la consulta falla.
    """
    try:
        info = _SHQUERYRBINFO()
        info.cbSize = ctypes.sizeof(info)
        result = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
        if result == 0:  # S_OK
            return int(info.i64Size), int(info.i64NumItems)
    except (AttributeError, OSError):
        pass
    return 0, 0


# --- Interfaz de consola ---


def ejecutar_limpieza(
    limpiar_temp: bool = False,
    limpiar_update: bool = False,
    descargas: list[str] | None = None,
    vaciar_papelera: bool = False,
    temp_paths: list[str] | None = None,
    papelera_size: int = 0,
    papelera_count: int = 0,
) -> dict:
    """Ejecuta la limpieza. UNICO lugar donde vive el plan de borrado.

    Esta funcion existe porque el orden de las operaciones y que cuenta como
    espacio liberado son INVARIANTES DE SEGURIDAD, no detalles de pantalla. Si
    cada interfaz (consola, GUI) arma su propio plan, tarde o temprano una de
    las dos diverge y borra algo que no debia. La interfaz pregunta; aqui se
    decide y se ejecuta.

    Los parametros son decisiones YA CONFIRMADAS por el usuario en la capa de
    interfaz: esta funcion no pregunta nada. Por eso todos los flags destructivos
    tienen default False y `descargas` default None: llamarla sin argumentos no
    borra absolutamente nada.

    Args:
        limpiar_temp: borrar archivos temporales (regenerables por Windows).
        limpiar_update: borrar cache de Windows Update (regenerable).
        descargas: rutas de descargas antiguas que el usuario eligio UNA POR
            UNA. Van a la Papelera, no se borran.
        vaciar_papelera: vaciar la papelera. IRREVERSIBLE.
        temp_paths: rutas de temporales detectadas por _scan_temp_files().
        papelera_size/papelera_count: lo que reporto _query_recycle_bin(), para
            poder informar cuanto se libero al vaciarla.

    Returns:
        dict con:
          liberado: bytes que de verdad se liberaron del disco.
          a_papelera: bytes movidos a la Papelera. NO son espacio liberado: el
            archivo sigue ocupando disco hasta que se vacie. Van aparte para no
            mentirle al usuario.
          limpiados: numero de archivos borrados o movidos.
          descargas_movidas: cuantas descargas se mandaron a la Papelera. Va
            aparte de `limpiados` para que la interfaz pueda decir exactamente
            "3 archivos movidos a la Papelera" sin tener que adivinarlo.
          papelera_vaciada: True si se vacio la papelera con exito.
          papelera_fallo: True si se pidio vaciar la papelera y no se pudo.
          descargas_fallaron: True si no se pudo mover a la Papelera; en ese
            caso NO se borro nada (nunca hay fallback a borrado permanente).
    """
    liberado = 0
    limpiados = 0
    a_papelera = 0
    descargas_movidas = 0
    papelera_vaciada = False
    papelera_fallo = False
    descargas_fallaron = False

    # ORDEN OBLIGATORIO: la papelera se vacia PRIMERO. Las descargas antiguas se
    # mandan a la papelera, asi que vaciarla despues destruiria para siempre lo
    # que acabamos de dejar ahi justo para que fuera recuperable.
    if vaciar_papelera:
        if _empty_recycle_bin():
            liberado += papelera_size
            limpiados += papelera_count
            papelera_vaciada = True
        else:
            papelera_fallo = True

    if limpiar_temp:
        for path in temp_paths or []:
            # proteger_rescatables=True: %TEMP% recibe los autorecuperados de
            # Office que el rescate del producto busca; no se borran aqui.
            f, r = _clean_dir(path, proteger_rescatables=True)
            liberado += f
            limpiados += r

    if limpiar_update:
        f, r = _clean_dir(WINDOWS_UPDATE_CACHE)
        liberado += f
        limpiados += r

    if descargas:
        movido, cuantos = _send_to_recycle_bin(descargas)
        if cuantos:
            a_papelera += movido
            limpiados += cuantos
            descargas_movidas = cuantos
        else:
            descargas_fallaron = True

    return {
        "liberado": liberado,
        "a_papelera": a_papelera,
        "limpiados": limpiados,
        "descargas_movidas": descargas_movidas,
        "papelera_vaciada": papelera_vaciada,
        "papelera_fallo": papelera_fallo,
        "descargas_fallaron": descargas_fallaron,
    }


def _choose_downloads(file_list: list[str]) -> list[str]:
    """Muestra las descargas antiguas y deja elegir cuales mandar a la papelera.

    Antes se borraba la lista completa a ciegas: el usuario nunca veia QUE se
    iba a borrar. Aqui se listan una por una y se puede seleccionar.

    Returns:
        Lista de rutas elegidas (vacia si el usuario cancela).
    """
    if not file_list:
        return []

    table = Table(title="Descargas antiguas encontradas")
    table.add_column("#", style="bold cyan", width=4, justify="right")
    table.add_column("Archivo", style="bold white", max_width=50)
    table.add_column("Tamano", justify="right", style="yellow")
    table.add_column("Ultima vez usado", style="dim")

    for i, filepath in enumerate(file_list, 1):
        try:
            stat = os.stat(filepath)
            size = format_size(stat.st_size)
            fecha = time.strftime("%d/%m/%Y", time.localtime(stat.st_mtime))
        except OSError:
            size = "?"
            fecha = "?"
        table.add_row(str(i), escape(os.path.basename(filepath)), size, fecha)

    console.print()
    console.print(table)
    console.print(
        "[dim]Se mandan a la Papelera de reciclaje, asi que puedes "
        "recuperarlos si te arrepientes.[/dim]"
    )

    choice = Prompt.ask(
        "[bold]Cuales mandas a la papelera? (numeros separados por coma, "
        "'todos', o Enter para cancelar)[/bold]",
        default="",
    ).strip().lower()

    if not choice:
        console.print("[yellow]No se toco ninguna descarga.[/yellow]")
        return []

    if choice == "todos":
        return list(file_list)

    try:
        indices = {int(x.strip()) - 1 for x in choice.split(",")}
    except ValueError:
        console.print("[red]Entrada invalida. No se toco ninguna descarga.[/red]")
        return []

    chosen = [file_list[i] for i in sorted(indices) if 0 <= i < len(file_list)]
    if not chosen:
        console.print("[yellow]Ningun numero valido. No se toco nada.[/yellow]")
    return chosen


def disk_cleaner_menu() -> None:
    """Menu del liberador de espacio."""
    console.print("\n[bold cyan]Liberar Espacio en Disco[/bold cyan]\n")

    # Escanear categorias
    with console.status("[bold green]Escaneando archivos temporales..."):
        temp_size, temp_count, temp_paths = _scan_temp_files()

    with console.status("[bold green]Escaneando cache de Windows Update..."):
        update_size, update_count = _scan_update_cache()

    with console.status("[bold green]Escaneando descargas antiguas..."):
        dl_size, dl_count, dl_files = _scan_old_downloads()

    with console.status("[bold green]Escaneando papelera de reciclaje..."):
        recycle_size, recycle_count = _query_recycle_bin()

    # Tabla resumen
    table = Table(title="Espacio recuperable")
    table.add_column("#", style="bold cyan", width=4, justify="right")
    table.add_column("Categoria", style="bold")
    table.add_column("Archivos", justify="right")
    table.add_column("Tamano", justify="right", style="yellow")

    categories = []

    if temp_count > 0:
        categories.append(("Archivos temporales", temp_count, temp_size, "temp"))
        table.add_row(str(len(categories)), "Archivos temporales", str(temp_count), format_size(temp_size))

    if update_count > 0:
        categories.append(("Cache de Windows Update", update_count, update_size, "update"))
        table.add_row(str(len(categories)), "Cache de Windows Update", str(update_count), format_size(update_size))
    elif not is_admin():
        table.add_row("-", "Cache de Windows Update", "-", "[dim](requiere admin)[/dim]")

    if dl_count > 0:
        categories.append((f"Descargas antiguas (>{OLD_DOWNLOAD_DAYS} dias)", dl_count, dl_size, "downloads"))
        table.add_row(str(len(categories)), f"Descargas antiguas (>{OLD_DOWNLOAD_DAYS} dias)", str(dl_count), format_size(dl_size))

    categories.append(("Papelera de reciclaje", recycle_count, recycle_size, "recycle"))
    if recycle_count > 0:
        table.add_row(str(len(categories)), "Papelera de reciclaje", str(recycle_count), format_size(recycle_size))
    else:
        table.add_row(str(len(categories)), "Papelera de reciclaje", "-", "-")

    console.print(table)

    total = temp_size + update_size + dl_size
    if total == 0 and recycle_count == 0:
        console.print("\n[bold green]No hay archivos para limpiar.[/bold green]")
        return

    console.print(f"\n[bold]Total estimado (sin papelera): {format_size(total)}[/bold]")

    # Preguntar cuales limpiar. Sin default: un Enter en vacio no selecciona
    # nada, para evitar que un usuario apurado borre todo por accidente
    # (incluida la papelera, que es irreversible).
    to_clean = Prompt.ask(
        "[bold]Numeros a limpiar (separados por coma, o 'todos')[/bold]",
        default="",
    ).strip().lower()

    if not to_clean:
        console.print("[yellow]No se selecciono nada. Cancelado.[/yellow]")
        return

    if to_clean == "todos":
        selected = set(range(len(categories)))
    else:
        try:
            selected = {int(x.strip()) - 1 for x in to_clean.split(",")}
        except ValueError:
            console.print("[red]Entrada invalida.[/red]")
            return

    # Vaciar la papelera es lo UNICO verdaderamente irreversible que queda:
    # requiere una confirmacion explicita adicional, separada de la seleccion
    # de numeros de arriba. Las descargas antiguas ya no entran aqui porque se
    # mandan a la papelera (recuperables) y ademas se eligen una por una.
    # Temporales y cache de Windows Update son regenerables por Windows.
    permanent_names = []
    for idx in sorted(selected):
        if idx < 0 or idx >= len(categories):
            continue
        name, count, size, cat_type = categories[idx]
        if cat_type == "recycle":
            permanent_names.append("Papelera de reciclaje (vaciarla es irreversible)")

    if permanent_names:
        console.print("\n[bold red]Esto borra PERMANENTEMENTE y no se puede deshacer:[/bold red]")
        for pname in permanent_names:
            console.print(f"  - {pname}")
        proceed_permanent = Confirm.ask(
            "[bold red]Confirmas el borrado permanente de lo anterior?[/bold red]",
            default=False,
        )
        if not proceed_permanent:
            selected = {
                idx for idx in selected
                if 0 <= idx < len(categories) and categories[idx][3] != "recycle"
            }
            console.print("[yellow]Se omitio el vaciado de la papelera.[/yellow]")

    # Traducir la seleccion por numeros a decisiones. El ORDEN de ejecucion y
    # que cuenta como liberado NO se deciden aqui: eso vive en
    # ejecutar_limpieza(), para que la consola y la GUI no tengan cada una su
    # propia version de un invariante de seguridad.
    valid = [idx for idx in selected if 0 <= idx < len(categories)]
    tipos = {categories[idx][3] for idx in valid}

    elegidas_dl = []
    if "downloads" in tipos:
        elegidas_dl = _choose_downloads(dl_files)

    # Decir QUE se esta limpiando, no solo "limpiando": el usuario acaba de
    # marcar varias categorias y necesita ver que se atendieron todas.
    nombres = [categories[idx][0] for idx in sorted(valid)]
    for nombre_cat in nombres:
        console.print(f"\n[bold yellow]Limpiando: {nombre_cat}...[/bold yellow]")

    resultado = ejecutar_limpieza(
        limpiar_temp="temp" in tipos,
        limpiar_update="update" in tipos,
        descargas=elegidas_dl,
        vaciar_papelera="recycle" in tipos,
        temp_paths=temp_paths,
        papelera_size=recycle_size,
        papelera_count=recycle_count,
    )

    if resultado["papelera_vaciada"]:
        console.print("  [green]Papelera vaciada.[/green]")
    if resultado["papelera_fallo"]:
        console.print("  [dim]La papelera ya estaba vacia o no se pudo vaciar.[/dim]")
    if resultado["descargas_movidas"]:
        console.print(
            f"  [green]{resultado['descargas_movidas']} archivo(s) movido(s) a la "
            f"Papelera (puedes recuperarlos desde ahi).[/green]"
        )
    if resultado["descargas_fallaron"]:
        console.print(
            "  [yellow]No se pudo mover a la Papelera; no se borro "
            "nada para no perder tus archivos.[/yellow]"
        )

    console.print(f"\n[bold green]Limpieza completada![/bold green]")
    console.print(f"  Archivos limpiados: [bold]{resultado['limpiados']}[/bold]")
    console.print(f"  Espacio liberado: [bold]{format_size(resultado['liberado'])}[/bold]")
    if resultado["a_papelera"]:
        console.print(
            f"  En la Papelera: [bold]{format_size(resultado['a_papelera'])}[/bold] "
            f"[dim](todavia ocupan disco; se liberan al vaciar la papelera, "
            f"pero mientras tanto puedes recuperarlos)[/dim]"
        )
