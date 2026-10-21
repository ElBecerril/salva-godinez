"""QA funcional de la GUI: calculadoras y generador de contrasenas.

Abre la App real, llena los campos y pulsa los botones de Sueldo neto,
Retenciones, Prestaciones y Contrasenas. Compara lo que la pantalla MUESTRA
contra lo que calcula tools/ (la fuente de verdad) y prueba entradas invalidas
o raras. Un panel de calculo que muestra '$nan' con 'Calculo listo' o que se
queda mudo por una excepcion en el callback de tkinter es peor que uno que no
existe: el usuario confia en el numero.

Solo pulsa paneles seguros (nada que borre o toque hardware). Se omite si no hay
pantalla/tkinter:

    python3 tests/test_gui_calculadoras.py
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
from gui.panels.contrasenas import PanelContrasenas  # noqa: E402
from gui.panels.prestaciones import PanelPrestaciones  # noqa: E402
from gui.panels.retenciones import PanelRetenciones  # noqa: E402
from gui.panels.sueldo import PanelSueldo  # noqa: E402
from tools import prestaciones_sim as ps  # noqa: E402
from tools import retention_calculator as rc  # noqa: E402
from tools import salary_calculator as sc  # noqa: E402
from tools._fiscal_helpers import fmt  # noqa: E402

errores_tk = []
app = gapp.App("qa")
app.report_callback_exception = lambda e, v, tb: errores_tk.append(
    "".join(traceback.format_exception(e, v, tb))[-500:])
app.update()


def hijos(w):
    for c in w.winfo_children():
        yield c
        yield from hijos(c)


def panel(cls):
    app._mostrar(cls)
    app.update()
    return app._panel_actual


def filas(p):
    return [tuple(p._tabla.item(i, "values")) for i in p._tabla.get_children()]


def pulsar(p, texto):
    for w in hijos(p):
        if isinstance(w, ttk.Button) and w.cget("text") == texto:
            w.invoke()
            app.update()
            return
    raise AssertionError(f"no hay boton '{texto}'")


def estado(p):
    return str(p._estado.cget("text"))


def sin_basura(texto):
    t = texto.lower()
    return "nan" not in t and "inf" not in t


# ------------------------------------------------------------------ Sueldo
p = panel(PanelSueldo)
for bruto in ("15000", "8,364.00", " 40000 ", "250000.5", "7000"):
    n = len(errores_tk)
    p._var_bruto.set(bruto)
    pulsar(p, "Calcular")
    v = float(bruto.strip().replace(",", ""))
    esperado = sc.calculate_neto(v)
    check(f"sueldo {bruto!r}: neto en pantalla == tools",
          p._neto_label.cget("text") == f"Sueldo neto: {fmt(esperado['net_salary'])}",
          p._neto_label.cget("text"))
    check(f"sueldo {bruto!r}: total deducciones = bruto - neto",
          ("Total deducciones", f"-{fmt(v - esperado['net_salary'])}") in filas(p))
    check(f"sueldo {bruto!r}: sin excepciones tk", len(errores_tk) == n)
for malo in ("", "abc", "0", "-100", "12k"):
    p._var_bruto.set("15000"); pulsar(p, "Calcular")
    p._var_bruto.set(malo); pulsar(p, "Calcular")
    check(f"sueldo invalido {malo!r}: alerta y limpia el resultado anterior",
          "numero" in estado(p).lower() and not filas(p) and p._neto_label.cget("text") == "",
          (estado(p), len(filas(p))))
for raro in ("nan", "inf", "-inf", "1e999"):
    n = len(errores_tk)
    p._var_bruto.set(raro); pulsar(p, "Calcular")
    mostrado = p._neto_label.cget("text") + " " + " ".join(f[1] for f in filas(p))
    check(f"sueldo raro {raro!r}: sin nan/inf ni excepcion",
          len(errores_tk) == n and sin_basura(mostrado), mostrado)

# ------------------------------------------------------------- Retenciones
p = panel(PanelRetenciones)
for monto in ("10000", "1,234.56", "25000", "100000"):
    v = float(monto.replace(",", ""))
    p._var_calculo.set("honorarios"); p._var_monto.set(monto); pulsar(p, "Calcular")
    check(f"honorarios {monto}: total == tools",
          p._total_label.cget("text") == f"Total a recibir: {fmt(rc.calculate_honorarios(v)['total'])}",
          p._total_label.cget("text"))
    p._var_calculo.set("resico"); pulsar(p, "Calcular")
    e = rc.calculate_resico(v)
    check(f"resico {monto}: neto == tools",
          "error" in e or p._total_label.cget("text") == f"Neto despues de ISR: {fmt(e['neto'])}",
          p._total_label.cget("text"))
for malo in ("", "x", "0", "-5"):
    p._var_monto.set(malo); pulsar(p, "Calcular")
    check(f"retenciones invalido {malo!r}", "numero" in estado(p).lower() and not filas(p), estado(p))
for raro in ("nan", "inf", "-inf", "1e308"):
    for modo in ("honorarios", "resico"):
        n = len(errores_tk)
        p._var_calculo.set(modo); p._var_monto.set(raro); pulsar(p, "Calcular")
        mostrado = p._total_label.cget("text") + " " + estado(p)
        check(f"retenciones {modo} {raro!r}: sin nan/inf ni excepcion",
              len(errores_tk) == n and sin_basura(mostrado), mostrado)

# ------------------------------------------------------------ Prestaciones
p = panel(PanelPrestaciones)
casos = [("aguinaldo", "500", "", "180"), ("vacaciones", "500", "5.5", "200"),
         ("finiquito", "400", "3", "120"), ("finiquito", "400", "16", "120"),
         ("liquidacion", "600", "10", "0"), ("liquidacion", "350.75", "0.5", "365")]
for calculo, sal, anos, dias in casos:
    p._var_calculo.set(calculo); p._actualizar_campos()
    p._var_salario.set(sal); p._var_anos.set(anos); p._var_dias.set(dias)
    pulsar(p, "Calcular")
    s, y, d = float(sal), (float(anos) if anos else 0), int(dias)
    esperado = {
        "aguinaldo": lambda: f"Aguinaldo bruto: {fmt(ps.calculate_aguinaldo(s, d)['bruto'])}",
        "vacaciones": lambda: f"Prima vacacional: {fmt(ps.calculate_vacaciones(s, y, d)['prima_bruta'])}",
        "finiquito": lambda: f"Total finiquito: {fmt(ps.calculate_finiquito(s, y, d)['total'])}",
        "liquidacion": lambda: f"Total liquidacion: {fmt(ps.calculate_liquidacion(s, y, d)['total_liquidacion'])}",
    }[calculo]()
    check(f"prestaciones {calculo} sal={sal} anos={anos} dias={dias}: total == tools",
          p._total_label.cget("text") == esperado, (p._total_label.cget("text"), esperado))
p._var_calculo.set("aguinaldo"); p._actualizar_campos(); app.update()
check("aguinaldo oculta el campo de anos", not p._entry_anos.winfo_ismapped())
p._var_calculo.set("finiquito"); p._actualizar_campos(); app.update()
check("finiquito muestra el campo de anos", p._entry_anos.winfo_ismapped())
for sal, anos, dias in [("", "3", "100"), ("abc", "3", "100"), ("0", "3", "100"), ("500", "x", "100"),
                        ("500", "-1", "100"), ("500", "3", ""), ("500", "3", "-4"), ("500", "3", "1.5")]:
    p._var_calculo.set("finiquito"); p._actualizar_campos()
    p._var_salario.set(sal); p._var_anos.set(anos); p._var_dias.set(dias)
    pulsar(p, "Calcular")
    check(f"prestaciones invalida sal={sal!r} anos={anos!r} dias={dias!r}",
          estado(p) != "Calculo listo." and not filas(p), (estado(p), len(filas(p))))
p._var_salario.set("500"); p._var_anos.set("3,5"); p._var_dias.set("100"); pulsar(p, "Calcular")
check("prestaciones acepta anos con coma decimal '3,5'", estado(p) == "Calculo listo.", estado(p))
for sal, anos, dias in [("nan", "3", "100"), ("500", "nan", "100"), ("inf", "3", "100"),
                        ("500", "inf", "100"), ("500", "3", "999999999")]:
    n = len(errores_tk)
    p._var_calculo.set("liquidacion"); p._actualizar_campos()
    p._var_salario.set(sal); p._var_anos.set(anos); p._var_dias.set(dias)
    pulsar(p, "Calcular")
    mostrado = p._total_label.cget("text") + " " + estado(p)
    check(f"prestaciones rara ({sal},{anos},{dias}): sin nan/inf ni excepcion",
          len(errores_tk) == n and sin_basura(mostrado), (mostrado, errores_tk[-1:] if len(errores_tk) > n else ""))

# ------------------------------------------------------------- Contrasenas
p = panel(PanelContrasenas)
for lon, simb, esperado_len in (("16", True, 16), ("8", False, 8), ("128", True, 128),
                                ("4", True, 8), ("500", True, 128), (" 20 ", False, 20)):
    p._var_longitud.set(lon); p._var_simbolos.set(simb); pulsar(p, "Generar")
    pw = p._var_password.get()
    check(f"contrasena long={lon!r} simbolos={simb}: largo {esperado_len}", len(pw) == esperado_len, len(pw))
    if not simb:
        check(f"contrasena long={lon!r} sin simbolos: solo alfanumerica", pw.isalnum(), pw)
for malo in ("", "abc", "12.5"):
    p._var_longitud.set(malo); p._var_password.set("previa"); pulsar(p, "Generar")
    check(f"contrasena longitud invalida {malo!r}: sin clave y con aviso",
          p._var_password.get() == "" and "numero" in estado(p).lower(),
          (p._var_password.get(), estado(p)))
p._var_longitud.set("16")
claves = set()
for _ in range(30):
    pulsar(p, "Generar"); claves.add(p._var_password.get())
check("contrasena: 30 generaciones distintas", len(claves) == 30, len(claves))
pulsar(p, "Generar"); clave = p._var_password.get(); pulsar(p, "Copiar")
check("contrasena: Copiar deja la clave en el portapapeles", app.clipboard_get() == clave)
p._var_password.set(""); pulsar(p, "Copiar")
check("contrasena: Copiar sin clave avisa", "primero" in estado(p).lower(), estado(p))

# -------------------------------------------------------------- Navegacion
panel(PanelSueldo)._var_bruto.set("12345")
panel(PanelRetenciones)
check("navegacion: el panel conserva lo escrito al volver",
      panel(PanelSueldo)._var_bruto.get() == "12345")
check("sin excepciones de tkinter en toda la corrida", not errores_tk, errores_tk[:1])
app.destroy()

print()
if fallos:
    print(f"RESULTADO: {fallos} FALLO(S)")
    sys.exit(1)
print("RESULTADO: TODO VERDE")
