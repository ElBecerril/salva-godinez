"""Pantalla: Probar si la impresora responde (ping + puertos).

No destructivo: solo consulta la red. Reusa tools/ping_checker.py tal cual
(ping_host, check_port); esta pantalla solo valida el texto que escribe el
usuario (mismo patron que ping_checker_menu() en consola) y pinta la tabla.
"""

import re
import tkinter as tk
from tkinter import ttk

from gui.base import EstadoLabel, ToolPanel
from tools.ping_checker import check_port, ping_host

# Mismos puertos y descripciones que ping_checker_menu() en consola.
_PUERTOS_IMPRESORA = [(9100, "RAW/JetDirect"), (631, "IPP/CUPS"), (515, "LPD")]

_HOST_VALIDO = re.compile(r"^[A-Za-z0-9.:_-]+$")


class PanelProbarImpresora(ToolPanel):
    TITULO = "Probar si la impresora responde"
    DESCRIPCION = (
        "Escribe la IP o el nombre de red de la impresora para ver si tu "
        "computadora la puede alcanzar. Util cuando dice 'sin conexion' o "
        "no imprime."
    )

    def build(self) -> None:
        entrada = ttk.Frame(self.body, style="Panel.TFrame")
        entrada.pack(fill="x")

        ttk.Label(
            entrada, text="IP o nombre del equipo:", style="Panel.TLabel",
        ).pack(side="left")

        self._var_host = tk.StringVar()
        self._campo = ttk.Entry(entrada, textvariable=self._var_host, width=28)
        self._campo.pack(side="left", padx=(10, 10))
        self._campo.bind("<Return>", lambda _e: self._probar())

        self._btn_probar = ttk.Button(
            entrada, text="Probar conexion", style="Accent.TButton",
            command=self._probar,
        )
        self._btn_probar.pack(side="left")

        self._barra = ttk.Progressbar(self.body, mode="indeterminate")

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(12, 6))

        # --- Puertos ---------------------------------------------------
        # Se empaqueta ANTES que la tabla de resultados (que expande), igual
        # que en espacio.py: si no, con la tabla llena el boton queda fuera.
        puertos_frame = ttk.Frame(self.body, style="Panel.TFrame")
        puertos_frame.pack(side="bottom", fill="x", pady=(12, 0))

        self._btn_puertos = ttk.Button(
            puertos_frame, text="Verificar puertos de impresora",
            style="Accent.TButton", command=self._verificar_puertos,
            state="disabled",
        )
        self._btn_puertos.pack(side="left")

        self._puertos_estado = EstadoLabel(self.body)
        self._puertos_estado.pack(side="bottom", anchor="w", pady=(6, 0))

        # --- Resultados del ping ----------------------------------------
        tabla_frame = ttk.Frame(self.body, style="Panel.TFrame")
        tabla_frame.pack(fill="both", expand=True)

        self._tabla = ttk.Treeview(
            tabla_frame, columns=("metrica", "valor"), show="headings",
            height=6,
        )
        self._tabla.heading("metrica", text="Metrica")
        self._tabla.heading("valor", text="Valor")
        self._tabla.column("metrica", width=180, anchor="w", stretch=False)
        self._tabla.column("valor", width=200, anchor="w", stretch=True)
        self._tabla.pack(fill="both", expand=True)

        self._host_probado = ""

    # ------------------------------------------------------------------
    # Ping
    # ------------------------------------------------------------------

    def _probar(self) -> None:
        host = self._var_host.get().strip()
        if not host:
            self._estado.alerta("Escribe la IP o el nombre de la impresora.")
            return
        if host.startswith("-") or host.startswith("/"):
            self._estado.alerta("Ese nombre no es valido.")
            return
        if not _HOST_VALIDO.match(host):
            self._estado.alerta("Ese nombre o IP no es valido.")
            return

        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
        self._puertos_estado.limpiar()
        self._btn_puertos.configure(state="disabled")

        self._btn_probar.configure(state="disabled")
        self._campo.configure(state="disabled")
        self._barra.pack(fill="x", pady=(4, 0))
        self._barra.start(12)
        self._estado.info(f"Haciendo ping a {host}...")

        self.run_async(lambda: ping_host(host), self._ping_listo)
        self._host_probado = host

    def _ping_listo(self, ok: bool, resultado) -> None:
        self._barra.stop()
        self._barra.pack_forget()
        self._btn_probar.configure(state="normal")
        self._campo.configure(state="normal")

        if not ok:
            self._estado.alerta(
                "No se pudo hacer la prueba de conexion. Intenta de nuevo."
            )
            return

        info = resultado
        self._pintar_ping(info)

        if info["ok"]:
            self._estado.exito(f"La impresora respondio en {self._host_probado}.")
        else:
            self._estado.alerta(
                f"No hubo respuesta de {self._host_probado}. Revisa que "
                "este encendida y conectada a la red."
            )

        self._btn_puertos.configure(state="normal")

    def _pintar_ping(self, info: dict) -> None:
        filas = [
            ("Enviados", str(info["sent"])),
            ("Recibidos", str(info["received"])),
            ("Perdidos", str(info["lost"])),
            ("Minimo (ms)", str(info["min_ms"])),
            ("Maximo (ms)", str(info["max_ms"])),
            ("Promedio (ms)", str(info["avg_ms"])),
        ]
        for metrica, valor in filas:
            self._tabla.insert("", "end", values=(metrica, valor))

    # ------------------------------------------------------------------
    # Puertos
    # ------------------------------------------------------------------

    def _verificar_puertos(self) -> None:
        host = self._host_probado
        if not host:
            return

        self._btn_puertos.configure(state="disabled")
        self._puertos_estado.info("Probando puertos de impresora...")

        def trabajo():
            return [(puerto, desc, check_port(host, puerto)) for puerto, desc in _PUERTOS_IMPRESORA]

        self.run_async(trabajo, self._puertos_listos)

    def _puertos_listos(self, ok: bool, resultado) -> None:
        self._btn_puertos.configure(state="normal")

        if not ok:
            self._puertos_estado.alerta("No se pudieron probar los puertos.")
            return

        partes = []
        for puerto, desc, abierto in resultado:
            estado = "abierto" if abierto else "cerrado"
            partes.append(f"{puerto} ({desc}): {estado}")
        self._puertos_estado.info("Puertos — " + "  ·  ".join(partes))
