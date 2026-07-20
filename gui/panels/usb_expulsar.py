"""Pantalla: Expulsar USB con Seguridad.

Replica el flujo de tools/usb_eject.py (usb_eject_menu): elegir la unidad y
expulsarla de forma segura antes de que el usuario la retire fisicamente. No
borra ni modifica archivos del usuario; el riesgo que evita es justo el
contrario (retirarla sin avisar a Windows puede corromper lo que estaba
escribiendose).
"""

import tkinter as tk
from tkinter import messagebox, ttk

from gui.base import EstadoLabel, ToolPanel
from tools import get_removable_drives
from tools.usb_eject import _eject_drive


class PanelUsbExpulsar(ToolPanel):
    TITULO = "Expulsar USB con seguridad"
    DESCRIPCION = (
        "Prepara tu USB para que la puedas retirar sin riesgo de danar los "
        "archivos que tenga a medio guardar."
    )

    def build(self) -> None:
        self._drives: list[str] = []

        fila_unidad = ttk.Frame(self.body, style="Panel.TFrame")
        fila_unidad.pack(fill="x")

        ttk.Label(fila_unidad, text="Unidad a expulsar:", style="Panel.TLabel").pack(side="left")

        self._var_drive = tk.StringVar()
        self._combo = ttk.Combobox(
            fila_unidad, textvariable=self._var_drive, state="readonly", width=10,
        )
        self._combo.pack(side="left", padx=(10, 10))

        ttk.Button(
            fila_unidad, text="Actualizar lista", command=self._detectar,
        ).pack(side="left")

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(12, 6))

        acciones = ttk.Frame(self.body, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(12, 0))

        self._btn_expulsar = ttk.Button(
            acciones, text="Expulsar", style="Accent.TButton",
            command=self._expulsar, state="disabled",
        )
        self._btn_expulsar.pack(side="left")

        self._detectar()

    # ------------------------------------------------------------------
    # Deteccion de unidades
    # ------------------------------------------------------------------

    def _detectar(self, anunciar: bool = True) -> None:
        """Refresca la lista de unidades.

        `anunciar=False` se usa justo despues de expulsar: ahi ya se muestra
        el resultado de la expulsion (exito o aviso), y refrescar la lista no
        debe pisar ese mensaje con "Elige la unidad...".
        """
        self._drives = get_removable_drives()
        self._combo.configure(values=self._drives)

        if not self._drives:
            self._var_drive.set("")
            self._btn_expulsar.configure(state="disabled")
            if anunciar:
                self._estado.alerta(
                    "No se detecto ninguna USB conectada. Conecta una y dale a "
                    "Actualizar lista."
                )
            return

        if self._var_drive.get() not in self._drives:
            self._var_drive.set(self._drives[0])
        self._btn_expulsar.configure(state="normal")
        if anunciar:
            self._estado.info("Elige la unidad y dale a Expulsar.")

    # ------------------------------------------------------------------
    # Expulsion
    # ------------------------------------------------------------------

    def _expulsar(self) -> None:
        drive = self._var_drive.get()
        if not drive:
            return

        if not messagebox.askyesno(
            "Expulsar USB",
            f"Vas a expulsar la unidad {drive}. Asegurate de haber cerrado "
            "cualquier archivo que tengas abierto desde ahi. Continuar?",
            parent=self,
        ):
            self._estado.info("Operacion cancelada.")
            return

        self._btn_expulsar.configure(state="disabled")
        self._combo.configure(state="disabled")
        self._estado.info(f"Expulsando {drive}...")

        def trabajo():
            return _eject_drive(drive)

        self.run_async(trabajo, self._expulsion_lista)

    def _expulsion_lista(self, ok: bool, resultado) -> None:
        self._combo.configure(state="readonly")
        if self._drives:
            self._btn_expulsar.configure(state="normal")

        if not ok:
            self._estado.alerta(
                "No se pudo completar la expulsion. Intenta de nuevo."
            )
            return

        status = resultado.get("status")
        drive = resultado.get("drive", "?")

        if status == "no_windows":
            self._estado.alerta("La expulsion segura solo esta disponible en Windows.")
        elif status == "open_error":
            self._estado.alerta(
                f"Error del sistema al intentar acceder a {drive}: "
                f"{resultado.get('error', '?')}"
            )
        elif status == "access_denied":
            self._estado.alerta(
                f"No se pudo acceder a {drive} para expulsarla. Puede que "
                "necesites permisos de administrador."
            )
        elif status == "in_use":
            self._estado.alerta(
                f"No se pudo expulsar {drive}: la unidad esta en uso. Cierra "
                "los archivos o programas que la esten usando e intenta de nuevo."
            )
        elif status == "ejected":
            self._estado.exito(
                f"Unidad {drive} expulsada correctamente. Ya puedes retirarla."
            )
            # Tras expulsarla ya no debe seguir en la lista de unidades, pero
            # sin pisar el mensaje de exito que se acaba de mostrar arriba.
            self._detectar(anunciar=False)
        elif status == "unverified":
            self._estado.alerta(
                f"Se envio la expulsion de {drive}, pero no se pudo confirmar "
                "si de verdad se solto. Verifica en el explorador de archivos "
                "antes de retirarla."
            )
        elif status == "still_present":
            self._estado.alerta(
                f"Se envio el comando de expulsion para {drive}, pero la "
                "unidad sigue apareciendo en el sistema. No la retires "
                "todavia; puede seguir en uso."
            )
        else:
            self._estado.alerta("No se pudo determinar el resultado de la expulsion.")
