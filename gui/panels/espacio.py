"""Pantalla de Liberar Espacio en Disco.

La escribe y mantiene el mismo criterio que la version de consola: esta es la
unica pantalla del piloto que BORRA cosas del usuario, asi que las reglas de
operaciones destructivas del proyecto aplican aqui con lupa.

Decisiones deliberadas, no accidentes:
  - Nada viene pre-seleccionado. El usuario marca lo que quiere limpiar.
  - Vaciar la papelera es lo unico irreversible y pide su propia confirmacion
    aparte, con el default en No.
  - Las descargas antiguas se listan UNA POR UNA con su fecha y se eligen a
    mano; se mandan a la Papelera, no se borran.
  - Si el usuario marca todo, la papelera se vacia ANTES de mover las
    descargas; al reves destruiriamos lo que acabamos de mandar ahi.
  - Lo movido a la papelera NO se reporta como espacio liberado, porque no lo
    es: sigue ocupando disco hasta que se vacie.
"""

import tkinter as tk
from tkinter import ttk

from config import OLD_DOWNLOAD_DAYS
from gui import theme
from gui.base import ToolPanel, EstadoLabel
from tools import format_size, is_admin
from tools.disk_cleaner import (
    _query_recycle_bin,
    _scan_old_downloads,
    _scan_temp_files,
    _scan_update_cache,
    ejecutar_limpieza,
)


class PanelEspacio(ToolPanel):
    TITULO = "Liberar espacio en disco"
    DESCRIPCION = (
        "Busca archivos que ya no sirven y ocupan lugar en tu computadora. "
        "Nada se borra hasta que tu lo marques y lo confirmes."
    )

    def build(self) -> None:
        self._temp = (0, 0, [])
        self._update = (0, 0)
        self._descargas = (0, 0, [])
        self._papelera = (0, 0)
        self._vars: dict[str, tk.BooleanVar] = {}
        self._filas: dict[str, ttk.Label] = {}
        self._archivos_dl: dict[str, tk.BooleanVar] = {}

        barra = ttk.Frame(self.body, style="Panel.TFrame")
        barra.pack(fill="x")

        self.btn_analizar = ttk.Button(
            barra, text="Analizar mi computadora", style="Accent.TButton",
            command=self._analizar,
        )
        self.btn_analizar.pack(side="left")

        self.progreso = ttk.Progressbar(barra, mode="indeterminate", length=200)

        self.estado = EstadoLabel(self.body)
        self.estado.pack(anchor="w", pady=(14, 0))
        self.estado.info("Todavia no he revisado nada. Dale a Analizar cuando quieras.")

        self.zona = ttk.Frame(self.body, style="Panel.TFrame")
        self.zona.pack(fill="both", expand=True, pady=(16, 0))

    # ------------------------------------------------------------------
    # Analisis
    # ------------------------------------------------------------------

    def _analizar(self) -> None:
        self.btn_analizar.configure(state="disabled")
        self.progreso.pack(side="left", padx=(14, 0))
        self.progreso.start(12)
        self.estado.info("Revisando... esto puede tardar un poco.")
        for w in self.zona.winfo_children():
            w.destroy()

        def trabajo():
            return {
                "temp": _scan_temp_files(),
                "update": _scan_update_cache(),
                "descargas": _scan_old_downloads(),
                "papelera": _query_recycle_bin(),
            }

        self.run_async(trabajo, self._analisis_listo)

    def _analisis_listo(self, ok: bool, res) -> None:
        self.progreso.stop()
        self.progreso.pack_forget()
        self.btn_analizar.configure(state="normal")

        if not ok:
            self.estado.alerta(f"No pude revisar el disco: {res}")
            return

        self._temp = res["temp"]
        self._update = res["update"]
        self._descargas = res["descargas"]
        self._papelera = res["papelera"]
        self._pintar_resultados()

    def _pintar_resultados(self) -> None:
        for w in self.zona.winfo_children():
            w.destroy()
        self._vars.clear()
        self._archivos_dl.clear()

        temp_size, temp_count, _ = self._temp
        up_size, up_count = self._update
        dl_size, dl_count, dl_files = self._descargas
        rb_size, rb_count = self._papelera

        hay_algo = temp_count or up_count or dl_count or rb_count
        if not hay_algo:
            self.estado.exito("Todo limpio: no encontre nada que valga la pena borrar.")
            return

        self.estado.info("Marca lo que quieras limpiar. Nada se toca hasta que confirmes.")

        ttk.Label(self.zona, text="Que encontre", style="Section.TLabel").pack(anchor="w")

        if temp_count:
            self._fila(
                "temp", "Archivos temporales", temp_count, temp_size,
                "Basura que dejan los programas. Windows los vuelve a crear solo.",
            )
        if up_count:
            self._fila(
                "update", "Cache de Windows Update", up_count, up_size,
                "Instaladores de actualizaciones ya aplicadas. Se pueden borrar.",
            )
        elif not is_admin():
            ttk.Label(
                self.zona,
                text="  Cache de Windows Update: para revisarlo hay que abrir la app como administrador.",
                style="Subtitle.TLabel",
            ).pack(anchor="w", pady=(6, 0))
        if dl_count:
            # SIN casilla propia: las descargas se eligen archivo por archivo en
            # la lista de abajo, que va inmediatamente despues de este
            # encabezado. Tener casilla aqui Y casilla por archivo confundia:
            # dos controles identicos que significan cosas distintas, y el
            # usuario (incluido el autor) marcaba los archivos y la app
            # respondia "no marcaste nada".
            self._encabezado_descargas(dl_count, dl_size)
            self._lista_descargas(dl_files)

        if rb_count:
            self._fila(
                "recycle", "Vaciar la papelera de reciclaje", rb_count, rb_size,
                "OJO: esto si es para siempre. Lo que este ahi no se puede recuperar.",
                peligroso=True,
            )

        # El boton se ancla abajo y se empaqueta ANTES de la lista de descargas
        # (que expande): si va despues, con muchas descargas el boton principal
        # queda fuera de la ventana y la pantalla parece no tener accion.
        acciones = ttk.Frame(self.zona, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(18, 0))
        self._btn_limpiar = ttk.Button(
            acciones, text="Limpiar lo que marque", style="Danger.TButton",
            command=self._limpiar,
        )
        self._btn_limpiar.pack(side="left")

    def _fila(self, clave, titulo, count, size, ayuda, peligroso=False) -> None:
        marco = ttk.Frame(self.zona, style="Panel.TFrame")
        marco.pack(fill="x", pady=(10, 0))

        # Sin pre-seleccion: marcar por default lo que borra es exactamente el
        # patron que el proyecto prohibe.
        var = tk.BooleanVar(value=False)
        self._vars[clave] = var

        ttk.Checkbutton(
            marco, variable=var,
            text=f"{titulo}  —  {count} archivo(s), {format_size(size)}",
        ).pack(anchor="w")
        ttk.Label(
            marco, text=f"     {ayuda}", style="Subtitle.TLabel",
            foreground=theme.DANGER if peligroso else theme.FG_SOFT,
        ).pack(anchor="w")

    def _encabezado_descargas(self, count: int, size: int) -> None:
        """Encabezado de las descargas: informa, no se marca."""
        marco = ttk.Frame(self.zona, style="Panel.TFrame")
        marco.pack(fill="x", pady=(14, 0))
        ttk.Label(
            marco,
            text=(f"Descargas de hace mas de {OLD_DOWNLOAD_DAYS} dias  —  "
                  f"{count} archivo(s), {format_size(size)}"),
            style="Section.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            marco,
            text="     Palomea las que quieras quitar. Van a la Papelera, asi que "
                 "puedes recuperarlas si te arrepientes.",
            style="Subtitle.TLabel",
        ).pack(anchor="w")

    def _lista_descargas(self, dl_files: list[str]) -> None:
        import os
        import time

        caja = ttk.Frame(self.zona, style="Panel.TFrame")
        caja.pack(fill="both", expand=True, pady=(6, 0), padx=(24, 0))

        # "Marcar todas / Ninguna": patron que la gente ya conoce de su correo,
        # y que no se confunde con una casilla que significa otra cosa.
        atajos = ttk.Frame(caja, style="Panel.TFrame")
        atajos.pack(anchor="w", pady=(0, 4))
        ttk.Button(
            atajos, text="Marcar todas", command=lambda: self._marcar_descargas(True),
        ).pack(side="left")
        ttk.Button(
            atajos, text="Ninguna", command=lambda: self._marcar_descargas(False),
        ).pack(side="left", padx=(8, 0))

        lienzo = tk.Canvas(caja, height=150, bg=theme.BG_PANEL, highlightthickness=1,
                           highlightbackground=theme.BORDER)
        scroll = ttk.Scrollbar(caja, orient="vertical", command=lienzo.yview)
        interior = ttk.Frame(lienzo, style="Panel.TFrame")
        interior.bind("<Configure>", lambda e: lienzo.configure(scrollregion=lienzo.bbox("all")))
        lienzo.create_window((0, 0), window=interior, anchor="nw")
        lienzo.configure(yscrollcommand=scroll.set)
        lienzo.pack(side="left", fill="both", expand=True, pady=(6, 0))
        scroll.pack(side="right", fill="y", pady=(6, 0))

        for ruta in dl_files:
            try:
                st = os.stat(ruta)
                detalle = f"{format_size(st.st_size)} · {time.strftime('%d/%m/%Y', time.localtime(st.st_mtime))}"
            except OSError:
                detalle = "?"
            var = tk.BooleanVar(value=False)
            self._archivos_dl[ruta] = var
            ttk.Checkbutton(
                interior, variable=var,
                text=f"{os.path.basename(ruta)}   ({detalle})",
            ).pack(anchor="w", padx=8)

    # ------------------------------------------------------------------
    # Marcado masivo de descargas
    # ------------------------------------------------------------------

    def _marcar_descargas(self, valor: bool) -> None:
        """Marca o desmarca todas las descargas de golpe."""
        for var in self._archivos_dl.values():
            var.set(valor)

    # ------------------------------------------------------------------
    # Limpieza
    # ------------------------------------------------------------------

    def _limpiar(self) -> None:
        # Guardia de reentrada. Deshabilitar el boton cubre el doble clic, pero
        # eso es proteccion en la VISTA; esto lo cubre aunque la llamada entre
        # por otro camino. Dos limpiezas a la vez sobre los mismos archivos se
        # pisan y dan reportes sin sentido.
        if getattr(self, "_limpiando", False):
            return

        elegidas_dl = [r for r, v in self._archivos_dl.items() if v.get()]
        marcadas = [k for k, v in self._vars.items() if v.get()]

        # Red de seguridad: si el usuario marco archivos concretos de la lista
        # de descargas, eso ES querer limpiarlas, aunque la casilla de la
        # categoria se haya quedado sin marcar. Antes esto contestaba "no
        # marcaste nada" con la lista llena de palomitas, y parecia que la app
        # estaba rota.
        if elegidas_dl:
            marcadas.append("downloads")

        if not marcadas:
            self.estado.info("No marcaste nada, asi que no toque nada.")
            return

        # La papelera es lo unico irreversible: confirmacion propia y separada,
        # con el default en No.
        if "recycle" in marcadas:
            rb_size, rb_count = self._papelera
            if not self.confirmar_destructivo(
                "Vaciar la papelera",
                f"Vas a borrar para siempre {rb_count} archivo(s) "
                f"({format_size(rb_size)}) de la papelera de reciclaje.\n\n"
                "Esto NO se puede deshacer. Si ahi hay algo que te importa, "
                "revisalo antes.\n\nSeguro que quieres vaciarla?",
            ):
                marcadas.remove("recycle")
                if not marcadas:
                    self.estado.info("No se vacio la papelera. No toque nada.")
                    return

        # Deshabilitar mientras corre: si no, un doble clic lanza DOS limpiezas
        # simultaneas sobre los mismos archivos y los resultados se pisan.
        self._limpiando = True
        self._btn_limpiar.configure(state="disabled")
        self.estado.info("Limpiando...")
        self._ejecutar(marcadas, elegidas_dl)

    def _ejecutar(self, marcadas: list[str], elegidas_dl: list[str]) -> None:
        temp_paths = self._temp[2]
        papelera_size, papelera_count = self._papelera

        # El PLAN de borrado (que orden, que cuenta como liberado, que hacer si
        # algo falla) NO se decide aqui: vive una sola vez en ejecutar_limpieza().
        # Esta pantalla solo traduce las casillas marcadas a decisiones.
        def trabajo():
            return ejecutar_limpieza(
                limpiar_temp="temp" in marcadas,
                limpiar_update="update" in marcadas,
                descargas=elegidas_dl if "downloads" in marcadas else [],
                vaciar_papelera="recycle" in marcadas,
                temp_paths=temp_paths,
                papelera_size=papelera_size,
                papelera_count=papelera_count,
            )

        # destructivo=True: borra archivos del usuario, asi que el hilo no es
        # daemon y la ventana no se deja cerrar hasta que termine.
        self.run_async(trabajo, self._limpieza_lista, destructivo=True)

    def _limpieza_lista(self, ok: bool, res) -> None:
        self._limpiando = False
        # El boton vive dentro de self.zona, que _pintar_resultados() destruye
        # y reconstruye; por eso se comprueba que siga existiendo.
        if self._btn_limpiar.winfo_exists():
            self._btn_limpiar.configure(state="normal")

        if not ok:
            self.estado.alerta(f"Algo fallo durante la limpieza: {res}")
            return

        partes = [
            f"Listo: {res['limpiados']} archivo(s) limpiados.",
            f"Espacio liberado: {format_size(res['liberado'])}.",
        ]
        if res["a_papelera"]:
            partes.append(
                f"Otros {format_size(res['a_papelera'])} estan en la Papelera: todavia "
                "ocupan disco y se liberan al vaciarla, pero mientras tanto puedes "
                "recuperarlos."
            )
        if res["papelera_fallo"]:
            _, papelera_count = self._papelera
            if papelera_count > 0:
                partes.append("No se pudo vaciar la papelera.")
            else:
                partes.append("La papelera ya estaba vacia.")
        if res["descargas_fallaron"]:
            partes.append(
                "No pude mover las descargas a la Papelera, asi que no borre ninguna: "
                "prefiero no liberar espacio antes que perderte un archivo."
            )
        self.estado.exito(" ".join(partes))

        # Re-analizar deja los numeros al dia sin que el usuario tenga que
        # adivinar si ya se aplico.
        self._analizar()
