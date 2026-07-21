"""Ventana principal de la GUI: barra lateral + area de contenido.

PILOTO: por ahora solo tres herramientas. La consola sigue siendo la interfaz
completa (main.py) y no se toca; esto es una segunda puerta de entrada para
evaluar si vale la pena portar las 23.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from gui import theme
from gui.panels.carpetas_red import PanelCarpetasRed
from gui.panels.comparar_excel import PanelCompararExcel
from gui.panels.compartir_impresora import PanelCompartirImpresora
from gui.panels.contrasenas import PanelContrasenas
from gui.panels.datos_equipo import PanelDatosEquipo
from gui.panels.desbloquear import PanelDesbloquear
from gui.panels.destrabar_impresora import PanelDestrabarImpresora
from gui.panels.espacio import PanelEspacio
from gui.panels.imagenes import PanelImagenes
from gui.panels.impresoras_duplicadas import PanelImpresorasDuplicadas
from gui.panels.limpiar_celdas import PanelLimpiarCeldas
from gui.panels.pdf import PanelPdf
from gui.panels.prestaciones import PanelPrestaciones
from gui.panels.probar_impresora import PanelProbarImpresora
from gui.panels.rescate import PanelRescate
from gui.panels.retenciones import PanelRetenciones
from gui.panels.sueldo import PanelSueldo
from gui.panels.unir_excel import PanelUnirExcel
from gui.panels.usb_estado import PanelUsbEstado
from gui.panels.usb_expulsar import PanelUsbExpulsar
from gui.panels.usb_respaldo import PanelUsbRespaldo
from gui.panels.usb_virus import PanelUsbVirus
from gui.panels.wifi import PanelWifi

# Las herramientas se agrupan igual que en el menu de la consola: con 23 en una
# lista plana nadie encuentra nada, y la agrupacion que ya existe es la que la
# gente conoce. Cada categoria es (titulo, [clases de panel]).
CATEGORIAS: list[tuple[str, list]] = [
    ("Archivos de Word y Excel", [
        PanelRescate, PanelLimpiarCeldas, PanelUnirExcel,
        PanelCompararExcel, PanelDesbloquear,
    ]),
    ("Impresoras", [
        PanelDestrabarImpresora, PanelImpresorasDuplicadas,
        PanelProbarImpresora, PanelCompartirImpresora,
    ]),
    ("USB, WiFi y Red", [
        PanelUsbVirus, PanelUsbEstado, PanelUsbRespaldo,
        PanelWifi, PanelUsbExpulsar, PanelCarpetasRed,
    ]),
    ("Limpieza y mantenimiento", [
        PanelDatosEquipo, PanelEspacio,
    ]),
    ("Calculadoras y herramientas", [
        PanelPdf, PanelContrasenas, PanelPrestaciones,
        PanelImagenes, PanelSueldo, PanelRetenciones,
    ]),
]


def _todos_los_paneles() -> list:
    return [clase for _, clases in CATEGORIAS for clase in clases]


class App(tk.Tk):
    def __init__(self, version: str = "") -> None:
        super().__init__()
        self.title("SalvaGodinez")
        self._ajustar_tamano()
        theme.apply_theme(self)

        self._version = version
        self._panel_actual: ttk.Frame | None = None
        self._cache: dict[type, ttk.Frame] = {}
        self._botones: dict[type, ttk.Button] = {}

        # Trabajos destructivos vivos. Los paneles lo suben y bajan via
        # run_async(destructivo=True); aqui solo se consulta al cerrar.
        self.jobs_destructivos = 0
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

        # Por que se cerro la ventana: "salir" o "consola". main.py lo usa para
        # decidir si abre el menu de texto o termina.
        self.salida = "salir"

        self._construir()
        self._mostrar(_todos_los_paneles()[0])

    def _ajustar_tamano(self) -> None:
        """Elige un tamano que SI quepa en la pantalla, y centra la ventana.

        El tamano comodo es 1120x720, pero en una laptop de oficina de 1366x768
        una ventana de 720 de alto mas la barra de titulo (~40) y la barra de
        tareas (~48) no cabe: la ventana se dibuja mas alta que el area util y
        el boton de accion de abajo queda cortado. Se limita al espacio real de
        la pantalla, dejando margen para esas dos barras.
        """
        pref_w, pref_h = 1120, 720
        pantalla_w = self.winfo_screenwidth()
        pantalla_h = self.winfo_screenheight()

        ancho = min(pref_w, pantalla_w - 40)
        alto = min(pref_h, pantalla_h - 96)

        x = max((pantalla_w - ancho) // 2, 0)
        # El -48 sube la ventana medio ancho de la barra de tareas para que no
        # quede pegada a ella.
        y = max((pantalla_h - alto - 48) // 2, 0)

        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        # El minimo tambien baja: 600 de alto era mas de lo que cabe con la
        # ventana ya ajustada en pantallas chicas.
        self.minsize(900, min(560, alto))

    def _al_cerrar(self) -> None:
        """No dejar cerrar la ventana a media operacion de borrado.

        Cerrar mientras se borra dejaria la limpieza a la mitad sin que el
        usuario se entere de que quedo incompleta.
        """
        if getattr(self, "jobs_destructivos", 0) > 0:
            messagebox.showwarning(
                "Espera un momento",
                "Todavia se estan limpiando archivos.\n\n"
                "Cerrar ahora dejaria la limpieza a medias. En cuanto termine "
                "puedes cerrar sin problema.",
                parent=self,
            )
            return
        self.destroy()

    def _conectar_rueda(self, lienzo, widgets) -> None:
        """Hace que la rueda del mouse desplace la lista de herramientas.

        Un area con scroll que no responde a la rueda se siente rota: la gente
        gira la rueda antes de buscar una barra con el cursor.

        Windows manda <MouseWheel> con delta multiplo de 120; X11 manda
        Button-4/5. Se atienden los dos porque el desarrollo es en Linux y la
        app corre en Windows.
        """
        def _scroll(delta: int) -> None:
            if lienzo.winfo_exists():
                lienzo.yview_scroll(delta, "units")

        def _windows(evento):
            _scroll(-1 if evento.delta > 0 else 1)

        for w in widgets:
            w.bind("<MouseWheel>", _windows, add="+")
            w.bind("<Button-4>", lambda _e: _scroll(-1), add="+")
            w.bind("<Button-5>", lambda _e: _scroll(1), add="+")

    def _volver_a_consola(self) -> None:
        """Cierra la ventana y le pide a main.py que abra el menu de texto."""
        if getattr(self, "jobs_destructivos", 0) > 0:
            messagebox.showwarning(
                "Espera un momento",
                "Todavia se estan limpiando archivos.\n\n"
                "En cuanto termine puedes cambiar de modo sin problema.",
                parent=self,
            )
            return
        self.salida = "consola"
        self.destroy()

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

        # Lo del fondo se empaqueta ANTES: si no, la lista (que expande) se come
        # el espacio y el boton de volver al modo texto queda fuera de la vista.
        self._pie_sidebar = ttk.Frame(sidebar, style="Sidebar.TFrame")
        self._pie_sidebar.pack(side="bottom", fill="x")

        # Con 23 herramientas la barra no cabe en pantallas chicas de oficina,
        # asi que va dentro de un area con scroll.
        area = ttk.Frame(sidebar, style="Sidebar.TFrame")
        area.pack(side="top", fill="both", expand=True)

        # La barra se empaqueta PRIMERO para que se reserve su ancho. Si se
        # empaqueta despues del lienzo, este ya ocupo todo y la barra queda
        # fuera de la vista: hay scroll, pero invisible.
        barra = ttk.Scrollbar(area, orient="vertical")
        barra.pack(side="right", fill="y")

        lienzo = tk.Canvas(area, bg=theme.BG_SIDEBAR, highlightthickness=0)
        lienzo.pack(side="left", fill="both", expand=True)
        barra.configure(command=lienzo.yview)
        lienzo.configure(yscrollcommand=barra.set)

        lista = tk.Frame(lienzo, bg=theme.BG_SIDEBAR)
        ventana = lienzo.create_window((0, 0), window=lista, anchor="nw")

        def _al_cambiar_lista(_e=None) -> None:
            lienzo.configure(scrollregion=lienzo.bbox("all"))

        def _al_cambiar_lienzo(evento) -> None:
            # La lista debe medir lo mismo que el lienzo (ya sin la barra), o
            # los botones se cortan a lo ancho.
            lienzo.itemconfigure(ventana, width=evento.width)

        _con_rueda = [lienzo, lista]

        lista.bind("<Configure>", _al_cambiar_lista)
        lienzo.bind("<Configure>", _al_cambiar_lienzo)
        self._lienzo_sidebar = lienzo

        for titulo, clases in CATEGORIAS:
            if not clases:
                continue
            tk.Label(
                lista, text=titulo.upper(), bg=theme.BG_SIDEBAR, fg="#6b7488",
                font=("Segoe UI", 8, "bold"), anchor="w", padx=20,
            ).pack(fill="x", pady=(14, 4))

            for clase in clases:
                b = tk.Button(
                    lista, text=clase.TITULO, anchor="w", padx=20, pady=8,
                    bg=theme.BG_SIDEBAR, fg=theme.FG_SIDEBAR, bd=0,
                    activebackground="#2b3242", activeforeground="#ffffff",
                    highlightthickness=0, font=("Segoe UI", 10), cursor="hand2",
                    wraplength=200, justify="left",
                    command=lambda c=clase: self._mostrar(c),
                )
                b.pack(fill="x")
                self._botones[clase] = b
                _con_rueda.append(b)

        if self._version:
            tk.Label(
                sidebar, text=f"v{self._version}", bg=theme.BG_SIDEBAR,
                fg="#6b7488", font=("Segoe UI", 9), anchor="w", padx=20,
            ).pack(in_=self._pie_sidebar, side="bottom", fill="x", pady=(0, 14))

        # Puerta de regreso al menu de texto. Va al fondo de la barra porque no
        # es una herramienta; es cambiar de modo.
        tk.Button(
            sidebar, text="Volver al modo texto", anchor="w", padx=20, pady=8,
            bg=theme.BG_SIDEBAR, fg=theme.FG_SIDEBAR, bd=0,
            activebackground="#2b3242", activeforeground="#ffffff",
            highlightthickness=0, font=("Segoe UI", 10), cursor="hand2",
            command=self._volver_a_consola,
        ).pack(in_=self._pie_sidebar, side="bottom", fill="x", pady=(0, 4))

        self._conectar_rueda(lienzo, _con_rueda + [etiqueta for etiqueta in lista.winfo_children()])

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


def run(version: str = "") -> str:
    """Abre la ventana principal.

    Returns:
        "salir" si el usuario cerro la app, o "consola" si pidio volver al
        menu de texto.
    """
    app = App(version)
    app.mainloop()
    return getattr(app, "salida", "salir")
