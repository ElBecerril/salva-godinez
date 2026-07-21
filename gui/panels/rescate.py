"""Pantalla: Rescatar archivos perdidos.

La herramienta estrella de la app: alguien perdio un Excel o un Word y lo
quiere de vuelta. Esta pantalla NO reimplementa la busqueda ni la copia: solo
llama a las funciones puras de searchers/ y reporting/console_report.py y
presenta el resultado.

La combinacion de busquedas (papelera, temporales, recientes de Windows,
disco completo, copias de seguridad) es la misma que option_full_search() en
main.py: ambas llaman a searchers.full_search.search_everywhere(), que vive
en searchers/ y no tiene UI propia. Aqui esa llamada corre en segundo plano
via run_async() para no congelar la ventana.
"""

import tkinter as tk
from tkinter import filedialog, ttk

from gui.base import EstadoLabel, ToolPanel
from reporting.console_report import (
    compute_unique_dest_path,
    copy_restored_file,
    resolve_restore_source,
)
from searchers.full_search import (
    ETAPA_DISCO,
    ETAPA_PAPELERA,
    ETAPA_RECIENTES,
    ETAPA_SHADOW,
    ETAPA_TEMPORALES,
    search_everywhere,
)


class PanelRescate(ToolPanel):
    TITULO = "Recuperar archivos perdidos"
    DESCRIPCION = (
        "Escribe el nombre (o parte del nombre) de un archivo de Word o "
        "Excel que hayas perdido. Se busca en la papelera de reciclaje, en "
        "los archivos temporales, en lo reciente de Windows, en el disco "
        "completo y en las copias de seguridad automaticas de Windows."
    )

    def build(self) -> None:
        self._por_iid: dict[str, dict] = {}
        self._siguiente_iid = 0

        # --- Fila de busqueda -------------------------------------------------
        entrada = ttk.Frame(self.body, style="Panel.TFrame")
        entrada.pack(fill="x")

        ttk.Label(
            entrada, text="Nombre del archivo:", style="Panel.TLabel",
        ).pack(side="left")

        self._var_nombre = tk.StringVar()
        self._campo = ttk.Entry(entrada, textvariable=self._var_nombre, width=32)
        self._campo.pack(side="left", padx=(10, 10))
        self._campo.bind("<Return>", lambda _e: self._buscar())

        self._btn_buscar = ttk.Button(
            entrada, text="Buscar", style="Accent.TButton", command=self._buscar,
        )
        self._btn_buscar.pack(side="left")

        # --- Progreso -----------------------------------------------------
        self._barra = ttk.Progressbar(self.body, mode="indeterminate")

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(10, 6))

        # --- Recuperar -----------------------------------------------------
        # Se empaqueta ANTES que la tabla y anclado abajo: si se empaqueta
        # despues, la tabla (expand=True) se come el espacio y el boton
        # principal termina fuera de la ventana.
        acciones = ttk.Frame(self.body, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(12, 0))

        self._btn_recuperar = ttk.Button(
            acciones, text="Recuperar a...", style="Accent.TButton",
            command=self._recuperar, state="disabled",
        )
        self._btn_recuperar.pack(side="left")

        # --- Resultados -----------------------------------------------------
        tabla_frame = ttk.Frame(self.body, style="Panel.TFrame")
        tabla_frame.pack(fill="both", expand=True)

        columnas = ("nombre", "donde", "tamano", "fecha", "origen")
        self._tabla = ttk.Treeview(
            tabla_frame, columns=columnas, show="headings", height=8,
        )
        self._tabla.heading("nombre", text="Nombre")
        self._tabla.heading("donde", text="Donde estaba")
        self._tabla.heading("tamano", text="Tamano")
        self._tabla.heading("fecha", text="Fecha")
        self._tabla.heading("origen", text="Origen")
        # Los anchos suman ~700 para que quepan sin scroll horizontal en la
        # ventana por defecto; "donde" se estira con la ventana porque es la
        # columna con el texto mas largo.
        self._tabla.column("nombre", width=190, anchor="w", stretch=False)
        self._tabla.column("donde", width=250, anchor="w", stretch=True)
        self._tabla.column("tamano", width=80, anchor="e", stretch=False)
        self._tabla.column("fecha", width=110, anchor="w", stretch=False)
        self._tabla.column("origen", width=150, anchor="w", stretch=False)

        scroll_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=scroll_y.set)
        self._tabla.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="left", fill="y")

        self._tabla.bind("<<TreeviewSelect>>", self._on_seleccion)

    # ------------------------------------------------------------------
    # Busqueda
    # ------------------------------------------------------------------

    def _buscar(self) -> None:
        nombre = self._var_nombre.get().strip()
        if not nombre:
            self._estado.alerta("Escribe al menos una parte del nombre del archivo.")
            return

        # Se vacia aqui, ANTES de arrancar, porque de aqui en adelante la
        # tabla se va llenando conforme llegan resultados por etapa (via
        # on_progress) y no se debe volver a limpiar hasta la proxima
        # busqueda: limpiarla al terminar haria parpadear todo lo que el
        # usuario ya estaba viendo.
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
        self._por_iid.clear()
        self._siguiente_iid = 0
        self._btn_recuperar.configure(state="disabled")

        self._btn_buscar.configure(state="disabled")
        self._campo.configure(state="disabled")
        self._barra.pack(fill="x", pady=(4, 0))
        self._barra.start(12)
        self._estado.info("Buscando...")

        def trabajo(progreso):
            return _buscar_en_todos_lados(nombre, progreso)

        self.run_async(trabajo, self._on_busqueda_lista, on_progress=self._on_progreso)

    def _on_progreso(self, tipo: str, dato) -> None:
        # Los dos tipos de aviso que manda _buscar_en_todos_lados, ya en el
        # hilo de la UI (run_async los saca de la cola via after()): texto de
        # estado, o una tanda de resultados nuevos de una etapa que termino.
        if tipo == "estado":
            self._estado.info(dato)
        elif tipo == "resultados":
            self._agregar_resultados(dato)

    def _agregar_resultados(self, resultados: list[dict]) -> None:
        """Suma filas a la tabla sin borrar lo que ya habia. `resultados` ya
        viene deduplicado (searchers/full_search.py) contra todo lo visto en
        etapas anteriores, asi que aqui no hay que filtrar nada mas.
        """
        for r in resultados:
            iid = str(self._siguiente_iid)
            self._siguiente_iid += 1
            self._por_iid[iid] = r
            self._tabla.insert(
                "", "end", iid=iid,
                values=(
                    r.get("nombre", "?"),
                    r.get("ruta", "?"),
                    r.get("tamano", "?"),
                    r.get("fecha", "?"),
                    r.get("origen", "?"),
                ),
            )

    def _on_busqueda_lista(self, ok: bool, resultado) -> None:
        self._barra.stop()
        self._barra.pack_forget()
        self._btn_buscar.configure(state="normal")
        self._campo.configure(state="normal")

        if not ok:
            self._estado.alerta(
                "No se pudo completar la busqueda. Intenta de nuevo."
            )
            self.error(
                "Error de busqueda",
                "Algo salio mal mientras se buscaba el archivo. Intenta de nuevo.",
            )
            return

        # NO se vuelve a llenar la tabla aqui: las filas ya llegaron una por
        # una via _on_progreso conforme cada etapa termino (mismo orden y
        # mismo conjunto que este `resultado` final, es la misma lista que
        # arma search_everywhere). Volver a insertarlas duplicaria filas y
        # ademas tkinter revienta con "Item 0 already exists" si se reusan
        # los mismos iid.
        resultados = resultado
        if not resultados:
            self._estado.alerta("No se encontro ningun archivo con ese nombre.")
            return

        self._estado.exito(f"Se encontraron {len(resultados)} archivo(s).")

    # ------------------------------------------------------------------
    # Seleccion y recuperacion
    # ------------------------------------------------------------------

    def _on_seleccion(self, _evento=None) -> None:
        seleccion = self._tabla.selection()
        self._btn_recuperar.configure(state="normal" if seleccion else "disabled")

    def _recuperar(self) -> None:
        seleccion = self._tabla.selection()
        if not seleccion:
            return

        seleccionado = self._por_iid.get(seleccion[0])
        if seleccionado is None:
            return

        resuelto = resolve_restore_source(seleccionado)
        if not resuelto["ok"]:
            if resuelto["error"] == "file_gone":
                self.error(
                    "Ya no se puede recuperar",
                    "Este archivo ya no esta disponible para copiar. "
                    "Puede que se haya vaciado la papelera o que se haya "
                    f"borrado de forma definitiva. Ubicacion original: "
                    f"{resuelto.get('ruta_mostrada', '?')}",
                )
            else:
                self.error(
                    "Ya no se puede recuperar",
                    "Este resultado no tiene la informacion necesaria para "
                    "recuperarlo.",
                )
            return

        carpeta_destino = filedialog.askdirectory(
            parent=self, title="Elige donde guardar el archivo recuperado",
        )
        if not carpeta_destino:
            return

        dest_path = compute_unique_dest_path(carpeta_destino, resuelto["nombre"])
        resultado_copia = copy_restored_file(resuelto["source"], dest_path)

        if resultado_copia["ok"]:
            self._estado.exito(f"Archivo recuperado en: {resultado_copia['dest']}")
            self.aviso(
                "Archivo recuperado",
                f"El archivo quedo guardado en:\n\n{resultado_copia['dest']}",
            )
        else:
            self.error(
                "No se pudo copiar el archivo",
                "No se pudo guardar el archivo en la carpeta elegida. "
                "Revisa que haya espacio disponible y que tengas permiso "
                "para escribir ahi.",
            )


# ----------------------------------------------------------------------
# Trabajo de fondo (corre en el hilo de busqueda, NO toca widgets)
# ----------------------------------------------------------------------


# Texto que se muestra al ARRANCAR cada etapa. search_everywhere avisa el
# inicio y el fin de cada una, asi que aqui solo hace falta mapear etapa ->
# texto: esta pantalla NO sabe (ni debe saber) en que orden corren.
_ETIQUETAS_INICIO = {
    ETAPA_PAPELERA: "Buscando en la papelera de reciclaje...",
    ETAPA_TEMPORALES: "Buscando en los archivos temporales y de autorecuperacion...",
    ETAPA_RECIENTES: "Buscando en los archivos recientes de Windows...",
    ETAPA_DISCO: "Escaneando el disco completo, esto puede tardar...",
    ETAPA_SHADOW: (
        "Buscando en las copias de seguridad automaticas de Windows, "
        "esto puede tardar varios minutos..."
    ),
}


def _buscar_en_todos_lados(nombre: str, progreso) -> list[dict]:
    """Corre la busqueda completa compartida (searchers/full_search.py) y
    traduce el avance a mensajes para la pantalla.

    `progreso` es el `_progress` de run_async: cada llamada viaja por una
    cola y se entrega en el hilo de la UI via `_on_progreso(tipo, dato)`.
    Aqui se mandan dos tipos: ("estado", texto) para lo que hoy ya se
    mostraba, y ("resultados", lista) cuando una etapa termina y trae
    resultados nuevos para pintar en la tabla — asi la tabla se va llenando
    etapa por etapa en vez de esperar a que termine todo.
    """

    def _progreso_disco(ruta: str) -> None:
        texto = ruta if len(ruta) < 60 else "..." + ruta[-57:]
        progreso("estado", f"Escaneando: {texto}")

    def _etapa(etapa: str, cantidad, resultados=None) -> None:
        # cantidad is None => la etapa acaba de empezar.
        if cantidad is None:
            progreso("estado", _ETIQUETAS_INICIO.get(etapa, "Buscando..."))
        elif resultados:
            progreso("resultados", resultados)

    return search_everywhere(
        nombre,
        progress_callback=_progreso_disco,
        stage_callback=_etapa,
    )
