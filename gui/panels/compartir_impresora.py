"""Pantalla: Compartir impresora en red.

Reusa tools/printer_share.py tal cual: obtener la lista de impresoras,
filtrar por compartidas/no compartidas, y cambiar el estado de comparticion.
No es una operacion destructiva (no borra nada y se puede revertir dandole
'Dejar de compartir'), pero SI afecta a otras personas de la red, asi que se
confirma antes de dejar de compartir, igual que en consola.
"""

import tkinter as tk
from tkinter import ttk

from gui.base import EstadoLabel, ToolPanel
from tools import is_admin
from tools.printer_share import (
    PrinterQueryError,
    _filter_shared,
    _filter_unshared,
    _get_printers,
    _set_printer_shared,
)


class PanelCompartirImpresora(ToolPanel):
    TITULO = "Compartir impresora en red"
    DESCRIPCION = (
        "Comparte una impresora conectada a esta computadora para que otras "
        "personas de la red la puedan usar, o deja de compartirla."
    )

    def build(self) -> None:
        self._por_iid: dict[str, dict] = {}

        barra = ttk.Frame(self.body, style="Panel.TFrame")
        barra.pack(fill="x")

        self._btn_actualizar = ttk.Button(
            barra, text="Ver impresoras", style="Accent.TButton",
            command=self._actualizar,
        )
        self._btn_actualizar.pack(side="left")

        self._barra = ttk.Progressbar(barra, mode="indeterminate", length=200)

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(12, 6))
        self._estado.info("Dale a 'Ver impresoras' para ver que tienes instalado.")

        # --- Acciones ------------------------------------------------------
        # side="bottom" y empaquetado ANTES de la tabla (que expande), para
        # que los botones no queden fuera de la ventana.
        acciones = ttk.Frame(self.body, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(12, 0))

        ttk.Label(acciones, text="Nombre en red:", style="Panel.TLabel").pack(side="left")
        self._var_share_name = tk.StringVar()
        self._campo_share_name = ttk.Entry(
            acciones, textvariable=self._var_share_name, width=20,
        )
        self._campo_share_name.pack(side="left", padx=(6, 12))

        self._btn_compartir = ttk.Button(
            acciones, text="Compartir", style="Accent.TButton",
            command=self._compartir, state="disabled",
        )
        self._btn_compartir.pack(side="left")

        self._btn_dejar = ttk.Button(
            acciones, text="Dejar de compartir", style="Accent.TButton",
            command=self._dejar_de_compartir, state="disabled",
        )
        self._btn_dejar.pack(side="left", padx=(8, 0))

        # --- Tabla -----------------------------------------------------
        tabla_frame = ttk.Frame(self.body, style="Panel.TFrame")
        tabla_frame.pack(fill="both", expand=True)

        columnas = ("nombre", "controlador", "compartida", "nombre_red")
        self._tabla = ttk.Treeview(
            tabla_frame, columns=columnas, show="headings", height=8,
        )
        self._tabla.heading("nombre", text="Nombre")
        self._tabla.heading("controlador", text="Controlador")
        self._tabla.heading("compartida", text="Compartida")
        self._tabla.heading("nombre_red", text="Nombre en red")
        self._tabla.column("nombre", width=200, anchor="w", stretch=True)
        self._tabla.column("controlador", width=180, anchor="w", stretch=False)
        self._tabla.column("compartida", width=90, anchor="center", stretch=False)
        self._tabla.column("nombre_red", width=140, anchor="w", stretch=False)

        scroll_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=scroll_y.set)
        self._tabla.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="left", fill="y")

        self._tabla.bind("<<TreeviewSelect>>", self._on_seleccion)

    # ------------------------------------------------------------------
    # Listar
    # ------------------------------------------------------------------

    def _actualizar(self) -> None:
        self._btn_actualizar.configure(state="disabled")
        self._barra.pack(side="left", padx=(14, 0))
        self._barra.start(12)
        self._estado.info("Buscando impresoras instaladas...")
        self._btn_compartir.configure(state="disabled")
        self._btn_dejar.configure(state="disabled")

        self.run_async(_get_printers, self._lista_lista)

    def _lista_lista(self, ok: bool, resultado) -> None:
        self._barra.stop()
        self._barra.pack_forget()
        self._btn_actualizar.configure(state="normal")

        if not ok:
            if isinstance(resultado, PrinterQueryError):
                self._estado.alerta(
                    "No se pudo obtener la lista de impresoras. Intenta de "
                    "nuevo."
                )
            else:
                self._estado.alerta("Algo salio mal al buscar impresoras.")
            return

        printers = resultado
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
        self._por_iid.clear()

        if not printers:
            self._estado.info("No hay impresoras instaladas en esta PC.")
            return

        for i, p in enumerate(printers):
            iid = str(i)
            self._por_iid[iid] = p
            compartida = "Si" if p.get("Shared", False) else "No"
            self._tabla.insert(
                "", "end", iid=iid,
                values=(
                    p.get("Name", "?"),
                    p.get("DriverName", ""),
                    compartida,
                    p.get("ShareName", "") or "",
                ),
            )

        self._estado.info(
            f"{len(printers)} impresora(s) instalada(s). Selecciona una de "
            "la lista para compartirla o dejar de compartirla."
        )

    # ------------------------------------------------------------------
    # Seleccion
    # ------------------------------------------------------------------

    def _on_seleccion(self, _evento=None) -> None:
        seleccion = self._tabla.selection()
        if not seleccion:
            self._btn_compartir.configure(state="disabled")
            self._btn_dejar.configure(state="disabled")
            return

        printer = self._por_iid.get(seleccion[0])
        if printer is None:
            return

        compartida = printer.get("Shared", False)
        self._btn_compartir.configure(
            state="disabled" if compartida else "normal"
        )
        self._btn_dejar.configure(
            state="normal" if compartida else "disabled"
        )
        if not compartida and not self._var_share_name.get().strip():
            nombre = printer.get("Name", "")
            self._var_share_name.set(nombre.replace(" ", "_")[:20])

    def _seleccionada(self) -> dict | None:
        seleccion = self._tabla.selection()
        if not seleccion:
            return None
        return self._por_iid.get(seleccion[0])

    # ------------------------------------------------------------------
    # Compartir / dejar de compartir
    # ------------------------------------------------------------------

    def _compartir(self) -> None:
        if not is_admin():
            self.error(
                "Hace falta ser administrador",
                "Para compartir una impresora hay que abrir la app como "
                "administrador.",
            )
            return

        printer = self._seleccionada()
        if printer is None:
            return
        nombre = printer.get("Name", "")

        share_name = self._var_share_name.get().strip()
        if not share_name:
            self._estado.alerta("Escribe un nombre para compartirla en la red.")
            return

        self._btn_compartir.configure(state="disabled")
        self._estado.info(f"Compartiendo '{nombre}'...")

        self.run_async(
            lambda: _set_printer_shared(nombre, True, share_name),
            self._cambio_listo,
        )

    def _dejar_de_compartir(self) -> None:
        if not is_admin():
            self.error(
                "Hace falta ser administrador",
                "Para modificar una impresora hay que abrir la app como "
                "administrador.",
            )
            return

        printer = self._seleccionada()
        if printer is None:
            return
        nombre = printer.get("Name", "")

        if not self.confirmar_destructivo(
            "Dejar de compartir",
            f"Vas a dejar de compartir '{nombre}'. Nadie mas en la red va a "
            "poder usarla hasta que la vuelvas a compartir.\n\n"
            "Quieres continuar?",
        ):
            self._estado.info("No se hizo ningun cambio.")
            return

        self._btn_dejar.configure(state="disabled")
        self._estado.info(f"Dejando de compartir '{nombre}'...")

        self.run_async(
            lambda: _set_printer_shared(nombre, False),
            self._cambio_listo,
        )

    def _cambio_listo(self, ok: bool, resultado) -> None:
        if not ok:
            self._estado.alerta("Algo salio mal al cambiar la comparticion.")
            self.error(
                "No se pudo completar",
                "Ocurrio un error inesperado. Intenta de nuevo.",
            )
            self._actualizar()
            return

        resultado_op = resultado
        if resultado_op["ok"]:
            self._estado.exito("Listo, el cambio se aplico correctamente.")
        elif resultado_op["error_kind"] == "timeout":
            self._estado.alerta("La operacion tardo demasiado. Intenta de nuevo.")
        elif resultado_op["error_kind"] == "os":
            self._estado.alerta("Hubo un error del sistema al hacer el cambio.")
        else:
            self._estado.alerta(
                "No se pudo hacer el cambio. Revisa que tengas permiso de "
                "administrador."
            )

        # Re-listar deja la tabla al dia con el estado real.
        self._actualizar()
