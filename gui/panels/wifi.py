"""Pantalla: Contrasenas WiFi guardadas.

Dato sensible: son las contrasenas de las redes WiFi que Windows recuerda.
Por eso esta pantalla NUNCA las escribe en un archivo ni las manda a ningun
lado; solo las lee via tools/wifi_passwords.get_wifi_passwords() (la misma
funcion de logica que usa la consola) y las muestra ocultas por defecto.

Alguien puede tener la pantalla proyectada en una sala de juntas, asi que la
contrasena de una red NO aparece en la tabla hasta que el usuario selecciona
esa fila y aprieta "Mostrar" a proposito. Hay tambien un boton "Copiar" que la
manda directo al portapapeles sin pasar por pantalla.
"""

import tkinter as tk
from tkinter import ttk

from gui.base import EstadoLabel, ToolPanel
from tools.wifi_passwords import _mask, get_wifi_passwords


class PanelWifi(ToolPanel):
    TITULO = "Ver contrasenas WiFi guardadas"
    DESCRIPCION = (
        "Muestra las redes WiFi que este equipo recuerda. Las contrasenas "
        "quedan ocultas: selecciona una red y usa 'Mostrar' o 'Copiar' solo "
        "cuando la necesites."
    )

    def build(self) -> None:
        # iid de la tabla -> registro completo (con la contrasena real).
        self._por_iid: dict[str, dict] = {}
        # iids cuya contrasena esta mostrada ahora mismo en claro.
        self._mostrando: set[str] = set()

        # --- Acciones --------------------------------------------------
        # Ancladas abajo y empaquetadas ANTES que la tabla: si no, la tabla
        # (expand=True) se come el espacio y quedan fuera de la ventana.
        acciones = ttk.Frame(self.body, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(12, 0))

        self._btn_buscar = ttk.Button(
            acciones, text="Buscar redes guardadas", style="Accent.TButton",
            command=self._buscar,
        )
        self._btn_buscar.pack(side="left")

        self._btn_mostrar = ttk.Button(
            acciones, text="Mostrar", command=self._alternar_mostrar, state="disabled",
        )
        self._btn_mostrar.pack(side="left", padx=(10, 0))

        self._btn_copiar = ttk.Button(
            acciones, text="Copiar contrasena", command=self._copiar, state="disabled",
        )
        self._btn_copiar.pack(side="left", padx=(10, 0))

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(0, 10))

        # --- Tabla -----------------------------------------------------
        tabla_frame = ttk.Frame(self.body, style="Panel.TFrame")
        tabla_frame.pack(fill="both", expand=True)

        columnas = ("red", "contrasena", "seguridad")
        self._tabla = ttk.Treeview(
            tabla_frame, columns=columnas, show="headings", height=12,
        )
        self._tabla.heading("red", text="Red")
        self._tabla.heading("contrasena", text="Contrasena")
        self._tabla.heading("seguridad", text="Seguridad")
        self._tabla.column("red", width=260, anchor="w", stretch=True)
        self._tabla.column("contrasena", width=160, anchor="w", stretch=False)
        self._tabla.column("seguridad", width=180, anchor="w", stretch=False)

        scroll_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=scroll_y.set)
        self._tabla.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="left", fill="y")

        self._tabla.bind("<<TreeviewSelect>>", self._on_seleccion)

        self._estado.info(
            "Aprieta 'Buscar redes guardadas' para ver las redes WiFi de este equipo."
        )

    # ------------------------------------------------------------------
    # Busqueda
    # ------------------------------------------------------------------

    def _buscar(self) -> None:
        for fila in self._tabla.get_children():
            self._tabla.delete(fila)
        self._por_iid.clear()
        self._mostrando.clear()
        self._btn_mostrar.configure(state="disabled", text="Mostrar")
        self._btn_copiar.configure(state="disabled")

        self._btn_buscar.configure(state="disabled")
        self._estado.info("Buscando redes WiFi guardadas...")

        self.run_async(get_wifi_passwords, self._on_busqueda_lista)

    def _on_busqueda_lista(self, ok: bool, resultado) -> None:
        self._btn_buscar.configure(state="normal")

        if not ok:
            self._estado.alerta("No se pudieron obtener las redes WiFi.")
            self.error(
                "Error",
                "No se pudo leer la lista de redes WiFi guardadas. Intenta de nuevo.",
            )
            return

        redes = resultado
        if not redes:
            self._estado.alerta("No se encontraron redes WiFi guardadas en este equipo.")
            return

        for i, red in enumerate(redes):
            iid = str(i)
            self._por_iid[iid] = red
            self._tabla.insert(
                "", "end", iid=iid,
                values=(red["red"], self._texto_oculto(red), red["seguridad"] or "?"),
            )

        self._estado.exito(f"Se encontraron {len(redes)} red(es).")

    def _texto_oculto(self, red: dict) -> str:
        if not red.get("contrasena"):
            return "(sin contrasena)"
        return _mask(red["contrasena"])

    # ------------------------------------------------------------------
    # Mostrar / ocultar / copiar
    # ------------------------------------------------------------------

    def _on_seleccion(self, _evento=None) -> None:
        seleccion = self._tabla.selection()
        if not seleccion:
            self._btn_mostrar.configure(state="disabled", text="Mostrar")
            self._btn_copiar.configure(state="disabled")
            return

        iid = seleccion[0]
        red = self._por_iid.get(iid, {})
        tiene_clave = bool(red.get("contrasena"))

        self._btn_copiar.configure(state="normal" if tiene_clave else "disabled")
        self._btn_mostrar.configure(
            state="normal" if tiene_clave else "disabled",
            text="Ocultar" if iid in self._mostrando else "Mostrar",
        )

    def _alternar_mostrar(self) -> None:
        seleccion = self._tabla.selection()
        if not seleccion:
            return
        iid = seleccion[0]
        red = self._por_iid.get(iid)
        if red is None or not red.get("contrasena"):
            return

        if iid in self._mostrando:
            self._mostrando.discard(iid)
            self._tabla.set(iid, "contrasena", self._texto_oculto(red))
            self._btn_mostrar.configure(text="Mostrar")
        else:
            self._mostrando.add(iid)
            self._tabla.set(iid, "contrasena", red["contrasena"])
            self._btn_mostrar.configure(text="Ocultar")

    def _copiar(self) -> None:
        seleccion = self._tabla.selection()
        if not seleccion:
            return
        red = self._por_iid.get(seleccion[0])
        if red is None or not red.get("contrasena"):
            return

        self.clipboard_clear()
        self.clipboard_append(red["contrasena"])
        self._estado.exito(f"Contrasena de '{red['red']}' copiada al portapapeles.")
