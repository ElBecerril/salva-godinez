"""Pantalla: Carpetas de red (unidades mapeadas).

Ve, conecta y desconecta unidades de red (letra: -> \\\\servidor\\carpeta).
Esta pantalla NO reimplementa el parseo de 'net use' ni la llamada al
sistema: usa las funciones de logica de tools/net_drive.py
(_parse_net_use_output, _run_net_use, NetUseError), las mismas que usa el
menu de consola net_drive_menu().

Desconectar una unidad no borra archivos, pero rompe accesos directos y
scripts que dependan de esa letra, asi que pasa SIEMPRE por
confirmar_destructivo() con default No antes de tocar nada.
"""

import tkinter as tk
from tkinter import ttk

from gui.base import EstadoLabel, ToolPanel
from tools.net_drive import NetUseError, _parse_net_use_output, _run_net_use

_OK_STATUSES = {"", "OK", "CORRECTO", "CONNECTED", "DISPONIBLE"}


class PanelCarpetasRed(ToolPanel):
    TITULO = "Conectar carpetas de red"
    DESCRIPCION = (
        "Ve las carpetas de red conectadas a este equipo, conecta una nueva "
        "o desconecta una que ya no uses."
    )

    def build(self) -> None:
        self._por_iid: dict[str, dict] = {}

        # --- Ver / desconectar ------------------------------------------
        acciones = ttk.Frame(self.body, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(12, 0))

        self._btn_actualizar = ttk.Button(
            acciones, text="Actualizar lista", style="Accent.TButton",
            command=self._actualizar,
        )
        self._btn_actualizar.pack(side="left")

        self._btn_desconectar = ttk.Button(
            acciones, text="Desconectar", style="Danger.TButton",
            command=self._desconectar, state="disabled",
        )
        self._btn_desconectar.pack(side="left", padx=(10, 0))

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(0, 10))

        tabla_frame = ttk.Frame(self.body, style="Panel.TFrame")
        tabla_frame.pack(fill="both", expand=True)

        columnas = ("letra", "remota", "estado")
        self._tabla = ttk.Treeview(
            tabla_frame, columns=columnas, show="headings", height=8,
        )
        self._tabla.heading("letra", text="Letra")
        self._tabla.heading("remota", text="Ruta remota")
        self._tabla.heading("estado", text="Estado")
        self._tabla.column("letra", width=70, anchor="w", stretch=False)
        self._tabla.column("remota", width=340, anchor="w", stretch=True)
        self._tabla.column("estado", width=140, anchor="w", stretch=False)

        scroll_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=scroll_y.set)
        self._tabla.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="left", fill="y")

        self._tabla.bind("<<TreeviewSelect>>", self._on_seleccion)

        # --- Conectar nueva ----------------------------------------------
        ttk.Label(
            self.body, text="Conectar una carpeta de red nueva",
            style="Section.TLabel",
        ).pack(anchor="w", pady=(18, 6))

        form = ttk.Frame(self.body, style="Panel.TFrame")
        form.pack(anchor="w", fill="x")

        ttk.Label(form, text="Letra:", style="Panel.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        self._var_letra = tk.StringVar()
        ttk.Entry(form, textvariable=self._var_letra, width=5).grid(row=0, column=1, sticky="w", padx=(6, 20))

        ttk.Label(form, text="Ruta UNC:", style="Panel.TLabel").grid(row=0, column=2, sticky="w", pady=4)
        self._var_ruta = tk.StringVar()
        ttk.Entry(form, textvariable=self._var_ruta, width=38).grid(row=0, column=3, sticky="w", padx=(6, 0))

        self._var_requiere_creds = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            form, text="Requiere usuario y contrasena",
            variable=self._var_requiere_creds, command=self._on_toggle_creds,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 4))

        ttk.Label(form, text="Usuario:", style="Panel.TLabel").grid(row=2, column=0, sticky="w", pady=4)
        self._var_usuario = tk.StringVar()
        self._campo_usuario = ttk.Entry(form, textvariable=self._var_usuario, width=20, state="disabled")
        self._campo_usuario.grid(row=2, column=1, columnspan=2, sticky="w", padx=(6, 20))

        ttk.Label(form, text="Contrasena:", style="Panel.TLabel").grid(row=2, column=3, sticky="w", pady=4)
        self._var_clave = tk.StringVar()
        self._campo_clave = ttk.Entry(
            form, textvariable=self._var_clave, width=20, show="*", state="disabled",
        )
        self._campo_clave.grid(row=2, column=4, sticky="w", padx=(6, 0))

        self._btn_conectar = ttk.Button(
            self.body, text="Conectar", style="Accent.TButton", command=self._conectar,
        )
        self._btn_conectar.pack(anchor="w", pady=(10, 0))

        self._actualizar()

    def _on_toggle_creds(self) -> None:
        estado = "normal" if self._var_requiere_creds.get() else "disabled"
        self._campo_usuario.configure(state=estado)
        self._campo_clave.configure(state=estado)

    # ------------------------------------------------------------------
    # Ver unidades mapeadas
    # ------------------------------------------------------------------

    def _actualizar(self) -> None:
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
        self._por_iid.clear()
        self._btn_desconectar.configure(state="disabled")
        self._btn_actualizar.configure(state="disabled")
        self._estado.info("Consultando carpetas de red conectadas...")

        self.run_async(_listar_unidades, self._on_lista_lista)

    def _on_lista_lista(self, ok: bool, resultado) -> None:
        self._btn_actualizar.configure(state="normal")

        if not ok or (isinstance(resultado, dict) and resultado.get("error")):
            self._estado.alerta("No se pudo consultar las carpetas de red conectadas.")
            return

        unidades = resultado
        if not unidades:
            self._estado.alerta("No hay carpetas de red conectadas en este equipo.")
            return

        for i, u in enumerate(unidades):
            iid = str(i)
            self._por_iid[iid] = u
            estado_texto = u["status"] if u["status"].strip() else "OK"
            self._tabla.insert(
                "", "end", iid=iid,
                values=(u["letter"], u["remote"], estado_texto),
            )

        self._estado.exito(f"Se encontraron {len(unidades)} carpeta(s) de red conectadas.")

    def _on_seleccion(self, _evento=None) -> None:
        seleccion = self._tabla.selection()
        self._btn_desconectar.configure(state="normal" if seleccion else "disabled")

    # ------------------------------------------------------------------
    # Desconectar
    # ------------------------------------------------------------------

    def _desconectar(self) -> None:
        seleccion = self._tabla.selection()
        if not seleccion:
            return
        unidad = self._por_iid.get(seleccion[0])
        if unidad is None:
            return

        confirmado = self.confirmar_destructivo(
            "Desconectar carpeta de red",
            f"Vas a desconectar la unidad {unidad['letter']} "
            f"({unidad['remote']}).\n\n"
            "Esto no borra ningun archivo, pero los accesos directos y "
            "programas que usen esta letra dejaran de funcionar hasta que "
            "la vuelvas a conectar.\n\n"
            "Deseas continuar?",
        )
        if not confirmado:
            return

        self._btn_desconectar.configure(state="disabled")
        self._btn_actualizar.configure(state="disabled")
        self._estado.info(f"Desconectando {unidad['letter']}...")

        def trabajo():
            return _desconectar_unidad(unidad["letter"])

        def on_done(ok: bool, resultado) -> None:
            self._btn_actualizar.configure(state="normal")
            if not ok or not resultado.get("ok"):
                mensaje = resultado.get("error", "Error desconocido") if ok else str(resultado)
                self._estado.alerta(f"No se pudo desconectar: {mensaje}")
                self.error(
                    "No se pudo desconectar",
                    f"No se pudo desconectar la unidad {unidad['letter']}. "
                    f"Detalle: {mensaje}",
                )
                return
            self._estado.exito(f"Unidad {unidad['letter']} desconectada.")
            self._actualizar()

        self.run_async(trabajo, on_done, destructivo=True)

    # ------------------------------------------------------------------
    # Conectar
    # ------------------------------------------------------------------

    def _conectar(self) -> None:
        letra = self._var_letra.get().strip().upper()
        if not letra or not letra[0].isalpha():
            self._estado.alerta("Escribe una letra de unidad valida, por ejemplo Z.")
            return
        letra = letra[0] + ":"

        ruta = self._var_ruta.get().strip()
        if not ruta.startswith("\\\\"):
            self._estado.alerta(
                "La ruta debe ser una ruta de red (debe empezar con \\\\)."
            )
            return

        args = [letra, ruta, "/persistent:yes"]
        clave = None
        if self._var_requiere_creds.get():
            usuario = self._var_usuario.get().strip()
            clave = self._var_clave.get()
            if not usuario:
                self._estado.alerta("Escribe el usuario para conectarte.")
                return
            # La clave va con '*' (net use la pide por stdin), NO como argumento:
            # en argv seria visible en la lista de procesos del sistema.
            args = [letra, ruta, "*", f"/user:{usuario}", "/persistent:yes"]

        self._btn_conectar.configure(state="disabled")
        self._estado.info(f"Conectando {letra}...")

        def trabajo():
            return _conectar_unidad(args, clave)

        def on_done(ok: bool, resultado) -> None:
            self._btn_conectar.configure(state="normal")
            if not ok or not resultado.get("ok"):
                mensaje = resultado.get("error", "Error desconocido") if ok else str(resultado)
                self._estado.alerta(f"No se pudo conectar: {mensaje}")
                self.error(
                    "No se pudo conectar",
                    f"No se pudo conectar la unidad {letra}. Revisa la ruta, "
                    f"el usuario y la contrasena.\n\nDetalle: {mensaje}",
                )
                return
            self._estado.exito(f"Unidad {letra} conectada a {ruta}.")
            self._var_letra.set("")
            self._var_ruta.set("")
            self._var_usuario.set("")
            self._var_clave.set("")
            self._actualizar()

        self.run_async(trabajo, on_done)


# ----------------------------------------------------------------------
# Trabajo de fondo (corre en el hilo de trabajo, NO toca widgets). Cada una
# envuelve las funciones de logica de tools/net_drive.py y traduce sus
# excepciones a un dict {"ok": .., "error": ..} para que la pantalla no
# tenga que atrapar excepciones especificas del modulo de logica.
# ----------------------------------------------------------------------


def _listar_unidades() -> list[dict]:
    try:
        return _parse_net_use_output()
    except NetUseError:
        return []


def _desconectar_unidad(letra: str) -> dict:
    try:
        resultado = _run_net_use([letra, "/delete"])
    except NetUseError as e:
        return {"ok": False, "error": str(e)}

    if resultado.returncode == 0:
        return {"ok": True}
    error = resultado.stderr.strip() or resultado.stdout.strip()
    return {"ok": False, "error": error}


def _conectar_unidad(args: list[str], password: str | None = None) -> dict:
    try:
        resultado = _run_net_use(args, password)
    except NetUseError as e:
        return {"ok": False, "error": str(e)}

    if resultado.returncode == 0:
        return {"ok": True}
    error = (getattr(resultado, "stderr", "") or "").strip() or \
            (getattr(resultado, "stdout", "") or "").strip()
    return {"ok": False, "error": error}
