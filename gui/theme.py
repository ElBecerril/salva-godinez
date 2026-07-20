"""Paleta y estilos compartidos de la interfaz grafica.

Un solo lugar para colores y fuentes: si cada pantalla define lo suyo, la app
termina pareciendo cinco programas distintos pegados con cinta.

Criterio de diseno: el publico son oficinistas en monitores de oficina, muchas
veces malos y con brillo alto. Se prioriza CONTRASTE y tamano de letra legible
por encima de que se vea moderno.
"""

import tkinter as tk
from tkinter import ttk

# Paleta: fondo claro, texto casi negro. Nada de gris sobre gris.
BG = "#f4f5f7"          # fondo de ventana
BG_PANEL = "#ffffff"    # fondo del area de contenido
BG_SIDEBAR = "#1f2430"  # barra lateral oscura
FG = "#14171f"          # texto principal
FG_SOFT = "#5b6272"     # texto secundario
FG_SIDEBAR = "#c7ccd8"  # texto de la barra lateral
ACCENT = "#2563c4"      # azul de accion
ACCENT_TEXT = "#ffffff"
DANGER = "#b3261e"      # rojo: solo para acciones que borran
OK = "#1a7f45"          # verde: solo para confirmaciones de exito
BORDER = "#d6d9e0"

FONT_BASE = ("Segoe UI", 11)
FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_SUBTITLE = ("Segoe UI", 11)
FONT_SECTION = ("Segoe UI", 12, "bold")
FONT_MONO = ("Consolas", 10)


def apply_theme(root: tk.Misc) -> ttk.Style:
    """Aplica el tema a la ventana. Devuelve el Style ya configurado."""
    style = ttk.Style(root)

    # "clam" es el unico tema de ttk que respeta los colores que uno pide en
    # Windows; con el tema nativo, background de los widgets se ignora.
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=BG)

    style.configure(".", font=FONT_BASE, background=BG, foreground=FG)
    style.configure("TFrame", background=BG)
    style.configure("Panel.TFrame", background=BG_PANEL)
    style.configure("Sidebar.TFrame", background=BG_SIDEBAR)

    style.configure("TLabel", background=BG, foreground=FG, font=FONT_BASE)
    style.configure("Panel.TLabel", background=BG_PANEL, foreground=FG)
    style.configure("Title.TLabel", background=BG_PANEL, foreground=FG, font=FONT_TITLE)
    style.configure("Subtitle.TLabel", background=BG_PANEL, foreground=FG_SOFT, font=FONT_SUBTITLE)
    style.configure("Section.TLabel", background=BG_PANEL, foreground=FG, font=FONT_SECTION)
    style.configure("Ok.TLabel", background=BG_PANEL, foreground=OK, font=FONT_SECTION)
    style.configure("Danger.TLabel", background=BG_PANEL, foreground=DANGER, font=FONT_BASE)

    style.configure(
        "TButton", font=FONT_BASE, padding=(14, 8),
        background="#e4e7ee", foreground=FG, borderwidth=0,
    )
    style.map("TButton", background=[("active", "#d3d8e3"), ("disabled", "#eef0f4")])

    style.configure(
        "Accent.TButton", font=("Segoe UI", 11, "bold"), padding=(16, 9),
        background=ACCENT, foreground=ACCENT_TEXT, borderwidth=0,
    )
    style.map(
        "Accent.TButton",
        background=[("active", "#1d4fa0"), ("disabled", "#a9bbdd")],
        foreground=[("disabled", "#eaeef7")],
    )

    # Rojo: reservado para lo que borra. Que se vea distinto no es decoracion,
    # es la senal de que ese boton no es como los demas.
    style.configure(
        "Danger.TButton", font=("Segoe UI", 11, "bold"), padding=(16, 9),
        background=DANGER, foreground="#ffffff", borderwidth=0,
    )
    style.map(
        "Danger.TButton",
        background=[("active", "#8c1d17"), ("disabled", "#dfb3b0")],
        foreground=[("disabled", "#f6eceb")],
    )

    style.configure("TEntry", fieldbackground="#ffffff", padding=6)
    style.configure("TCheckbutton", background=BG_PANEL, foreground=FG, font=FONT_BASE)

    style.configure(
        "Treeview", background="#ffffff", fieldbackground="#ffffff",
        foreground=FG, rowheight=26, borderwidth=0,
    )
    style.configure(
        "Treeview.Heading", font=("Segoe UI", 10, "bold"),
        background="#e9ecf2", foreground=FG, padding=6,
    )
    style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "#ffffff")])

    style.configure("TProgressbar", background=ACCENT, troughcolor="#e2e5ec", borderwidth=0)

    return style
