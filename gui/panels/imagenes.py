"""Pantalla: Conversor de Imagenes.

Solo presenta la logica que ya existe en tools/image_converter.py; la
conversion (Pillow, manejo de EXIF/transparencia/multiframe, ruta de salida
segura) NO se reimplementa aqui.
"""

import os
import tkinter as tk
from tkinter import filedialog, ttk

from gui.base import EstadoLabel, ToolPanel
from tools.image_converter import (
    IMAGE_EXTENSIONS,
    SUPPORTED_FORMATS,
    _collect_images,
    _convert_image,
    _get_pillow,
)

_TIPOS_DIALOGO = [
    ("Imagenes", " ".join(f"*{ext}" for ext in sorted(IMAGE_EXTENSIONS))),
    ("Todos los archivos", "*.*"),
]


class PanelImagenes(ToolPanel):
    TITULO = "Convertir imagenes"
    DESCRIPCION = (
        "Convierte imagenes entre PNG, JPG, BMP, WEBP e ICO. Elige uno o "
        "varios archivos (o una carpeta completa), el formato destino y "
        "donde guardar el resultado."
    )

    def build(self) -> None:
        self._archivos: list[str] = []

        origen = ttk.Frame(self.body, style="Panel.TFrame")
        origen.pack(fill="x")

        ttk.Button(
            origen, text="Elegir archivo(s)...", command=self._elegir_archivos,
        ).pack(side="left")
        ttk.Button(
            origen, text="Elegir carpeta...", command=self._elegir_carpeta,
        ).pack(side="left", padx=(10, 0))

        self._label_origen = ttk.Label(self.body, text="Ningun archivo seleccionado.", style="Panel.TLabel")
        self._label_origen.pack(anchor="w", pady=(8, 0))

        opciones = ttk.Frame(self.body, style="Panel.TFrame")
        opciones.pack(fill="x", pady=(14, 0))

        ttk.Label(opciones, text="Formato destino:", style="Panel.TLabel").pack(side="left")
        self._var_formato = tk.StringVar(value=next(iter(SUPPORTED_FORMATS)))
        combo = ttk.Combobox(
            opciones, textvariable=self._var_formato, state="readonly",
            values=list(SUPPORTED_FORMATS.keys()), width=10,
        )
        combo.pack(side="left", padx=(10, 20))

        ttk.Label(opciones, text="Carpeta de salida:", style="Panel.TLabel").pack(side="left")
        self._var_destino = tk.StringVar()
        ttk.Entry(opciones, textvariable=self._var_destino, width=30).pack(
            side="left", padx=(10, 6)
        )
        ttk.Button(
            opciones, text="Elegir...", command=self._elegir_destino,
        ).pack(side="left")

        acciones = ttk.Frame(self.body, style="Panel.TFrame")
        acciones.pack(fill="x", pady=(14, 0))

        self._boton_convertir = ttk.Button(
            acciones, text="Convertir", style="Accent.TButton", command=self._convertir,
        )
        self._boton_convertir.pack(side="left")

        self._barra = ttk.Progressbar(acciones, mode="determinate", length=220)
        self._barra.pack(side="left", padx=(16, 0))

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(10, 0))

        tabla_frame = ttk.Frame(self.body, style="Panel.TFrame")
        tabla_frame.pack(fill="both", expand=True, pady=(4, 0))

        columnas = ("archivo", "resultado")
        self._tabla = ttk.Treeview(
            tabla_frame, columns=columnas, show="headings", height=10,
        )
        self._tabla.heading("archivo", text="Archivo")
        self._tabla.heading("resultado", text="Resultado")
        self._tabla.column("archivo", width=340, anchor="w", stretch=True)
        self._tabla.column("resultado", width=280, anchor="w", stretch=True)

        scroll_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=scroll_y.set)
        self._tabla.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="left", fill="y")

    # ------------------------------------------------------------------

    def _elegir_archivos(self) -> None:
        rutas = filedialog.askopenfilenames(
            title="Elegir imagenes", filetypes=_TIPOS_DIALOGO, parent=self,
        )
        if not rutas:
            return
        self._archivos = list(rutas)
        self._label_origen.configure(
            text=f"{len(self._archivos)} archivo(s) seleccionado(s)."
        )
        if not self._var_destino.get():
            self._var_destino.set(os.path.dirname(self._archivos[0]) or ".")

    def _elegir_carpeta(self) -> None:
        carpeta = filedialog.askdirectory(title="Elegir carpeta con imagenes", parent=self)
        if not carpeta:
            return
        collected = _collect_images(carpeta)
        if collected["error"]:
            self._estado.alerta(collected["error"])
            self._archivos = []
            self._label_origen.configure(text="Ningun archivo seleccionado.")
            return
        self._archivos = collected["images"]
        if not self._archivos:
            self._estado.alerta("No se encontraron imagenes en esa carpeta.")
            self._label_origen.configure(text="Ningun archivo seleccionado.")
            return
        self._estado.limpiar()
        self._label_origen.configure(
            text=f"{len(self._archivos)} imagen(es) encontrada(s) en la carpeta."
        )
        if not self._var_destino.get():
            target = self._var_formato.get()
            self._var_destino.set(os.path.join(carpeta, f"convertido_{target}"))

    def _elegir_destino(self) -> None:
        carpeta = filedialog.askdirectory(title="Carpeta de salida", parent=self)
        if carpeta:
            self._var_destino.set(carpeta)

    # ------------------------------------------------------------------

    def _convertir(self) -> None:
        self._estado.limpiar()
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)

        if not self._archivos:
            self._estado.alerta("Primero elige uno o varios archivos, o una carpeta.")
            return

        destino = self._var_destino.get().strip().strip('"')
        if not destino:
            self._estado.alerta("Elige una carpeta de salida.")
            return

        Image = _get_pillow()
        if not Image:
            self._estado.alerta("Pillow no esta instalado. Ejecuta: pip install Pillow")
            return

        try:
            os.makedirs(destino, exist_ok=True)
        except OSError as e:
            self._estado.alerta(f"No se pudo crear la carpeta de salida: {e}")
            return

        target_ext = SUPPORTED_FORMATS[self._var_formato.get()]
        archivos = list(self._archivos)

        self._boton_convertir.configure(state="disabled")
        self._barra.configure(maximum=len(archivos), value=0)
        self._estado.info("Convirtiendo...")

        def work(progreso):
            resultados = []
            for src in archivos:
                r = _convert_image(Image, src, target_ext, destino)
                resultados.append((src, r))
                progreso(len(resultados))
            return resultados

        def on_progress(hechos):
            self._barra.configure(value=hechos)

        def on_done(ok, carga):
            self._boton_convertir.configure(state="normal")
            if not ok:
                self._estado.alerta(f"Error inesperado: {carga}")
                return

            convertidos = 0
            fallidos = 0
            for src, r in carga:
                nombre = os.path.basename(src)
                if r["ok"]:
                    convertidos += 1
                    texto = "Convertido"
                    if r["multiframe"]:
                        texto += f" (solo 1er frame de {r['multiframe']})"
                    self._tabla.insert("", "end", values=(nombre, texto))
                else:
                    fallidos += 1
                    self._tabla.insert("", "end", values=(nombre, f"Error: {r['error']}"))

            resumen = f"Convertidos: {convertidos}"
            if fallidos:
                resumen += f" | Fallidos: {fallidos}"
                self._estado.alerta(resumen)
            else:
                self._estado.exito(resumen + f" | Carpeta: {destino}")

        self.run_async(work, on_done, on_progress=on_progress)
