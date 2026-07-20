"""Pantalla: Destrabar impresora (reset del spooler de Windows).

Esta pantalla NO reimplementa nada de tools/spooler.py: solo encadena sus
funciones de logica (detener el servicio, vaciar la cola, reiniciarlo,
verificar que quedo corriendo) y presenta el resultado. El flujo replica
exactamente el de reset_spooler() en consola.

DESTRUCTIVO: vaciar la cola cancela los trabajos de impresion pendientes de
TODOS los usuarios de esta PC y es irreversible. Por eso hay confirmacion
explicita (default No) antes de tocar nada, igual que en consola.
"""

import tkinter as tk
from tkinter import ttk

from gui.base import EstadoLabel, ToolPanel
from tools import is_admin
from tools.spooler import (
    _check_spooler_running,
    _clear_spool_queue,
    _count_pending_jobs,
    _start_spooler_service,
    _stop_spooler_service,
)


class PanelDestrabarImpresora(ToolPanel):
    TITULO = "Destrabar impresora"
    DESCRIPCION = (
        "Si la impresora se quedo pegada o no imprime nada, esto reinicia "
        "el servicio de impresion de Windows. OJO: si hay trabajos "
        "esperando en la fila, se cancelan para TODAS las personas que "
        "usan esta computadora, y no se pueden recuperar."
    )

    def build(self) -> None:
        acciones = ttk.Frame(self.body, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(18, 0))

        self._btn = ttk.Button(
            acciones, text="Destrabar impresora", style="Danger.TButton",
            command=self._iniciar,
        )
        self._btn.pack(side="left")

        self._barra = ttk.Progressbar(self.body, mode="indeterminate")

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(16, 0))
        self._estado.info(
            "Dale a 'Destrabar impresora' cuando quieras. Primero se revisa "
            "si hay trabajos pendientes."
        )

    # ------------------------------------------------------------------

    def _iniciar(self) -> None:
        if not is_admin():
            self.error(
                "Hace falta ser administrador",
                "Para destrabar la impresora hay que abrir la app como "
                "administrador.",
            )
            return

        # Contar los pendientes es solo leer una carpeta local, es rapido:
        # no hace falta run_async para esto, igual que en consola.
        pendientes = _count_pending_jobs()

        if pendientes:
            if not self.confirmar_destructivo(
                "Destrabar impresora",
                f"Hay {pendientes} trabajo(s) de impresion esperando en la "
                "fila.\n\nDestrabar la impresora los CANCELA para todas las "
                "personas que usan esta computadora, y no se puede "
                "deshacer.\n\nQuieres continuar de todas formas?",
            ):
                self._estado.info("No se hizo nada. La fila sigue igual.")
                return

        self._btn.configure(state="disabled")
        self._barra.pack(fill="x", pady=(4, 0))
        self._barra.start(12)
        self._estado.info("Destrabando la impresora, un momento...")

        self.run_async(_reset_spooler, self._listo, destructivo=True)

    def _listo(self, ok: bool, resultado) -> None:
        self._barra.stop()
        self._barra.pack_forget()
        self._btn.configure(state="normal")

        if not ok:
            self._estado.alerta("Algo salio mal al destrabar la impresora.")
            self.error(
                "No se pudo destrabar la impresora",
                "Ocurrio un error inesperado. Intenta de nuevo, o reinicia "
                "la computadora si el problema sigue.",
            )
            return

        res = resultado

        if not res["stop"]["ok"]:
            self._estado.alerta(
                "No se pudo detener el servicio de impresion."
            )
            self.error(
                "No se pudo destrabar la impresora",
                "No se pudo detener el servicio de impresion de Windows. "
                "Intenta de nuevo.",
            )
            return

        if not res["running"]:
            self._estado.alerta(
                "El servicio de impresion no quedo funcionando."
            )
            mensaje = (
                "El servicio de impresion no volvio a arrancar solo.\n\n"
                "Intenta reiniciar la computadora, o pide ayuda a soporte "
                "tecnico para reiniciar el servicio 'Print Spooler'."
            )
            if res["clear"]["removed"]:
                mensaje += (
                    f"\n\nSe alcanzaron a borrar {res['clear']['removed']} "
                    "trabajo(s) de la fila antes de la falla."
                )
            self.error("No se pudo destrabar la impresora", mensaje)
            return

        removed = res["clear"]["removed"]
        failed = res["clear"]["failed"]

        if failed:
            self._estado.alerta(
                f"La impresora se reinicio, pero {len(failed)} trabajo(s) "
                "de la fila no se pudieron borrar. Puede que sigan "
                "apareciendo en la lista de impresion."
            )
        elif removed:
            self._estado.exito(
                f"Listo: se cancelaron {removed} trabajo(s) pendientes y la "
                "impresora quedo funcionando de nuevo."
            )
        else:
            self._estado.exito(
                "Listo: la impresora quedo funcionando de nuevo. No habia "
                "trabajos pendientes en la fila."
            )


def _reset_spooler() -> dict:
    """Encadena la logica de tools/spooler.py, igual que reset_spooler() en
    consola, pero sin imprimir nada: el resultado se traduce a pantalla en
    _listo(). Corre en el hilo de trabajo de run_async.
    """
    stop_result = _stop_spooler_service()
    if not stop_result["ok"]:
        return {
            "stop": stop_result,
            "clear": {"removed": 0, "failed": []},
            "start": {"ok": False},
            "running": False,
        }

    clear_result = _clear_spool_queue()
    start_result = _start_spooler_service()
    running_result = _check_spooler_running()

    return {
        "stop": stop_result,
        "clear": clear_result,
        "start": start_result,
        "running": running_result["running"],
    }
