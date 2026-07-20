"""Pantalla: Respaldo Rapido a USB.

Replica el flujo de tools/usb_backup.py (usb_backup_menu): copia el
Escritorio y Documentos del usuario a una carpeta nueva dentro de la USB
elegida. No es una operacion destructiva (no borra ni sobrescribe archivos
del usuario, solo copia hacia la USB), pero igual pide confirmar antes de
empezar porque puede tardar.
"""

import os
import platform
import shutil
import tkinter as tk
from tkinter import messagebox, ttk

from config import BACKUP_SOURCES
from gui.base import EstadoLabel, ToolPanel
from tools import format_size, get_removable_drives
from tools.usb_backup import _calculate_backup_size, _copy_files


class PanelUsbRespaldo(ToolPanel):
    TITULO = "Respaldar archivos a USB"
    DESCRIPCION = (
        "Copia tu Escritorio y tus Documentos a la USB, en una carpeta nueva "
        "con la fecha de hoy. Tus archivos originales no se tocan."
    )

    def build(self) -> None:
        self._drives: list[str] = []
        self._total_bytes = 0
        self._valid_sources: list[str] = []

        fila_unidad = ttk.Frame(self.body, style="Panel.TFrame")
        fila_unidad.pack(fill="x")

        ttk.Label(fila_unidad, text="Unidad destino:", style="Panel.TLabel").pack(side="left")

        self._var_drive = tk.StringVar()
        self._combo = ttk.Combobox(
            fila_unidad, textvariable=self._var_drive, state="readonly", width=10,
        )
        self._combo.pack(side="left", padx=(10, 10))

        ttk.Button(
            fila_unidad, text="Actualizar lista", command=self._detectar,
        ).pack(side="left")

        self._btn_calcular = ttk.Button(
            fila_unidad, text="Ver que se va a respaldar", style="Accent.TButton",
            command=self._calcular, state="disabled",
        )
        self._btn_calcular.pack(side="left", padx=(10, 0))

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(12, 6))

        self._barra = ttk.Progressbar(self.body, mode="determinate")

        # --- Boton principal, anclado abajo ---------------------------------
        acciones = ttk.Frame(self.body, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(12, 0))

        self._btn_respaldar = ttk.Button(
            acciones, text="Iniciar respaldo", style="Accent.TButton",
            command=self._iniciar_respaldo, state="disabled",
        )
        self._btn_respaldar.pack(side="left")

        self._zona = ttk.Frame(self.body, style="Panel.TFrame")
        self._zona.pack(fill="both", expand=True, pady=(10, 0))

        self._detectar()

    # ------------------------------------------------------------------
    # Deteccion de unidades
    # ------------------------------------------------------------------

    def _detectar(self) -> None:
        self._drives = get_removable_drives()
        self._combo.configure(values=self._drives)

        for w in self._zona.winfo_children():
            w.destroy()
        self._btn_respaldar.configure(state="disabled")

        if not self._drives:
            self._var_drive.set("")
            self._btn_calcular.configure(state="disabled")
            self._estado.alerta(
                "No se detecto ninguna USB conectada. Conecta una y dale a "
                "Actualizar lista."
            )
            return

        if self._var_drive.get() not in self._drives:
            self._var_drive.set(self._drives[0])
        self._btn_calcular.configure(state="normal")
        self._estado.info("Elige la unidad destino y dale a 'Ver que se va a respaldar'.")

    # ------------------------------------------------------------------
    # Calculo previo
    # ------------------------------------------------------------------

    def _calcular(self) -> None:
        drive = self._var_drive.get()
        if not drive:
            return

        self._valid_sources = [s for s in BACKUP_SOURCES if os.path.isdir(s)]
        if not self._valid_sources:
            self._estado.alerta(
                "No se encontraron las carpetas de Escritorio o Documentos "
                "en esta computadora."
            )
            return

        for w in self._zona.winfo_children():
            w.destroy()
        self._btn_calcular.configure(state="disabled")
        self._btn_respaldar.configure(state="disabled")
        self._estado.info("Calculando cuanto se va a respaldar...")

        def trabajo():
            return _calculate_backup_size(self._valid_sources)

        self.run_async(trabajo, lambda ok, res: self._calculo_listo(ok, res, drive))

    def _calculo_listo(self, ok: bool, resultado, drive: str) -> None:
        self._btn_calcular.configure(state="normal" if self._drives else "disabled")

        if not ok:
            self._estado.alerta("No se pudo calcular el tamano del respaldo. Intenta de nuevo.")
            return

        total_bytes, file_count = resultado
        self._total_bytes = total_bytes

        try:
            free = shutil.disk_usage(drive).free
        except OSError:
            free = 0

        for w in self._zona.winfo_children():
            w.destroy()

        resumen = ttk.Frame(self._zona, style="Panel.TFrame")
        resumen.pack(anchor="w", fill="x")

        filas = [
            ("Carpetas de origen", ", ".join(os.path.basename(s) for s in self._valid_sources)),
            ("Archivos a copiar", str(file_count)),
            ("Tamano total", format_size(total_bytes)),
            ("Espacio libre en la USB", format_size(free)),
        ]
        for etiqueta, valor in filas:
            fila = ttk.Frame(resumen, style="Panel.TFrame")
            fila.pack(anchor="w", fill="x", pady=1)
            ttk.Label(fila, text=f"{etiqueta}:", style="Panel.TLabel", width=22).pack(side="left")
            ttk.Label(fila, text=str(valor), style="Panel.TLabel").pack(side="left")

        if total_bytes > free:
            self._estado.alerta("No hay suficiente espacio libre en la USB para este respaldo.")
            self._btn_respaldar.configure(state="disabled")
        else:
            self._estado.info("Listo para respaldar cuando quieras.")
            self._btn_respaldar.configure(state="normal")

    # ------------------------------------------------------------------
    # Respaldo
    # ------------------------------------------------------------------

    def _iniciar_respaldo(self) -> None:
        if getattr(self, "_respaldando", False):
            return

        drive = self._var_drive.get()
        if not drive or not self._valid_sources:
            return

        hostname = platform.node()
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        dest_base = os.path.join(drive, f"Respaldo_{hostname}_{date_str}")

        if not messagebox.askyesno(
            "Iniciar respaldo",
            f"Se va a copiar a:\n\n{dest_base}\n\nEsto puede tardar varios "
            "minutos dependiendo de cuantos archivos tengas. Continuar?",
            parent=self,
        ):
            return

        self._respaldando = True
        self._btn_respaldar.configure(state="disabled")
        self._btn_calcular.configure(state="disabled")
        self._combo.configure(state="disabled")
        self._barra.configure(maximum=max(self._total_bytes, 1), value=0)
        self._barra.pack(fill="x", pady=(4, 0))
        self._estado.info("Copiando archivos...")

        def trabajo(progreso):
            return _copy_files(
                self._valid_sources, dest_base,
                progress_callback=lambda n: progreso(n),
            )

        # destructivo=False: esto COPIA hacia la USB, no borra ni mueve nada
        # del usuario (los originales en Escritorio/Documentos no se tocan).
        self.run_async(
            trabajo, lambda ok, res: self._respaldo_listo(ok, res, dest_base),
            on_progress=self._on_progreso, destructivo=False,
        )

    def _on_progreso(self, avance: int) -> None:
        try:
            self._barra.configure(value=min(self._barra["value"] + avance, self._barra["maximum"]))
        except tk.TclError:
            pass

    def _respaldo_listo(self, ok: bool, resultado, dest_base: str) -> None:
        self._respaldando = False
        self._barra.stop() if hasattr(self._barra, "stop") else None
        self._barra.pack_forget()
        if self._drives:
            self._btn_calcular.configure(state="normal")
            self._btn_respaldar.configure(state="normal")
        self._combo.configure(state="readonly")

        if not ok:
            self._estado.alerta(
                "Algo fallo durante el respaldo. Puede que la USB se haya "
                "desconectado a la mitad. Revisa la unidad antes de retirarla."
            )
            return

        copied, skipped, failed = resultado
        partes = [f"Listo: {copied} archivo(s) copiados."]
        if skipped:
            partes.append(f"{skipped} sin cambios (ya estaban al dia).")
        if failed:
            partes.append(f"{len(failed)} no se pudieron copiar.")
        partes.append(f"Ubicacion: {dest_base}")

        if failed:
            self._estado.alerta(" ".join(partes))
        else:
            self._estado.exito(" ".join(partes))
