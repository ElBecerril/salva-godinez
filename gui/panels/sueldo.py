"""Pantalla: Calculadora de Sueldo Neto (ISR/IMSS).

Solo presenta la logica que ya existe en tools/salary_calculator.py; el
calculo (ISR Art. 96, cuotas IMSS, subsidio al empleo 2026) NO se reimplementa
aqui. Ver ese modulo para el detalle legal de cada formula.
"""

import re
import tkinter as tk
from tkinter import ttk

from gui.base import EstadoLabel, ToolPanel
from tools._fiscal_helpers import DISCLAIMER, fmt
from tools.salary_calculator import calculate_neto

# Misma nota legal que muestra la consola (salary_calculator.py) para el caso
# de salario minimo: Art. 96 LISR (no se retiene ISR) + Art. 36 LSS (la cuota
# obrero del IMSS la paga el patron).
_NOTA_SALARIO_MINIMO = (
    "Ganas el salario minimo: por ley no se te retiene ISR (Art. 96 LISR) y "
    "tu cuota del IMSS la paga el patron (Art. 36 LSS)."
)

# El DISCLAIMER esta escrito con markup de rich (para la consola). Aqui solo
# se le quitan las etiquetas de color ([yellow]...[/yellow], [dim]...[/dim])
# para que no aparezcan como texto literal en pantalla; el contenido y el
# orden de las palabras no se tocan.
_DISCLAIMER_TEXTO = re.sub(r"\[/?[a-z]+\]", "", DISCLAIMER)


class PanelSueldo(ToolPanel):
    TITULO = "Calcular sueldo neto"
    DESCRIPCION = (
        "Escribe el salario bruto mensual y calcula el desglose de ISR, "
        "subsidio al empleo y cuotas IMSS hasta llegar al sueldo neto."
    )

    def build(self) -> None:
        entrada = ttk.Frame(self.body, style="Panel.TFrame")
        entrada.pack(fill="x")

        ttk.Label(
            entrada, text="Salario bruto mensual:", style="Panel.TLabel",
        ).pack(side="left")

        self._var_bruto = tk.StringVar()
        campo = ttk.Entry(entrada, textvariable=self._var_bruto, width=18)
        campo.pack(side="left", padx=(10, 10))
        campo.bind("<Return>", lambda _e: self._calcular())

        ttk.Button(
            entrada, text="Calcular", style="Accent.TButton",
            command=self._calcular,
        ).pack(side="left")

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(10, 0))

        # Neto destacado: es el numero que la persona vino a buscar.
        self._neto_label = ttk.Label(
            self.body, text="", style="Ok.TLabel", font=("Segoe UI", 20, "bold"),
        )
        self._neto_label.pack(anchor="w", pady=(14, 4))

        # El disclaimer se ancla ABAJO y se empaqueta ANTES que la tabla: si va
        # despues, la tabla (expand=True) lo empuja fuera de la ventana. Que el
        # aviso de "esto es una ESTIMACION" se vea no es opcional.
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
        # Sin esto el tag "negrita" de _fila() no pinta nada.
        self._tabla.tag_configure("negrita", font=("Segoe UI", 11, "bold"))

        # Con scroll: el desglose no siempre cabe, y sin barra las ultimas
        # filas (justo donde va el total de deducciones) quedan inalcanzables.
        scroll_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=scroll_y.set)
        self._tabla.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="left", fill="y")

    # ------------------------------------------------------------------

    def _fila(self, concepto: str, monto: str = "", *, negrita: bool = False) -> None:
        tag = "negrita" if negrita else ""
        self._tabla.insert("", "end", values=(concepto, monto), tags=(tag,))

    def _calcular(self) -> None:
        self._estado.limpiar()
        self._neto_label.configure(text="")
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)

        texto = self._var_bruto.get().strip().replace(",", "")
        try:
            bruto = float(texto)
        except ValueError:
            self._estado.alerta("Escribe un numero, por ejemplo 15000")
            return

        if bruto <= 0:
            self._estado.alerta("Escribe un numero, por ejemplo 15000")
            return

        # Mismo flujo que salary_calculator_menu() en tools/salary_calculator.py,
        # ahora centralizado en calculate_neto() para que consola y GUI no se
        # desincronicen.
        resultado = calculate_neto(bruto)
        isr = resultado["isr"]
        if "error" in isr:
            self._estado.alerta(
                f"No se pudo calcular el ISR: {isr['error']}"
            )
            return

        imss = resultado["imss"]
        total_imss = resultado["total_imss"]
        base_gravable = resultado["taxable_base"]
        isr_total = resultado["isr_total"]
        subsidio_empleo = resultado["subsidio_empleo"]
        isr_neto = resultado["isr_neto"]
        neto = resultado["net_salary"]
        total_deducciones = bruto - neto

        self._fila("Salario bruto", fmt(bruto), negrita=True)

        if resultado["salario_minimo"]:
            self._fila("  IMSS a cargo del trabajador", f"-{fmt(0)}")
            self._fila("  ISR a cargo del trabajador", f"-{fmt(0)}")
        else:
            self._fila("Deducciones IMSS (SBC integrado)", "")
            for concepto, monto in imss.items():
                self._fila(f"  {concepto}", f"-{fmt(monto)}")
            self._fila("  Total IMSS", f"-{fmt(total_imss)}", negrita=True)

            self._fila("ISR Art. 96", "")
            self._fila("  Base gravable", fmt(base_gravable))
            self._fila("  Total ISR", f"-{fmt(isr_total)}")
            if subsidio_empleo:
                self._fila("  Subsidio al empleo", f"+{fmt(subsidio_empleo)}")
                self._fila("  ISR neto a cargo", f"-{fmt(isr_neto)}", negrita=True)

        self._fila("Total deducciones", f"-{fmt(total_deducciones)}", negrita=True)

        self._neto_label.configure(text=f"Sueldo neto: {fmt(neto)}")
        if resultado["salario_minimo"]:
            self._estado.exito(_NOTA_SALARIO_MINIMO)
        else:
            self._estado.exito("Calculo listo.")
