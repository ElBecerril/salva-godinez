"""Pantalla: Quitar impresoras duplicadas (fantasma).

Reusa por completo la logica de tools/ghost_printers.py: obtener la lista de
impresoras, detectar cuales son "fantasma" (copias duplicadas o redirigidas
de sesion remota) y borrarlas por nombre. Esta pantalla solo pinta la lista
y las casillas; la deteccion y el borrado viven en tools/.

DESTRUCTIVO: quitar una impresora es irreversible (hay que volver a
instalarla desde cero). Solo se ofrecen para borrado en bloque las que
tools/ghost_printers.py marca como "_auto_candidate" (patron sin ambiguedad);
las demas se muestran como aviso para revision manual, igual que en consola.
"""

import tkinter as tk
from tkinter import ttk

from gui.base import EstadoLabel, ToolPanel
from tools import is_admin
from tools.ghost_printers import (
    PrinterQueryError,
    _get_printers,
    _identify_ghosts,
    _remove_printer,
)


class PanelImpresorasDuplicadas(ToolPanel):
    TITULO = "Quitar impresoras duplicadas"
    DESCRIPCION = (
        "Busca impresoras 'fantasma': copias duplicadas (ej. 'HP Copia 2') "
        "o impresoras redirigidas de una sesion remota. Nada se borra hasta "
        "que tu lo marques y lo confirmes."
    )

    def build(self) -> None:
        self._candidatos: list[dict] = []
        self._vars: dict[str, tk.BooleanVar] = {}

        barra = ttk.Frame(self.body, style="Panel.TFrame")
        barra.pack(fill="x")

        self._btn_buscar = ttk.Button(
            barra, text="Buscar impresoras", style="Accent.TButton",
            command=self._buscar,
        )
        self._btn_buscar.pack(side="left")

        self._barra = ttk.Progressbar(barra, mode="indeterminate", length=200)

        self._estado = EstadoLabel(self.body)
        self._estado.pack(anchor="w", pady=(14, 0))
        self._estado.info(
            "Todavia no he revisado nada. Dale a 'Buscar impresoras' cuando "
            "quieras."
        )

        self._zona = ttk.Frame(self.body, style="Panel.TFrame")
        self._zona.pack(fill="both", expand=True, pady=(16, 0))

    # ------------------------------------------------------------------
    # Busqueda
    # ------------------------------------------------------------------

    def _buscar(self) -> None:
        self._btn_buscar.configure(state="disabled")
        self._barra.pack(side="left", padx=(14, 0))
        self._barra.start(12)
        self._estado.info("Buscando impresoras instaladas...")
        for w in self._zona.winfo_children():
            w.destroy()

        self.run_async(_get_printers, self._busqueda_lista)

    def _busqueda_lista(self, ok: bool, resultado) -> None:
        self._barra.stop()
        self._barra.pack_forget()
        self._btn_buscar.configure(state="normal")

        if not ok:
            if isinstance(resultado, PrinterQueryError):
                self._estado.alerta(
                    "No se pudo obtener la lista de impresoras. Intenta de "
                    "nuevo."
                )
            else:
                self._estado.alerta("Algo salio mal al buscar impresoras.")
            return

        printers = resultado
        if not printers:
            self._estado.info("No hay impresoras instaladas en esta PC.")
            return

        ghosts = _identify_ghosts(printers)
        if not ghosts:
            self._estado.exito(
                f"Revise {len(printers)} impresora(s) y no encontre "
                "ninguna duplicada."
            )
            return

        self._estado.info(
            f"Encontre {len(ghosts)} impresora(s) que parecen duplicadas."
        )
        self._pintar(ghosts)

    # ------------------------------------------------------------------
    # Pintado
    # ------------------------------------------------------------------

    def _pintar(self, ghosts: list[dict]) -> None:
        for w in self._zona.winfo_children():
            w.destroy()
        self._vars.clear()

        candidatos = [g for g in ghosts if g.get("_auto_candidate")]
        solo_revision = [g for g in ghosts if not g.get("_auto_candidate")]
        self._candidatos = candidatos

        if solo_revision:
            ttk.Label(
                self._zona, text="Para revisar a mano", style="Section.TLabel",
            ).pack(anchor="w")
            ttk.Label(
                self._zona,
                text=(
                    "Estos nombres podrian ser duplicados, pero no es "
                    "seguro: revisalos tu y borralos desde Configuracion de "
                    "Windows si de verdad sobran."
                ),
                style="Subtitle.TLabel",
            ).pack(anchor="w", pady=(2, 6))
            for g in solo_revision:
                ttk.Label(
                    self._zona, text=f"  •  {g.get('Name', '?')}",
                    style="Panel.TLabel",
                ).pack(anchor="w")

        if not candidatos:
            return

        ttk.Label(
            self._zona, text="Candidatas a eliminar", style="Section.TLabel",
        ).pack(anchor="w", pady=(14 if solo_revision else 0, 0))

        if not is_admin():
            ttk.Label(
                self._zona,
                text=(
                    "Para borrar impresoras hay que abrir la app como "
                    "administrador."
                ),
                style="Subtitle.TLabel",
            ).pack(anchor="w", pady=(4, 0))
            return

        lista = ttk.Frame(self._zona, style="Panel.TFrame")
        lista.pack(fill="x", pady=(6, 0))

        for g in candidatos:
            nombre = g.get("Name", "?")
            var = tk.BooleanVar(value=False)
            self._vars[nombre] = var
            fila = ttk.Frame(lista, style="Panel.TFrame")
            fila.pack(fill="x", pady=(2, 0))
            ttk.Checkbutton(fila, variable=var, text=nombre).pack(anchor="w")
            ttk.Label(
                fila, text=f"     {g.get('_ghost_reason', '')}",
                style="Subtitle.TLabel",
            ).pack(anchor="w")

        acciones = ttk.Frame(self._zona, style="Panel.TFrame")
        acciones.pack(side="bottom", fill="x", pady=(18, 0))
        self._btn_eliminar = ttk.Button(
            acciones, text="Eliminar las marcadas", style="Danger.TButton",
            command=self._eliminar,
        )
        self._btn_eliminar.pack(side="left")

    # ------------------------------------------------------------------
    # Eliminacion
    # ------------------------------------------------------------------

    def _eliminar(self) -> None:
        if getattr(self, "_eliminando", False):
            return

        marcadas = [nombre for nombre, v in self._vars.items() if v.get()]
        if not marcadas:
            self._estado.info("No marcaste nada, asi que no toque nada.")
            return

        if not self.confirmar_destructivo(
            "Eliminar impresoras",
            f"Vas a eliminar {len(marcadas)} impresora(s):\n\n"
            + "\n".join(f"- {n}" for n in marcadas)
            + "\n\nEsto no se puede deshacer: para volver a tenerlas hay que "
            "instalarlas de nuevo.\n\nSeguro que quieres eliminarlas?",
        ):
            self._estado.info("No se elimino ninguna impresora.")
            return

        self._eliminando = True
        self._btn_eliminar.configure(state="disabled")
        self._estado.info("Eliminando...")

        def trabajo():
            eliminadas = []
            fallidas = []
            for nombre in marcadas:
                if _remove_printer(nombre):
                    eliminadas.append(nombre)
                else:
                    fallidas.append(nombre)
            return {"eliminadas": eliminadas, "fallidas": fallidas}

        self.run_async(trabajo, self._eliminacion_lista, destructivo=True)

    def _eliminacion_lista(self, ok: bool, resultado) -> None:
        self._eliminando = False
        if self._btn_eliminar.winfo_exists():
            self._btn_eliminar.configure(state="normal")

        if not ok:
            self._estado.alerta("Algo salio mal al eliminar las impresoras.")
            self.error(
                "No se pudo completar",
                "Ocurrio un error inesperado al eliminar las impresoras.",
            )
            return

        eliminadas = resultado["eliminadas"]
        fallidas = resultado["fallidas"]

        if eliminadas:
            self._estado.exito(
                f"Se eliminaron {len(eliminadas)} impresora(s)."
                + (f" No se pudieron eliminar: {', '.join(fallidas)}." if fallidas else "")
            )
        else:
            self._estado.alerta(
                "No se pudo eliminar ninguna impresora. Intenta de nuevo."
            )

        # Re-buscar deja la lista al dia sin que el usuario tenga que
        # adivinar si ya se aplico.
        self._buscar()
