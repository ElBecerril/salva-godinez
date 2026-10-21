"""Regresion de tools/pdf_tools.open_pdf / read_pdf_total / read_pdf_for_protect.

Bug que cubre: en la GUI, al elegir un PDF en Dividir, Eliminar, Rotar, etc. a
veces "no pasaba nada" (ni el archivo elegido, ni un mensaje). Dos causas:
  - `reader.is_encrypted` sigue en True aunque decrypt("") funcione, asi que se
    rechazaba todo PDF cifrado con clave de usuario VACIA (comunes: PDFs
    "protegidos" solo contra edicion o copiado).
  - PdfReader() lanza DependencyError (no PdfReadError) con un PDF AES si falta
    `cryptography`, y cualquier excepcion rara de pypdf escapaba sin atrapar:
    en el .exe de ventana el callback de tkinter la perdia en silencio.

Los casos AES se omiten si no esta instalada `cryptography` (ya esta en
requirements.txt). Solo necesita pypdf:

    python3 tests/test_pdf_open.py
"""

import os
import sys
import tempfile

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

import pypdf  # noqa: E402

from tools import pdf_tools as P  # noqa: E402


fallos = 0


def check(nombre, cond, extra=""):
    global fallos
    fallos += not cond
    marca = "OK " if cond else "FAIL"
    detalle = f" -> {extra}" if not cond and extra else ""
    print(f"[{marca}] {nombre}{detalle}")


try:
    import cryptography  # noqa: F401
    HAY_CRYPTO = True
except ImportError:
    HAY_CRYPTO = False


def crear_pdf(path, paginas=3, user="", owner=None, algoritmo=None):
    w = pypdf.PdfWriter()
    for _ in range(paginas):
        w.add_blank_page(200, 200)
    if algoritmo:
        w.encrypt(user_password=user, owner_password=owner, algorithm=algoritmo)
    with open(path, "wb") as f:
        w.write(f)
    return path


def paginas(path):
    return len(pypdf.PdfReader(path).pages)


with tempfile.TemporaryDirectory(prefix="salvagodinez_test_") as tmp:
    ruta = lambda n: os.path.join(tmp, n)  # noqa: E731

    # --- PDF normal ------------------------------------------------------
    normal = crear_pdf(ruta("normal.pdf"))
    r = P.open_pdf(normal)
    check("open_pdf: PDF normal -> ok", r["ok"] and len(r["reader"].pages) == 3, r)
    r = P.read_pdf_total(normal)
    check("read_pdf_total: PDF normal -> 3 paginas", r["ok"] and r["total"] == 3, r)

    # --- Cifrado con clave de usuario VACIA: debe poder abrirse ----------
    casos_vacios = [("RC4-128", True)]
    if HAY_CRYPTO:
        casos_vacios += [("AES-128", True), ("AES-256", True)]
    else:
        print("[SKIP] casos AES -> falta la libreria cryptography")
    for alg, _ in casos_vacios:
        pdf = crear_pdf(ruta(f"vacio_{alg}.pdf"), paginas=3, user="", owner="duenio", algoritmo=alg)
        r = P.open_pdf(pdf)
        check(f"open_pdf: {alg} con clave de usuario vacia -> se abre",
              r["ok"] and len(r["reader"].pages) == 3, r)
        r = P.read_pdf_total(pdf)
        check(f"read_pdf_total: {alg} con clave vacia -> 3 paginas",
              r["ok"] and r["total"] == 3, r)
        # De punta a punta: la operacion sobre ese PDF produce un archivo bueno.
        ap = P.open_pdf(pdf)
        out = P.delete_pages_do(ap["pypdf"], ap["reader"], pdf, [0])
        check(f"eliminar paginas sobre {alg} con clave vacia -> copia de 2 paginas",
              out.get("ok") and paginas(out["output"]) == 2, out)
        ap = P.open_pdf(pdf)
        out = P.split_pdf_do(ap["pypdf"], ap["reader"], pdf, ruta(f"div_{alg}"), "individual")
        check(f"dividir {alg} con clave vacia -> 3 archivos",
              out.get("ok") and out.get("total") == 3, out)

    # --- Cifrado que EXIGE clave: mensaje de 'protegido', no mudo --------
    exige = crear_pdf(ruta("exige_clave.pdf"), user="secreta", algoritmo="RC4-128")
    for nombre, fn in (("open_pdf", P.open_pdf), ("read_pdf_total", P.read_pdf_total)):
        r = fn(exige)
        check(f"{nombre}: PDF que exige clave -> error 'encrypted'",
              r["ok"] is False and r["error"] == "encrypted", r)

    # --- Archivos que no son PDF / danados: error claro, sin excepcion ---
    open(ruta("texto.pdf"), "w", encoding="utf-8").write("esto no es un pdf")
    open(ruta("vacio.pdf"), "wb").close()
    for nombre in ("texto.pdf", "vacio.pdf"):
        for etiqueta, fn in (("open_pdf", P.open_pdf), ("read_pdf_total", P.read_pdf_total)):
            try:
                r = fn(ruta(nombre))
                check(f"{etiqueta}({nombre}) -> error 'corrupt'",
                      r["ok"] is False and r["error"] == "corrupt", r)
            except Exception as e:  # noqa: BLE001
                check(f"{etiqueta}({nombre}) no debe lanzar excepcion", False, repr(e))
    check("open_pdf: ruta inexistente -> not_found",
          P.open_pdf(ruta("no_existe.pdf")) == {"ok": False, "error": "not_found"})

    # --- Excepciones raras de pypdf: nunca deben escapar -----------------
    original = pypdf.PdfReader

    class _Lanza:
        def __init__(self, exc):
            self.exc = exc

        def __call__(self, *a, **k):
            raise self.exc

    try:
        pypdf.PdfReader = _Lanza(ValueError("pdf raro"))
        for etiqueta, fn, esperado in (("open_pdf", P.open_pdf, "corrupt"),
                                       ("read_pdf_total", P.read_pdf_total, "corrupt"),
                                       ("read_pdf_for_protect", P.read_pdf_for_protect, "read_error")):
            r = fn(normal)
            check(f"{etiqueta}: ValueError de pypdf -> '{esperado}', no excepcion",
                  r["ok"] is False and r["error"] == esperado, r)

        # Falta cryptography con un PDF AES: error propio, no excepcion muda.
        pypdf.PdfReader = _Lanza(pypdf.errors.DependencyError("cryptography>=3.1 is required"))
        for etiqueta, fn in (("open_pdf", P.open_pdf), ("read_pdf_total", P.read_pdf_total),
                             ("read_pdf_for_protect", P.read_pdf_for_protect)):
            r = fn(normal)
            check(f"{etiqueta}: falta cryptography -> 'no_crypto'",
                  r["ok"] is False and r["error"] == "no_crypto", r)
    finally:
        pypdf.PdfReader = original

    # DependencyError al DESCIFRAR (la clave vacia necesita AES): tambien no_crypto.
    class _LectorAes:
        is_encrypted = True
        pages = []

        def __init__(self, *a, **k):
            pass

        def decrypt(self, _pw):
            raise pypdf.errors.DependencyError("cryptography>=3.1 is required")

    try:
        pypdf.PdfReader = _LectorAes
        r = P.open_pdf(normal)
        check("open_pdf: DependencyError al descifrar -> 'no_crypto'",
              r["ok"] is False and r["error"] == "no_crypto", r)
    finally:
        pypdf.PdfReader = original

    check("MENSAJE_NO_CRYPTO existe y explica que hacer",
          "AES" in P.MENSAJE_NO_CRYPTO and "version" in P.MENSAJE_NO_CRYPTO)


print()
if fallos:
    print(f"RESULTADO: {fallos} FALLO(S)")
    sys.exit(1)
print("RESULTADO: TODO VERDE")
