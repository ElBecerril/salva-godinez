"""Regresion de tools/usb_disinfect: que detecta, que borra y que NO borra.

Es codigo destructivo sobre la USB del usuario. Invariantes que cubre:
  - scan_usb detecta autorun/nombres de malware (riesgo Alto) y ejecutables
    sueltos (riesgo Medio), recorre subcarpetas hasta max_depth y no se pasa.
  - clean_usb SOLO borra riesgo Alto: un .exe legitimo del usuario (Medio)
    nunca se borra en bloque.
  - unhide_folders reporta lo que REALMENTE cambio (antes decia "restaurado"
    aunque attrib no hubiera hecho nada) y distingue USB danada de USB con virus.

Corre sobre una carpeta temporal que hace de USB, sin tocar unidades reales.
Las pruebas de atributos ocultos usan attrib de Windows y se omiten en otros SO.
Solo stdlib:

    python3 tests/test_usb_disinfect.py
"""

import os
import subprocess
import sys
import tempfile

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

from tools import usb_disinfect as ud  # noqa: E402


fallos = 0


def check(nombre, cond, extra=""):
    global fallos
    fallos += not cond
    marca = "OK " if cond else "FAIL"
    detalle = f" -> {extra}" if not cond and extra else ""
    print(f"[{marca}] {nombre}{detalle}")


def escribir(path, contenido="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(contenido)
    return path


def por_archivo(amenazas):
    return {os.path.basename(a["archivo"]): a for a in amenazas}


with tempfile.TemporaryDirectory(prefix="salvagodinez_test_") as tmp:
    usb = os.path.join(tmp, "usb") + os.sep

    # --- scan_usb ---------------------------------------------------------
    escribir(os.path.join(usb, "AUTORUN.INF"))                 # nivel 0, mayusculas
    escribir(os.path.join(usb, "recycler.exe"))                # nombre conocido
    escribir(os.path.join(usb, "tarea.pdf"))                   # limpio
    escribir(os.path.join(usb, "foto.jpg"))                    # limpio
    escribir(os.path.join(usb, "programa.EXE"))                # ejecutable suelto
    escribir(os.path.join(usb, "uno", "script.vbs"))           # nivel 1
    escribir(os.path.join(usb, "uno", "dos", "setup.bat"))     # nivel 2 (ultimo)
    escribir(os.path.join(usb, "uno", "dos", "tres", "hondo.exe"))  # nivel 3: fuera

    amenazas = ud.scan_usb(usb)
    t = por_archivo(amenazas)
    check("autorun.inf (sin importar mayusculas) -> riesgo Alto",
          t.get("AUTORUN.INF", {}).get("riesgo") == "Alto", t.keys())
    check("recycler.exe -> riesgo Alto",
          t.get("recycler.exe", {}).get("riesgo") == "Alto")
    check("ejecutable suelto -> riesgo Medio (extension en mayusculas)",
          t.get("programa.EXE", {}).get("riesgo") == "Medio")
    check("detecta en subcarpetas (nivel 1 y 2)",
          "script.vbs" in t and "setup.bat" in t, t.keys())
    check("respeta max_depth: no baja al nivel 3", "hondo.exe" not in t, t.keys())
    check("archivos normales no se marcan",
          "tarea.pdf" not in t and "foto.jpg" not in t)
    check("max_depth=1 solo escanea la raiz",
          set(por_archivo(ud.scan_usb(usb, max_depth=1))) ==
          {"AUTORUN.INF", "recycler.exe", "programa.EXE"})
    check("scan_usb de ruta inexistente -> []",
          ud.scan_usb(os.path.join(tmp, "no_existe") + os.sep) == [])

    # .lnk: sospechoso solo si apunta a un ejecutable (lector parchado).
    escribir(os.path.join(usb, "docs.lnk"))
    escribir(os.path.join(usb, "ok.lnk"))
    lector_orig = ud._read_lnk_target
    ud._read_lnk_target = lambda p: (r"C:\x\virus.exe" if p.endswith("docs.lnk")
                                     else r"C:\x\carpeta" if p.endswith("ok.lnk")
                                     else None)
    try:
        t = por_archivo(ud.scan_usb(usb))
        check(".lnk que apunta a .exe -> sospechoso (Medio)",
              t.get("docs.lnk", {}).get("riesgo") == "Medio", t.keys())
        check(".lnk a una carpeta -> no sospechoso", "ok.lnk" not in t)
        ud._read_lnk_target = lambda p: None
        check(".lnk ilegible -> no sospechoso", not ud._is_suspicious_lnk("x.lnk"))
    finally:
        ud._read_lnk_target = lector_orig

    # --- clean_usb --------------------------------------------------------
    amenazas = ud.scan_usb(usb)
    res = ud.clean_usb(usb, amenazas)
    borrados = {os.path.basename(r["archivo"]) for r in res if r["ok"]}
    check("clean_usb borra los de riesgo Alto",
          borrados == {"AUTORUN.INF", "recycler.exe"}, borrados)
    check("clean_usb NO borra el .exe suelto (riesgo Medio)",
          os.path.exists(os.path.join(usb, "programa.EXE")))
    check("clean_usb NO borra scripts/lnk de riesgo Medio",
          os.path.exists(os.path.join(usb, "uno", "script.vbs"))
          and os.path.exists(os.path.join(usb, "uno", "dos", "setup.bat"))
          and os.path.exists(os.path.join(usb, "docs.lnk")))
    check("clean_usb no toca archivos limpios",
          os.path.exists(os.path.join(usb, "tarea.pdf"))
          and os.path.exists(os.path.join(usb, "foto.jpg")))
    check("clean_usb([]) -> []", ud.clean_usb(usb, []) == [])
    # Un archivo que ya no existe se reporta como fallo, no truena.
    r = ud.clean_usb(usb, [{"archivo": os.path.join(usb, "fantasma.inf"), "riesgo": "Alto"}])
    check("clean_usb con archivo inexistente -> ok False con error",
          len(r) == 1 and r[0]["ok"] is False and r[0]["error"], r)
    # Aunque la amenaza venga marcada Medio, ni se intenta.
    r = ud.clean_usb(usb, [{"archivo": os.path.join(usb, "programa.EXE"), "riesgo": "Medio"}])
    check("clean_usb ignora riesgo Medio aunque se lo pasen",
          r == [] and os.path.exists(os.path.join(usb, "programa.EXE")), r)

    # --- unhide_folders (attrib real, Windows) ----------------------------
    if os.name == "nt":
        salud_orig, run_orig = ud.check_fs_health, subprocess.run
        ud.check_fs_health = lambda d: {"healthy": True}
        try:
            usb2 = os.path.join(tmp, "usb2") + os.sep
            ocultos = [escribir(os.path.join(usb2, "Documentos", "a.txt")),
                       escribir(os.path.join(usb2, "Fotos", "b.jpg"))]
            for carpeta in ("Documentos", "Fotos"):
                subprocess.run(["attrib", "+h", "+s", os.path.join(usb2, carpeta)],
                               check=True, capture_output=True)
            antes, _ = ud._count_hidden(usb2)
            check("setup: 2 carpetas ocultas detectadas por _count_hidden",
                  antes == 2, antes)
            r = ud.unhide_folders(usb2)
            check("unhide_folders restaura y reporta lo que cambio",
                  r.get("ok") is True and r.get("changed") == 2, r)
            check("despues de restaurar ya no hay nada oculto",
                  ud._count_hidden(usb2)[0] == 0)
            check("los archivos siguen ahi tras restaurar",
                  all(os.path.exists(p) for p in ocultos))

            # Nada oculto: ok con changed 0 (no inventa restauraciones).
            r = ud.unhide_folders(usb2)
            check("sin nada oculto -> ok con changed 0",
                  r.get("ok") is True and r.get("changed") == 0, r)

            # attrib sale con 0 pero no cambia nada: NO debe cantar exito.
            subprocess.run(["attrib", "+h", os.path.join(usb2, "Fotos")],
                           check=True, capture_output=True)

            class _FalsoOk:
                returncode, stdout, stderr = 0, "", ""
            ud.subprocess.run = lambda *a, **k: _FalsoOk()
            r = ud.unhide_folders(usb2)
            ud.subprocess.run = run_orig
            check("attrib rc=0 pero quedan ocultas -> ok False con remaining",
                  r.get("ok") is False and r.get("remaining", 0) >= 1, r)

            # attrib falla (rc != 0).
            class _FalsoFalla:
                returncode, stdout, stderr = 5, "", "Acceso denegado"
            ud.subprocess.run = lambda *a, **k: _FalsoFalla()
            r = ud.unhide_folders(usb2)
            ud.subprocess.run = run_orig
            check("attrib falla -> ok False con returncode y detalle",
                  r.get("ok") is False and r.get("returncode") == 5
                  and "denegado" in r.get("detail", ""), r)

            # Sistema de archivos danado: no se corre attrib ni se miente.
            llamado = []
            ud.check_fs_health = lambda d: {"healthy": False, "status": "Unhealthy|Full Repair Needed"}
            ud.subprocess.run = lambda *a, **k: llamado.append(a) or _FalsoOk()
            r = ud.unhide_folders(usb2)
            ud.subprocess.run = run_orig
            check("volumen danado -> fs_damaged y NO ejecuta attrib",
                  r.get("fs_damaged") is True and r.get("ok") is False and not llamado,
                  (r, llamado))

            # Unidad ilegible (no existe): se trata como danada, no como exito.
            ud.check_fs_health = lambda d: {"healthy": True}
            r = ud.unhide_folders(os.path.join(tmp, "desconectada") + os.sep)
            check("unidad ilegible -> fs_damaged, no 'restaurado'",
                  r.get("ok") is False and r.get("fs_damaged") is True, r)
        finally:
            ud.check_fs_health = salud_orig
            ud.subprocess.run = run_orig
    else:
        print("[SKIP] unhide_folders -> requiere attrib de Windows")

    # check_fs_health: letra vacia no truena.
    check("check_fs_health('') -> unknown", ud.check_fs_health("") == {"unknown": True})


print()
if fallos:
    print(f"RESULTADO: {fallos} FALLO(S)")
    sys.exit(1)
print("RESULTADO: TODO VERDE")
