"""Pantalla: Quitar Virus de la USB.

Replica el flujo de tools/usb_disinfect.py (usb_disinfect_menu): detectar
unidades, escanear, y ofrecer borrar SOLO las amenazas de riesgo Alto que el
usuario marque una por una. Las de riesgo Medio (ejecutables sueltos, accesos
directos sospechosos) nunca se borran desde aqui, igual que en consola: se
listan como aviso para revision manual.

Esta es la pantalla mas peligrosa de las cuatro: BORRA archivos de la USB del
usuario. Nada viene pre-marcado y el borrado exige confirmacion explicita con
default en No (ver reglas de operaciones destructivas del proyecto).
"""

import os
import tkinter as tk
from tkinter import ttk

from gui.base import EstadoLabel, ToolPanel
from tools import get_removable_drives
from tools.usb_disinfect import clean_usb, scan_usb, unhide_folders


class PanelUsbVirus(ToolPanel):
    TITULO = "Quitar virus de la USB"
    DESCRIPCION = (
        "Busca en tu USB los archivos que usan los virus para copiarse solos "
        "(autorun.inf, programas con nombres sospechosos, accesos directos "
        "que en realidad abren un programa). Tu decides cuales se borran."
    )

    def build(self) -> None:
        self._drives: list[str] = []
        self._threats: list[dict] = []
        self._vars_alto: dict[int, tk.BooleanVar] = {}

        # --- Unidad -----------------------------------------------------
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

        self._btn_escanear = ttk.Button(
            fila_unidad, text="Escanear", style="Accent.TButton",
            command=self._escanear, state="disabled",
        )
        self._btn_escanear.pack(side="left", padx=(10, 0))

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(12, 6))

        # --- Acciones (ancladas abajo, antes de la zona que expande) -------
        acciones = ttk.Frame(self.body, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(12, 0))

        self._btn_borrar = ttk.Button(
            acciones, text="Eliminar lo marcado", style="Danger.TButton",
            command=self._eliminar, state="disabled",
        )
        self._btn_borrar.pack(side="left")

        self._btn_restaurar = ttk.Button(
            acciones, text="Restaurar carpetas ocultas", style="Accent.TButton",
            command=self._restaurar_ocultas, state="disabled",
        )
        self._btn_restaurar.pack(side="left", padx=(10, 0))

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

        if not self._drives:
            self._var_drive.set("")
            self._btn_escanear.configure(state="disabled")
            self._btn_borrar.configure(state="disabled")
            self._btn_restaurar.configure(state="disabled")
            self._estado.alerta(
                "No se detecto ninguna USB conectada. Conecta una y dale a "
                "Actualizar lista."
            )
            return

        if self._var_drive.get() not in self._drives:
            self._var_drive.set(self._drives[0])
        self._btn_escanear.configure(state="normal")
        self._estado.info("Elige la unidad y dale a Escanear.")

    # ------------------------------------------------------------------
    # Escaneo
    # ------------------------------------------------------------------

    def _escanear(self) -> None:
        drive = self._var_drive.get()
        if not drive:
            return

        for w in self._zona.winfo_children():
            w.destroy()
        self._vars_alto.clear()
        self._btn_borrar.configure(state="disabled")
        self._btn_restaurar.configure(state="disabled")
        self._btn_escanear.configure(state="disabled")
        self._btn_detectar.configure(state="disabled")
        self._combo.configure(state="disabled")
        self._estado.info(f"Escaneando {drive}, puede tardar un momento...")

        def trabajo():
            return scan_usb(drive)

        self.run_async(trabajo, lambda ok, res: self._escaneo_listo(ok, res, drive))

    def _escaneo_listo(self, ok: bool, resultado, drive: str) -> None:
        self._combo.configure(state="readonly")
        self._btn_detectar.configure(state="normal")
        self._btn_escanear.configure(state="normal" if self._drives else "disabled")
        self._btn_restaurar.configure(state="normal" if self._drives else "disabled")

        if not ok:
            self._estado.alerta(
                "No se pudo escanear la unidad. Puede que se haya "
                "desconectado a medio escaneo. Vuelve a intentarlo."
            )
            return

        self._threats = resultado
        self._pintar_amenazas(drive)

    def _pintar_amenazas(self, drive: str) -> None:
        for w in self._zona.winfo_children():
            w.destroy()
        self._vars_alto.clear()

        if not self._threats:
            self._estado.exito(f"No se encontro ninguna amenaza en {drive}.")
            return

        altos = [t for t in self._threats if t.get("riesgo") == "Alto"]
        medios = [t for t in self._threats if t.get("riesgo") != "Alto"]

        self._estado.alerta(
            f"Se encontraron {len(self._threats)} archivo(s) sospechoso(s) en {drive}."
        )

        lienzo_frame = ttk.Frame(self._zona, style="Panel.TFrame")
        lienzo_frame.pack(fill="both", expand=True)

        lienzo = tk.Canvas(lienzo_frame, bg="#ffffff", highlightthickness=0)
        scroll = ttk.Scrollbar(lienzo_frame, orient="vertical", command=lienzo.yview)
        interior = ttk.Frame(lienzo, style="Panel.TFrame")
        interior.bind("<Configure>", lambda e: lienzo.configure(scrollregion=lienzo.bbox("all")))
        lienzo.create_window((0, 0), window=interior, anchor="nw")
        lienzo.configure(yscrollcommand=scroll.set)
        lienzo.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")

        if altos:
            ttk.Label(
                interior, text="Riesgo alto - se pueden eliminar (marca las que quieras borrar):",
                style="Section.TLabel",
            ).pack(anchor="w", pady=(4, 2))
            for i, t in enumerate(altos):
                var = tk.BooleanVar(value=False)  # nunca pre-marcado
                self._vars_alto[i] = var
                ttk.Checkbutton(
                    interior, variable=var,
                    text=f"{t['tipo']}: {os.path.basename(t['archivo'])}",
                    command=self._actualizar_boton_borrar,
                ).pack(anchor="w", padx=8)
                ttk.Label(
                    interior, text=f"     {t['archivo']}", style="Subtitle.TLabel",
                ).pack(anchor="w")
            self._altos = altos
        else:
            self._altos = []

        if medios:
            ttk.Label(
                interior,
                text="Riesgo medio - revisalos tu mismo, no se borran automaticamente:",
                style="Section.TLabel",
            ).pack(anchor="w", pady=(14, 2))
            for t in medios:
                ttk.Label(
                    interior, text=f"  - {t['tipo']}: {t['archivo']}",
                    style="Subtitle.TLabel",
                ).pack(anchor="w", padx=8)

        self._actualizar_boton_borrar()

    def _actualizar_boton_borrar(self) -> None:
        hay_marcado = any(v.get() for v in self._vars_alto.values())
        self._btn_borrar.configure(state="normal" if hay_marcado else "disabled")

    # ------------------------------------------------------------------
    # Borrado (destructivo)
    # ------------------------------------------------------------------

    def _eliminar(self) -> None:
        if getattr(self, "_borrando", False):
            return

        seleccionadas = [self._altos[i] for i, v in self._vars_alto.items() if v.get()]
        if not seleccionadas:
            self._estado.info("No marcaste ninguna amenaza, asi que no borre nada.")
            return

        lista = "\n".join(f"  - {os.path.basename(t['archivo'])}" for t in seleccionadas)
        if not self.confirmar_destructivo(
            "Eliminar archivos de la USB",
            f"Vas a borrar {len(seleccionadas)} archivo(s) de la USB de forma "
            f"permanente:\n\n{lista}\n\nEsto NO se puede deshacer. Seguro que "
            "quieres eliminarlos?",
        ):
            self._estado.info("No se borro nada.")
            return

        drive = self._var_drive.get()
        self._borrando = True
        self._btn_borrar.configure(state="disabled")
        self._btn_escanear.configure(state="disabled")
        self._btn_restaurar.configure(state="disabled")
        self._btn_detectar.configure(state="disabled")
        self._combo.configure(state="disabled")
        self._estado.info("Eliminando...")

        def trabajo():
            return clean_usb(drive, seleccionadas)

        self.run_async(trabajo, self._eliminacion_lista, destructivo=True)

    def _eliminacion_lista(self, ok: bool, resultado) -> None:
        self._borrando = False
        self._combo.configure(state="readonly")
        self._btn_detectar.configure(state="normal")
        if self._drives:
            self._btn_escanear.configure(state="normal")
            self._btn_restaurar.configure(state="normal")

        if not ok:
            self._estado.alerta(
                "Algo fallo al borrar. Puede que la USB se haya desconectado "
                "a la mitad. Vuelve a escanear para ver que quedo."
            )
            return

        eliminados = [r for r in resultado if r["ok"]]
        fallidos = [r for r in resultado if not r["ok"]]

        partes = [f"Se eliminaron {len(eliminados)} archivo(s)."]
        if fallidos:
            partes.append(f"{len(fallidos)} no se pudieron borrar.")
        self._estado.exito(" ".join(partes)) if not fallidos else self._estado.alerta(" ".join(partes))

        # Re-escanear deja la lista al dia (lo borrado ya no debe aparecer).
        self._escanear()

    # ------------------------------------------------------------------
    # Carpetas ocultas (no destructivo: solo quita atributos oculto/sistema)
    # ------------------------------------------------------------------

    def _restaurar_ocultas(self) -> None:
        drive = self._var_drive.get()
        if not drive:
            return

        self._btn_restaurar.configure(state="disabled")
        self._btn_escanear.configure(state="disabled")
        self._btn_detectar.configure(state="disabled")
        self._combo.configure(state="disabled")
        self._estado.info("Restaurando carpetas ocultas...")

        def trabajo():
            return unhide_folders(drive)

        self.run_async(trabajo, self._restauracion_lista)

    def _restauracion_lista(self, ok: bool, resultado) -> None:
        self._combo.configure(state="readonly")
        self._btn_detectar.configure(state="normal")
        if self._drives:
            self._btn_restaurar.configure(state="normal")
            self._btn_escanear.configure(state="normal")

        if not ok:
            self._estado.alerta("No se pudo completar la restauracion. Intenta de nuevo.")
            return

        if resultado.get("ok"):
            self._estado.exito("Carpetas y archivos ocultos por el virus quedaron visibles de nuevo.")
        elif "error" in resultado:
            self._estado.alerta(f"No se pudo restaurar: {resultado['error']}")
        else:
            self._estado.alerta(
                "No se pudieron restaurar todas las carpetas. Es posible que "
                "no todas queden visibles."
            )
