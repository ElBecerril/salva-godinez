"""Despedida de la version con ventanas: el mensaje de apoyo al cerrar la app.

Existe porque el mensaje de "apoyame en mis redes" vivia SOLO en la despedida
de consola (main.show_farewell), que dejo de correr cuando la GUI paso a ser la
interfaz por default: al cerrar la ventana, main() nunca se llamaba y el mensaje
nunca se veia. Es el mismo patron del updater/aviso de origen que se rescato en
v2.5.2 — algo que colgaba del punto de entrada viejo quedo huerfano.

A diferencia de la de consola (un Prompt con numeros), aca son botones clicables
que abren el navegador, que es lo que un godinez espera de una ventana.
"""

import tkinter as tk
import webbrowser
from tkinter import ttk

from config import CANALES_APOYO
from gui import theme


def mostrar_despedida(parent: tk.Misc) -> None:
    """Muestra el dialogo de despedida, modal y centrado sobre la ventana.

    Bloquea hasta que el usuario lo cierra (con un boton, la X o Escape). No
    lanza si algo falla al abrir el navegador: la app tiene que poder cerrarse
    igual.
    """
    dlg = tk.Toplevel(parent)
    dlg.title("Gracias por usar SalvaGodinez")
    dlg.configure(bg=theme.BG_PANEL)
    dlg.resizable(False, False)
    # Sin boton de maximizar/minimizar; se comporta como dialogo.
    dlg.transient(parent)

    cont = ttk.Frame(dlg, style="Panel.TFrame", padding=(28, 24))
    cont.pack(fill="both", expand=True)

    ttk.Label(
        cont, text="Espero haberte salvado el dia", style="Title.TLabel",
    ).pack(anchor="w")

    ttk.Label(
        cont,
        text=(
            "SalvaGodinez es gratis y siempre lo sera. Lo hago yo solo; ya que "
            "te saque del apuro, pasate a reirte un rato: en mis redes hago "
            "comedia, no trabajo."
        ),
        style="Subtitle.TLabel", justify="left", wraplength=420,
    ).pack(anchor="w", pady=(8, 18))

    def _abrir(url: str) -> None:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001 - abrir el navegador nunca debe tumbar el cierre
            pass

    for nombre, handle, url in CANALES_APOYO:
        ttk.Button(
            cont, text=f"{nombre}  ({handle})", style="Accent.TButton",
            command=lambda u=url: _abrir(u),
        ).pack(fill="x", pady=(0, 8))

    ttk.Button(
        cont, text="Cerrar", command=dlg.destroy,
    ).pack(anchor="e", pady=(10, 0))

    # Escape y la X cierran igual que "Cerrar".
    dlg.bind("<Escape>", lambda _e: dlg.destroy())
    dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)

    _centrar_sobre(dlg, parent)

    # Modal: toma el foco y bloquea la ventana de atras hasta que se cierra.
    dlg.grab_set()
    dlg.focus_set()
    parent.wait_window(dlg)


def _centrar_sobre(dlg: tk.Toplevel, parent: tk.Misc) -> None:
    """Centra el dialogo sobre la ventana padre (o la pantalla si no hay una)."""
    dlg.update_idletasks()
    ancho = dlg.winfo_width()
    alto = dlg.winfo_height()
    try:
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = px + (pw - ancho) // 2
        y = py + (ph - alto) // 2
    except tk.TclError:
        x = (dlg.winfo_screenwidth() - ancho) // 2
        y = (dlg.winfo_screenheight() - alto) // 2
    dlg.geometry(f"+{max(x, 0)}+{max(y, 0)}")
