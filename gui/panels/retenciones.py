"""Pantalla: Calculadora de Retenciones (Honorarios / RESICO).

Solo presenta la logica que ya existe en tools/retention_calculator.py; los
calculos (IVA, retencion ISR/IVA, tasa fija RESICO) NO se reimplementan aqui.
Ver ese modulo para el detalle legal de cada formula.
"""

import re
import tkinter as tk
from tkinter import ttk

from gui.base import EstadoLabel, ToolPanel
from tools._fiscal_helpers import DISCLAIMER, fmt
from tools.retention_calculator import calculate_honorarios, calculate_resico

_DISCLAIMER_TEXTO = re.sub(r"\[/?[a-z]+\]", "", DISCLAIMER)

_OPCIONES = (
    ("honorarios", "Honorarios (persona fisica)"),
    ("resico", "RESICO (personas fisicas)"),
)


class PanelRetenciones(ToolPanel):
    TITULO = "Retenciones de honorarios"
    DESCRIPCION = (
        "Calcula las retenciones de un pago por honorarios (persona fisica) "
        "o el ISR de RESICO segun el ingreso mensual."
    )

    def build(self) -> None:
        opciones = ttk.Frame(self.body, style="Panel.TFrame")
        opciones.pack(fill="x")

        ttk.Label(opciones, text="Calculo:", style="Panel.TLabel").pack(side="left")

        self._var_calculo = tk.StringVar(value=_OPCIONES[0][0])
        for valor, etiqueta in _OPCIONES:
            ttk.Radiobutton(
                opciones, text=etiqueta, value=valor, variable=self._var_calculo,
                command=self._actualizar_etiqueta,
            ).pack(side="left", padx=(10, 0))

        entrada = ttk.Frame(self.body, style="Panel.TFrame")
        entrada.pack(fill="x", pady=(14, 0))

        self._label_monto = ttk.Label(
            entrada, text="Subtotal (monto antes de impuestos):", style="Panel.TLabel",
        )
        self._label_monto.pack(side="left")

        self._var_monto = tk.StringVar()
        campo = ttk.Entry(entrada, textvariable=self._var_monto, width=18)
        campo.pack(side="left", padx=(10, 10))
        campo.bind("<Return>", lambda _e: self._calcular())

        ttk.Button(
            entrada, text="Calcular", style="Accent.TButton", command=self._calcular,
        ).pack(side="left")

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(10, 0))

        self._total_label = ttk.Label(
            self.body, text="", style="Ok.TLabel", font=("Segoe UI", 20, "bold"),
        )
        self._total_label.pack(anchor="w", pady=(14, 4))

        # El disclaimer se ancla ABAJO y se empaqueta ANTES que la tabla.
        ttk.Label(
            self.body, text=_DISCLAIMER_TEXTO, style="Subtitle.TLabel",
            wraplength=820, justify="left",
        ).pack(side="bottom", anchor="w", pady=(10, 0))

        tabla_frame = ttk.Frame(self.body, style="Panel.TFrame")
        tabla_frame.pack(fill="both", expand=True, pady=(4, 0))

        columnas = ("concepto", "monto")
        self._tabla = ttk.Treeview(
            tabla_frame, columns=columnas, show="headings", height=10,
        )
        self._tabla.heading("concepto", text="Concepto")
        self._tabla.heading("monto", text="Monto")
        self._tabla.column("concepto", width=380, anchor="w", stretch=True)
        self._tabla.column("monto", width=160, anchor="e", stretch=False)
        self._tabla.tag_configure("negrita", font=("Segoe UI", 11, "bold"))

        scroll_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=scroll_y.set)
        self._tabla.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="left", fill="y")

    # ------------------------------------------------------------------

    def _actualizar_etiqueta(self) -> None:
        if self._var_calculo.get() == "resico":
            self._label_monto.configure(text="Ingreso mensual:")
        else:
            self._label_monto.configure(text="Subtotal (monto antes de impuestos):")

    def _fila(self, concepto: str, monto: str = "", *, negrita: bool = False) -> None:
        tag = "negrita" if negrita else ""
        self._tabla.insert("", "end", values=(concepto, monto), tags=(tag,))

    def _calcular(self) -> None:
        self._estado.limpiar()
        self._total_label.configure(text="")
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)

        texto = self._var_monto.get().strip().replace(",", "")
        try:
            monto = float(texto)
        except ValueError:
            self._estado.alerta("Escribe un numero, por ejemplo 15000")
            return

        if monto <= 0:
            self._estado.alerta("Escribe un numero, por ejemplo 15000")
            return

        if self._var_calculo.get() == "honorarios":
            self._mostrar_honorarios(monto)
        else:
            self._mostrar_resico(monto)

    def _mostrar_honorarios(self, subtotal: float) -> None:
        result = calculate_honorarios(subtotal)
        iva = result["iva"]
        isr_retenido = result["isr_retenido"]
        iva_retenido = result["iva_retenido"]
        total = result["total"]

        self._fila("Subtotal", fmt(subtotal))
        self._fila("IVA (16%)", f"+{fmt(iva)}")
        self._fila("ISR retenido (10%)", f"-{fmt(isr_retenido)}")
        self._fila("IVA retenido (2/3)", f"-{fmt(iva_retenido)}")
        self._fila("Total a recibir", fmt(total), negrita=True)
        self._fila("Total en factura (subtotal + IVA)", fmt(subtotal + iva))

        self._total_label.configure(text=f"Total a recibir: {fmt(total)}")
        self._estado.exito("Calculo listo.")

    def _mostrar_resico(self, income: float) -> None:
        result = calculate_resico(income)
        if "error" in result:
            self._estado.alerta(
                f"No se encontro el rango fiscal para ese monto: {result['error']}"
            )
            return

        lim_inf = result["lim_inf"]
        lim_sup = result["lim_sup"]
        tasa = result["tasa"]
        isr_total = result["isr_total"]
        tasa_efectiva = result["tasa_efectiva"]
        neto = result["neto"]

        rango_sup = "en adelante" if lim_sup == float("inf") else fmt(lim_sup)

        self._fila("Ingreso mensual", fmt(income))
        self._fila("Rango aplicable", f"{fmt(lim_inf)} - {rango_sup}")
        self._fila(f"Tasa fija del rango ({tasa:.2%})", fmt(isr_total))
        self._fila("ISR a pagar", fmt(isr_total), negrita=True)
        self._fila("Tasa efectiva", f"{tasa_efectiva:.2f}%")
        self._fila("Neto despues de ISR", fmt(neto), negrita=True)

        self._total_label.configure(text=f"Neto despues de ISR: {fmt(neto)}")
        self._estado.exito("Calculo listo.")
