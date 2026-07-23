"""Pantalla: Herramientas PDF (unir, dividir, rotar, proteger, convertir...).

Es la herramienta mas grande de la app (10 operaciones), asi que la pantalla
NO puede ser ni 10 botones sueltos ni un formulario gigante con todos los
campos a la vez. Se eligio: lista de operaciones a la izquierda + un
formulario a la derecha que cambia segun cual este seleccionada. Cada
formulario muestra SOLO los campos que esa operacion necesita (por ejemplo,
"Rotar" no muestra el campo de contrasena, y "Proteger" no muestra el de
angulo). Es el mismo patron mental que un asistente de instalacion: una tarea
a la vez, sin que el resto distraiga.

Ninguna operacion se reimplementa aqui: todas llaman a las funciones puras de
tools/pdf_tools.py (las *_do y los helpers de apertura/parseo) y solo
presentan resultado. El flujo de cada una imita a pdf_menu() de la consola.
"""

import os
import tkinter as tk
from tkinter import filedialog, ttk

from gui import theme
from gui.base import EstadoLabel, ToolPanel
from tools.pdf_tools import (
    _import_docx,
    _import_pillow,
    _import_pymupdf,
    clean_metadata_do,
    delete_pages_do,
    extract_text_do,
    get_pdf_metadata_fields,
    images_to_pdf_do,
    merge_pdfs_do,
    open_pdf,
    parse_dpi,
    parse_page_selection,
    parse_reorder,
    pdf_to_images_do,
    pdf_to_word_do,
    protect_pdf_do,
    read_pdf_for_protect,
    read_pdf_total,
    reorder_pages_do,
    rotate_pages_do,
    split_pdf_do,
    unprotect_pdf_do,
)

_FILTRO_PDF = [("Archivos PDF", "*.pdf")]
_EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _imagenes(n: int) -> str:
    """'1 imagen' / '3 imagenes' — evita el '1 imagenes' que se leia raro."""
    return f"{n} imagen" if n == 1 else f"{n} imagenes"

# Codigos de error que devuelven open_pdf / read_pdf_total / read_pdf_for_protect
# cuando el problema esta en ABRIR el archivo (no en guardar el resultado).
_CODIGOS_APERTURA = {
    "no_pypdf", "not_found", "corrupt", "read_error", "encrypted",
    "wrong_password", "wrong_password_or_corrupt",
}

_MENSAJES_APERTURA = {
    "no_pypdf": "Falta instalar la libreria pypdf. Ejecuta: pip install pypdf",
    "not_found": "No se encontro el archivo.",
    "corrupt": "El archivo esta danado o no es un PDF valido.",
    "read_error": "El archivo esta danado o no es un PDF valido.",
    "encrypted": (
        "Este PDF esta protegido con contrasena. Usa primero la operacion "
        "'Proteger / Desproteger PDF' para quitarle la proteccion."
    ),
    "wrong_password": "La contrasena no es correcta.",
    "wrong_password_or_corrupt": "La contrasena no es correcta, o el archivo esta danado.",
}


class PanelPdf(ToolPanel):
    TITULO = "Editar PDF"
    DESCRIPCION = (
        "Elige una operacion de la lista. Cada una te pide solo lo que "
        "necesita: nunca se sobrescribe tu archivo original, siempre se "
        "crea una copia nueva."
    )

    # (id interno, texto de la lista) — mismo orden que pdf_menu() en consola.
    OPERACIONES = [
        ("unir", "Unir PDFs"),
        ("dividir", "Dividir PDF"),
        ("rotar", "Rotar paginas"),
        ("eliminar", "Eliminar paginas"),
        ("reordenar", "Reordenar paginas"),
        ("extraer", "Extraer texto"),
        ("img_a_pdf", "Imagenes a PDF"),
        ("pdf_a_img", "PDF a imagenes"),
        ("pdf_a_word", "PDF a Word"),
        ("proteger", "Proteger / desproteger PDF"),
        ("metadatos", "Ver / limpiar metadatos"),
    ]

    # ------------------------------------------------------------------
    # Armado de la pantalla
    # ------------------------------------------------------------------

    def build(self) -> None:
        # El estado se ancla ABAJO y se empaqueta ANTES que el contenido
        # principal: si va despues, el area de la lista+formulario (que
        # expande) lo saca de la ventana.
        self._estado = EstadoLabel(self.body)
        self._estado.pack(side="bottom", anchor="w", fill="x", pady=(10, 0))

        cont = ttk.Frame(self.body, style="Panel.TFrame")
        cont.pack(fill="both", expand=True)

        # --- Columna izquierda: lista de operaciones ------------------
        col_lista = ttk.Frame(cont, style="Panel.TFrame")
        col_lista.pack(side="left", fill="y", padx=(0, 20))

        ttk.Label(col_lista, text="Operacion:", style="Section.TLabel").pack(
            anchor="w", pady=(0, 8)
        )

        self._lista = tk.Listbox(
            col_lista, height=len(self.OPERACIONES), width=28,
            exportselection=False, activestyle="none",
            bg="#ffffff", fg=theme.FG, font=theme.FONT_BASE,
            selectbackground=theme.ACCENT, selectforeground="#ffffff",
            borderwidth=1, relief="solid", highlightthickness=0,
        )
        # PyMuPDF es opcional (no siempre viaja en el .exe). Se checa UNA vez
        # aqui para: (1) marcar "PDF a imagenes" como no disponible en la lista,
        # y (2) que su formulario avise de entrada en vez de dejar al usuario
        # elegir archivo, formato, resolucion y carpeta para recien entonces
        # decirle que no se puede.
        self._pymupdf_ok = _import_pymupdf() is not None
        # PDF a Word necesita PyMuPDF (leer el PDF) Y python-docx (crear el .docx).
        self._word_ok = self._pymupdf_ok and _import_docx() is not None

        for _id, etiqueta in self.OPERACIONES:
            if _id == "pdf_a_img" and not self._pymupdf_ok:
                etiqueta = f"{etiqueta} (no disponible)"
            elif _id == "pdf_a_word" and not self._word_ok:
                etiqueta = f"{etiqueta} (no disponible)"
            self._lista.insert("end", etiqueta)
        self._lista.pack(fill="y")
        self._lista.bind("<<ListboxSelect>>", self._on_operacion)

        # --- Columna derecha: formulario de la operacion elegida ------
        self._form_frame = ttk.Frame(cont, style="Panel.TFrame")
        self._form_frame.pack(side="left", fill="both", expand=True)

        self._constructores = {
            "unir": self._form_unir,
            "dividir": self._form_dividir,
            "rotar": self._form_rotar,
            "eliminar": self._form_eliminar,
            "reordenar": self._form_reordenar,
            "extraer": self._form_extraer,
            "img_a_pdf": self._form_img_a_pdf,
            "pdf_a_img": self._form_pdf_a_img,
            "pdf_a_word": self._form_pdf_a_word,
            "proteger": self._form_proteger,
            "metadatos": self._form_metadatos,
        }

        self._lista.selection_set(0)
        self._mostrar_operacion(self.OPERACIONES[0][0])

    def _on_operacion(self, _evento=None) -> None:
        seleccion = self._lista.curselection()
        if not seleccion:
            return
        op_id = self.OPERACIONES[seleccion[0]][0]
        self._estado.limpiar()
        self._mostrar_operacion(op_id)

    def _mostrar_operacion(self, op_id: str) -> None:
        for widget in self._form_frame.winfo_children():
            widget.destroy()
        self._constructores[op_id](self._form_frame)

    # ------------------------------------------------------------------
    # Helpers compartidos por todos los formularios
    # ------------------------------------------------------------------

    def _texto_error_apertura(self, resultado: dict) -> str:
        return _MENSAJES_APERTURA.get(
            resultado.get("error"), "No se pudo abrir el archivo."
        )

    def _texto_error(self, resultado: dict, generico: str = None) -> str:
        """Traduce el dict de error de un *_do a un mensaje para el usuario.

        Si el error vino de la apertura (archivo corrupto/cifrado/etc.) usa
        ese mensaje especifico; si vino de guardar el resultado, usa uno
        generico (guardar casi siempre falla por permisos o espacio).
        """
        if resultado.get("error") in _CODIGOS_APERTURA:
            return self._texto_error_apertura(resultado)
        return generico or (
            "No se pudo guardar el archivo. Revisa permisos o espacio en disco."
        )

    def _ejecutar(self, boton: ttk.Button, trabajo, al_terminar) -> None:
        """Corre `trabajo` en segundo plano y reactiva `boton` al terminar.

        `trabajo` no debe tocar widgets (corre en otro hilo). `al_terminar`
        recibe el dict de resultado y corre en el hilo de la UI.
        """
        self._estado.info("Procesando...")
        boton.configure(state="disabled")

        def _done(ok: bool, resultado) -> None:
            if boton.winfo_exists():
                boton.configure(state="normal")
            if not ok:
                self._estado.alerta("Ocurrio un error inesperado.")
                self.error(
                    "Error inesperado",
                    "Algo salio mal durante la operacion. Intenta de nuevo.",
                )
                return
            al_terminar(resultado)

        self.run_async(trabajo, _done)

    def _seccion(self, frame, titulo: str, descripcion: str) -> None:
        ttk.Label(frame, text=titulo, style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            frame, text=descripcion, style="Subtitle.TLabel",
            wraplength=520, justify="left",
        ).pack(anchor="w", pady=(2, 12))

    def _boton_accion(self, frame, texto: str) -> ttk.Button:
        acciones = ttk.Frame(frame, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(14, 0))
        boton = ttk.Button(acciones, text=texto, style="Accent.TButton")
        boton.pack(side="left")
        return boton

    # ------------------------------------------------------------------
    # 1. Unir PDFs
    # ------------------------------------------------------------------

    def _form_unir(self, frame) -> None:
        self._seccion(
            frame, "Unir PDFs",
            "Agrega dos o mas archivos PDF; se unen en el orden de la lista.",
        )
        estado_local = {"paths": []}

        btn = self._boton_accion(frame, "Unir y guardar como...")

        botones = ttk.Frame(frame, style="Panel.TFrame")
        botones.pack(fill="x", pady=(0, 8))

        lista_frame = ttk.Frame(frame, style="Panel.TFrame")
        lista_frame.pack(fill="both", expand=True)

        lb = tk.Listbox(
            lista_frame, height=8, exportselection=False,
            bg="#ffffff", fg=theme.FG, borderwidth=1, relief="solid",
        )
        lb.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(lista_frame, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=scroll.set)
        scroll.pack(side="left", fill="y")

        def _agregar() -> None:
            nuevos = filedialog.askopenfilenames(
                parent=self, title="Elige PDFs para unir", filetypes=_FILTRO_PDF,
            )
            for p in nuevos:
                estado_local["paths"].append(p)
                lb.insert("end", os.path.basename(p))
            self._estado.limpiar()

        def _quitar() -> None:
            seleccion = lb.curselection()
            for i in reversed(seleccion):
                lb.delete(i)
                del estado_local["paths"][i]

        ttk.Button(botones, text="Agregar PDFs...", command=_agregar).pack(side="left")
        ttk.Button(
            botones, text="Quitar seleccionado", command=_quitar,
        ).pack(side="left", padx=(8, 0))

        def _unir() -> None:
            paths = list(estado_local["paths"])
            if len(paths) < 2:
                self._estado.alerta("Agrega al menos 2 PDFs para unir.")
                return
            salida = filedialog.asksaveasfilename(
                parent=self, title="Guardar PDF unido como",
                defaultextension=".pdf", filetypes=_FILTRO_PDF,
                initialfile="unido.pdf",
            )
            if not salida:
                return

            # overwrite=True: el dialogo nativo ya pregunto "reemplazar?" si el
            # archivo existia y el usuario confirmo, asi que se escribe en el
            # nombre exacto en vez de renombrar a "_1". merge_pdfs_do respeta
            # igual el guard de no pisar un PDF de entrada (same_as_input).
            def trabajo():
                return merge_pdfs_do(paths, salida, overwrite=True)

            def al_terminar(resultado) -> None:
                if not resultado.get("ok"):
                    if resultado.get("error") == "same_as_input":
                        self.error(
                            "No se pudo unir",
                            "El archivo de salida no puede ser igual a uno "
                            "de los PDF de entrada.",
                        )
                    elif resultado.get("error") == "no_pages":
                        self.error(
                            "No se pudo unir",
                            "No se pudo leer ninguna pagina de los PDF "
                            "elegidos (pueden estar danados o cifrados).",
                        )
                    else:
                        self.error("No se pudo unir", self._texto_error(resultado))
                    self._estado.alerta("No se pudo unir los PDF.")
                    return
                extra = ""
                if resultado.get("warnings"):
                    extra = "\n\nSe omitieron algunos archivos:\n" + "\n".join(
                        resultado["warnings"]
                    )
                self._estado.exito(
                    f"PDF unido creado: {resultado['output']} "
                    f"({resultado['total_pages']} paginas)"
                )
                self.aviso(
                    "PDF unido",
                    f"Se creo:\n\n{resultado['output']}\n\n"
                    f"{resultado['total_pages']} paginas en total.{extra}",
                )

            self._ejecutar(btn, trabajo, al_terminar)

        btn.configure(command=_unir)

    # ------------------------------------------------------------------
    # 2. Dividir PDF
    # ------------------------------------------------------------------

    def _form_dividir(self, frame) -> None:
        self._seccion(
            frame, "Dividir PDF",
            "Separa un PDF en paginas individuales, o extrae solo un rango.",
        )
        estado_local = {"path": None, "total": None}

        btn = self._boton_accion(frame, "Dividir...")

        archivo_lbl = ttk.Label(frame, text="Ningun PDF elegido.", style="Panel.TLabel")
        archivo_lbl.pack(anchor="w", pady=(0, 10))

        def _elegir() -> None:
            path = filedialog.askopenfilename(
                parent=self, title="Elige el PDF a dividir", filetypes=_FILTRO_PDF,
            )
            if not path:
                return
            resultado = read_pdf_total(path)
            if not resultado["ok"]:
                self.error("No se pudo abrir el PDF", self._texto_error_apertura(resultado))
                return
            estado_local["path"] = path
            estado_local["total"] = resultado["total"]
            archivo_lbl.configure(
                text=f"{os.path.basename(path)} ({resultado['total']} paginas)"
            )
            self._estado.limpiar()

        ttk.Button(frame, text="Elegir PDF...", command=_elegir).pack(anchor="w")

        modo_var = tk.StringVar(value="individual")
        ttk.Radiobutton(
            frame, text="Una pagina por archivo", variable=modo_var, value="individual",
        ).pack(anchor="w", pady=(12, 0))
        ttk.Radiobutton(
            frame, text="Extraer un rango de paginas", variable=modo_var, value="rango",
        ).pack(anchor="w")

        rango_frame = ttk.Frame(frame, style="Panel.TFrame")
        rango_frame.pack(anchor="w", pady=(6, 0))
        ttk.Label(rango_frame, text="Rango (ej: 2-4):", style="Panel.TLabel").pack(side="left")
        rango_var = tk.StringVar()
        ttk.Entry(rango_frame, textvariable=rango_var, width=10).pack(side="left", padx=(8, 0))

        def _dividir() -> None:
            if not estado_local["path"]:
                self._estado.alerta("Primero elige un PDF.")
                return
            modo = modo_var.get()
            rango = rango_var.get().strip()
            if modo == "rango" and not rango:
                self._estado.alerta("Escribe un rango, por ejemplo 2-4.")
                return
            carpeta = filedialog.askdirectory(
                parent=self, title="Elige la carpeta de salida",
            )
            if not carpeta:
                return

            path, total = estado_local["path"], estado_local["total"]

            def trabajo():
                apertura = read_pdf_total(path)
                if not apertura["ok"]:
                    return apertura
                if modo == "individual":
                    return split_pdf_do(apertura["pypdf"], apertura["reader"], path, carpeta, modo)
                return split_pdf_do(apertura["pypdf"], apertura["reader"], path, carpeta, modo, rango)

            def al_terminar(resultado) -> None:
                if not resultado.get("ok"):
                    err = resultado.get("error")
                    if err == "invalid_range":
                        self.error(
                            "Rango invalido",
                            f"El PDF tiene paginas 1-{resultado.get('total', total)}.",
                        )
                    elif err == "invalid_format":
                        self.error(
                            "Formato invalido",
                            "Escribe el rango como inicio-fin, por ejemplo 2-4.",
                        )
                    else:
                        self.error("No se pudo dividir", self._texto_error(resultado))
                    self._estado.alerta("No se pudo dividir el PDF.")
                    return
                if resultado["mode"] == "individual":
                    self._estado.exito(
                        f"{resultado['total']} archivos creados en: {resultado['output_dir']}"
                    )
                    self.aviso(
                        "PDF dividido",
                        f"Se crearon {resultado['total']} archivos en:\n\n"
                        f"{resultado['output_dir']}",
                    )
                else:
                    self._estado.exito(f"PDF creado: {resultado['output']}")
                    self.aviso(
                        "PDF dividido",
                        f"Se creo:\n\n{resultado['output']}\n\n"
                        f"{resultado['pages']} paginas.",
                    )

            self._ejecutar(btn, trabajo, al_terminar)

        btn.configure(command=_dividir)

    # ------------------------------------------------------------------
    # 3. Rotar paginas
    # ------------------------------------------------------------------

    def _form_rotar(self, frame) -> None:
        self._seccion(
            frame, "Rotar paginas",
            "Rota todas las paginas de un PDF, o solo algunas.",
        )
        estado_local = {"path": None, "total": None}

        btn = self._boton_accion(frame, "Rotar y guardar copia")

        archivo_lbl = ttk.Label(frame, text="Ningun PDF elegido.", style="Panel.TLabel")
        archivo_lbl.pack(anchor="w", pady=(0, 10))

        def _elegir() -> None:
            path = filedialog.askopenfilename(
                parent=self, title="Elige el PDF a rotar", filetypes=_FILTRO_PDF,
            )
            if not path:
                return
            resultado = open_pdf(path)
            if not resultado["ok"]:
                self.error("No se pudo abrir el PDF", self._texto_error_apertura(resultado))
                return
            estado_local["path"] = path
            estado_local["total"] = len(resultado["reader"].pages)
            archivo_lbl.configure(
                text=f"{os.path.basename(path)} ({estado_local['total']} paginas)"
            )
            self._estado.limpiar()

        ttk.Button(frame, text="Elegir PDF...", command=_elegir).pack(anchor="w")

        angulo_var = tk.StringVar(value="90")
        angulo_frame = ttk.Frame(frame, style="Panel.TFrame")
        angulo_frame.pack(anchor="w", pady=(12, 0))
        ttk.Label(angulo_frame, text="Angulo:", style="Panel.TLabel").pack(side="left")
        for valor in ("90", "180", "270"):
            ttk.Radiobutton(
                angulo_frame, text=f"{valor} grados", variable=angulo_var, value=valor,
            ).pack(side="left", padx=(8, 0))

        alcance_var = tk.StringVar(value="todas")
        ttk.Radiobutton(
            frame, text="Rotar todas las paginas", variable=alcance_var, value="todas",
        ).pack(anchor="w", pady=(12, 0))
        ttk.Radiobutton(
            frame, text="Elegir paginas", variable=alcance_var, value="elegir",
        ).pack(anchor="w")

        seleccion_frame = ttk.Frame(frame, style="Panel.TFrame")
        seleccion_frame.pack(anchor="w", pady=(6, 0))
        ttk.Label(
            seleccion_frame, text="Paginas (ej: 1,3,5 o 2-4):", style="Panel.TLabel",
        ).pack(side="left")
        seleccion_var = tk.StringVar()
        ttk.Entry(seleccion_frame, textvariable=seleccion_var, width=16).pack(
            side="left", padx=(8, 0)
        )

        def _rotar() -> None:
            if not estado_local["path"]:
                self._estado.alerta("Primero elige un PDF.")
                return
            path, total = estado_local["path"], estado_local["total"]
            angulo = int(angulo_var.get())

            if alcance_var.get() == "todas":
                indices = set(range(total))
            else:
                indices, error = parse_page_selection(seleccion_var.get().strip(), total)
                if indices is None:
                    self._estado.alerta(error)
                    return

            def trabajo():
                apertura = open_pdf(path)
                if not apertura["ok"]:
                    return apertura
                return rotate_pages_do(apertura["pypdf"], apertura["reader"], path, angulo, indices)

            def al_terminar(resultado) -> None:
                if not resultado.get("ok"):
                    self.error("No se pudo rotar", self._texto_error(resultado))
                    self._estado.alerta("No se pudo rotar el PDF.")
                    return
                self._estado.exito(f"PDF rotado creado: {resultado['output']}")
                self.aviso(
                    "PDF rotado",
                    f"Se creo:\n\n{resultado['output']}\n\n"
                    f"{resultado['rotated_count']} paginas rotadas {angulo} grados.",
                )

            self._ejecutar(btn, trabajo, al_terminar)

        btn.configure(command=_rotar)

    # ------------------------------------------------------------------
    # 4. Eliminar paginas
    # ------------------------------------------------------------------

    def _form_eliminar(self, frame) -> None:
        self._seccion(
            frame, "Eliminar paginas",
            "Quita paginas especificas de un PDF (no puedes quitarlas todas).",
        )
        estado_local = {"path": None, "total": None}

        btn = self._boton_accion(frame, "Eliminar y guardar copia")

        archivo_lbl = ttk.Label(frame, text="Ningun PDF elegido.", style="Panel.TLabel")
        archivo_lbl.pack(anchor="w", pady=(0, 10))

        def _elegir() -> None:
            path = filedialog.askopenfilename(
                parent=self, title="Elige el PDF", filetypes=_FILTRO_PDF,
            )
            if not path:
                return
            resultado = open_pdf(path)
            if not resultado["ok"]:
                self.error("No se pudo abrir el PDF", self._texto_error_apertura(resultado))
                return
            estado_local["path"] = path
            estado_local["total"] = len(resultado["reader"].pages)
            archivo_lbl.configure(
                text=f"{os.path.basename(path)} ({estado_local['total']} paginas)"
            )
            self._estado.limpiar()

        ttk.Button(frame, text="Elegir PDF...", command=_elegir).pack(anchor="w")

        seleccion_frame = ttk.Frame(frame, style="Panel.TFrame")
        seleccion_frame.pack(anchor="w", pady=(12, 0))
        ttk.Label(
            seleccion_frame, text="Paginas a eliminar (ej: 1,3,5 o 2-4):",
            style="Panel.TLabel",
        ).pack(anchor="w")
        seleccion_var = tk.StringVar()
        ttk.Entry(seleccion_frame, textvariable=seleccion_var, width=24).pack(
            anchor="w", pady=(4, 0)
        )

        def _eliminar() -> None:
            if not estado_local["path"]:
                self._estado.alerta("Primero elige un PDF.")
                return
            path, total = estado_local["path"], estado_local["total"]
            seleccion = seleccion_var.get().strip()
            if not seleccion:
                self._estado.alerta("Escribe que paginas eliminar.")
                return
            indices, error = parse_page_selection(seleccion, total)
            if indices is None:
                self._estado.alerta(error)
                return
            if len(indices) >= total:
                self._estado.alerta("No puedes eliminar todas las paginas del PDF.")
                return

            def trabajo():
                apertura = open_pdf(path)
                if not apertura["ok"]:
                    return apertura
                return delete_pages_do(apertura["pypdf"], apertura["reader"], path, indices)

            def al_terminar(resultado) -> None:
                if not resultado.get("ok"):
                    self.error("No se pudo editar el PDF", self._texto_error(resultado))
                    self._estado.alerta("No se pudo eliminar las paginas.")
                    return
                self._estado.exito(f"PDF creado: {resultado['output']}")
                self.aviso(
                    "Paginas eliminadas",
                    f"Se creo:\n\n{resultado['output']}\n\n"
                    f"{resultado['deleted']} paginas eliminadas, "
                    f"{resultado['remaining']} restantes.",
                )

            self._ejecutar(btn, trabajo, al_terminar)

        btn.configure(command=_eliminar)

    # ------------------------------------------------------------------
    # 5. Reordenar paginas
    # ------------------------------------------------------------------

    def _form_reordenar(self, frame) -> None:
        self._seccion(
            frame, "Reordenar paginas",
            "Cambia el orden de las paginas de un PDF.",
        )
        estado_local = {"path": None, "total": None}

        btn = self._boton_accion(frame, "Reordenar y guardar copia")

        archivo_lbl = ttk.Label(frame, text="Ningun PDF elegido.", style="Panel.TLabel")
        archivo_lbl.pack(anchor="w", pady=(0, 10))

        def _elegir() -> None:
            path = filedialog.askopenfilename(
                parent=self, title="Elige el PDF a reordenar", filetypes=_FILTRO_PDF,
            )
            if not path:
                return
            resultado = open_pdf(path)
            if not resultado["ok"]:
                self.error("No se pudo abrir el PDF", self._texto_error_apertura(resultado))
                return
            estado_local["path"] = path
            estado_local["total"] = len(resultado["reader"].pages)
            orden_actual = ",".join(str(i) for i in range(1, estado_local["total"] + 1))
            archivo_lbl.configure(
                text=f"{os.path.basename(path)} ({estado_local['total']} paginas). "
                     f"Orden actual: {orden_actual}"
            )
            self._estado.limpiar()

        ttk.Button(frame, text="Elegir PDF...", command=_elegir).pack(anchor="w")

        orden_frame = ttk.Frame(frame, style="Panel.TFrame")
        orden_frame.pack(anchor="w", fill="x", pady=(12, 0))
        ttk.Label(
            orden_frame, text="Nuevo orden (ej: 3,1,2,5,4):", style="Panel.TLabel",
        ).pack(anchor="w")
        orden_var = tk.StringVar()
        ttk.Entry(orden_frame, textvariable=orden_var, width=40).pack(anchor="w", pady=(4, 0))

        def _reordenar() -> None:
            if not estado_local["path"]:
                self._estado.alerta("Primero elige un PDF.")
                return
            path, total = estado_local["path"], estado_local["total"]
            texto_orden = orden_var.get().strip()
            if not texto_orden:
                self._estado.alerta("Escribe el nuevo orden de las paginas.")
                return
            nuevo_orden, error = parse_reorder(texto_orden, total)
            if nuevo_orden is None:
                self._estado.alerta(error)
                return

            def trabajo():
                apertura = open_pdf(path)
                if not apertura["ok"]:
                    return apertura
                return reorder_pages_do(apertura["pypdf"], apertura["reader"], path, nuevo_orden)

            def al_terminar(resultado) -> None:
                if not resultado.get("ok"):
                    self.error("No se pudo reordenar", self._texto_error(resultado))
                    self._estado.alerta("No se pudo reordenar el PDF.")
                    return
                self._estado.exito(f"PDF reordenado creado: {resultado['output']}")
                self.aviso("PDF reordenado", f"Se creo:\n\n{resultado['output']}")

            self._ejecutar(btn, trabajo, al_terminar)

        btn.configure(command=_reordenar)

    # ------------------------------------------------------------------
    # 6. Extraer texto
    # ------------------------------------------------------------------

    def _form_extraer(self, frame) -> None:
        self._seccion(
            frame, "Extraer texto",
            "Guarda todo el texto de un PDF en un archivo .txt.",
        )
        estado_local = {"path": None}

        btn = self._boton_accion(frame, "Extraer texto")

        archivo_lbl = ttk.Label(frame, text="Ningun PDF elegido.", style="Panel.TLabel")
        archivo_lbl.pack(anchor="w", pady=(0, 10))

        def _elegir() -> None:
            path = filedialog.askopenfilename(
                parent=self, title="Elige el PDF", filetypes=_FILTRO_PDF,
            )
            if not path:
                return
            resultado = open_pdf(path)
            if not resultado["ok"]:
                self.error("No se pudo abrir el PDF", self._texto_error_apertura(resultado))
                return
            estado_local["path"] = path
            total = len(resultado["reader"].pages)
            archivo_lbl.configure(text=f"{os.path.basename(path)} ({total} paginas)")
            self._estado.limpiar()

        ttk.Button(frame, text="Elegir PDF...", command=_elegir).pack(anchor="w")

        def _extraer() -> None:
            if not estado_local["path"]:
                self._estado.alerta("Primero elige un PDF.")
                return
            path = estado_local["path"]

            def trabajo():
                apertura = open_pdf(path)
                if not apertura["ok"]:
                    return apertura
                return extract_text_do(apertura["pypdf"], apertura["reader"], path)

            def al_terminar(resultado) -> None:
                if not resultado.get("ok"):
                    if resultado.get("error") == "no_text":
                        self.error(
                            "Sin texto para extraer",
                            "No se encontro texto en este PDF. Puede ser un "
                            "PDF escaneado (una imagen), en cuyo caso no hay "
                            "texto que extraer.",
                        )
                        self._estado.alerta("El PDF no tiene texto para extraer.")
                    else:
                        self.error("No se pudo extraer el texto", self._texto_error(resultado))
                        self._estado.alerta("No se pudo extraer el texto.")
                    return
                self._estado.exito(f"Texto extraido: {resultado['output']}")
                self.aviso(
                    "Texto extraido",
                    f"Se creo:\n\n{resultado['output']}\n\n"
                    f"{resultado['chars']:,} caracteres.",
                )

            self._ejecutar(btn, trabajo, al_terminar)

        btn.configure(command=_extraer)

    # ------------------------------------------------------------------
    # 7. Imagenes a PDF
    # ------------------------------------------------------------------

    def _form_img_a_pdf(self, frame) -> None:
        self._seccion(
            frame, "Imagenes a PDF",
            "Convierte una o varias imagenes (JPG, PNG, BMP, WEBP) en un solo PDF.",
        )
        estado_local = {"paths": []}

        btn = self._boton_accion(frame, "Crear PDF...")

        botones = ttk.Frame(frame, style="Panel.TFrame")
        botones.pack(fill="x", pady=(0, 8))

        lista_frame = ttk.Frame(frame, style="Panel.TFrame")
        lista_frame.pack(fill="both", expand=True)

        lb = tk.Listbox(
            lista_frame, height=8, exportselection=False,
            bg="#ffffff", fg=theme.FG, borderwidth=1, relief="solid",
        )
        lb.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(lista_frame, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=scroll.set)
        scroll.pack(side="left", fill="y")

        def _agregar() -> None:
            nuevos = filedialog.askopenfilenames(
                parent=self, title="Elige imagenes",
                filetypes=[
                    ("Imagenes", "*.jpg *.jpeg *.png *.bmp *.webp"),
                    ("Todos los archivos", "*.*"),
                ],
            )
            hubo_invalida = False
            for p in nuevos:
                ext = os.path.splitext(p)[1].lower()
                if ext not in _EXTENSIONES_IMAGEN:
                    hubo_invalida = True
                    continue
                estado_local["paths"].append(p)
                lb.insert("end", os.path.basename(p))
            if hubo_invalida:
                self._estado.alerta("Se omitieron archivos con formato no soportado.")
            else:
                self._estado.limpiar()

        def _quitar() -> None:
            seleccion = lb.curselection()
            for i in reversed(seleccion):
                lb.delete(i)
                del estado_local["paths"][i]

        ttk.Button(botones, text="Agregar imagenes...", command=_agregar).pack(side="left")
        ttk.Button(
            botones, text="Quitar seleccionada", command=_quitar,
        ).pack(side="left", padx=(8, 0))

        def _crear() -> None:
            paths = list(estado_local["paths"])
            if not paths:
                self._estado.alerta("Agrega al menos una imagen.")
                return
            Image = _import_pillow()
            if not Image:
                self.error(
                    "Funcion no disponible",
                    "Esta version no incluye la libreria Pillow, necesaria "
                    "para convertir imagenes a PDF.",
                )
                return
            salida = filedialog.asksaveasfilename(
                parent=self, title="Guardar PDF como",
                defaultextension=".pdf", filetypes=_FILTRO_PDF,
                initialfile="imagenes.pdf",
            )
            if not salida:
                return
            # images_to_pdf_do no protege contra sobrescritura por si sola,
            # pero aca la salida es un PDF nuevo a partir de imagenes (no
            # hay riesgo de pisar un archivo de entrada): si "salida" ya
            # existia, el dialogo nativo ya pregunto "reemplazar?" y el
            # usuario confirmo, asi que se escribe en el nombre exacto en
            # vez de renombrar a "_1" (eso contradiria esa confirmacion).

            def trabajo():
                return images_to_pdf_do(Image, paths, salida)

            def al_terminar(resultado) -> None:
                if not resultado.get("ok"):
                    self.error(
                        "No se pudo crear el PDF",
                        "Revisa que las imagenes no esten danadas o sean "
                        "demasiado pesadas.",
                    )
                    self._estado.alerta("No se pudo crear el PDF.")
                    return
                self._estado.exito(
                    f"PDF creado: {resultado['output']} ({_imagenes(resultado['count'])})"
                )
                self.aviso(
                    "PDF creado",
                    f"Se creo:\n\n{resultado['output']}\n\n"
                    f"{_imagenes(resultado['count'])}.",
                )

            self._ejecutar(btn, trabajo, al_terminar)

        btn.configure(command=_crear)

    # ------------------------------------------------------------------
    # 8. PDF a imagenes
    # ------------------------------------------------------------------

    def _form_pdf_a_img(self, frame) -> None:
        self._seccion(
            frame, "PDF a imagenes",
            "Convierte cada pagina de un PDF en una imagen PNG o JPG.",
        )

        # Si falta PyMuPDF, no se arma el formulario: se avisa aqui mismo, para
        # que el usuario no llene todo y choque con el error hasta el final.
        if not self._pymupdf_ok:
            ttk.Label(
                frame,
                text=(
                    "Esta version no incluye el componente necesario para "
                    "convertir PDF a imagenes, asi que esta funcion no esta "
                    "disponible.\n\nEl resto de las herramientas de PDF si "
                    "funciona."
                ),
                style="Panel.TLabel", justify="left", wraplength=560,
            ).pack(anchor="w", pady=(6, 0))
            return

        estado_local = {"path": None}

        btn = self._boton_accion(frame, "Convertir")

        archivo_lbl = ttk.Label(frame, text="Ningun PDF elegido.", style="Panel.TLabel")
        archivo_lbl.pack(anchor="w", pady=(0, 10))

        def _elegir() -> None:
            path = filedialog.askopenfilename(
                parent=self, title="Elige el PDF", filetypes=_FILTRO_PDF,
            )
            if not path:
                return
            estado_local["path"] = path
            archivo_lbl.configure(text=os.path.basename(path))
            self._estado.limpiar()

        ttk.Button(frame, text="Elegir PDF...", command=_elegir).pack(anchor="w")

        formato_var = tk.StringVar(value="png")
        formato_frame = ttk.Frame(frame, style="Panel.TFrame")
        formato_frame.pack(anchor="w", pady=(12, 0))
        ttk.Label(formato_frame, text="Formato:", style="Panel.TLabel").pack(side="left")
        ttk.Radiobutton(
            formato_frame, text="PNG", variable=formato_var, value="png",
        ).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(
            formato_frame, text="JPG", variable=formato_var, value="jpg",
        ).pack(side="left", padx=(8, 0))

        dpi_frame = ttk.Frame(frame, style="Panel.TFrame")
        dpi_frame.pack(anchor="w", pady=(10, 0))
        ttk.Label(dpi_frame, text="Resolucion (DPI, 72-600):", style="Panel.TLabel").pack(
            side="left"
        )
        dpi_var = tk.StringVar(value="150")
        ttk.Entry(dpi_frame, textvariable=dpi_var, width=8).pack(side="left", padx=(8, 0))

        def _convertir() -> None:
            if not estado_local["path"]:
                self._estado.alerta("Primero elige un PDF.")
                return
            fitz = _import_pymupdf()
            if not fitz:
                self.error(
                    "Funcion no disponible",
                    "Esta version no incluye la libreria PyMuPDF, necesaria "
                    "para convertir PDF a imagenes.",
                )
                return
            dpi, error = parse_dpi(dpi_var.get().strip())
            if dpi is None:
                self._estado.alerta(error)
                return

            carpeta = filedialog.askdirectory(
                parent=self, title="Elige la carpeta de salida",
            )
            if not carpeta:
                return

            path, fmt = estado_local["path"], formato_var.get()

            def trabajo():
                return pdf_to_images_do(fitz, path, fmt, dpi, carpeta)

            def al_terminar(resultado) -> None:
                if not resultado.get("ok"):
                    self.error(
                        "No se pudo convertir",
                        "No se pudo convertir el PDF a imagenes. Puede estar "
                        "danado, protegido, o no haber espacio en disco.",
                    )
                    self._estado.alerta("No se pudo convertir el PDF.")
                    return
                self._estado.exito(
                    f"Listo. {_imagenes(resultado['count'])} en: {resultado['output_dir']}"
                )
                self.aviso(
                    "Conversion lista",
                    f"Se guardo en:\n\n{resultado['output_dir']}\n\n"
                    f"{_imagenes(resultado['count'])} ({resultado['dpi']} DPI)",
                )

            self._ejecutar(btn, trabajo, al_terminar)

        btn.configure(command=_convertir)

    # ------------------------------------------------------------------
    # 9. PDF a Word
    # ------------------------------------------------------------------

    def _form_pdf_a_word(self, frame) -> None:
        self._seccion(
            frame, "PDF a Word",
            "Extrae el texto del PDF a un documento Word (.docx) editable. Es "
            "texto simple: no reconstruye tablas ni columnas complejas.",
        )

        if not self._word_ok:
            ttk.Label(
                frame,
                text=(
                    "Esta version no incluye el componente necesario para "
                    "convertir PDF a Word, asi que esta funcion no esta "
                    "disponible.\n\nEl resto de las herramientas de PDF si "
                    "funciona."
                ),
                style="Panel.TLabel", justify="left", wraplength=560,
            ).pack(anchor="w", pady=(6, 0))
            return

        estado_local = {"path": None}
        btn = self._boton_accion(frame, "Convertir a Word")

        archivo_lbl = ttk.Label(frame, text="Ningun PDF elegido.", style="Panel.TLabel")
        archivo_lbl.pack(anchor="w", pady=(0, 10))

        def _elegir() -> None:
            path = filedialog.askopenfilename(
                parent=self, title="Elige el PDF", filetypes=_FILTRO_PDF,
            )
            if not path:
                return
            estado_local["path"] = path
            archivo_lbl.configure(text=os.path.basename(path))
            self._estado.limpiar()

        ttk.Button(frame, text="Elegir PDF...", command=_elegir).pack(anchor="w")

        def _convertir() -> None:
            if not estado_local["path"]:
                self._estado.alerta("Primero elige un PDF.")
                return
            fitz = _import_pymupdf()
            Document = _import_docx()
            if not fitz or not Document:
                self.error(
                    "Funcion no disponible",
                    "Esta version no incluye las librerias necesarias para "
                    "convertir PDF a Word.",
                )
                return

            path = estado_local["path"]
            sugerido = os.path.splitext(os.path.basename(path))[0] + ".docx"
            salida = filedialog.asksaveasfilename(
                parent=self, title="Guardar Word como", defaultextension=".docx",
                initialfile=sugerido, filetypes=[("Documento Word", "*.docx")],
            )
            if not salida:
                return

            def trabajo():
                # overwrite=True: el dialogo nativo ya confirmo reemplazar.
                return pdf_to_word_do(fitz, Document, path, salida, overwrite=True)

            def al_terminar(resultado) -> None:
                if not resultado.get("ok"):
                    if resultado.get("error") == "encrypted":
                        self.error(
                            "PDF protegido",
                            "El PDF esta protegido con password. Desprotegelo "
                            "primero con la opcion 'Proteger / desproteger PDF'.",
                        )
                    else:
                        self.error(
                            "No se pudo convertir",
                            "No se pudo convertir el PDF a Word. Puede estar "
                            "danado o no haber espacio en disco.",
                        )
                    self._estado.alerta("No se pudo convertir el PDF a Word.")
                    return
                if resultado.get("empty"):
                    self._estado.info(
                        "Listo, pero el PDF no tenia texto seleccionable (puede "
                        "ser un escaneo): el Word quedo vacio."
                    )
                else:
                    self._estado.exito(f"Word creado: {resultado['output']}")
                extra = ("\n\nOjo: el PDF no tenia texto seleccionable, el Word "
                         "quedo vacio." if resultado.get("empty") else "")
                self.aviso(
                    "Conversion lista",
                    f"Se guardo en:\n\n{resultado['output']}\n\n"
                    f"{resultado['pages']} paginas.{extra}",
                )

            self._ejecutar(btn, trabajo, al_terminar)

        btn.configure(command=_convertir)

    # ------------------------------------------------------------------
    # 10. Proteger / desproteger PDF
    # ------------------------------------------------------------------

    def _form_proteger(self, frame) -> None:
        self._seccion(
            frame, "Proteger / desproteger PDF",
            "Agrega o quita una contrasena a un PDF. La contrasena nunca se "
            "guarda en ningun lado.",
        )
        estado_local = {"path": None, "encriptado": None}

        btn = self._boton_accion(frame, "Elige un PDF primero")
        btn.configure(state="disabled")

        archivo_lbl = ttk.Label(frame, text="Ningun PDF elegido.", style="Panel.TLabel")
        archivo_lbl.pack(anchor="w", pady=(0, 10))

        subform = ttk.Frame(frame, style="Panel.TFrame")

        pass_actual_var = tk.StringVar()
        pass_nueva_var = tk.StringVar()
        pass_confirmar_var = tk.StringVar()

        def _proteger() -> None:
            path = estado_local["path"]
            nueva = pass_nueva_var.get()
            confirmar = pass_confirmar_var.get()
            if not nueva:
                self._estado.alerta("Escribe una contrasena.")
                return
            if nueva != confirmar:
                self._estado.alerta("Las contrasenas no coinciden.")
                return
            base_name = os.path.splitext(path)[0]

            def trabajo():
                apertura = read_pdf_for_protect(path)
                if not apertura["ok"]:
                    return apertura
                return protect_pdf_do(apertura["pypdf"], apertura["reader"], nueva, base_name)

            def al_terminar(resultado) -> None:
                pass_nueva_var.set("")
                pass_confirmar_var.set("")
                if not resultado.get("ok"):
                    self.error("No se pudo proteger", self._texto_error(resultado))
                    self._estado.alerta("No se pudo proteger el PDF.")
                    return
                self._estado.exito(f"PDF protegido creado: {resultado['output']}")
                self.aviso("PDF protegido", f"Se creo:\n\n{resultado['output']}")

            self._ejecutar(btn, trabajo, al_terminar)

        def _desproteger() -> None:
            path = estado_local["path"]
            actual = pass_actual_var.get()
            base_name = os.path.splitext(path)[0]

            def trabajo():
                apertura = read_pdf_for_protect(path)
                if not apertura["ok"]:
                    return apertura
                return unprotect_pdf_do(apertura["pypdf"], apertura["reader"], actual, base_name)

            def al_terminar(resultado) -> None:
                pass_actual_var.set("")
                if not resultado.get("ok"):
                    err = resultado.get("error")
                    if err in ("wrong_password", "wrong_password_or_corrupt"):
                        self.error(
                            "Contrasena incorrecta",
                            "La contrasena no es correcta, o el archivo esta danado.",
                        )
                    else:
                        self.error("No se pudo quitar la proteccion", self._texto_error(resultado))
                    self._estado.alerta("No se pudo quitar la proteccion.")
                    return
                self._estado.exito(f"PDF desprotegido creado: {resultado['output']}")
                self.aviso("PDF desprotegido", f"Se creo:\n\n{resultado['output']}")

            self._ejecutar(btn, trabajo, al_terminar)

        def _actualizar_subform() -> None:
            for widget in subform.winfo_children():
                widget.destroy()
            if estado_local["encriptado"]:
                ttk.Label(subform, text="Contrasena actual:", style="Panel.TLabel").pack(anchor="w")
                ttk.Entry(subform, textvariable=pass_actual_var, show="*", width=28).pack(
                    anchor="w", pady=(4, 0)
                )
                btn.configure(text="Quitar proteccion", command=_desproteger)
            else:
                ttk.Label(subform, text="Nueva contrasena:", style="Panel.TLabel").pack(anchor="w")
                ttk.Entry(subform, textvariable=pass_nueva_var, show="*", width=28).pack(
                    anchor="w", pady=(4, 8)
                )
                ttk.Label(subform, text="Confirmar contrasena:", style="Panel.TLabel").pack(anchor="w")
                ttk.Entry(subform, textvariable=pass_confirmar_var, show="*", width=28).pack(
                    anchor="w", pady=(4, 0)
                )
                btn.configure(text="Proteger PDF", command=_proteger)
            btn.configure(state="normal")

        def _elegir() -> None:
            path = filedialog.askopenfilename(
                parent=self, title="Elige el PDF", filetypes=_FILTRO_PDF,
            )
            if not path:
                return
            resultado = read_pdf_for_protect(path)
            if not resultado["ok"]:
                self.error("No se pudo abrir el PDF", self._texto_error(resultado, "No se pudo leer el archivo."))
                return
            estado_local["path"] = path
            estado_local["encriptado"] = resultado["reader"].is_encrypted
            estado_texto = "protegido con contrasena" if estado_local["encriptado"] else "sin proteccion"
            archivo_lbl.configure(text=f"{os.path.basename(path)} — {estado_texto}")
            _actualizar_subform()
            self._estado.limpiar()

        ttk.Button(frame, text="Elegir PDF...", command=_elegir).pack(anchor="w")
        subform.pack(anchor="w", fill="x", pady=(12, 0))

    # ------------------------------------------------------------------
    # 10. Ver / limpiar metadatos
    # ------------------------------------------------------------------

    def _form_metadatos(self, frame) -> None:
        self._seccion(
            frame, "Ver / limpiar metadatos",
            "Muestra la informacion oculta del PDF (autor, fechas...) y "
            "permite crear una copia sin ella.",
        )
        estado_local = {"path": None}

        btn = self._boton_accion(frame, "Limpiar metadatos (crear copia)")
        btn.configure(state="disabled")

        archivo_lbl = ttk.Label(frame, text="Ningun PDF elegido.", style="Panel.TLabel")
        archivo_lbl.pack(anchor="w", pady=(0, 10))

        info_lbl = ttk.Label(
            frame, text="", style="Panel.TLabel", justify="left", wraplength=520,
        )
        info_lbl.pack(anchor="w")

        def _elegir() -> None:
            path = filedialog.askopenfilename(
                parent=self, title="Elige el PDF", filetypes=_FILTRO_PDF,
            )
            if not path:
                return
            resultado = open_pdf(path)
            if not resultado["ok"]:
                self.error("No se pudo abrir el PDF", self._texto_error_apertura(resultado))
                return
            estado_local["path"] = path
            reader = resultado["reader"]
            total = len(reader.pages)
            archivo_lbl.configure(text=f"{os.path.basename(path)} ({total} paginas)")

            campos = get_pdf_metadata_fields(reader.metadata) if reader.metadata else []
            if campos:
                info_lbl.configure(
                    text="\n".join(f"{etiqueta}: {valor}" for etiqueta, valor in campos)
                )
            else:
                info_lbl.configure(text="Este PDF no tiene metadatos adicionales.")

            btn.configure(state="normal")
            self._estado.limpiar()

        ttk.Button(frame, text="Elegir PDF...", command=_elegir).pack(anchor="w")

        def _limpiar() -> None:
            path = estado_local["path"]

            def trabajo():
                apertura = open_pdf(path)
                if not apertura["ok"]:
                    return apertura
                return clean_metadata_do(apertura["pypdf"], apertura["reader"], path)

            def al_terminar(resultado) -> None:
                if not resultado.get("ok"):
                    self.error("No se pudo limpiar", self._texto_error(resultado))
                    self._estado.alerta("No se pudieron limpiar los metadatos.")
                    return
                self._estado.exito(f"PDF sin metadatos creado: {resultado['output']}")
                self.aviso("Metadatos limpiados", f"Se creo:\n\n{resultado['output']}")

            self._ejecutar(btn, trabajo, al_terminar)

        btn.configure(command=_limpiar)
