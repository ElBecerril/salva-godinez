"""
Buscador de Archivos Excel Perdidos - Ejecutable standalone
by El_Becerril

Busca archivos Excel perdidos usando: papelera, disco completo,
temporales/autorecuperacion, recientes de Windows y shadow copies.
"""

import json
import os
import re
import shutil
import string
import struct
import subprocess
import sys
import time
from datetime import datetime

# ── Intentar importar Rich, si no existe usar fallback ──────────────────────

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich import box

    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    class _FakeConsole:
        def print(self, *a, **kw):
            text = str(a[0]) if a else ""
            # Limpiar tags de Rich
            import re as _re
            text = _re.sub(r"\[/?[^\]]*\]", "", text)
            print(text)
        def status(self, *a, **kw):
            return _NullCtx()
    class _NullCtx:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def update(self, *a): pass
    console = _FakeConsole()

# ── Configuracion ───────────────────────────────────────────────────────────

EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".xlsb", ".csv"}
RECOVERY_PATHS = [
    os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Excel"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Office", "UnsavedFiles"),
    os.environ.get("TEMP", ""),
]
RECENT_PATH = os.path.join(
    os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Recent"
)
SKIP_DIRS = {"$Recycle.Bin", "System Volume Information", "Windows", "$WinREAgent", "Recovery"}

# ── Utilidades ──────────────────────────────────────────────────────────────

def format_size(size_bytes):
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_ext(filename):
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot != -1 else ""


def file_info(filepath):
    try:
        stat = os.stat(filepath)
        return {
            "nombre": os.path.basename(filepath),
            "ruta": filepath,
            "tamano": format_size(stat.st_size),
            "fecha": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "mtime": stat.st_mtime,
        }
    except OSError:
        return None


def deduplicate(results):
    seen = set()
    unique = []
    for r in results:
        key = r.get("ruta", "")
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique

# ── Buscador: Papelera de reciclaje ────────────────────────────────────────

def search_recycle_bin(name_filter=""):
    ps_script = r"""
$shell = New-Object -ComObject Shell.Application
$folder = $shell.NameSpace(0x0a)
$items = $folder.Items()
$results = @()
foreach ($item in $items) {
    $results += @{
        Name = $folder.GetDetailsOf($item, 0)
        OriginalPath = $folder.GetDetailsOf($item, 1)
        DeleteDate = $folder.GetDetailsOf($item, 2)
        Size = $folder.GetDetailsOf($item, 3)
    }
}
$results | ConvertTo-Json -Compress
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        data = json.loads(result.stdout.strip())
        if isinstance(data, dict):
            data = [data]

        found = []
        nl = name_filter.lower()
        for item in data:
            name = item.get("Name", "")
            if get_ext(name) not in EXCEL_EXTENSIONS:
                continue
            if nl and nl not in name.lower():
                continue
            found.append({
                "nombre": name,
                "ruta": item.get("OriginalPath", "?"),
                "tamano": item.get("Size", "?"),
                "fecha": item.get("DeleteDate", "?"),
                "origen": "Papelera de reciclaje",
            })
        return found
    except Exception:
        return []

# ── Buscador: Disco completo ──────────────────────────────────────────────

def get_drives():
    drives = []
    for letter in string.ascii_uppercase:
        p = f"{letter}:\\"
        if os.path.exists(p):
            drives.append(p)
    return drives


def search_disk_by_name(name_filter, progress_cb=None):
    nl = name_filter.lower()
    results = []
    for drive in get_drives():
        for dirpath, dirnames, filenames in os.walk(drive, topdown=True):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if progress_cb:
                progress_cb(dirpath)
            for fname in filenames:
                ext = get_ext(fname)
                if ext not in EXCEL_EXTENSIONS:
                    continue
                if nl and nl not in fname.lower():
                    continue
                info = file_info(os.path.join(dirpath, fname))
                if info:
                    info["origen"] = f"Disco ({drive.rstrip(chr(92))})"
                    results.append(info)
    return results


def search_recent_excel(days=30, progress_cb=None):
    cutoff = time.time() - (days * 86400)
    results = []
    for drive in get_drives():
        for dirpath, dirnames, filenames in os.walk(drive, topdown=True):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if progress_cb:
                progress_cb(dirpath)
            for fname in filenames:
                if get_ext(fname) not in EXCEL_EXTENSIONS:
                    continue
                info = file_info(os.path.join(dirpath, fname))
                if info and info["mtime"] >= cutoff:
                    info["origen"] = f"Disco ({drive.rstrip(chr(92))})"
                    results.append(info)
    results.sort(key=lambda x: x.get("mtime", 0), reverse=True)
    return results

# ── Buscador: Temporales / Autorecuperacion ────────────────────────────────

def search_temp_files(name_filter=""):
    results = []
    nl = name_filter.lower()
    for base in RECOVERY_PATHS:
        if not os.path.isdir(base):
            continue
        try:
            for dirpath, _, filenames in os.walk(base):
                for fname in filenames:
                    fl = fname.lower()
                    ext = get_ext(fl)
                    is_temp = (
                        ext in EXCEL_EXTENSIONS
                        or (fl.startswith(("~$", "~")) and ext in EXCEL_EXTENSIONS | {".tmp", ".xlk"})
                        or ext in (".xar", ".asd")
                    )
                    if not is_temp:
                        continue
                    if nl and nl not in fl:
                        continue
                    info = file_info(os.path.join(dirpath, fname))
                    if info:
                        info["origen"] = "Autorecuperacion / Temp"
                        results.append(info)
        except OSError:
            continue
    return results

# ── Buscador: Archivos recientes de Windows (.lnk) ────────────────────────

def read_lnk_target(lnk_path):
    try:
        with open(lnk_path, "rb") as f:
            content = f.read()
        if len(content) < 76:
            return None
        header_size = struct.unpack_from("<I", content, 0)[0]
        if header_size != 0x4C:
            return None
        flags = struct.unpack_from("<I", content, 0x14)[0]
        offset = 0x4C
        if flags & 0x01:  # HasLinkTargetIDList
            if offset + 2 > len(content):
                return None
            id_size = struct.unpack_from("<H", content, offset)[0]
            offset += 2 + id_size
        if flags & 0x02:  # HasLinkInfo
            if offset + 20 > len(content):
                return None
            # LinkInfoFlags en offset+8: bit 0 = VolumeIDAndLocalBasePath
            link_info_flags = struct.unpack_from("<I", content, offset + 8)[0]
            if not (link_info_flags & 0x01):
                return None  # No hay ruta local (posible ruta de red)
            lbp_offset = struct.unpack_from("<I", content, offset + 16)[0]
            path_start = offset + lbp_offset
            if path_start >= len(content):
                return None
            end = content.index(b"\x00", path_start)
            path = content[path_start:end].decode("latin-1")
            if path and os.path.splitext(path)[1]:
                return path
        return None
    except (OSError, struct.error, ValueError):
        return None


def search_recent_files(name_filter=""):
    results = []
    nl = name_filter.lower()
    if not os.path.isdir(RECENT_PATH):
        return results
    try:
        for fname in os.listdir(RECENT_PATH):
            if not fname.lower().endswith(".lnk"):
                continue
            target = read_lnk_target(os.path.join(RECENT_PATH, fname))
            if not target:
                continue
            if get_ext(target) not in EXCEL_EXTENSIONS:
                continue
            tname = os.path.basename(target)
            if nl and nl not in tname.lower():
                continue
            exists = os.path.isfile(target)
            if exists:
                info = file_info(target)
                if not info:
                    continue
            else:
                info = {"nombre": tname, "ruta": target, "tamano": "N/A", "fecha": "N/A"}
            info["origen"] = f"Recientes ({'Existe' if exists else 'NO encontrado'})"
            results.append(info)
    except OSError:
        pass
    return results

# ── Buscador: Shadow Copies (VSS) ─────────────────────────────────────────

def search_shadow_copies(name_filter, original_path=""):
    results = []
    try:
        r = subprocess.run(
            ["vssadmin", "list", "shadows"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if r.returncode != 0:
            return results
    except Exception:
        return results

    shadows = []
    current = {}
    for line in r.stdout.splitlines():
        line = line.strip()
        m = re.search(r"(\\\\[?]\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy\d+)", line)
        if m:
            current["path"] = m.group(1)
        if "Original Volume" in line or "Volumen original" in line:
            m2 = re.search(r"\(([A-Z]):\\\)", line, re.IGNORECASE)
            if m2:
                current["drive"] = m2.group(1)
        if "creation date" in line.lower() or "fecha de creacion" in line.lower():
            parts = line.split(":", 1)
            if len(parts) > 1:
                current["date"] = parts[1].strip()
        if "path" in current and "drive" in current:
            shadows.append(current)
            current = {}

    nl = name_filter.lower()
    for shadow in shadows:
        sp = shadow.get("path", "")
        sd = shadow.get("date", "?")
        search_root = sp + "\\Users"
        if not os.path.isdir(search_root):
            continue
        try:
            for dirpath, dirnames, filenames in os.walk(search_root):
                depth = dirpath.count("\\") - search_root.count("\\")
                if depth > 5:
                    dirnames.clear()
                    continue
                for fn in filenames:
                    if get_ext(fn) not in EXCEL_EXTENSIONS:
                        continue
                    if nl and nl not in fn.lower():
                        continue
                    info = file_info(os.path.join(dirpath, fn))
                    if info:
                        info["fecha"] = sd
                        info["origen"] = "Shadow Copy (VSS)"
                        results.append(info)
        except OSError:
            continue
    return results

# ── Reporte ─────────────────────────────────────────────────────────────────

def show_results(results, title="Resultados"):
    if HAS_RICH:
        if not results:
            console.print(Panel("[yellow]No se encontraron archivos.[/yellow]", title=title))
            return
        table = Table(title=title, show_lines=True)
        table.add_column("#", style="bold cyan", width=4, justify="right")
        table.add_column("Nombre", style="bold white", max_width=40)
        table.add_column("Ruta", style="dim", max_width=60)
        table.add_column("Tamano", justify="right", style="green")
        table.add_column("Fecha", style="yellow")
        table.add_column("Origen", style="magenta")
        for i, r in enumerate(results, 1):
            table.add_row(str(i), r.get("nombre","?"), r.get("ruta","?"),
                          r.get("tamano","?"), r.get("fecha","?"), r.get("origen","?"))
        console.print(table)
    else:
        print(f"\n  === {title} ===\n")
        if not results:
            print("  No se encontraron archivos.\n")
            return
        print(f"  {'#':>4}  {'Nombre':<35} {'Ruta':<55} {'Tamano':>10}  {'Fecha':<17} {'Origen'}")
        print("  " + "-" * 140)
        for i, r in enumerate(results, 1):
            nombre = r.get("nombre", "?")[:33]
            ruta = r.get("ruta", "?")
            if len(ruta) > 53:
                ruta = "..." + ruta[-50:]
            print(f"  {i:>4}  {nombre:<35} {ruta:<55} {r.get('tamano','?'):>10}  {r.get('fecha','?'):<17} {r.get('origen','?')}")

    print(f"\n  Total: {len(results)} archivo(s) encontrado(s)\n")


def offer_restore(results):
    if not results:
        return
    print("  Puedes copiar un archivo encontrado a otra ubicacion.")
    try:
        choice = input("  Numero del archivo a copiar (0 para omitir): ").strip()
        idx = int(choice) if choice else 0
    except (ValueError, EOFError):
        return
    if idx < 1 or idx > len(results):
        return

    selected = results[idx - 1]
    source = selected["ruta"]
    if not os.path.isfile(source):
        print(f"  El archivo ya no existe en: {source}")
        return

    default_dest = os.path.join(os.path.expanduser("~"), "Desktop")
    try:
        dest_dir = input(f"  Carpeta destino (Enter = {default_dest}): ").strip()
    except EOFError:
        return
    if not dest_dir:
        dest_dir = default_dest
    if not os.path.isdir(dest_dir):
        print(f"  La carpeta no existe: {dest_dir}")
        return

    dest_path = os.path.join(dest_dir, selected["nombre"])
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(selected["nombre"])
        c = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(dest_dir, f"{base}_recuperado{c}{ext}")
            c += 1
    try:
        shutil.copy2(source, dest_path)
        print(f"\n  Archivo copiado exitosamente a: {dest_path}\n")
    except OSError as e:
        print(f"  Error al copiar: {e}")

# ── Opciones del menu ──────────────────────────────────────────────────────

def ask_name():
    try:
        return input("  Nombre (o parte del nombre) del archivo: ").strip()
    except EOFError:
        return ""


def make_progress(status_obj=None):
    def cb(path):
        display = path if len(path) < 60 else "..." + path[-57:]
        if status_obj and HAS_RICH:
            status_obj.update(f"[bold green]Escaneando:[/bold green] {display}")
    return cb


def option_search_by_name():
    name = ask_name()
    if not name:
        print("  Debes ingresar un nombre.")
        return
    all_results = []

    with console.status("[bold green]Buscando en papelera de reciclaje...") as s:
        all_results.extend(search_recycle_bin(name))

    with console.status("[bold green]Buscando en temporales / autorecuperacion...") as s:
        all_results.extend(search_temp_files(name))

    with console.status("[bold green]Revisando archivos recientes de Windows...") as s:
        all_results.extend(search_recent_files(name))

    print("  Buscando en todos los discos (esto puede tardar)...")
    with console.status("[bold green]Escaneando discos...") as s:
        all_results.extend(search_disk_by_name(name, make_progress(s)))

    with console.status("[bold green]Revisando shadow copies (VSS)...") as s:
        all_results.extend(search_shadow_copies(name))

    all_results = deduplicate(all_results)
    show_results(all_results, title=f"Resultados para '{name}'")
    offer_restore(all_results)


def option_recent_excel():
    print("  Buscando archivos Excel de los ultimos 30 dias...")
    with console.status("[bold green]Escaneando discos...") as s:
        results = search_recent_excel(progress_cb=make_progress(s))
    show_results(results, title="Archivos Excel recientes (ultimos 30 dias)")
    offer_restore(results)


def option_recycle_bin():
    try:
        name = input("  Filtrar por nombre (Enter para ver todos): ").strip()
    except EOFError:
        name = ""
    with console.status("[bold green]Revisando papelera de reciclaje..."):
        results = search_recycle_bin(name)
    show_results(results, title="Archivos Excel en la Papelera")
    offer_restore(results)


def option_temp_files():
    try:
        name = input("  Filtrar por nombre (Enter para ver todos): ").strip()
    except EOFError:
        name = ""
    with console.status("[bold green]Buscando en temporales / autorecuperacion..."):
        results = search_temp_files(name)
    show_results(results, title="Archivos Temporales / Autorecuperacion")
    offer_restore(results)


def option_recent_windows():
    try:
        name = input("  Filtrar por nombre (Enter para ver todos): ").strip()
    except EOFError:
        name = ""
    with console.status("[bold green]Revisando archivos recientes de Windows..."):
        results = search_recent_files(name)
    show_results(results, title="Archivos Recientes de Windows")
    offer_restore(results)


def option_full_search():
    name = ask_name()
    if not name:
        print("  Debes ingresar un nombre.")
        return
    all_results = []

    steps = [
        ("Papelera de reciclaje", lambda: search_recycle_bin(name)),
        ("Temporales / autorecuperacion", lambda: search_temp_files(name)),
        ("Archivos recientes de Windows", lambda: search_recent_files(name)),
    ]
    for label, searcher in steps:
        with console.status(f"[bold green]Buscando en {label}..."):
            r = searcher()
            all_results.extend(r)
            if r:
                print(f"    +{len(r)} encontrado(s) en {label}")

    print("  Escaneando todos los discos...")
    with console.status("[bold green]Escaneando discos...") as s:
        r = search_disk_by_name(name, make_progress(s))
        all_results.extend(r)
        if r:
            print(f"    +{len(r)} encontrado(s) en discos")

    with console.status("[bold green]Revisando shadow copies (VSS)..."):
        r = search_shadow_copies(name)
        all_results.extend(r)
        if r:
            print(f"    +{len(r)} encontrado(s) en Shadow Copies")

    all_results = deduplicate(all_results)
    show_results(all_results, title=f"Busqueda completa para '{name}'")
    offer_restore(all_results)

# ── Main ────────────────────────────────────────────────────────────────────

BANNER = r"""
  ____                           _
 | __ ) _   _ ___  ___ __ _ ___| | ___  _ __
 |  _ \| | | / __|/ __/ _` / __| |/ _ \| '__|
 | |_) | |_| \__ \ (_| (_| \__ \ | (_) | |
 |____/ \__,_|___/\___\__,_|___/_|\___/|_|

  Buscador de Archivos Excel Perdidos
  by El_Becerril
"""

MENU = """  +---------------------------------------------------+
  |             Menu Principal                        |
  +---------------------------------------------------+
  |  1 - Buscar por nombre de archivo                 |
  |  2 - Buscar todos los Excel recientes (30 dias)   |
  |  3 - Revisar papelera de reciclaje                |
  |  4 - Revisar archivos temporales / autorecup.     |
  |  5 - Revisar archivos recientes de Windows        |
  |  6 - Busqueda completa (todas las opciones)       |
  |  0 - Salir                                        |
  +---------------------------------------------------+"""


def main():
    try:
        while True:
            os.system("cls" if os.name == "nt" else "clear")
            if HAS_RICH:
                console.print(f"[bold cyan]{BANNER}[/bold cyan]")
                console.print(Panel(
                    "[bold]1[/bold] - Buscar por nombre de archivo\n"
                    "[bold]2[/bold] - Buscar todos los Excel recientes (30 dias)\n"
                    "[bold]3[/bold] - Revisar papelera de reciclaje\n"
                    "[bold]4[/bold] - Revisar archivos temporales / autorecup.\n"
                    "[bold]5[/bold] - Revisar archivos recientes de Windows\n"
                    "[bold]6[/bold] - Busqueda completa (todas las opciones)\n"
                    "[bold]0[/bold] - Salir",
                    title="[bold yellow]Menu Principal[/bold yellow]", box=box.ROUNDED,
                ))
            else:
                print(BANNER)
                print(MENU)

            try:
                choice = input("\n  Selecciona una opcion: ").strip()
            except EOFError:
                break

            if choice == "1":
                option_search_by_name()
            elif choice == "2":
                option_recent_excel()
            elif choice == "3":
                option_recycle_bin()
            elif choice == "4":
                option_temp_files()
            elif choice == "5":
                option_recent_windows()
            elif choice == "6":
                option_full_search()
            elif choice == "0":
                print("\n  Hasta luego!")
                break
            else:
                print("  Opcion no valida.")

            try:
                input("\n  Presiona Enter para volver al menu...")
            except EOFError:
                break
    except KeyboardInterrupt:
        print("\n  Hasta luego!")


if __name__ == "__main__":
    main()
