"""Pantalla: Generador de Contrasenas Seguras.

Solo presenta la logica que ya existe en tools/password_generator.py; la
generacion (modulo secrets) NO se reimplementa aqui.
"""

import tkinter as tk
from tkinter import ttk

from gui.base import EstadoLabel, ToolPanel
from tools.password_generator import generate_password


class PanelContrasenas(ToolPanel):
    TITULO = "Generar contrasenas seguras"
    DESCRIPCION = (
        "Genera contrasenas seguras con el modulo secrets de Python. Elige "
        "la longitud y si quieres incluir simbolos, y copiala con un clic."
    )

    def build(self) -> None:
        entrada = ttk.Frame(self.body, style="Panel.TFrame")
        entrada.pack(fill="x")

        ttk.Label(entrada, text="Longitud:", style="Panel.TLabel").pack(side="left")

        self._var_longitud = tk.StringVar(value="16")
        campo = ttk.Entry(entrada, textvariable=self._var_longitud, width=6)
        campo.pack(side="left", padx=(10, 20))
        campo.bind("<Return>", lambda _e: self._generar())

        self._var_simbolos = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            entrada, text="Incluir simbolos (!@#$%&*)", variable=self._var_simbolos,
        ).pack(side="left")

        ttk.Button(
            entrada, text="Generar", style="Accent.TButton", command=self._generar,
        ).pack(side="left", padx=(20, 0))

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(10, 0))

        resultado = ttk.Frame(self.body, style="Panel.TFrame")
        resultado.pack(anchor="w", pady=(14, 0), fill="x")

        self._var_password = tk.StringVar()
        self._campo_password = ttk.Entry(
            resultado, textvariable=self._var_password, width=42,
            font=("Consolas", 14), state="readonly",
        )
        self._campo_password.pack(side="left")

        ttk.Button(
            resultado, text="Copiar", command=self._copiar,
        ).pack(side="left", padx=(10, 0))

    # ------------------------------------------------------------------

    def _generar(self) -> None:
        self._estado.limpiar()
        self._var_password.set("")

        texto = self._var_longitud.get().strip()
        try:
            longitud = int(texto)
        except ValueError:
            self._estado.alerta("Escribe un numero, por ejemplo 16")
            return

        if longitud < 8:
            self._estado.alerta("Longitud minima: 8 caracteres. Se uso 8.")
            longitud = 8
        elif longitud > 128:
            self._estado.alerta("Longitud maxima: 128 caracteres. Se uso 128.")
            longitud = 128

        password = generate_password(longitud, self._var_simbolos.get())
        self._var_password.set(password)
        if not self._estado.cget("text"):
            self._estado.exito("Contrasena generada.")

    def _copiar(self) -> None:
        password = self._var_password.get()
        if not password:
            self._estado.alerta("Genera una contrasena primero.")
            return
        self.clipboard_clear()
        self.clipboard_append(password)
        self._estado.exito("Copiada al portapapeles.")
