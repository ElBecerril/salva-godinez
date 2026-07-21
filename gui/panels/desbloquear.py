"""Pantalla: Desbloquear archivo en uso.

Presenta tools/file_unlocker.py: _find_locking_processes() detecta que
procesos tienen abierto un archivo (via Restart Manager, con un fallback de
PowerShell que NO ve archivos de datos abiertos) y _kill_process() cierra un
proceso por PID. Ninguna de las dos se reimplementa aqui.
"""

import os
import tkinter as tk
from tkinter import filedialog, ttk

from gui.base import EstadoLabel, ToolPanel
from tools.file_unlocker import _find_locking_processes, _kill_process


class PanelDesbloquear(ToolPanel):
    TITULO = "Desbloquear archivo en uso"
    DESCRIPCION = (
        "Si Windows no te deja borrar, mover o guardar un archivo porque "
        "'esta abierto en otro programa', elige el archivo aqui para ver que "
        "procesos lo estan usando y, si quieres, cerrarlos a la fuerza."
    )

    def build(self) -> None:
        self._filepath: str | None = None
        self._por_iid: dict[str, dict] = {}

        # --- Elegir archivo -------------------------------------------------
        fila_archivo = ttk.Frame(self.body, style="Panel.TFrame")
        fila_archivo.pack(fill="x")
        ttk.Button(
            fila_archivo, text="Elegir archivo bloqueado...", command=self._elegir_archivo,
        ).pack(side="left")
        self._label_archivo = ttk.Label(
            fila_archivo, text="Ningun archivo elegido.", style="Panel.TLabel",
        )
        self._label_archivo.pack(side="left", padx=(12, 0))

        # --- Buscar -----------------------------------------------------
        fila_accion = ttk.Frame(self.body, style="Panel.TFrame")
        fila_accion.pack(fill="x", pady=(14, 0))
        self._btn_buscar = ttk.Button(
            fila_accion, text="Buscar procesos", style="Accent.TButton",
            command=self._buscar, state="disabled",
        )
        self._btn_buscar.pack(side="left")
        self._barra = ttk.Progressbar(fila_accion, mode="indeterminate", length=180)

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(10, 6))

        # --- Cerrar procesos (abajo, antes de la tabla) ------------------
        acciones = ttk.Frame(self.body, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(12, 0))
        self._btn_cerrar = ttk.Button(
            acciones, text="Cerrar proceso(s) seleccionado(s)", style="Danger.TButton",
            command=self._cerrar_seleccionados, state="disabled",
        )
        self._btn_cerrar.pack(side="left")

        # --- Tabla de procesos ------------------------------------------
        tabla_frame = ttk.Frame(self.body, style="Panel.TFrame")
        tabla_frame.pack(fill="both", expand=True, pady=(4, 0))

        columnas = ("pid", "proceso")
        self._tabla = ttk.Treeview(
            tabla_frame, columns=columnas, show="headings", height=8,
            selectmode="extended",
        )
        self._tabla.heading("pid", text="PID")
        self._tabla.heading("proceso", text="Proceso")
        self._tabla.column("pid", width=90, anchor="w", stretch=False)
        self._tabla.column("proceso", width=320, anchor="w", stretch=True)

        scroll_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=scroll_y.set)
        self._tabla.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="left", fill="y")
        self._tabla.bind("<<TreeviewSelect>>", self._on_seleccion)

    # ------------------------------------------------------------------

    def _elegir_archivo(self) -> None:
        ruta = filedialog.askopenfilename(
            parent=self, title="Elige el archivo bloqueado",
            filetypes=[("Todos los archivos", "*.*")],
        )
        if not ruta:
            return
        self._filepath = ruta
        self._label_archivo.configure(text=os.path.basename(ruta))
        self._btn_buscar.configure(state="normal")
        self._estado.limpiar()
        self._btn_cerrar.configure(state="disabled")
        self._por_iid.clear()
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)

    def _buscar(self) -> None:
        if not self._filepath:
            return

        self._por_iid.clear()
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
        self._btn_cerrar.configure(state="disabled")

        self._btn_buscar.configure(state="disabled")
        self._barra.pack(side="left", padx=(12, 0))
        self._barra.start(12)
        self._estado.info("Buscando procesos que bloquean el archivo...")

        ruta = self._filepath
        self.run_async(lambda: _find_locking_processes(ruta), self._on_busqueda_lista)

    def _on_busqueda_lista(self, ok: bool, resultado) -> None:
        self._barra.stop()
        self._barra.pack_forget()
        self._btn_buscar.configure(state="normal")

        if not ok:
            self._estado.alerta("No se pudo revisar el archivo.")
            self.error("Error", "Algo salio mal al buscar los procesos. Intenta de nuevo.")
            return

        procesos = resultado["procesos"]
        certero = resultado["certero"]

        if not procesos:
            if certero:
                self._estado.exito("No se detectaron procesos bloqueando el archivo.")
            else:
                self._estado.alerta(
                    "No se pudo determinar que proceso bloquea el archivo. El metodo "
                    "de deteccion disponible no alcanza a ver documentos abiertos "
                    "(por ejemplo, un Excel o Word abierto). El archivo puede seguir "
                    "bloqueado aunque no se haya detectado ningun proceso."
                )
            return

        for i, p in enumerate(procesos):
            iid = str(i)
            self._por_iid[iid] = p
            self._tabla.insert("", "end", iid=iid, values=(p["pid"], p["nombre"]))

        self._estado.info(
            f"Se encontraron {len(procesos)} proceso(s). Selecciona los que quieras cerrar."
        )

    def _on_seleccion(self, _evento=None) -> None:
        self._btn_cerrar.configure(
            state="normal" if self._tabla.selection() else "disabled"
        )

    def _cerrar_seleccionados(self) -> None:
        seleccion = self._tabla.selection()
        if not seleccion:
            return

        procesos = [self._por_iid[iid] for iid in seleccion if iid in self._por_iid]
        if not procesos:
            return

        nombres = ", ".join(f"{p['nombre']} (PID {p['pid']})" for p in procesos)
        if not self.confirmar_destructivo(
            "Cerrar procesos",
            f"Vas a forzar el cierre de {len(procesos)} proceso(s):\n\n{nombres}\n\n"
            "Cualquier trabajo sin guardar en esos programas se perdera. "
            "Seguro que quieres continuar?",
        ):
            return

        self._btn_cerrar.configure(state="disabled")
        self._estado.info("Cerrando proceso(s)...")

        def trabajo():
            resultados = []
            for p in procesos:
                ok = _kill_process(p["pid"])
                resultados.append({"pid": p["pid"], "nombre": p["nombre"], "ok": ok})
            return resultados

        # destructivo=True: fuerza el cierre de programas del usuario, asi que
        # el hilo no es daemon y la ventana no se deja cerrar hasta que termine.
        self.run_async(trabajo, self._on_cierre_listo, destructivo=True)

    def _on_cierre_listo(self, ok: bool, resultado) -> None:
        if self._btn_cerrar.winfo_exists():
            self._on_seleccion()

        if not ok:
            self._estado.alerta("No se pudo completar el cierre de procesos.")
            self.error("Error", "Algo salio mal al cerrar los procesos. Intenta de nuevo.")
            return

        cerrados = 0
        fallidos = []
        for r in resultado:
            if r["ok"]:
                cerrados += 1
                for iid, p in list(self._por_iid.items()):
                    if p["pid"] == r["pid"] and self._tabla.exists(iid):
                        self._tabla.delete(iid)
                        del self._por_iid[iid]
            else:
                fallidos.append(r["nombre"])

        texto = f"{cerrados} proceso(s) cerrado(s)."
        if fallidos:
            texto += f" No se pudo cerrar: {', '.join(fallidos)}."
        self._estado.exito(texto) if cerrados else self._estado.alerta(texto)
