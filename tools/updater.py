"""
Auto-updater: verifica GitHub Releases y ofrece descargar nueva version.
"""

import glob
import hashlib
import json
import os
import re
import ssl
import sys
import tempfile
import urllib.request

from rich.panel import Panel
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn
from rich.prompt import Confirm
from rich.markup import escape
from utils import console

REPO = "ElBecerril/salva-godinez"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"

# Limite maximo razonable para el .exe del updater (evita descargas
# descontroladas o respuestas maliciosas con Content-Length falso/ausente).
MAX_DOWNLOAD_SIZE = 200 * 1024 * 1024  # 200 MB


# --- Logica (sin UI) ---


_SSL_CTX = None


def _get_ssl_context() -> ssl.SSLContext:
    """Contexto SSL con CA certs empaquetados (certifi).

    En el .exe congelado (PyInstaller/Windows), el modulo `ssl` no encuentra
    los certificados raiz del sistema, asi que `urlopen` contra
    https://api.github.com fallaba con CERTIFICATE_VERIFY_FAILED y el chequeo
    de actualizaciones volvia vacio EN SILENCIO (por eso el dialogo "no salia"
    sin haber tocado nunca la red con exito). certifi trae su propio bundle de
    CAs (el de Mozilla) y se empaqueta en el .exe, garantizando la
    verificacion en cualquier entorno.

    `import certifi` es perezoso a proposito: si no esta disponible (dev en
    Linux sin instalarlo), se cae al contexto por defecto del sistema, que ahi
    si funciona. La verificacion de certificado NUNCA se desactiva.
    """
    global _SSL_CTX
    if _SSL_CTX is None:
        try:
            import certifi
            _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            _SSL_CTX = ssl.create_default_context()
    return _SSL_CTX


def _get_desktop_path() -> str:
    """Ruta REAL del Escritorio, resolviendo la redireccion de OneDrive (KFM).

    En oficinas con Microsoft 365, OneDrive suele redirigir el Escritorio a
    `~/OneDrive/Desktop` (o `Escritorio`); el `~/Desktop` hardcodeado ya no
    existe, y el move de la actualizacion fallaba con FileNotFoundError DESPUES
    de haber verificado bien la descarga (el usuario veia "no se pudo
    descargar" con el hash correcto). `SHGetKnownFolderPath` devuelve la ruta
    real. Fuera de Windows (dev) o si algo falla, cae a `~/Desktop`.
    """
    try:
        import ctypes

        class _GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", ctypes.c_ulong),
                ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        # FOLDERID_Desktop = {B4BFCC3A-DB2C-424C-B029-7FE99A87C641}
        folderid_desktop = _GUID(
            0xB4BFCC3A, 0xDB2C, 0x424C,
            (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41),
        )
        path_ptr = ctypes.c_wchar_p()
        res = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(folderid_desktop), 0, None, ctypes.byref(path_ptr)
        )
        if res == 0 and path_ptr.value:
            path = path_ptr.value
            ctypes.windll.ole32.CoTaskMemFree(path_ptr)
            if os.path.isdir(path):
                return path
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), "Desktop")


def _parse_version(tag: str) -> tuple:
    """'v3.0.0' -> (3, 0, 0); tolera sufijos tipo '-beta'/'-rc1'.

    Antes se hacia `int(x) for x in tag.lstrip("vV").split(".")`, que lanzaba
    ValueError con un tag no estrictamente numerico (p.ej. 'v2.6.0-beta') y
    mataba el chequeo de actualizaciones EN SILENCIO en la GUI (misma clase de
    fallo que el bug de SSL). Ahora se extrae la parte numerica inicial; si el
    tag no trae una version reconocible se devuelve (0,), que nunca se
    interpreta como mas nueva que la local (fail-safe: mejor no ofrecer update
    que tronar el chequeo).
    """
    match = re.match(r"v?(\d+(?:\.\d+)*)", tag.strip())
    if not match:
        return (0,)
    return tuple(int(x) for x in match.group(1).split("."))


def _extract_sha256(body: str, filename: str) -> str | None:
    """Extrae hash SHA-256 del body del Release.

    Busca patrones como:
        abc123...  SalvaGodinez.exe        (formato sha256sum, el preferido)
        SHA-256: abc123...
        SHA-256:
        ```
        abc123...
        ```                                 (hash dentro de un bloque markdown)
    """
    if not body:
        return None
    # Primero el patron que ata el hash al filename del asset (mas
    # especifico): <hex>  <filename>. Se intenta antes del patron generico
    # para no agarrar el hash de otro asset cuando el body lista varios.
    # [\s`]+ tolera un backtick de cierre entre el hash y el nombre (formato
    # `<hex>` <archivo>), ademas de los espacios del formato sha256sum.
    match = re.search(rf"([0-9a-fA-F]{{64}})[\s`]+\S*{re.escape(filename)}", body)
    if match:
        return match.group(1).lower()
    # Fallback: una etiqueta "SHA-256" seguida del hash, TOLERANDO lo que haya
    # en medio (dos puntos, saltos de linea, y hasta un bloque de codigo ```).
    # Antes se exigia "SHA-256:\s*<hex>" en la misma linea, y un hash dentro de
    # un fence markdown quedaba fuera de alcance -> el updater rechazaba la
    # actualizacion por "sin firma" aunque el hash SI estuviera en las notas
    # (bug real cazado en la VM). Los lookarounds fijan el hash a EXACTAMENTE
    # 64 hex (no agarra un hash mas largo). DOTALL para que `.` cruce saltos.
    match = re.search(
        r"SHA-?256.*?(?<![0-9a-fA-F])([0-9a-fA-F]{64})(?![0-9a-fA-F])",
        body, re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group(1).lower()
    return None


def fetch_latest_release() -> dict:
    """Consulta la API de GitHub Releases por el ultimo release.

    Returns:
        {"ok": True, "data": <json decodificado>} o
        {"ok": False, "error": str(e)}.
    """
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"User-Agent": "SalvaGodinez-Updater"},
        )
        with urllib.request.urlopen(req, timeout=5, context=_get_ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {"ok": True, "data": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def check_update_available(current_version: str, release_data: dict) -> dict:
    """Compara la version local contra la del release remoto.

    Returns:
        dict con "disponible" (bool) y "remote_tag" (str, puede ser "").
    """
    remote_tag = release_data.get("tag_name", "")
    if not remote_tag:
        return {"disponible": False, "remote_tag": ""}

    local_tuple = _parse_version(current_version)
    remote_tuple = _parse_version(remote_tag)

    return {"disponible": remote_tuple > local_tuple, "remote_tag": remote_tag}


def get_exe_asset(release_data: dict) -> dict | None:
    """Devuelve el asset .exe del release, o None si no hay."""
    assets = release_data.get("assets", [])
    return next((a for a in assets if a["name"].endswith(".exe")), None)


def download_update(
    url: str,
    filename: str,
    expected_sha256: str | None = None,
    progress_callback=None,
) -> dict:
    """Descarga un archivo a una ubicacion temporal, lo verifica y lo instala.

    El orden es deliberado por seguridad: se descarga primero a un archivo
    temporal (el Escritorio no se toca todavia), se verifica el SHA-256 y
    SOLO si la verificacion es exitosa se mueve el archivo temporal a su
    ubicacion final en el Escritorio. Si el Release no incluye un hash de
    referencia, la actualizacion se RECHAZA (no se instala nada que no se
    pueda verificar). Solo despues de confirmar que ese move fue exitoso se
    borran las versiones anteriores del Escritorio; asi, si el move falla,
    las versiones viejas siguen intactas.

    Args:
        url: URL de descarga del asset.
        filename: nombre con el que se guardara en el Escritorio.
        expected_sha256: hash de referencia extraido del Release, o None.
        progress_callback: opcional, callable(written, total) invocado tras
            cada chunk leido (total puede ser 0 si no se conoce).

    Returns:
        dict con al menos "ok" (bool) y "reason" (str, codigo de motivo) y,
        segun el caso, "dest", "actual_hash", "expected_sha256",
        "removed_old" (lista de rutas eliminadas), "old_errors" (lista de
        (ruta, error) para versiones anteriores que no se pudieron borrar).
    """
    desktop = _get_desktop_path()
    dest = os.path.join(desktop, filename)

    # El temporal se crea EN EL MISMO directorio que el destino (el Escritorio),
    # no en %TEMP%, para que el paso final sea un rename ATOMICO en el mismo
    # volumen (os.replace) en vez de una copia cross-volume (shutil.move) que,
    # si se interrumpe a la mitad, dejaria un .exe truncado que "ya paso" la
    # verificacion. Con esto, un corte a media descarga solo deja un .tmp
    # inofensivo; el .exe final aparece completo o no aparece.
    try:
        os.makedirs(desktop, exist_ok=True)
    except OSError:
        pass
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="salvagodinez_update_", suffix=".tmp", dir=desktop)
    os.close(tmp_fd)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SalvaGodinez-Updater"})
        resp = urllib.request.urlopen(req, timeout=30, context=_get_ssl_context())
        total = int(resp.headers.get("Content-Length", 0))

        if total > MAX_DOWNLOAD_SIZE:
            return {
                "ok": False,
                "reason": "too_large_header",
                "max_size": MAX_DOWNLOAD_SIZE,
            }

        sha256 = hashlib.sha256()
        written = 0

        with open(tmp_path, "wb") as f:
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_DOWNLOAD_SIZE:
                    return {
                        "ok": False,
                        "reason": "too_large_stream",
                        "max_size": MAX_DOWNLOAD_SIZE,
                    }
                f.write(chunk)
                sha256.update(chunk)
                if progress_callback:
                    progress_callback(written, total)

        actual_hash = sha256.hexdigest()

        if expected_sha256:
            if actual_hash != expected_sha256:
                return {
                    "ok": False,
                    "reason": "hash_mismatch",
                    "expected_sha256": expected_sha256,
                    "actual_hash": actual_hash,
                }
        else:
            # Sin hash de referencia en el Release no hay forma de verificar que
            # el .exe es el que el autor publico. Se rechaza (fail-closed) en vez
            # de instalar "con precaucion": un Release sin hash no debe llegar al
            # Escritorio del usuario.
            return {"ok": False, "reason": "no_reference_hash"}

        # Solo ahora, con la descarga ya verificada, es seguro tocar el Escritorio.
        # os.replace es un rename ATOMICO en el mismo volumen (el tmp vive en el
        # Escritorio): el .exe destino aparece completo de golpe, nunca a medias.
        # Solo si el move fue exitoso se borran versiones anteriores; si falla,
        # las versiones viejas siguen ahi.
        os.replace(tmp_path, dest)

        current_exe = os.path.normcase(os.path.abspath(sys.executable)) if getattr(sys, "frozen", False) else ""
        dest_abs = os.path.normcase(os.path.abspath(dest))
        removed_old = []
        old_errors = []
        for old in glob.glob(os.path.join(desktop, "SalvaGodinez*.exe")):
            # normcase: en Windows el filesystem es case-insensitive; sin esto,
            # un casing distinto podria intentar borrar el .exe en ejecucion.
            old_abs = os.path.normcase(os.path.abspath(old))
            if old_abs != current_exe and old_abs != dest_abs:
                try:
                    os.remove(old)
                    removed_old.append(old)
                except OSError as e:
                    old_errors.append((old, str(e)))

        return {
            "ok": True,
            "reason": "installed",
            "dest": dest,
            "actual_hash": actual_hash,
            "removed_old": removed_old,
            "old_errors": old_errors,
        }

    except Exception as e:
        return {"ok": False, "reason": "exception", "error": str(e)}
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


# --- Interfaz de consola ---


def check_for_updates(current_version: str) -> None:
    """Verifica si hay una version nueva en GitHub Releases.

    Envoltura a prueba de todo: esta funcion se llama al ARRANCAR la app
    (main.py), antes del try principal, asi que una excepcion aqui tumba la
    app entera antes de que el usuario vea el menu. Buscar actualizaciones es
    una comodidad, nunca una razon para que la herramienta no abra.
    """
    try:
        _check_for_updates(current_version)
    except Exception as e:
        console.print(f"[dim]No se pudo verificar actualizaciones: {escape(str(e))}[/dim]")


def _check_for_updates(current_version: str) -> None:
    """Implementacion de la verificacion. Ver check_for_updates()."""
    release = fetch_latest_release()
    if not release["ok"]:
        # Esto solo cubre la verificacion de si hay una version nueva
        # (llamada a la API de GitHub): sin internet, timeout, API error, etc.
        # No cubre la descarga en si, que reporta sus propios errores abajo.
        console.print(f"[dim]No se pudo verificar actualizaciones: {escape(str(release['error']))}[/dim]")
        return

    data = release["data"]
    status = check_update_available(current_version, data)
    if not status["disponible"]:
        return

    remote_tag = status["remote_tag"]

    console.print(
        Panel(
            f"[bold]Nueva version disponible:[/bold] {escape(remote_tag)}\n"
            f"[dim]Tu version actual: v{current_version}[/dim]",
            title="[bold yellow]Actualizacion disponible[/bold yellow]",
            border_style="yellow",
        )
    )

    if not Confirm.ask("[yellow]Deseas descargar la nueva version?[/yellow]", default=False):
        return

    exe_asset = get_exe_asset(data)
    if not exe_asset:
        console.print("[red]No se encontro archivo .exe en el Release.[/red]")
        return

    # Extraer hash SHA-256 del body del Release (si el autor lo incluyo)
    release_body = data.get("body", "")
    expected_hash = _extract_sha256(release_body, exe_asset["name"])

    filename = f"SalvaGodinez_{remote_tag}.exe"

    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
    ) as progress:
        task = progress.add_task("Descargando...", total=None)

        def _on_progress(written: int, total: int) -> None:
            if progress.tasks[0].total is None and total:
                progress.update(task, total=total)
            progress.update(task, completed=written)

        result = download_update(
            exe_asset["browser_download_url"],
            filename,
            expected_hash,
            progress_callback=_on_progress,
        )

    if result["ok"]:
        console.print("[green]SHA-256 verificado correctamente.[/green]")
        console.print(f"[bold green]Guardado en:[/bold green] {escape(result['dest'])}")
        for old, err in result.get("old_errors", []):
            console.print(f"[yellow]No se pudo eliminar version anterior {escape(old)}: {escape(str(err))}[/yellow]")
        return

    reason = result.get("reason")
    if reason == "too_large_header":
        console.print(
            f"[bold red]La descarga excede el tamano maximo permitido "
            f"({result['max_size'] // (1024 * 1024)} MB segun Content-Length). "
            "Se aborta por seguridad. El Escritorio no fue modificado.[/bold red]"
        )
    elif reason == "too_large_stream":
        console.print(
            f"[bold red]La descarga supero el tamano maximo permitido "
            f"({result['max_size'] // (1024 * 1024)} MB). "
            "Se aborta por seguridad. El Escritorio no fue modificado.[/bold red]"
        )
    elif reason == "hash_mismatch":
        console.print(
            f"[bold red]Verificacion SHA-256 fallida![/bold red]\n"
            f"[red]Esperado: {result['expected_sha256']}[/red]\n"
            f"[red]Obtenido: {result['actual_hash']}[/red]\n"
            f"[red]La descarga se descarto por seguridad. El Escritorio no fue modificado.[/red]"
        )
    elif reason == "no_reference_hash":
        console.print(
            "[bold red]El Release no incluye un hash SHA-256 de referencia para "
            "verificar la descarga.[/bold red]\n"
            "[red]Por seguridad no se instala una actualizacion que no se puede "
            "verificar; el Escritorio no fue modificado.[/red]\n"
            "[dim]Descarga la version nueva manualmente desde el Release oficial en "
            "GitHub si lo necesitas.[/dim]"
        )
    elif reason == "exception":
        console.print(f"[bold red]Error al descargar la actualizacion: {escape(str(result['error']))}[/bold red]")
