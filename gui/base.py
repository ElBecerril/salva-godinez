"""Contrato base de las pantallas de la GUI y utilidades compartidas.

Aqui vive lo que NO debe reinventar cada pantalla: como se corre trabajo lento
sin congelar la ventana, y como se pide una confirmacion destructiva.
"""

import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from gui import theme


class ToolPanel(ttk.Frame):
    """Base de cada pantalla de herramienta.

    Cada subclase define TITULO y DESCRIPCION (texto plano, sin jerga: lo lee
    alguien que no sabe que es un directorio) e implementa build().

    REGLA DE ORO: una pantalla NUNCA reimplementa un calculo ni una operacion
    de archivos. Importa la funcion de logica del modulo de tools/ o searchers/
    correspondiente y solo la presenta. Si la logica que necesitas no existe
    todavia, se agrega en tools/, no aqui.
    """

    TITULO = "Herramienta"
    DESCRIPCION = ""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, style="Panel.TFrame", padding=(28, 22))
        self._jobs: list[threading.Thread] = []
        self._cabecera()
        self.body = ttk.Frame(self, style="Panel.TFrame")
        self.body.pack(fill="both", expand=True, pady=(18, 0))
        self.build()

    def _cabecera(self) -> None:
        ttk.Label(self, text=self.TITULO, style="Title.TLabel").pack(anchor="w")
        if not self.DESCRIPCION:
            return

        desc = ttk.Label(
            self, text=self.DESCRIPCION, style="Subtitle.TLabel", justify="left",
        )
        desc.pack(anchor="w", fill="x", pady=(6, 0))

        # wraplength en tkinter es un ancho FIJO en pixeles: si se deja un
        # numero a ojo, el texto se corta en ventanas angostas y deja hueco en
        # las anchas. Se recalcula con el ancho real del panel.
        def _reajustar(evento) -> None:
            # 56 = el padding horizontal del panel (28 por lado) + margen.
            ancho = max(evento.width - 72, 200)
            if desc.cget("wraplength") != ancho:
                desc.configure(wraplength=ancho)

        self.bind("<Configure>", _reajustar)

    def build(self) -> None:
        """Construye el contenido dentro de self.body. La implementa la subclase."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Trabajo en segundo plano
    # ------------------------------------------------------------------

    def run_async(self, work, on_done, on_progress=None, destructivo=False) -> None:
        """Corre work() en otro hilo y entrega el resultado en el hilo de la UI.

        Escanear el disco o hablar con PowerShell tarda segundos. Si eso corre
        en el hilo de tkinter, la ventana se congela y Windows la marca como
        "no responde", que para el usuario significa "se trabo, la mato".

        tkinter NO es thread-safe: desde el hilo de trabajo esta PROHIBIDO
        tocar widgets. Por eso el resultado viaja por una cola y se entrega en
        el hilo principal via after().

        Args:
            work: callable sin argumentos, se ejecuta en el hilo de trabajo.
                Si acepta un parametro, recibe un callback de progreso.
            on_done: callable(ok: bool, resultado). Corre en el hilo de la UI.
                Si ok es False, resultado es la excepcion.
            on_progress: opcional, callable(*args) invocado en el hilo de la UI
                cada vez que work reporta avance.
            destructivo: True si el trabajo BORRA o mueve archivos del usuario.
                Cambia dos cosas: el hilo deja de ser daemon (Python no termina
                hasta que acabe) y se le avisa a la ventana para que no se deje
                cerrar mientras corre. Un hilo daemon muere de golpe al cerrar
                la app, y morir a la mitad de un borrado deja al usuario con
                media operacion hecha y sin saberlo.
        """
        cola: queue.Queue = queue.Queue()

        def _progress(*args) -> None:
            cola.put(("progress", args))

        def _worker() -> None:
            try:
                # Una excepcion aqui NO debe matar la app: viaja a la UI como
                # dato y la pantalla decide como mostrarla.
                resultado = work(_progress) if on_progress else work()
                cola.put(("done", resultado))
            except Exception as e:  # noqa: BLE001 - se reporta, no se traga
                cola.put(("error", e))

        def _drenar() -> None:
            entregado = False
            try:
                while True:
                    tipo, carga = cola.get_nowait()
                    if tipo == "progress":
                        # No entregar progreso a un panel ya destruido, y que un
                        # on_progress que lance (p.ej. TclError si el widget
                        # murio a media operacion) NO mate el sondeo: si _drenar
                        # muere aqui, el "done" nunca llega y, en un trabajo
                        # destructivo, el contador se queda arriba y la ventana
                        # queda imposible de cerrar. El on_done tiene su propia
                        # red (baja el contador antes de pintar).
                        if on_progress and self.winfo_exists():
                            try:
                                on_progress(*carga)
                            except Exception:  # noqa: BLE001 - se ignora, no mata el sondeo
                                pass
                    else:
                        entregado = True
                        # Bajar el contador ANTES de on_done: si la pantalla
                        # falla al pintar el resultado, la ventana igual debe
                        # poder cerrarse. Y va aqui, en el hilo de la UI, no en
                        # el worker: llamar a winfo_toplevel() desde el hilo de
                        # trabajo revienta con "main thread is not in main loop"
                        # y dejaria el contador arriba para siempre — la ventana
                        # nunca se volveria a dejar cerrar.
                        if destructivo:
                            self._fin_destructivo(raiz)
                        # Si la pantalla ya no existe no hay a quien entregarle
                        # el resultado, pero el contador YA bajo arriba, que es
                        # lo que importa para poder cerrar la ventana.
                        if self.winfo_exists():
                            on_done(tipo == "done", carga)
            except queue.Empty:
                pass
            if not entregado:
                # Se sondea desde la ventana RAIZ, no desde el panel: si el
                # panel se destruye a medio trabajo, sus callbacks de after()
                # dejan de dispararse EN SILENCIO (no lanza excepcion) y el
                # contador se quedaria arriba para siempre, dejando la ventana
                # imposible de cerrar. La raiz sobrevive a los paneles.
                raiz.after(80, _drenar)

        # Se resuelve UNA vez, aqui en el hilo de la UI: el sondeo se agenda
        # sobre la raiz para que sobreviva a la destruccion del panel.
        raiz = self.winfo_toplevel()

        if destructivo:
            self._inicio_destructivo(raiz)

        hilo = threading.Thread(target=_worker, daemon=not destructivo)
        self._jobs.append(hilo)
        hilo.start()
        raiz.after(80, _drenar)

    # Contador de trabajos destructivos vivos, guardado en la ventana raiz para
    # que esta pueda consultarlo antes de dejarse cerrar. Ambos metodos corren
    # SIEMPRE en el hilo de la UI, asi que no hace falta candado.

    # La raiz llega por parametro, ya resuelta desde run_async: pedirla con
    # self.winfo_toplevel() fallaria justo en el caso que hay que cubrir, que
    # es el panel destruido a medio trabajo.

    def _inicio_destructivo(self, raiz) -> None:
        raiz.jobs_destructivos = getattr(raiz, "jobs_destructivos", 0) + 1

    def _fin_destructivo(self, raiz) -> None:
        raiz.jobs_destructivos = max(getattr(raiz, "jobs_destructivos", 1) - 1, 0)

    # ------------------------------------------------------------------
    # Confirmaciones
    # ------------------------------------------------------------------

    def confirmar_destructivo(self, titulo: str, mensaje: str) -> bool:
        """Pide confirmacion para algo que borra. El default SIEMPRE es No.

        No usar para preguntas normales: este dialogo es la ultima linea antes
        de tocar archivos del usuario. Ver las reglas del proyecto sobre
        operaciones destructivas.
        """
        return messagebox.askyesno(
            titulo, mensaje, icon="warning", default="no", parent=self,
        )

    def aviso(self, titulo: str, mensaje: str) -> None:
        messagebox.showinfo(titulo, mensaje, parent=self)

    def error(self, titulo: str, mensaje: str) -> None:
        messagebox.showerror(titulo, mensaje, parent=self)


class EstadoLabel(ttk.Label):
    """Etiqueta de estado que cambia de color segun el tipo de mensaje."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, text="", style="Panel.TLabel", wraplength=760, justify="left")

    def info(self, texto: str) -> None:
        self.configure(text=texto, foreground=theme.FG_SOFT)

    def exito(self, texto: str) -> None:
        self.configure(text=texto, foreground=theme.OK)

    def alerta(self, texto: str) -> None:
        self.configure(text=texto, foreground=theme.DANGER)

    def limpiar(self) -> None:
        self.configure(text="")
