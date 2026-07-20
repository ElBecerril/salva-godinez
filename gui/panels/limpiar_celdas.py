"""Pantalla: Quitar espacios que rompen formulas (limpieza de celdas Excel).

Solo presenta la logica de tools/excel_cell_cleaner.py: clean_file() abre el
libro y arma la lista de cambios, y esta pantalla nada mas la pinta y, si el
usuario confirma, guarda el resultado con un nombre nuevo (nunca sobre el
archivo original).
"""

import os
import tkinter as tk
from tkinter import filedialog, ttk

from gui.base import EstadoLabel, ToolPanel
from tools.excel_cell_cleaner import _safe_output_path, clean_file

_FILTROS = [("Archivos de Excel", "*.xlsx *.xlsm"), ("Todos los archivos", "*.*")]


class PanelLimpiarCeldas(ToolPanel):
    TITULO = "Quitar espacios que rompen formulas"
    DESCRIPCION = (
        "Elige un archivo de Excel y se revisan todas sus celdas de texto en "
        "busca de espacios dobles, espacios al principio/final y caracteres "
        "invisibles (la causa mas comun de que un BUSCARV o una comparacion "
        "'no encuentren' algo que a simple vista se ve igual). El archivo "
        "original nunca se modifica: se guarda una copia limpia aparte."
    )

    def build(self) -> None:
        self._filepath: str | None = None
        self._wb = None

        # --- Elegir archivo -------------------------------------------------
        fila_archivo = ttk.Frame(self.body, style="Panel.TFrame")
        fila_archivo.pack(fill="x")

        ttk.Button(
            fila_archivo, text="Elegir archivo de Excel...",
            command=self._elegir_archivo,
        ).pack(side="left")

        self._label_archivo = ttk.Label(
            fila_archivo, text="Ningun archivo elegido.", style="Panel.TLabel",
        )
        self._label_archivo.pack(side="left", padx=(12, 0))

        # --- Analizar ---------------------------------------------------
        fila_accion = ttk.Frame(self.body, style="Panel.TFrame")
        fila_accion.pack(fill="x", pady=(14, 0))

        self._btn_analizar = ttk.Button(
            fila_accion, text="Analizar celdas", style="Accent.TButton",
            command=self._analizar, state="disabled",
        )
        self._btn_analizar.pack(side="left")

        self._barra = ttk.Progressbar(fila_accion, mode="indeterminate", length=180)

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(10, 6))

        # --- Guardar (abajo, antes de la tabla que expande) -----------------
        acciones = ttk.Frame(self.body, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(12, 0))

        self._btn_guardar = ttk.Button(
            acciones, text="Guardar archivo limpio...", style="Accent.TButton",
            command=self._guardar, state="disabled",
        )
        self._btn_guardar.pack(side="left")

        # --- Tabla de cambios ------------------------------------------------
        tabla_frame = ttk.Frame(self.body, style="Panel.TFrame")
        tabla_frame.pack(fill="both", expand=True, pady=(4, 0))

        columnas = ("hoja", "celda", "antes", "despues")
        self._tabla = ttk.Treeview(
            tabla_frame, columns=columnas, show="headings", height=14,
        )
        self._tabla.heading("hoja", text="Hoja")
        self._tabla.heading("celda", text="Celda")
        self._tabla.heading("antes", text="Antes")
        self._tabla.heading("despues", text="Despues")
        self._tabla.column("hoja", width=120, anchor="w", stretch=False)
        self._tabla.column("celda", width=80, anchor="w", stretch=False)
        self._tabla.column("antes", width=280, anchor="w", stretch=True)
        self._tabla.column("despues", width=280, anchor="w", stretch=True)

        scroll_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=scroll_y.set)
        self._tabla.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="left", fill="y")

    # ------------------------------------------------------------------

    def _elegir_archivo(self) -> None:
        ruta = filedialog.askopenfilename(
            parent=self, title="Elige el archivo de Excel", filetypes=_FILTROS,
        )
        if not ruta:
            return
        self._cerrar_wb_actual()
        self._filepath = ruta
        self._label_archivo.configure(text=os.path.basename(ruta))
        self._btn_analizar.configure(state="normal")
        self._btn_guardar.configure(state="disabled")
        self._estado.limpiar()
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)

    def _cerrar_wb_actual(self) -> None:
        if self._wb is not None:
            try:
                self._wb.close()
            except Exception:
                pass
            self._wb = None

    def _analizar(self) -> None:
        if not self._filepath:
            return
        self._cerrar_wb_actual()
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
        self._btn_guardar.configure(state="disabled")

        self._btn_analizar.configure(state="disabled")
        self._barra.pack(side="left", padx=(12, 0))
        self._barra.start(12)
        self._estado.info("Analizando celdas...")

        ruta = self._filepath
        self.run_async(lambda: clean_file(ruta), self._on_analisis)

    def _on_analisis(self, ok: bool, resultado) -> None:
        self._barra.stop()
        self._barra.pack_forget()
        self._btn_analizar.configure(state="normal")

        if not ok:
            self._estado.alerta("No se pudo analizar el archivo.")
            self.error("Error", "Algo salio mal al analizar el archivo. Intenta de nuevo.")
            return

        if not resultado.get("ok"):
            if resultado.get("error"):
                self._estado.alerta("No se pudo abrir el archivo (corrupto o formato invalido).")
                self.error(
                    "No se pudo abrir el archivo",
                    "El archivo esta danado, protegido con contrasena, o no es un "
                    f"Excel valido.\n\nDetalle: {resultado['error']}",
                )
            else:
                self._estado.alerta("No se pudo cargar el modulo de Excel.")
                self.error(
                    "Falta un componente",
                    "No se pudo cargar el modulo para leer archivos de Excel. "
                    "Reinstala la aplicacion.",
                )
            return

        self._wb = resultado.get("_wb")
        cambios = resultado["changes"]

        self._estado.info(
            f"Celdas de texto analizadas: {resultado['total_cells']}   -   "
            f"Celdas con cambios: {resultado['cleaned_cells']}"
        )

        if not cambios:
            self._estado.exito("No se encontraron celdas por limpiar. El archivo ya esta bien.")
            self._cerrar_wb_actual()
            return

        for c in cambios:
            self._tabla.insert("", "end", values=(c["hoja"], c["celda"], c["antes"], c["despues"]))

        self._btn_guardar.configure(state="normal")

    def _guardar(self) -> None:
        if self._wb is None or not self._filepath:
            return

        base, ext = os.path.splitext(self._filepath)
        sugerido = _safe_output_path(f"{base}_limpio{ext}")

        destino = filedialog.asksaveasfilename(
            parent=self, title="Guardar archivo limpio",
            initialdir=os.path.dirname(sugerido),
            initialfile=os.path.basename(sugerido),
            defaultextension=ext, filetypes=_FILTROS,
        )
        if not destino:
            return

        if os.path.abspath(destino) == os.path.abspath(self._filepath):
            self.error(
                "No se puede sobrescribir el original",
                "Elige un nombre distinto al del archivo original para no perderlo.",
            )
            return

        try:
            self._wb.save(destino)
        except OSError as e:
            self.error(
                "No se pudo guardar",
                "No se pudo guardar el archivo. Revisa que no este abierto en Excel "
                f"y que haya espacio en el disco.\n\nDetalle: {e}",
            )
            return
        finally:
            self._cerrar_wb_actual()

        self._estado.exito(f"Archivo guardado en: {destino}")
        self._btn_guardar.configure(state="disabled")
        self.aviso("Archivo guardado", f"El archivo limpio quedo guardado en:\n\n{destino}")
