"""Ventana principal de la GUI: barra lateral + area de contenido.

PILOTO: por ahora solo tres herramientas. La consola sigue siendo la interfaz
completa (main.py) y no se toca; esto es una segunda puerta de entrada para
evaluar si vale la pena portar las 23.
"""

import tkinter as tk
from tkinter import ttk

from gui import theme
from gui.panels.sueldo import PanelSueldo
from gui.panels.rescate import PanelRescate
from gui.panels.espacio import PanelEspacio

PANELES = (PanelRescate, PanelSueldo, PanelEspacio)


class App(tk.Tk):
    def __init__(self, version: str = "") -> None:
        super().__init__()
        self.title("SalvaGodinez")
        self.geometry("1120x720")
        self.minsize(900, 600)
        theme.apply_theme(self)

        self._version = version
        self._panel_actual: ttk.Frame | None = None
        self._cache: dict[type, ttk.Frame] = {}
        self._botones: dict[type, ttk.Button] = {}

        self._construir()
        self._mostrar(PANELES[0])

    def _construir(self) -> None:
        contenedor = ttk.Frame(self)
        contenedor.pack(fill="both", expand=True)

        sidebar = ttk.Frame(contenedor, style="Sidebar.TFrame", width=232)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # OJO: los widgets tk clasicos (no ttk) NO aceptan pady como tupla en
        # el constructor; el espaciado asimetrico va en el pack().
        tk.Label(
            sidebar, text="SalvaGodinez", bg=theme.BG_SIDEBAR, fg="#ffffff",
            font=("Segoe UI", 15, "bold"), anchor="w", padx=20,
        ).pack(fill="x", pady=(22, 2))
        tk.Label(
            sidebar, text="La navaja suiza de la oficina", bg=theme.BG_SIDEBAR,
            fg=theme.FG_SIDEBAR, font=("Segoe UI", 9), anchor="w", padx=20,
        ).pack(fill="x", pady=(0, 18))

        for clase in PANELES:
            b = tk.Button(
                sidebar, text=clase.TITULO, anchor="w", padx=20, pady=11,
                bg=theme.BG_SIDEBAR, fg=theme.FG_SIDEBAR, bd=0,
                activebackground="#2b3242", activeforeground="#ffffff",
                highlightthickness=0, font=("Segoe UI", 11), cursor="hand2",
                command=lambda c=clase: self._mostrar(c),
            )
            b.pack(fill="x")
            self._botones[clase] = b

        if self._version:
            tk.Label(
                sidebar, text=f"v{self._version}", bg=theme.BG_SIDEBAR,
                fg="#6b7488", font=("Segoe UI", 9), anchor="w", padx=20,
            ).pack(side="bottom", fill="x", pady=(0, 14))

        self.contenido = ttk.Frame(contenedor, style="Panel.TFrame")
        self.contenido.pack(side="left", fill="both", expand=True)

    def _mostrar(self, clase) -> None:
        if self._panel_actual is not None:
            self._panel_actual.pack_forget()

        # Se cachea la instancia: recrear la pantalla en cada clic perderia lo
        # que el usuario ya habia escrito o buscado.
        panel = self._cache.get(clase)
        if panel is None:
            panel = clase(self.contenido)
            self._cache[clase] = panel

        panel.pack(fill="both", expand=True)
        self._panel_actual = panel

        for c, boton in self._botones.items():
            activo = c is clase
            boton.configure(
                bg="#2b3242" if activo else theme.BG_SIDEBAR,
                fg="#ffffff" if activo else theme.FG_SIDEBAR,
            )


def run(version: str = "") -> None:
    App(version).mainloop()
