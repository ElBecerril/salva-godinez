"""Pantalla: Revisar Estado de la USB.

Replica el flujo de tools/usb_health.py (usb_health_menu): informacion
basica de la unidad, y de forma opcional (porque tardan) una prueba de
velocidad, una verificacion rapida de autenticidad y chkdsk en modo lectura.
Ninguna de estas operaciones borra ni modifica archivos del usuario.
"""

import tkinter as tk
from tkinter import ttk

from gui.base import EstadoLabel, ToolPanel
from tools import format_size, get_removable_drives
from tools.usb_health import (
    _check_filesystem,
    _detect_fake_usb,
    _get_usb_info,
    _speed_test,
)


class PanelUsbEstado(ToolPanel):
    TITULO = "Revisar estado de la USB"
    DESCRIPCION = (
        "Muestra el tamano, espacio libre y salud de tu USB. Tambien puedes "
        "medir su velocidad y revisar si tiene errores. Nada de esto borra "
        "archivos."
    )

    def build(self) -> None:
        self._drives: list[str] = []
        self._info: dict = {}

        fila_unidad = ttk.Frame(self.body, style="Panel.TFrame")
        fila_unidad.pack(fill="x")

        ttk.Label(fila_unidad, text="Unidad USB:", style="Panel.TLabel").pack(side="left")

        self._var_drive = tk.StringVar()
        self._combo = ttk.Combobox(
            fila_unidad, textvariable=self._var_drive, state="readonly", width=10,
        )
        self._combo.pack(side="left", padx=(10, 10))

        self._btn_detectar = ttk.Button(
            fila_unidad, text="Actualizar lista", command=self._detectar,
        )
        self._btn_detectar.pack(side="left")

        self._btn_revisar = ttk.Button(
            fila_unidad, text="Revisar", style="Accent.TButton",
            command=self._revisar, state="disabled",
        )
        self._btn_revisar.pack(side="left", padx=(10, 0))

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(12, 6))

        # --- Botones de diagnostico, anclados abajo -------------------------
        acciones = ttk.Frame(self.body, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(12, 0))

        self._btn_diag = ttk.Button(
            acciones, text="Probar velocidad y autenticidad", style="Accent.TButton",
            command=self._diagnosticar, state="disabled",
        )
        self._btn_diag.pack(side="left")

        self._btn_chkdsk = ttk.Button(
            acciones, text="Revisar errores del sistema de archivos (mas lento)",
            command=self._chkdsk, state="disabled",
        )
        self._btn_chkdsk.pack(side="left", padx=(10, 0))

        # --- Zona de resultados ---------------------------------------------
        self._zona = ttk.Frame(self.body, style="Panel.TFrame")
        self._zona.pack(fill="both", expand=True, pady=(6, 0))

        self._detectar()

    # ------------------------------------------------------------------
    # Deteccion de unidades
    # ------------------------------------------------------------------

    def _detectar(self) -> None:
        self._drives = get_removable_drives()
        self._combo.configure(values=self._drives)

        for w in self._zona.winfo_children():
            w.destroy()

        if not self._drives:
            self._var_drive.set("")
            self._btn_revisar.configure(state="disabled")
            self._btn_diag.configure(state="disabled")
            self._btn_chkdsk.configure(state="disabled")
            self._estado.alerta(
                "No se detecto ninguna USB conectada. Conecta una y dale a "
                "Actualizar lista."
            )
            return

        if self._var_drive.get() not in self._drives:
            self._var_drive.set(self._drives[0])
        self._btn_revisar.configure(state="normal")
        self._btn_diag.configure(state="disabled")
        self._btn_chkdsk.configure(state="disabled")
        self._estado.info("Elige la unidad y dale a Revisar.")

    # ------------------------------------------------------------------
    # Informacion basica
    # ------------------------------------------------------------------

    def _revisar(self) -> None:
        drive = self._var_drive.get()
        if not drive:
            return

        for w in self._zona.winfo_children():
            w.destroy()
        self._btn_revisar.configure(state="disabled")
        self._btn_diag.configure(state="disabled")
        self._btn_chkdsk.configure(state="disabled")
        self._btn_detectar.configure(state="disabled")
        self._combo.configure(state="disabled")
        self._estado.info(f"Obteniendo informacion de {drive}...")

        def trabajo():
            return _get_usb_info(drive)

        self.run_async(trabajo, lambda ok, res: self._info_lista(ok, res, drive))

    def _info_lista(self, ok: bool, resultado, drive: str) -> None:
        self._combo.configure(state="readonly")
        self._btn_detectar.configure(state="normal")
        self._btn_revisar.configure(state="normal" if self._drives else "disabled")

        if not ok:
            self._estado.alerta(
                "No se pudo obtener informacion de la unidad. Puede que se "
                "haya desconectado. Intenta de nuevo."
            )
            return

        self._info = resultado
        self._btn_diag.configure(state="normal" if self._drives else "disabled")
        self._btn_chkdsk.configure(state="normal" if self._drives else "disabled")
        self._estado.info(f"Informacion de {drive}:")
        self._pintar_info(drive, resultado)

    def _pintar_info(self, drive: str, info: dict) -> None:
        for w in self._zona.winfo_children():
            w.destroy()

        tabla = ttk.Frame(self._zona, style="Panel.TFrame")
        tabla.pack(anchor="w", fill="x")

        filas = [
            ("Unidad", drive),
            ("Etiqueta", info.get("label", "?")),
            ("Sistema de archivos", info.get("filesystem", "?")),
            ("Tamano total", format_size(info.get("size", 0))),
            ("Espacio libre", format_size(info.get("free", 0))),
            ("Estado de salud", info.get("health", "?")),
        ]
        for etiqueta, valor in filas:
            fila = ttk.Frame(tabla, style="Panel.TFrame")
            fila.pack(anchor="w", fill="x", pady=1)
            ttk.Label(fila, text=f"{etiqueta}:", style="Panel.TLabel", width=20).pack(side="left")
            ttk.Label(fila, text=str(valor), style="Panel.TLabel").pack(side="left")

        self._resultados_diag = ttk.Frame(self._zona, style="Panel.TFrame")
        self._resultados_diag.pack(anchor="w", fill="x", pady=(16, 0))

    # ------------------------------------------------------------------
    # Diagnosticos opcionales (velocidad + autenticidad)
    # ------------------------------------------------------------------

    def _diagnosticar(self) -> None:
        drive = self._var_drive.get()
        if not drive:
            return

        self._btn_diag.configure(state="disabled")
        self._btn_chkdsk.configure(state="disabled")
        self._btn_revisar.configure(state="disabled")
        self._btn_detectar.configure(state="disabled")
        self._combo.configure(state="disabled")
        self._estado.info("Midiendo velocidad y revisando autenticidad, un momento...")

        reported_size = self._info.get("size", 0)

        def trabajo():
            speed = _speed_test(drive)
            fake = _detect_fake_usb(drive, reported_size=reported_size)
            return speed, fake

        self.run_async(trabajo, self._diagnostico_listo)

    def _diagnostico_listo(self, ok: bool, resultado) -> None:
        self._combo.configure(state="readonly")
        self._btn_detectar.configure(state="normal")
        if self._drives:
            self._btn_diag.configure(state="normal")
            self._btn_chkdsk.configure(state="normal")
            self._btn_revisar.configure(state="normal")

        # Cinturon extra: si mientras corria el trabajo el usuario le dio a
        # "Revisar" o "Actualizar lista", la zona de resultados ya no existe.
        if not hasattr(self, "_resultados_diag") or not self._resultados_diag.winfo_exists():
            return

        if not ok:
            self._estado.alerta(
                "No se pudo completar la prueba. Puede que la USB se haya "
                "desconectado. Intenta de nuevo."
            )
            return

        speed, fake = resultado
        self._estado.info("Resultado de la prueba:")

        for w in self._resultados_diag.winfo_children():
            w.destroy()

        ttk.Label(self._resultados_diag, text="Velocidad", style="Section.TLabel").pack(anchor="w")
        if "error" in speed:
            ttk.Label(
                self._resultados_diag, text=f"  No se pudo medir: {speed['error']}",
                style="Panel.TLabel",
            ).pack(anchor="w")
        else:
            ttk.Label(
                self._resultados_diag,
                text=f"  Escritura: {speed['write_mbps']:.1f} MB/s    "
                     f"Lectura: {speed['read_mbps']:.1f} MB/s",
                style="Panel.TLabel",
            ).pack(anchor="w")

        ttk.Label(
            self._resultados_diag, text="Autenticidad (prueba rapida, no concluyente)",
            style="Section.TLabel",
        ).pack(anchor="w", pady=(10, 0))
        ttk.Label(
            self._resultados_diag, text=f"  {fake.get('detail', '?')}",
            style="Panel.TLabel",
        ).pack(anchor="w")

    # ------------------------------------------------------------------
    # chkdsk (solo lectura, mas lento: boton aparte como en consola)
    # ------------------------------------------------------------------

    def _chkdsk(self) -> None:
        drive = self._var_drive.get()
        if not drive:
            return

        self._btn_diag.configure(state="disabled")
        self._btn_chkdsk.configure(state="disabled")
        self._btn_revisar.configure(state="disabled")
        self._btn_detectar.configure(state="disabled")
        self._combo.configure(state="disabled")
        self._estado.info("Revisando el sistema de archivos, esto puede tardar varios minutos...")

        def trabajo():
            return _check_filesystem(drive)

        self.run_async(trabajo, self._chkdsk_listo)

    def _chkdsk_listo(self, ok: bool, resultado) -> None:
        self._combo.configure(state="readonly")
        self._btn_detectar.configure(state="normal")
        if self._drives:
            self._btn_diag.configure(state="normal")
            self._btn_chkdsk.configure(state="normal")
            self._btn_revisar.configure(state="normal")

        if not ok:
            self._estado.alerta(
                "No se pudo completar la revision. Puede que la USB se haya "
                "desconectado a medio proceso."
            )
            return

        if resultado.get("ok"):
            self._estado.exito("No se detectaron errores en el sistema de archivos.")
        else:
            self._estado.alerta(
                "Se detectaron posibles errores en el sistema de archivos de "
                "la USB. Considera respaldar tus archivos importantes."
            )
