"""Regresion de tools/usb_backup: el respaldo no debe perder ni pisar nada.

Cubre _calculate_backup_size y _copy_files sobre carpetas temporales:
  - copia la estructura completa (subcarpetas, vacias incluidas) y los archivos;
  - la segunda corrida omite lo identico (no recopia 10 GB cada vez);
  - un archivo que cambio SI se vuelve a copiar;
  - un archivo que no se puede copiar se registra en `failed` y el respaldo
    sigue con los demas (nunca aborta a medias);
  - si no se puede crear una CARPETA en la USB (llena, de solo lectura o
    retirada a media copia) tambien se registra y sigue: antes la excepcion se
    escapaba y tumbaba todo el respaldo sin el resumen de lo ya copiado;
  - el progreso suma exactamente los bytes; nunca modifica el origen.

No toca unidades reales. Solo stdlib:

    python3 tests/test_usb_backup.py
"""

import os
import shutil
import sys
import tempfile
import time

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

from tools import usb_backup as ub  # noqa: E402


fallos = 0


def check(nombre, cond, extra=""):
    global fallos
    fallos += not cond
    marca = "OK " if cond else "FAIL"
    detalle = f" -> {extra}" if not cond and extra else ""
    print(f"[{marca}] {nombre}{detalle}")


def escribir(path, contenido):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(contenido)
    return path


def leer(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


with tempfile.TemporaryDirectory(prefix="salvagodinez_test_") as tmp:
    escritorio = os.path.join(tmp, "Desktop")
    docs = os.path.join(tmp, "Documents")
    escribir(os.path.join(escritorio, "nota.txt"), "a" * 10)
    escribir(os.path.join(escritorio, "sub", "foto.jpg"), "b" * 20)
    escribir(os.path.join(docs, "tesis.docx"), "c" * 30)
    escribir(os.path.join(docs, "a", "b", "profundo.txt"), "d" * 40)
    os.makedirs(os.path.join(docs, "carpeta_vacia"))
    fantasma = os.path.join(tmp, "NoExiste")

    # --- _calculate_backup_size -----------------------------------------
    check("tamano total y numero de archivos", ub._calculate_backup_size([escritorio, docs]) == (100, 4))
    check("origen inexistente se ignora (no truena)",
          ub._calculate_backup_size([fantasma, escritorio]) == (30, 2))
    check("sin origenes -> (0, 0)", ub._calculate_backup_size([]) == (0, 0))

    # --- primera copia ----------------------------------------------------
    usb = os.path.join(tmp, "USB", "Respaldo_PC_20260101")
    avance = []
    copiados, omitidos, fallidos = ub._copy_files([escritorio, docs, fantasma], usb, avance.append)
    check("primera copia: 4 copiados, 0 omitidos, 0 fallidos", (copiados, omitidos, fallidos) == (4, 0, []),
          (copiados, omitidos, fallidos))
    check("conserva la estructura <origen>/<subcarpetas>/archivo",
          leer(os.path.join(usb, "Desktop", "nota.txt")) == "a" * 10
          and leer(os.path.join(usb, "Desktop", "sub", "foto.jpg")) == "b" * 20
          and leer(os.path.join(usb, "Documents", "a", "b", "profundo.txt")) == "d" * 40)
    check("el progreso suma exactamente los bytes del respaldo", sum(avance) == 100, sum(avance))
    check("el origen quedo intacto",
          leer(os.path.join(escritorio, "nota.txt")) == "a" * 10
          and os.path.isdir(os.path.join(docs, "carpeta_vacia")))

    # --- segunda copia: nada cambio ----------------------------------------
    avance2 = []
    copiados, omitidos, fallidos = ub._copy_files([escritorio, docs], usb, avance2.append)
    check("segunda corrida sin cambios: 0 copiados, 4 omitidos", (copiados, omitidos, fallidos) == (0, 4, []),
          (copiados, omitidos, fallidos))
    check("omitir tambien avanza el progreso (la barra llega al 100%)", sum(avance2) == 100, sum(avance2))

    # --- un archivo cambia: solo ese se vuelve a copiar --------------------
    time.sleep(0.05)
    escribir(os.path.join(escritorio, "nota.txt"), "NUEVO CONTENIDO MAS LARGO")
    copiados, omitidos, fallidos = ub._copy_files([escritorio, docs], usb)
    check("archivo modificado: se recopia solo ese (1 copiado, 3 omitidos)",
          (copiados, omitidos, fallidos) == (1, 3, []), (copiados, omitidos, fallidos))
    check("el respaldo tiene la version nueva",
          leer(os.path.join(usb, "Desktop", "nota.txt")) == "NUEVO CONTENIDO MAS LARGO")

    # --- un archivo no se puede copiar: el resto sigue ---------------------
    usb2 = os.path.join(tmp, "USB2", "Respaldo")
    copy2_orig = shutil.copy2

    def copy2_roto(src, dst, **k):
        if os.path.basename(src) == "foto.jpg":
            raise PermissionError(13, "Acceso denegado")
        return copy2_orig(src, dst, **k)

    shutil.copy2 = copy2_roto
    try:
        avance3 = []
        copiados, omitidos, fallidos = ub._copy_files([escritorio, docs], usb2, avance3.append)
    finally:
        shutil.copy2 = copy2_orig
    check("archivo bloqueado: se registra en failed con su error y el resto se copia",
          copiados == 3 and len(fallidos) == 1 and fallidos[0][0].endswith("foto.jpg")
          and "denegado" in fallidos[0][1].lower(), (copiados, fallidos))
    check("el fallido no deja un archivo a medias en el destino",
          not os.path.exists(os.path.join(usb2, "Desktop", "sub", "foto.jpg")))
    total_actual = ub._calculate_backup_size([escritorio, docs])[0]   # nota.txt ya cambio de tamano
    check("el progreso cuenta 0 bytes para el fallido (total menos los 20 de foto.jpg)",
          sum(avance3) == total_actual - 20, (sum(avance3), total_actual))

    # --- no se puede crear una carpeta en la USB ---------------------------
    usb3 = os.path.join(tmp, "USB3", "Respaldo")
    makedirs_orig = os.makedirs

    def makedirs_roto(path, *a, **k):
        if os.path.normpath(path).endswith(os.path.join("Documents", "a", "b")):
            raise OSError(28, "No queda espacio en el dispositivo")
        return makedirs_orig(path, *a, **k)

    os.makedirs = makedirs_roto
    try:
        try:
            avance4 = []
            copiados, omitidos, fallidos = ub._copy_files([escritorio, docs], usb3, avance4.append)
            check("carpeta imposible de crear: no escapa la excepcion y registra los archivos como fallidos",
                  len(fallidos) == 1 and fallidos[0][0].endswith("profundo.txt")
                  and "espacio" in fallidos[0][1].lower(), (copiados, fallidos))
            check("...y el resto del respaldo SI se hizo (3 archivos)", copiados == 3, copiados)
            check("...y el progreso suma todo menos los 40 bytes que fallaron",
                  sum(avance4) == total_actual - 40, (sum(avance4), total_actual))
        except OSError as e:
            check("carpeta imposible de crear: no debe tumbar todo el respaldo", False, repr(e))
    finally:
        os.makedirs = makedirs_orig

    # --- el respaldo no borra nada del destino ------------------------------
    extra = escribir(os.path.join(usb, "Desktop", "ya_estaba_en_la_usb.txt"), "no me borres")
    ub._copy_files([escritorio, docs], usb)
    check("no borra archivos que ya estaban en la USB", os.path.exists(extra))


print()
if fallos:
    print(f"RESULTADO: {fallos} FALLO(S)")
    sys.exit(1)
print("RESULTADO: TODO VERDE")
