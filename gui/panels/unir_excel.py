"""Pantalla: Unir varios Excel en uno.

Presenta los dos modos de tools/excel_consolidator.py (mismo flujo que
consolidator_menu() en consola):
  1. Unir archivos: cada archivo aporta sus hojas a un workbook nuevo.
  2. Unir hojas: las hojas de UN archivo se apilan verticalmente en una sola.

Ninguno de los dos modos reimplementa la union: solo arma la lista de
archivos/opciones que el usuario eligio y llama a _merge_files()/_merge_sheets().
"""

import os
import tkinter as tk
from tkinter import filedialog, ttk

from gui.base import EstadoLabel, ToolPanel
from tools.excel_consolidator import _merge_files, _merge_sheets, _safe_output_path

_FILTROS = [("Archivos de Excel", "*.xlsx *.xlsm"), ("Todos los archivos", "*.*")]


class PanelUnirExcel(ToolPanel):
    TITULO = "Unir varios Excel en uno"
    DESCRIPCION = (
        "Dos formas de unir: 'Unir archivos' junta varios libros de Excel en "
        "uno solo (cada archivo se convierte en sus propias hojas), y 'Unir "
        "hojas' apila las hojas de UN archivo en una sola tabla larga. En "
        "ambos casos las formulas se convierten a su valor actual, y siempre "
        "se crea un archivo nuevo: el original nunca se toca."
    )

    def build(self) -> None:
        self._var_modo = tk.StringVar(value="archivos")

        selector = ttk.Frame(self.body, style="Panel.TFrame")
        selector.pack(fill="x")
        ttk.Radiobutton(
            selector, text="Unir archivos", value="archivos",
            variable=self._var_modo, command=self._cambiar_modo,
        ).pack(side="left")
        ttk.Radiobutton(
            selector, text="Unir hojas", value="hojas",
            variable=self._var_modo, command=self._cambiar_modo,
        ).pack(side="left", padx=(16, 0))

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(10, 6))

        self._barra = ttk.Progressbar(self.body, mode="indeterminate")

        self._zona = ttk.Frame(self.body, style="Panel.TFrame")
        self._zona.pack(fill="both", expand=True, pady=(6, 0))

        self._frame_archivos = self._build_modo_archivos(self._zona)
        self._frame_hojas = self._build_modo_hojas(self._zona)
        self._cambiar_modo()

    def _cambiar_modo(self) -> None:
        self._estado.limpiar()
        if self._var_modo.get() == "archivos":
            self._frame_hojas.pack_forget()
            self._frame_archivos.pack(fill="both", expand=True)
        else:
            self._frame_archivos.pack_forget()
            self._frame_hojas.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Modo 1: unir archivos
    # ------------------------------------------------------------------

    def _build_modo_archivos(self, master) -> ttk.Frame:
        marco = ttk.Frame(master, style="Panel.TFrame")

        self._archivos: list[str] = []

        botones = ttk.Frame(marco, style="Panel.TFrame")
        botones.pack(fill="x")
        ttk.Button(
            botones, text="Agregar archivos...", command=self._agregar_archivos,
        ).pack(side="left")
        self._btn_quitar = ttk.Button(
            botones, text="Quitar seleccionado", command=self._quitar_archivo,
            state="disabled",
        )
        self._btn_quitar.pack(side="left", padx=(8, 0))

        lista_frame = ttk.Frame(marco, style="Panel.TFrame")
        lista_frame.pack(fill="both", expand=True, pady=(8, 0))
        self._lista_archivos = ttk.Treeview(
            lista_frame, columns=("archivo",), show="headings", height=6,
        )
        self._lista_archivos.heading("archivo", text="Archivos a unir (en este orden)")
        self._lista_archivos.column("archivo", anchor="w", stretch=True)
        scroll = ttk.Scrollbar(lista_frame, orient="vertical", command=self._lista_archivos.yview)
        self._lista_archivos.configure(yscrollcommand=scroll.set)
        self._lista_archivos.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")
        self._lista_archivos.bind("<<TreeviewSelect>>", self._on_seleccion_archivos)

        fila_salida = ttk.Frame(marco, style="Panel.TFrame")
        fila_salida.pack(fill="x", pady=(10, 0))
        ttk.Label(fila_salida, text="Archivo de salida:", style="Panel.TLabel").pack(side="left")
        self._var_salida_archivos = tk.StringVar()
        ttk.Entry(
            fila_salida, textvariable=self._var_salida_archivos, state="readonly", width=48,
        ).pack(side="left", padx=(8, 8))
        ttk.Button(
            fila_salida, text="Elegir...", command=self._elegir_salida_archivos,
        ).pack(side="left")

        ttk.Button(
            marco, text="Unir archivos", style="Accent.TButton",
            command=self._unir_archivos,
        ).pack(anchor="w", pady=(12, 0))

        return marco

    def _agregar_archivos(self) -> None:
        rutas = filedialog.askopenfilenames(
            parent=self, title="Elige los archivos a unir", filetypes=_FILTROS,
        )
        if not rutas:
            return
        for ruta in rutas:
            if ruta not in self._archivos:
                self._archivos.append(ruta)
                self._lista_archivos.insert("", "end", iid=ruta, values=(ruta,))

        if not self._var_salida_archivos.get() and self._archivos:
            sugerido = os.path.join(os.path.dirname(self._archivos[0]), "consolidado.xlsx")
            self._var_salida_archivos.set(sugerido)

    def _on_seleccion_archivos(self, _evento=None) -> None:
        self._btn_quitar.configure(
            state="normal" if self._lista_archivos.selection() else "disabled"
        )

    def _quitar_archivo(self) -> None:
        for iid in self._lista_archivos.selection():
            self._lista_archivos.delete(iid)
            if iid in self._archivos:
                self._archivos.remove(iid)
        self._on_seleccion_archivos()

    def _elegir_salida_archivos(self) -> None:
        inicial = self._var_salida_archivos.get() or "consolidado.xlsx"
        destino = filedialog.asksaveasfilename(
            parent=self, title="Guardar consolidado como",
            initialdir=os.path.dirname(inicial) or None,
            initialfile=os.path.basename(inicial),
            defaultextension=".xlsx", filetypes=_FILTROS,
        )
        if destino:
            self._var_salida_archivos.set(destino)

    def _unir_archivos(self) -> None:
        if len(self._archivos) < 2:
            self._estado.alerta("Agrega al menos 2 archivos para unir.")
            return
        salida = self._var_salida_archivos.get().strip()
        if not salida:
            self._estado.alerta("Elige donde guardar el archivo de salida.")
            return

        self._estado.info(
            "Uniendo archivos... Aviso: las formulas se convierten a su valor actual."
        )
        self._barra.pack(fill="x", pady=(4, 6))
        self._barra.start(12)

        archivos = list(self._archivos)
        self.run_async(
            lambda: _merge_files(archivos, salida), self._on_union_archivos_lista,
        )

    def _on_union_archivos_lista(self, ok: bool, resultado) -> None:
        self._barra.stop()
        self._barra.pack_forget()

        if not ok:
            self._estado.alerta("No se pudo completar la union.")
            self.error("Error", "Algo salio mal al unir los archivos. Intenta de nuevo.")
            return

        mensajes_error = []
        for nombre, err in resultado["open_errors"]:
            mensajes_error.append(f"No se pudo abrir {nombre}: {err}")

        if resultado["output_conflict"]:
            self._estado.alerta(
                "El archivo de salida no puede ser igual a uno de los archivos de entrada."
            )
            self.error(
                "Ruta de salida invalida",
                "El archivo de salida no puede ser igual a uno de los archivos de entrada "
                "(se perderia el original). Elige otra ruta.",
            )
            return

        if resultado["save_error"]:
            self._estado.alerta("No se pudo guardar el archivo.")
            self.error(
                "No se pudo guardar",
                "No se pudo guardar el archivo de salida. Revisa que no este abierto "
                f"y que haya espacio en disco.\n\nDetalle: {resultado['save_error']}",
            )
            return

        if resultado["forced_xlsx"]:
            mensajes_error.append(
                "El archivo se genero como .xlsx: ninguno de los archivos de origen "
                "tenia macros, un .xlsm sin macros queda danado."
            )

        if not resultado["sheets"]:
            self._estado.alerta("No se pudo unir ningun archivo." + (" " + " ".join(mensajes_error) if mensajes_error else ""))
            return

        texto = f"Consolidado creado: {resultado['output']} ({resultado['sheets']} hojas)."
        if mensajes_error:
            texto += " " + " ".join(mensajes_error)
        self._estado.exito(texto)
        self.aviso("Archivos unidos", f"El archivo quedo guardado en:\n\n{resultado['output']}")

    # ------------------------------------------------------------------
    # Modo 2: unir hojas
    # ------------------------------------------------------------------

    def _build_modo_hojas(self, master) -> ttk.Frame:
        marco = ttk.Frame(master, style="Panel.TFrame")

        self._archivo_hojas: str | None = None

        fila_archivo = ttk.Frame(marco, style="Panel.TFrame")
        fila_archivo.pack(fill="x")
        ttk.Button(
            fila_archivo, text="Elegir archivo de Excel...", command=self._elegir_archivo_hojas,
        ).pack(side="left")
        self._label_archivo_hojas = ttk.Label(
            fila_archivo, text="Ningun archivo elegido.", style="Panel.TLabel",
        )
        self._label_archivo_hojas.pack(side="left", padx=(12, 0))

        fila_salida = ttk.Frame(marco, style="Panel.TFrame")
        fila_salida.pack(fill="x", pady=(10, 0))
        ttk.Label(fila_salida, text="Archivo de salida:", style="Panel.TLabel").pack(side="left")
        self._var_salida_hojas = tk.StringVar()
        ttk.Entry(
            fila_salida, textvariable=self._var_salida_hojas, state="readonly", width=48,
        ).pack(side="left", padx=(8, 8))
        self._btn_elegir_salida_hojas = ttk.Button(
            fila_salida, text="Elegir...", command=self._elegir_salida_hojas, state="disabled",
        )
        self._btn_elegir_salida_hojas.pack(side="left")

        self._var_encabezado = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            marco, variable=self._var_encabezado,
            text="Todas las hojas tienen una fila de encabezado (se descarta la "
                 "repetida en la hoja 2 en adelante)",
        ).pack(anchor="w", pady=(12, 0))

        ttk.Label(
            marco,
            text="Aviso: las formulas se convierten a su valor actual.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(6, 0))

        ttk.Button(
            marco, text="Unir hojas", style="Accent.TButton", command=self._unir_hojas,
        ).pack(anchor="w", pady=(12, 0))

        return marco

    def _elegir_archivo_hojas(self) -> None:
        ruta = filedialog.askopenfilename(
            parent=self, title="Elige el archivo de Excel", filetypes=_FILTROS,
        )
        if not ruta:
            return
        self._archivo_hojas = ruta
        self._label_archivo_hojas.configure(text=os.path.basename(ruta))
        base, ext = os.path.splitext(ruta)
        self._var_salida_hojas.set(f"{base}_consolidado{ext}")
        self._btn_elegir_salida_hojas.configure(state="normal")

    def _elegir_salida_hojas(self) -> None:
        inicial = self._var_salida_hojas.get()
        destino = filedialog.asksaveasfilename(
            parent=self, title="Guardar como",
            initialdir=os.path.dirname(inicial) or None,
            initialfile=os.path.basename(inicial),
            defaultextension=".xlsx", filetypes=_FILTROS,
        )
        if destino:
            self._var_salida_hojas.set(destino)

    def _unir_hojas(self) -> None:
        if not self._archivo_hojas:
            self._estado.alerta("Elige primero un archivo de Excel.")
            return
        salida = self._var_salida_hojas.get().strip()
        if not salida:
            self._estado.alerta("Elige donde guardar el archivo de salida.")
            return

        self._estado.info("Uniendo hojas...")
        self._barra.pack(fill="x", pady=(4, 6))
        self._barra.start(12)

        archivo = self._archivo_hojas
        con_encabezado = self._var_encabezado.get()
        self.run_async(
            lambda: _merge_sheets(archivo, salida, skip_header=con_encabezado),
            self._on_union_hojas_lista,
        )

    def _on_union_hojas_lista(self, ok: bool, resultado) -> None:
        self._barra.stop()
        self._barra.pack_forget()

        if not ok:
            self._estado.alerta("No se pudo completar la union.")
            self.error("Error", "Algo salio mal al unir las hojas. Intenta de nuevo.")
            return

        if resultado["open_error"]:
            self._estado.alerta("No se pudo abrir el archivo.")
            self.error(
                "No se pudo abrir el archivo",
                "El archivo esta danado, protegido con contrasena, o no es un "
                f"Excel valido.\n\nDetalle: {resultado['open_error']}",
            )
            return

        if resultado["input_conflict"]:
            self._estado.alerta("El archivo de salida no puede ser igual al de entrada.")
            self.error(
                "Ruta de salida invalida",
                "El archivo de salida no puede ser igual al archivo de entrada "
                "(se perderia el original). Elige otra ruta.",
            )
            return

        if resultado["save_error"]:
            self._estado.alerta("No se pudo guardar el archivo.")
            self.error(
                "No se pudo guardar",
                "No se pudo guardar el archivo de salida. Revisa que no este abierto "
                f"y que haya espacio en disco.\n\nDetalle: {resultado['save_error']}",
            )
            return

        aviso_extra = ""
        if resultado["forced_xlsx"]:
            aviso_extra = (
                " El archivo se genero como .xlsx: el resultado no tiene macros, "
                "un .xlsm sin macros queda danado."
            )

        if not resultado["rows"]:
            self._estado.alerta("No se genero ninguna fila." + aviso_extra)
            return

        texto = f"Archivo creado: {resultado['output']} ({resultado['rows']} filas)."
        self._estado.exito(texto + aviso_extra)
        self.aviso("Hojas unidas", f"El archivo quedo guardado en:\n\n{resultado['output']}")
