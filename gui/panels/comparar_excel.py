"""Pantalla: Comparar dos archivos de Excel.

Presenta tools/excel_comparator.py: compare_files() abre ambos libros y arma
las diferencias celda por celda, y opcionalmente _generate_diff_report()
guarda una copia del primer archivo con las celdas distintas marcadas en
rojo. La comparacion en si no se reimplementa aqui.
"""

import os
import tkinter as tk
from tkinter import filedialog, ttk

from gui.base import EstadoLabel, ToolPanel
from tools.excel_comparator import _generate_diff_report, _safe_output_path, compare_files

_FILTROS = [("Archivos de Excel", "*.xlsx *.xlsm"), ("Todos los archivos", "*.*")]


class PanelCompararExcel(ToolPanel):
    TITULO = "Comparar dos archivos de Excel"
    DESCRIPCION = (
        "Elige dos versiones de un mismo archivo de Excel y se revisan celda "
        "por celda para mostrarte que cambio. Tambien avisa si alguna hoja "
        "existe solo en uno de los dos archivos. Al final puedes guardar un "
        "reporte con las diferencias marcadas en rojo, sin tocar los "
        "archivos originales."
    )

    def build(self) -> None:
        self._path1: str | None = None
        self._path2: str | None = None
        self._wb1 = None
        self._wb2 = None
        self._comparacion: dict | None = None

        # --- Elegir archivos --------------------------------------------
        fila1 = ttk.Frame(self.body, style="Panel.TFrame")
        fila1.pack(fill="x")
        ttk.Button(
            fila1, text="Elegir primer archivo...", command=lambda: self._elegir(1),
        ).pack(side="left")
        self._label1 = ttk.Label(fila1, text="Ningun archivo elegido.", style="Panel.TLabel")
        self._label1.pack(side="left", padx=(12, 0))

        fila2 = ttk.Frame(self.body, style="Panel.TFrame")
        fila2.pack(fill="x", pady=(6, 0))
        ttk.Button(
            fila2, text="Elegir segundo archivo...", command=lambda: self._elegir(2),
        ).pack(side="left")
        self._label2 = ttk.Label(fila2, text="Ningun archivo elegido.", style="Panel.TLabel")
        self._label2.pack(side="left", padx=(12, 0))

        # --- Comparar ---------------------------------------------------
        fila_accion = ttk.Frame(self.body, style="Panel.TFrame")
        fila_accion.pack(fill="x", pady=(14, 0))
        self._btn_comparar = ttk.Button(
            fila_accion, text="Comparar", style="Accent.TButton", command=self._comparar,
        )
        self._btn_comparar.pack(side="left")
        self._barra = ttk.Progressbar(fila_accion, mode="indeterminate", length=180)

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(10, 6))

        # --- Generar reporte (abajo, antes de la tabla) ----------------
        acciones = ttk.Frame(self.body, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(12, 0))
        self._btn_reporte = ttk.Button(
            acciones, text="Guardar reporte con diferencias...", style="Accent.TButton",
            command=self._generar_reporte, state="disabled",
        )
        self._btn_reporte.pack(side="left")

        # --- Tabla de diferencias -----------------------------------------
        tabla_frame = ttk.Frame(self.body, style="Panel.TFrame")
        tabla_frame.pack(fill="both", expand=True, pady=(4, 0))

        columnas = ("hoja", "celda", "v1", "v2")
        self._tabla = ttk.Treeview(
            tabla_frame, columns=columnas, show="headings", height=8,
        )
        self._tabla.heading("hoja", text="Hoja")
        self._tabla.heading("celda", text="Celda")
        self._tabla.heading("v1", text="Archivo 1")
        self._tabla.heading("v2", text="Archivo 2")
        self._tabla.column("hoja", width=120, anchor="w", stretch=False)
        self._tabla.column("celda", width=80, anchor="w", stretch=False)
        self._tabla.column("v1", width=260, anchor="w", stretch=True)
        self._tabla.column("v2", width=260, anchor="w", stretch=True)

        scroll_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=scroll_y.set)
        self._tabla.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="left", fill="y")

    # ------------------------------------------------------------------

    def _elegir(self, cual: int) -> None:
        ruta = filedialog.askopenfilename(
            parent=self, title="Elige el archivo de Excel", filetypes=_FILTROS,
        )
        if not ruta:
            return
        if cual == 1:
            self._path1 = ruta
            self._label1.configure(text=os.path.basename(ruta))
        else:
            self._path2 = ruta
            self._label2.configure(text=os.path.basename(ruta))

    def _cerrar_libros(self) -> None:
        for atributo in ("_wb1", "_wb2"):
            wb = getattr(self, atributo)
            if wb is not None:
                try:
                    wb.close()
                except Exception:
                    pass
                setattr(self, atributo, None)

    def _comparar(self) -> None:
        if not self._path1 or not self._path2:
            self._estado.alerta("Elige los dos archivos a comparar.")
            return

        self._cerrar_libros()
        self._comparacion = None
        self._btn_reporte.configure(state="disabled")
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)

        self._btn_comparar.configure(state="disabled")
        self._barra.pack(side="left", padx=(12, 0))
        self._barra.start(12)
        self._estado.info("Comparando archivos...")

        p1, p2 = self._path1, self._path2
        self.run_async(lambda: compare_files(p1, p2), self._on_comparacion)

    def _on_comparacion(self, ok: bool, resultado) -> None:
        self._barra.stop()
        self._barra.pack_forget()
        self._btn_comparar.configure(state="normal")

        if not ok:
            self._estado.alerta("No se pudo completar la comparacion.")
            self.error("Error", "Algo salio mal al comparar los archivos. Intenta de nuevo.")
            return

        if not resultado.get("ok"):
            self._estado.alerta("No se pudo abrir uno de los archivos.")
            detalle = resultado.get("error")
            self.error(
                "No se pudo abrir el archivo",
                "Uno de los dos archivos esta danado, protegido con contrasena, o no "
                "es un Excel valido." + (f"\n\nDetalle: {detalle}" if detalle else ""),
            )
            return

        self._wb1 = resultado.pop("_wb1", None)
        self._wb2 = resultado.pop("_wb2", None)
        self._comparacion = resultado

        partes = []
        if resultado["sheets_only_v1"]:
            partes.append(f"Hojas solo en el archivo 1: {', '.join(resultado['sheets_only_v1'])}.")
        if resultado["sheets_only_v2"]:
            partes.append(f"Hojas solo en el archivo 2: {', '.join(resultado['sheets_only_v2'])}.")

        total_diffs = sum(len(d) for d in resultado["common_diffs"].values())

        if total_diffs == 0:
            if resultado.get("common_count", 0) == 0:
                encabezado = "Los dos archivos no tienen ninguna hoja en comun."
            else:
                encabezado = "Los archivos son identicos en las hojas comunes."
                aviso = resultado.get("data_only_warning")
                if aviso:
                    partes.append(f"Aviso: {aviso}")
            partes.insert(0, encabezado)
            self._estado.exito(" ".join(partes))
            self._cerrar_libros()
            return

        # Tope de filas en la tabla: con dos archivos grandes y muy distintos
        # puede haber cientos de miles de diferencias, y cada insert() corre
        # en el hilo de la UI. Sin tope la ventana se congela igual que sin
        # run_async. La consola capea a 30 por hoja; aca se usa un tope mas
        # generoso (500 en total) porque la tabla se puede scrollear.
        TOPE_FILAS = 500
        filas_insertadas = 0
        for hoja, diffs in resultado["common_diffs"].items():
            for d in diffs:
                if filas_insertadas >= TOPE_FILAS:
                    break
                self._tabla.insert("", "end", values=(hoja, d["celda"], d["v1"], d["v2"]))
                filas_insertadas += 1
            if filas_insertadas >= TOPE_FILAS:
                break

        if total_diffs > TOPE_FILAS:
            self._tabla.insert(
                "", "end",
                values=("...", "", f"y {total_diffs - TOPE_FILAS} mas", ""),
            )

        partes.insert(0, f"{total_diffs} diferencia(s) encontrada(s).")
        self._estado.exito(" ".join(partes))
        self._btn_reporte.configure(state="normal")

    def _generar_reporte(self) -> None:
        if not self._comparacion or self._wb1 is None or not self._path1 or not self._path2:
            return

        base, ext = os.path.splitext(self._path1)
        sugerido = _safe_output_path(f"{base}_comparado{ext}")

        destino = filedialog.asksaveasfilename(
            parent=self, title="Guardar reporte de diferencias",
            initialdir=os.path.dirname(sugerido),
            initialfile=os.path.basename(sugerido),
            defaultextension=ext, filetypes=_FILTROS,
        )
        if not destino:
            return

        if os.path.abspath(destino) in (os.path.abspath(self._path1), os.path.abspath(self._path2)):
            self.error(
                "Ruta invalida",
                "El reporte no puede guardarse con el mismo nombre que ninguno de "
                "los archivos originales (se perderian formulas/datos). Elige otra ruta.",
            )
            return

        self._comparacion["_wb1"] = self._wb1

        # _generate_diff_report pinta celdas y guarda a disco: con archivos
        # grandes puede tardar, asi que corre en el hilo de trabajo de
        # run_async para no congelar la ventana. wb1/comparacion son
        # atributos simples (no widgets), se leen aca y no se tocan de nuevo
        # hasta el callback de UI.
        path1, path2, comparacion = self._path1, self._path2, self._comparacion
        self._btn_reporte.configure(state="disabled")
        self._estado.info("Guardando reporte...")

        def _trabajo():
            _generate_diff_report(path1, path2, comparacion, destino)
            return destino

        self.run_async(_trabajo, lambda ok, res: self._on_reporte_guardado(ok, res, destino))

    def _on_reporte_guardado(self, ok: bool, resultado, destino: str) -> None:
        if not ok:
            # _generate_diff_report solo cierra/guarda wb1 en el path de
            # exito: si fallo, wb1 y wb2 siguen abiertos y utilizables para
            # reintentar sin tener que comparar de nuevo. Se reactiva el
            # boton para que el siguiente clic no caiga en silencio.
            self._btn_reporte.configure(state="normal")
            detalle = f"\n\nDetalle: {resultado}" if isinstance(resultado, OSError) else ""
            self._estado.alerta("No se pudo guardar el reporte.")
            self.error(
                "No se pudo guardar",
                "No se pudo guardar el reporte. Revisa que no este abierto en Excel "
                f"y que haya espacio en el disco.{detalle}",
            )
            return

        # _generate_diff_report ya guardo y cerro wb1; wb2 sigue abierto.
        self._wb1 = None
        self._cerrar_libros()

        self._estado.exito(f"Reporte guardado en: {destino}")
        self._btn_reporte.configure(state="disabled")
        self.aviso("Reporte guardado", f"El reporte quedo guardado en:\n\n{destino}")
