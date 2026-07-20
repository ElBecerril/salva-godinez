"""Pantalla: Simulador de Prestaciones Laborales.

Solo presenta la logica que ya existe en tools/prestaciones_sim.py; los
calculos (aguinaldo, vacaciones/prima, finiquito, liquidacion) NO se
reimplementan aqui. Ver ese modulo para el detalle legal de cada formula.
"""

import re
import tkinter as tk
from tkinter import ttk

from gui.base import EstadoLabel, ToolPanel
from tools._fiscal_helpers import DISCLAIMER, fmt
from tools.prestaciones_sim import (
    calculate_aguinaldo,
    calculate_finiquito,
    calculate_liquidacion,
    calculate_vacaciones,
)

# El DISCLAIMER esta escrito con markup de rich (para la consola). Aqui solo
# se le quitan las etiquetas de color para que no aparezcan como texto
# literal en pantalla; el contenido y el orden de las palabras no se tocan.
_DISCLAIMER_TEXTO = re.sub(r"\[/?[a-z]+\]", "", DISCLAIMER)

_OPCIONES = (
    ("aguinaldo", "Aguinaldo"),
    ("vacaciones", "Vacaciones y Prima"),
    ("finiquito", "Finiquito (renuncia)"),
    ("liquidacion", "Liquidacion (despido)"),
)


class PanelPrestaciones(ToolPanel):
    TITULO = "Calcular finiquito y prestaciones"
    DESCRIPCION = (
        "Calcula aguinaldo, vacaciones y prima vacacional, finiquito o "
        "liquidacion. Escribe el salario diario y, segun el calculo, los "
        "anos de antiguedad y los dias trabajados en el ano."
    )

    def build(self) -> None:
        # --- Seleccion de calculo ---
        opciones = ttk.Frame(self.body, style="Panel.TFrame")
        opciones.pack(fill="x")

        ttk.Label(opciones, text="Calculo:", style="Panel.TLabel").pack(side="left")

        self._var_calculo = tk.StringVar(value=_OPCIONES[0][0])
        for valor, etiqueta in _OPCIONES:
            ttk.Radiobutton(
                opciones, text=etiqueta, value=valor, variable=self._var_calculo,
                command=self._actualizar_campos,
            ).pack(side="left", padx=(10, 0))

        # --- Campos de entrada ---
        entrada = ttk.Frame(self.body, style="Panel.TFrame")
        entrada.pack(fill="x", pady=(14, 0))

        ttk.Label(entrada, text="Salario diario:", style="Panel.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self._var_salario = tk.StringVar()
        ttk.Entry(entrada, textvariable=self._var_salario, width=16).grid(
            row=0, column=1, sticky="w", pady=4
        )

        self._label_anos = ttk.Label(entrada, text="Anos de antiguedad:", style="Panel.TLabel")
        self._label_anos.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self._var_anos = tk.StringVar()
        self._entry_anos = ttk.Entry(entrada, textvariable=self._var_anos, width=16)
        self._entry_anos.grid(row=1, column=1, sticky="w", pady=4)

        self._label_dias = ttk.Label(entrada, text="Dias trabajados en el ano:", style="Panel.TLabel")
        self._label_dias.grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        self._var_dias = tk.StringVar()
        self._entry_dias = ttk.Entry(entrada, textvariable=self._var_dias, width=16)
        self._entry_dias.grid(row=2, column=1, sticky="w", pady=4)

        ttk.Button(
            entrada, text="Calcular", style="Accent.TButton", command=self._calcular,
        ).grid(row=0, column=2, rowspan=3, sticky="ns", padx=(16, 0))

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(10, 0))

        self._total_label = ttk.Label(
            self.body, text="", style="Ok.TLabel", font=("Segoe UI", 20, "bold"),
        )
        self._total_label.pack(anchor="w", pady=(14, 4))

        # El disclaimer se ancla ABAJO y se empaqueta ANTES que la tabla: si
        # va despues, la tabla (expand=True) lo empuja fuera de la ventana.
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

        self._actualizar_campos()

    # ------------------------------------------------------------------

    def _actualizar_campos(self) -> None:
        """Muestra/oculta anos y dias segun el calculo elegido, como hace el
        menu de consola (aguinaldo no pide anos)."""
        calculo = self._var_calculo.get()

        if calculo == "aguinaldo":
            self._label_anos.grid_remove()
            self._entry_anos.grid_remove()
        else:
            self._label_anos.grid()
            self._entry_anos.grid()

        # Todos los calculos piden dias trabajados en el ano.
        self._label_dias.grid()
        self._entry_dias.grid()

    def _fila(self, concepto: str, monto: str = "", *, negrita: bool = False) -> None:
        tag = "negrita" if negrita else ""
        self._tabla.insert("", "end", values=(concepto, monto), tags=(tag,))

    def _leer_salario(self) -> float | None:
        texto = self._var_salario.get().strip().replace(",", "")
        try:
            valor = float(texto)
        except ValueError:
            return None
        if valor <= 0:
            return None
        return valor

    def _leer_entero(self, var: tk.StringVar) -> int | None:
        texto = var.get().strip()
        try:
            valor = int(texto)
        except ValueError:
            return None
        if valor < 0:
            return None
        return valor

    def _calcular(self) -> None:
        self._estado.limpiar()
        self._total_label.configure(text="")
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)

        salario = self._leer_salario()
        if salario is None:
            self._estado.alerta("Escribe un numero, por ejemplo 15000")
            return

        calculo = self._var_calculo.get()

        anos = 0
        if calculo != "aguinaldo":
            anos = self._leer_entero(self._var_anos)
            if anos is None:
                self._estado.alerta("Escribe un numero, por ejemplo 15000")
                return

        dias = self._leer_entero(self._var_dias)
        if dias is None:
            self._estado.alerta("Escribe un numero, por ejemplo 15000")
            return

        if calculo == "aguinaldo":
            self._mostrar_aguinaldo(salario, dias)
        elif calculo == "vacaciones":
            self._mostrar_vacaciones(salario, anos, dias)
        elif calculo == "finiquito":
            self._mostrar_finiquito(salario, anos, dias)
        elif calculo == "liquidacion":
            self._mostrar_liquidacion(salario, anos, dias)

        self._estado.exito("Calculo listo.")

    def _mostrar_aguinaldo(self, salario: float, dias: int) -> None:
        result = calculate_aguinaldo(salario, dias)
        self._fila("Aguinaldo bruto", fmt(result["bruto"]), negrita=True)
        self._fila("Exento (30 UMA)", fmt(result["exento"]))
        self._fila("Gravado", fmt(result["gravado"]))
        self._total_label.configure(text=f"Aguinaldo bruto: {fmt(result['bruto'])}")

    def _mostrar_vacaciones(self, salario: float, anos: int, dias: int) -> None:
        result = calculate_vacaciones(salario, anos, dias)
        self._fila("Dias de vacaciones", f"{result['dias']:.1f}")
        self._fila("Prima vacacional bruta", fmt(result["prima_bruta"]), negrita=True)
        self._fila("Prima exenta (15 UMA)", fmt(result["prima_exenta"]))
        self._fila("Prima gravada", fmt(result["prima_gravada"]))
        self._total_label.configure(text=f"Prima vacacional: {fmt(result['prima_bruta'])}")

    def _mostrar_finiquito(self, salario: float, anos: int, dias: int) -> None:
        result = calculate_finiquito(salario, anos, dias)
        self._fila("Aguinaldo proporcional", fmt(result["aguinaldo"]))
        self._fila(
            f"Vacaciones ({result['vacaciones_dias']:.1f} dias)", fmt(result["vacaciones_pago"])
        )
        self._fila("Prima vacacional", fmt(result["prima_vacacional"]))
        if result["prima_antiguedad"] > 0:
            self._fila("Prima de antiguedad (>=15 anos)", fmt(result["prima_antiguedad"]))
        self._fila("Total finiquito", fmt(result["total"]), negrita=True)
        self._total_label.configure(text=f"Total finiquito: {fmt(result['total'])}")

    def _mostrar_liquidacion(self, salario: float, anos: int, dias: int) -> None:
        result = calculate_liquidacion(salario, anos, dias)
        self._fila("Aguinaldo proporcional", fmt(result["aguinaldo"]))
        self._fila(
            f"Vacaciones ({result['vacaciones_dias']:.1f} dias)", fmt(result["vacaciones_pago"])
        )
        self._fila("Prima vacacional", fmt(result["prima_vacacional"]))
        self._fila("3 meses (constitucional)", fmt(result["tres_meses"]))
        self._fila("20 dias por ano", fmt(result["veinte_por_ano"]))
        self._fila("Prima de antiguedad", fmt(result["prima_antiguedad"]))
        self._fila("Total liquidacion", fmt(result["total_liquidacion"]), negrita=True)
        self._total_label.configure(text=f"Total liquidacion: {fmt(result['total_liquidacion'])}")
