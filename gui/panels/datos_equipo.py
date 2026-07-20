"""Pantalla: Datos del equipo.

Solo lectura: muestra hostname, IP, MAC, sistema operativo, usuario, etc. Esta
pantalla NO reimplementa la recoleccion de datos, solo llama a la funcion de
logica de tools/system_info.py y la presenta en una tabla, igual que
show_system_info() hace en la consola.
"""

import tkinter as tk
from tkinter import ttk

from gui.base import EstadoLabel, ToolPanel
from tools.system_info import get_system_info

# Mismas etiquetas y orden que show_system_info() en tools/system_info.py, asi
# la version de escritorio muestra exactamente lo mismo que la de consola.
_ETIQUETAS = {
    "hostname": "Hostname",
    "ip": "IP Local",
    "mac": "MAC Address",
    "sistema": "Sistema",
    "version": "Version",
    "arquitectura": "Arquitectura",
    "procesador": "Procesador",
    "usuario": "Usuario",
    "dominio": "Dominio",
}


class PanelDatosEquipo(ToolPanel):
    TITULO = "Ver datos del equipo"
    DESCRIPCION = (
        "Muestra el nombre del equipo, la direccion IP, el usuario y otros "
        "datos basicos. Util cuando soporte tecnico te los pide por telefono."
    )

    def build(self) -> None:
        self._info: dict = {}

        # --- Accion --------------------------------------------------------
        # Se empaqueta ANTES que la tabla y anclado abajo, si no la tabla
        # (expand=True) se come el espacio y el boton queda fuera de la
        # ventana.
        acciones = ttk.Frame(self.body, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(12, 0))

        self._btn_actualizar = ttk.Button(
            acciones, text="Actualizar", style="Accent.TButton",
            command=self._actualizar,
        )
        self._btn_actualizar.pack(side="left")

        self._btn_copiar = ttk.Button(
            acciones, text="Copiar todo", command=self._copiar, state="disabled",
        )
        self._btn_copiar.pack(side="left", padx=(10, 0))

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(0, 10))

        # --- Tabla -----------------------------------------------------
        tabla_frame = ttk.Frame(self.body, style="Panel.TFrame")
        tabla_frame.pack(fill="both", expand=True)

        columnas = ("campo", "valor")
        self._tabla = ttk.Treeview(
            tabla_frame, columns=columnas, show="headings", height=9,
        )
        self._tabla.heading("campo", text="Dato")
        self._tabla.heading("valor", text="Valor")
        self._tabla.column("campo", width=160, anchor="w", stretch=False)
        self._tabla.column("valor", width=420, anchor="w", stretch=True)

        scroll_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=scroll_y.set)
        self._tabla.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="left", fill="y")

        # Se carga sola al abrir la pantalla: es solo lectura, no hace falta
        # que el usuario pida "Actualizar" la primera vez.
        self._actualizar()

    # ------------------------------------------------------------------

    def _actualizar(self) -> None:
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
        self._btn_copiar.configure(state="disabled")
        self._btn_actualizar.configure(state="disabled")
        self._estado.info("Recopilando informacion del equipo...")

        self.run_async(get_system_info, self._on_listo)

    def _on_listo(self, ok: bool, resultado) -> None:
        self._btn_actualizar.configure(state="normal")

        if not ok:
            self._estado.alerta("No se pudo obtener la informacion del equipo.")
            self.error(
                "Error",
                "No se pudo recopilar la informacion del equipo. Intenta de nuevo.",
            )
            return

        self._info = resultado
        if not self._info:
            self._estado.alerta("No hay nada que mostrar.")
            return

        for clave, etiqueta in _ETIQUETAS.items():
            self._tabla.insert("", "end", values=(etiqueta, self._info.get(clave, "?")))

        self._btn_copiar.configure(state="normal")
        self._estado.exito("Listo.")

    def _copiar(self) -> None:
        if not self._info:
            return
        lineas = [
            f"{etiqueta}: {self._info.get(clave, '?')}"
            for clave, etiqueta in _ETIQUETAS.items()
        ]
        texto = "\n".join(lineas)
        self.clipboard_clear()
        self.clipboard_append(texto)
        self._estado.exito("Datos copiados al portapapeles.")
