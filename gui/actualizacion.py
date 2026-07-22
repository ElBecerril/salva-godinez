"""Arranque de la version con ventanas: aviso de origen + auto-update, en GUI.

Antes esto vivia SOLO en la consola (main.arranque_comun): al abrir la app se
corria check_for_updates() y _show_source_notice(), ambos de texto, con la
ventana negra visible. Eso obligaba a mostrar la consola al arrancar (poco
confiable) y a contestar el "hay version nueva?" en negro.

Aqui se presentan los dos como ventanas de tkinter, para que la consola pueda
esconderse desde el arranque y el usuario vea una app limpia.

REGLA: la LOGICA del updater (bajar, verificar SHA-256) NO se reimplementa. Se
reusan tal cual las funciones de tools/updater.py; aqui solo esta la
presentacion. La verificacion de hash es critica de seguridad y no se toca.
"""

import os
import queue
import threading
import tkinter as tk
from tkinter import ttk

from gui import theme
from tools.updater import (
    check_update_available,
    download_update,
    fetch_latest_release,
    get_exe_asset,
    _extract_sha256,
)


# ---------------------------------------------------------------------------
# Correr trabajo lento (red/descarga) sin congelar la ventana.
# Mismo patron que ToolPanel.run_async, pero standalone: este modulo no es un
# panel. tkinter NO es thread-safe, asi que el resultado y el progreso viajan
# por una cola y se entregan en el hilo de la UI via after().
# ---------------------------------------------------------------------------

def _en_hilo(root, work, on_done, on_progress=None) -> None:
    cola: queue.Queue = queue.Queue()

    def _progress(*args):
        cola.put(("progress", args))

    def _worker():
        try:
            resultado = work(_progress) if on_progress else work()
            cola.put(("done", resultado))
        except Exception as e:  # noqa: BLE001 - se reporta, no tumba la app
            cola.put(("error", e))

    def _drenar():
        entregado = False
        try:
            while True:
                tipo, carga = cola.get_nowait()
                if tipo == "progress":
                    if on_progress:
                        on_progress(*carga)
                else:
                    entregado = True
                    if root.winfo_exists():
                        on_done(tipo == "done", carga)
        except queue.Empty:
            pass
        if not entregado and root.winfo_exists():
            root.after(80, _drenar)

    threading.Thread(target=_worker, daemon=True).start()
    root.after(80, _drenar)


# ---------------------------------------------------------------------------
# Aviso de origen oficial (contra clones con virus). Se muestra UNA vez por
# version: justo cuando el usuario acaba de conseguir un .exe nuevo, que es
# cuando una copia falsa seria el riesgo. No molesta en cada arranque.
# ---------------------------------------------------------------------------

def _marca_path() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, ".salvagodinez_origen")


def _origen_ya_visto(version: str) -> bool:
    try:
        with open(_marca_path(), encoding="utf-8") as f:
            return f.read().strip() == version
    except OSError:
        return False


def _marcar_origen_visto(version: str) -> None:
    try:
        with open(_marca_path(), "w", encoding="utf-8") as f:
            f.write(version)
    except OSError:
        pass


def _mostrar_aviso_origen(root, version: str) -> None:
    if version and _origen_ya_visto(version):
        return

    dlg = _dialogo_base(root, "Origen oficial")
    cont = ttk.Frame(dlg, style="Panel.TFrame", padding=(28, 24))
    cont.pack(fill="both", expand=True)

    ttk.Label(cont, text="Descarga segura", style="Title.TLabel").pack(anchor="w")
    ttk.Label(
        cont,
        text=(
            "SalvaGodinez solo es oficial si lo bajaste de:\n"
            "github.com/ElBecerril/salva-godinez\n\n"
            "Si lo conseguiste en otra pagina, grupo o link, borralo: puede ser "
            "una copia falsa con virus."
        ),
        style="Subtitle.TLabel", justify="left", wraplength=420,
    ).pack(anchor="w", pady=(8, 18))

    ttk.Button(cont, text="Entendido", style="Accent.TButton",
               command=dlg.destroy).pack(anchor="e")

    dlg.bind("<Escape>", lambda _e: dlg.destroy())
    dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)
    _centrar(dlg, root)
    dlg.grab_set()
    dlg.focus_set()
    if version:
        _marcar_origen_visto(version)
    root.wait_window(dlg)


# ---------------------------------------------------------------------------
# Auto-update en ventana. La logica (bajar + verificar SHA) es de tools/updater.
# ---------------------------------------------------------------------------

def _revisar_y_ofrecer(root, version: str) -> None:
    """Chequea en segundo plano; si hay version nueva, ofrece descargarla.

    Silencioso si no hay internet o no hay actualizacion: buscar updates es una
    comodidad, no debe estorbar ni con errores en pantalla al arrancar.
    """
    def work():
        release = fetch_latest_release()
        if not release["ok"]:
            return None
        data = release["data"]
        estado = check_update_available(version, data)
        if not estado["disponible"]:
            return None
        return {"remote_tag": estado["remote_tag"], "data": data}

    def on_done(ok, resultado):
        if ok and resultado:
            _dialogo_actualizacion(root, version, resultado["remote_tag"], resultado["data"])

    _en_hilo(root, work, on_done)


def _dialogo_actualizacion(root, version: str, remote_tag: str, data: dict) -> None:
    dlg = _dialogo_base(root, "Actualizacion disponible")
    cont = ttk.Frame(dlg, style="Panel.TFrame", padding=(28, 24))
    cont.pack(fill="both", expand=True)

    ttk.Label(cont, text="Hay una version nueva", style="Title.TLabel").pack(anchor="w")
    ttk.Label(
        cont,
        text=(
            f"Version nueva: {remote_tag}\n"
            f"Tu version: v{version}\n\n"
            "Se descarga a tu Escritorio y se verifica que sea la original antes "
            "de guardarla. Despues cierra esta app y abre el archivo nuevo."
        ),
        style="Subtitle.TLabel", justify="left", wraplength=420,
    ).pack(anchor="w", pady=(8, 16))

    # Zona que cambia: botones -> barra de progreso -> resultado.
    estado = ttk.Label(cont, text="", style="Panel.TLabel", justify="left", wraplength=420)
    barra = ttk.Progressbar(cont, mode="determinate", length=420)

    botones = ttk.Frame(cont, style="Panel.TFrame")
    botones.pack(fill="x", pady=(4, 0))

    def _cerrar():
        dlg.destroy()

    def _descargar():
        exe_asset = get_exe_asset(data)
        if not exe_asset:
            estado.configure(text="El Release no incluye un archivo .exe.")
            estado.pack(anchor="w", pady=(6, 0))
            return

        expected = _extract_sha256(data.get("body", ""), exe_asset["name"])
        filename = f"SalvaGodinez_{remote_tag}.exe"

        # Cambiar la UI a "descargando": fuera los botones, entra la barra.
        for w in botones.winfo_children():
            w.configure(state="disabled")
        estado.configure(text="Descargando y verificando...")
        estado.pack(anchor="w", pady=(6, 6))
        barra.pack(anchor="w", pady=(0, 6))
        barra.configure(value=0, maximum=100)

        def work(progress):
            return download_update(
                exe_asset["browser_download_url"], filename, expected,
                progress_callback=lambda w, t: progress(w, t),
            )

        def on_progress(written, total):
            if total and barra.winfo_exists():
                barra.configure(value=min(100, written * 100 // total))

        def on_done(ok, resultado):
            if not barra.winfo_exists():
                return
            barra.pack_forget()
            _mostrar_resultado(resultado if ok else {"ok": False, "reason": "exception",
                                                     "error": str(resultado)})

        def _mostrar_resultado(result):
            if result.get("ok"):
                estado.configure(
                    text=("Listo. Se verifico la firma (SHA-256) y se guardo en tu "
                          f"Escritorio:\n{result['dest']}\n\nCierra esta app y abre el "
                          "archivo nuevo para actualizar."),
                    foreground=theme.OK,
                )
            else:
                estado.configure(text=_texto_error(result), foreground=theme.DANGER)
            # Un solo boton para cerrar.
            for w in botones.winfo_children():
                w.destroy()
            ttk.Button(botones, text="Cerrar", command=_cerrar).pack(side="right")

        _en_hilo(root, work, on_done, on_progress=on_progress)

    ttk.Button(botones, text="Ahora no", command=_cerrar).pack(side="right")
    ttk.Button(botones, text="Descargar", style="Accent.TButton",
               command=_descargar).pack(side="right", padx=(0, 8))

    dlg.bind("<Escape>", lambda _e: _cerrar())
    dlg.protocol("WM_DELETE_WINDOW", _cerrar)
    _centrar(dlg, root)
    dlg.grab_set()
    dlg.focus_set()


def _texto_error(result: dict) -> str:
    """Traduce el codigo de motivo de download_update a texto para el usuario.

    Los mensajes de seguridad (hash distinto, sin hash de referencia) dejan
    claro que NO se instalo nada — el Escritorio no se toca si la verificacion
    falla, igual que en la version de consola.
    """
    reason = result.get("reason")
    if reason == "hash_mismatch":
        return ("La descarga no coincide con la firma esperada. Se descarto por "
                "seguridad; tu Escritorio no fue modificado.")
    if reason == "no_reference_hash":
        return ("El Release no trae la firma (SHA-256) para verificar la descarga. "
                "Por seguridad no se instala algo que no se puede verificar. "
                "Si lo necesitas, descarga la version nueva a mano desde el Release "
                "oficial en GitHub.")
    if reason in ("too_large_header", "too_large_stream"):
        mb = result.get("max_size", 0) // (1024 * 1024)
        return (f"La descarga excede el tamano maximo permitido ({mb} MB). Se aborto "
                "por seguridad; tu Escritorio no fue modificado.")
    if reason == "exception":
        return f"No se pudo descargar la actualizacion: {result.get('error', '')}"
    return "No se pudo completar la actualizacion."


# ---------------------------------------------------------------------------
# Utilidades de dialogo (modal, centrado sobre la ventana principal).
# ---------------------------------------------------------------------------

def _dialogo_base(root, titulo: str) -> tk.Toplevel:
    dlg = tk.Toplevel(root)
    dlg.title(titulo)
    dlg.configure(bg=theme.BG_PANEL)
    dlg.resizable(False, False)
    dlg.transient(root)
    return dlg


def _centrar(dlg: tk.Toplevel, root) -> None:
    dlg.update_idletasks()
    ancho, alto = dlg.winfo_width(), dlg.winfo_height()
    try:
        x = root.winfo_rootx() + (root.winfo_width() - ancho) // 2
        y = root.winfo_rooty() + (root.winfo_height() - alto) // 2
    except tk.TclError:
        x = (dlg.winfo_screenwidth() - ancho) // 2
        y = (dlg.winfo_screenheight() - alto) // 2
    dlg.geometry(f"+{max(x, 0)}+{max(y, 0)}")


# ---------------------------------------------------------------------------
# Punto de entrada: lo llama App al arrancar.
# ---------------------------------------------------------------------------

def arranque_gui(root, version: str) -> None:
    """Aviso de origen (una vez por version) + revision de actualizaciones.

    Best-effort: si algo falla aqui, la app tiene que seguir abierta igual.
    """
    try:
        _mostrar_aviso_origen(root, version)
    except Exception:  # noqa: BLE001
        pass
    try:
        _revisar_y_ofrecer(root, version)
    except Exception:  # noqa: BLE001
        pass
