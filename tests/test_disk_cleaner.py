"""Regresion de tools/disk_cleaner: lo que BORRA y lo que no debe borrar.

Es codigo destructivo: un error aca es perdida de datos del usuario. Cubre las
invariantes que documenta el modulo:
  - ejecutar_limpieza() sin argumentos no borra nada.
  - los autorecuperados de Office (~$, .asd, .tmp...) sobreviven a la limpieza
    de temporales, y el tamano estimado (_scan_dir) coincide con lo que se borra.
  - la Papelera se vacia ANTES de mandar las descargas a ella.
  - si mover a la Papelera falla, NO hay fallback a borrado permanente.

Todo corre sobre carpetas temporales y con la Papelera y la cache de Windows
Update parchadas: no toca nada real. Solo stdlib:

    python3 tests/test_disk_cleaner.py
"""

import os
import sys
import tempfile
import time

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

from tools import disk_cleaner as dc  # noqa: E402


fallos = 0


def check(nombre, cond, extra=""):
    global fallos
    fallos += not cond
    marca = "OK " if cond else "FAIL"
    detalle = f" -> {extra}" if not cond and extra else ""
    print(f"[{marca}] {nombre}{detalle}")


def escribir(path, contenido="x" * 100):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(contenido)
    return path


with tempfile.TemporaryDirectory(prefix="salvagodinez_test_") as tmp:

    # --- _scan_dir / _clean_dir -------------------------------------------
    t1 = os.path.join(tmp, "temp1")
    basura = [escribir(os.path.join(t1, "a.log")),
              escribir(os.path.join(t1, "sub", "b.dat")),
              escribir(os.path.join(t1, "sub", "hondo", "c.bin"))]
    rescatables = [escribir(os.path.join(t1, "~$libro.xlsx")),
                   escribir(os.path.join(t1, "sub", "auto.asd")),
                   escribir(os.path.join(t1, "x.tmp"))]

    check("_scan_dir inexistente -> (0, 0)",
          dc._scan_dir(os.path.join(tmp, "nada")) == (0, 0))
    check("_clean_dir inexistente -> (0, 0)",
          dc._clean_dir(os.path.join(tmp, "nada")) == (0, 0))

    size_all, n_all = dc._scan_dir(t1)
    check("_scan_dir cuenta todo sin proteccion", n_all == 6 and size_all == 600,
          (size_all, n_all))
    size_p, n_p = dc._scan_dir(t1, proteger_rescatables=True)
    check("_scan_dir con proteccion excluye los rescatables",
          n_p == 3 and size_p == 300, (size_p, n_p))

    liberado, borrados = dc._clean_dir(t1, proteger_rescatables=True)
    check("_clean_dir reporta lo mismo que prometio _scan_dir",
          (liberado, borrados) == (size_p, n_p), (liberado, borrados))
    check("_clean_dir borro la basura",
          not any(os.path.exists(p) for p in basura))
    check("_clean_dir conservo TODOS los rescatables",
          all(os.path.exists(p) for p in rescatables),
          [p for p in rescatables if not os.path.exists(p)])
    check("_clean_dir no borra la carpeta raiz", os.path.isdir(t1))
    check("_clean_dir quito el subdir que quedo vacio (hondo)",
          not os.path.exists(os.path.join(t1, "sub", "hondo")))
    check("_clean_dir conservo el subdir con un rescatable",
          os.path.isdir(os.path.join(t1, "sub")))

    t2 = os.path.join(tmp, "temp2")
    escribir(os.path.join(t2, "~$a.docx"))
    escribir(os.path.join(t2, "z.tmp"))
    f, n = dc._clean_dir(t2)  # sin proteger: borra todo
    check("_clean_dir sin proteccion borra tambien los rescatables",
          n == 2 and not os.listdir(t2), (f, n, os.listdir(t2)))

    # --- _scan_old_downloads ----------------------------------------------
    dl = os.path.join(tmp, "Downloads")
    viejo = escribir(os.path.join(dl, "viejo.zip"))
    nuevo = escribir(os.path.join(dl, "nuevo.zip"))
    os.makedirs(os.path.join(dl, "carpeta_vieja"))
    hace_100 = time.time() - 100 * 86400
    os.utime(viejo, (hace_100, hace_100))
    os.utime(os.path.join(dl, "carpeta_vieja"), (hace_100, hace_100))

    dl_orig = dc.DOWNLOADS_PATH
    dc.DOWNLOADS_PATH = dl
    try:
        tam, cnt, lista = dc._scan_old_downloads(days=30)
        check("descargas antiguas: solo el archivo viejo",
              cnt == 1 and lista == [viejo], (cnt, lista))
        check("descargas antiguas: ignora carpetas y archivos nuevos",
              nuevo not in lista and not any("carpeta_vieja" in p for p in lista))
        check("descargas antiguas: escanear NO borra",
              os.path.exists(viejo) and os.path.exists(nuevo))
        dc.DOWNLOADS_PATH = os.path.join(tmp, "no_existe")
        check("descargas inexistente -> (0, 0, [])",
              dc._scan_old_downloads() == (0, 0, []))
    finally:
        dc.DOWNLOADS_PATH = dl_orig

    # --- ejecutar_limpieza (Papelera y WU parchadas) ----------------------
    llamadas = []
    orig_empty, orig_send, orig_wu = (dc._empty_recycle_bin,
                                      dc._send_to_recycle_bin,
                                      dc.WINDOWS_UPDATE_CACHE)
    send_ok = [True]

    def falso_vaciar():
        llamadas.append("vaciar")
        return True

    def falso_enviar(lista):
        llamadas.append(("enviar", list(lista)))
        if not send_ok[0]:
            return (0, 0)
        return (sum(os.path.getsize(p) for p in lista), len(lista))

    wu = os.path.join(tmp, "wu_cache")
    dc._empty_recycle_bin, dc._send_to_recycle_bin = falso_vaciar, falso_enviar
    dc.WINDOWS_UPDATE_CACHE = wu
    try:
        # Sin argumentos: no hace NADA.
        t3 = os.path.join(tmp, "temp3")
        sobrevive = escribir(os.path.join(t3, "keep.log"))
        escribir(os.path.join(wu, "upd.cab"))
        r = dc.ejecutar_limpieza()
        check("ejecutar_limpieza() sin args no toca nada",
              os.path.exists(sobrevive) and os.listdir(wu) and not llamadas
              and r["liberado"] == 0 and r["limpiados"] == 0, (r, llamadas))

        # limpiar_temp sin temp_paths: no borra.
        dc.ejecutar_limpieza(limpiar_temp=True)
        check("limpiar_temp sin temp_paths no borra", os.path.exists(sobrevive))

        # limpiar_temp con paths: borra y protege rescatables.
        auto = escribir(os.path.join(t3, "~$x.xlsx"))
        r = dc.ejecutar_limpieza(limpiar_temp=True, temp_paths=[t3])
        check("limpiar_temp borra la basura y conserva el autorecuperado",
              not os.path.exists(sobrevive) and os.path.exists(auto)
              and r["limpiados"] == 1 and r["liberado"] == 100, r)

        # limpiar_update vacia la cache de WU (nada protegido).
        r = dc.ejecutar_limpieza(limpiar_update=True)
        check("limpiar_update vacia la cache de Windows Update",
              not os.listdir(wu) and r["limpiados"] == 1, (r, os.listdir(wu)))

        # Orden: papelera PRIMERO, luego descargas a la papelera.
        llamadas.clear()
        d1 = escribir(os.path.join(dl, "d1.bin"))
        r = dc.ejecutar_limpieza(vaciar_papelera=True, descargas=[d1],
                                 papelera_size=5000, papelera_count=7)
        check("orden: vaciar papelera ANTES de enviar descargas",
              llamadas == ["vaciar", ("enviar", [d1])], llamadas)
        check("papelera vaciada suma a liberado, descargas NO",
              r["liberado"] == 5000 and r["a_papelera"] == 100
              and r["papelera_vaciada"] and r["descargas_movidas"] == 1, r)
        check("limpiados = papelera + descargas", r["limpiados"] == 8, r)

        # Papelera que falla: se reporta, no se suma nada.
        def vaciar_falla():
            llamadas.append("vaciar")
            return False
        dc._empty_recycle_bin = vaciar_falla
        r = dc.ejecutar_limpieza(vaciar_papelera=True, papelera_size=5000,
                                 papelera_count=7)
        check("papelera que falla: papelera_fallo y 0 liberado",
              r["papelera_fallo"] and not r["papelera_vaciada"]
              and r["liberado"] == 0 and r["limpiados"] == 0, r)

        # Sin fallback destructivo: si no se puede mandar a la Papelera, el
        # archivo sigue ahi.
        send_ok[0] = False
        d2 = escribir(os.path.join(dl, "d2.bin"))
        r = dc.ejecutar_limpieza(descargas=[d2])
        check("enviar a papelera falla -> descargas_fallaron y el archivo SIGUE",
              r["descargas_fallaron"] and os.path.exists(d2)
              and r["descargas_movidas"] == 0 and r["a_papelera"] == 0, r)
    finally:
        dc._empty_recycle_bin, dc._send_to_recycle_bin = orig_empty, orig_send
        dc.WINDOWS_UPDATE_CACHE = orig_wu

    # --- _send_to_recycle_bin: entradas degeneradas (sin tocar la Papelera) -
    check("_send_to_recycle_bin([]) -> (0, 0)", dc._send_to_recycle_bin([]) == (0, 0))
    check("_send_to_recycle_bin con rutas inexistentes -> (0, 0)",
          dc._send_to_recycle_bin([os.path.join(tmp, "fantasma.bin")]) == (0, 0))


print()
if fallos:
    print(f"RESULTADO: {fallos} FALLO(S)")
    sys.exit(1)
print("RESULTADO: TODO VERDE")
