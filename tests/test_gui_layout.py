"""QA de la GUI real: los 23 paneles abren, y nada queda cortado.

Abre la App de verdad (una ventana, unos segundos) y para cada panel, a tamano
normal y al MINIMO que permite la app (900x560), comprueba:
  - se construye y se puede mostrar, sin excepciones de tkinter;
  - tiene al menos un control interactivo;
  - ningun boton/campo queda fuera de la ventana;
  - ningun boton, etiqueta o radio pide mas ancho del que recibio (el texto se
    corta por el borde: 'Elegir...' quedaba en 'Ele', el aviso legal perdia
    palabras). Es lo que no se ve en un test de logica.

Se omite solo si no hay pantalla/tkinter. Solo stdlib + las dependencias de la app:

    python3 tests/test_gui_layout.py
"""

import os
import sys
import tkinter as tk
import traceback
from tkinter import ttk

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

fallos = 0


def check(nombre, cond, extra=""):
    global fallos
    fallos += not cond
    marca = "OK " if cond else "FAIL"
    detalle = f" -> {extra}" if not cond and extra else ""
    print(f"[{marca}] {nombre}{detalle}")


try:
    probe = tk.Tk()
    probe.destroy()
except tk.TclError as e:
    print(f"[SKIP] sin pantalla o sin tkinter utilizable -> {e}")
    sys.exit(0)

import gui.actualizacion as _act  # noqa: E402
_act.arranque_gui = lambda *a, **k: None  # sin dialogos de origen ni red
from gui import app as gapp  # noqa: E402

errores_tk = []


def hijos(w):
    for c in w.winfo_children():
        yield c
        yield from hijos(c)


def ancestros(w):
    p = w.master
    while p is not None:
        yield p
        p = getattr(p, "master", None)


def texto_de(w):
    try:
        return str(w.cget("text"))[:28]
    except tk.TclError:
        return ""


app = gapp.App("qa")
app.report_callback_exception = lambda e, v, tb: errores_tk.append(
    "".join(traceback.format_exception(e, v, tb))[-400:])
app.update()

paneles = gapp._todos_los_paneles()
check("la app registra los 23 paneles", len(paneles) == 23, len(paneles))

CONTROLES = (ttk.Button, ttk.Entry, ttk.Combobox, tk.Text, ttk.Checkbutton,
             ttk.Radiobutton, tk.Listbox, ttk.Treeview, ttk.Spinbox)
CON_TEXTO = (ttk.Button, ttk.Label, ttk.Radiobutton, ttk.Checkbutton)

for tam, geometria in (("normal", None), ("minimo", "900x560+20+20")):
    if geometria:
        app.geometry(geometria)
    app.lift()
    app.update()
    for cls in paneles:
        antes = len(errores_tk)
        etiqueta = f"{cls.__name__} ({tam})"
        try:
            app._mostrar(cls)
            app.update_idletasks()
            app.update()
        except Exception:  # noqa: BLE001
            check(f"{etiqueta}: se muestra", False, traceback.format_exc()[-200:])
            continue
        panel = app._panel_actual
        problemas = []
        if not isinstance(panel, cls):
            problemas.append(f"panel actual = {type(panel).__name__}")
        controles = [w for w in hijos(panel) if isinstance(w, CONTROLES)]
        if not controles:
            problemas.append("sin controles")

        x0, y0 = app.winfo_rootx(), app.winfo_rooty()
        x1, y1 = x0 + app.winfo_width(), y0 + app.winfo_height()
        for w in hijos(panel):
            if not w.winfo_ismapped():
                continue
            # Lo que vive en un Canvas con scroll puede quedar fuera a proposito.
            if any(isinstance(p, tk.Canvas) for p in ancestros(w)):
                continue
            if isinstance(w, CONTROLES):
                wx0, wy0 = w.winfo_rootx(), w.winfo_rooty()
                wx1, wy1 = wx0 + w.winfo_width(), wy0 + w.winfo_height()
                if wx1 > x1 + 1 or wy1 > y1 + 1 or wx0 < x0 - 1 or wy0 < y0 - 1:
                    problemas.append(f"{type(w).__name__} '{texto_de(w)}' fuera de la ventana")
            if isinstance(w, CON_TEXTO) and w.winfo_reqwidth() > w.winfo_width() + 1:
                problemas.append(
                    f"{type(w).__name__} '{texto_de(w)}' pide {w.winfo_reqwidth()}px "
                    f"y recibe {w.winfo_width()}px (texto cortado)")
        if len(errores_tk) > antes:
            problemas.append("excepcion tk: " + errores_tk[-1].strip().splitlines()[-1])
        check(f"{etiqueta}: abre sin errores ni recortes", not problemas, "; ".join(problemas[:4]))

# Navegar dos veces al mismo panel (cache) y volver no debe fallar ni perder estado.
try:
    app._mostrar(paneles[3]); app._mostrar(paneles[3]); app._mostrar(paneles[0]); app.update()
    check("navegacion con cache de paneles", True)
except Exception:  # noqa: BLE001
    check("navegacion con cache de paneles", False, traceback.format_exc()[-200:])

check("sin excepciones de tkinter en toda la corrida", not errores_tk, errores_tk[:1])
app.destroy()

print()
if fallos:
    print(f"RESULTADO: {fallos} FALLO(S)")
    sys.exit(1)
print("RESULTADO: TODO VERDE")
