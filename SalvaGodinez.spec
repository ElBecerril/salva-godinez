# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all

# PyMuPDF (import `fitz`) es codigo nativo: trae .pyd + DLLs de MuPDF y datos.
# collect_all los arrastra todos; sin esto el .exe compila pero "PDF a imagenes"
# no encontraria la libreria en runtime (la GUI la marca "(no disponible)").
# `fitz` va explicito en hiddenimports porque es el alias que importa el codigo
# de forma perezosa dentro de una funcion.
pymupdf_datas, pymupdf_binaries, pymupdf_hidden = collect_all('pymupdf')

# python-docx (import `docx`) trae plantillas .docx/.xml como datos; sin
# collect_all, "PDF a Word" fallaria en runtime al crear el Document.
docx_datas, docx_binaries, docx_hidden = collect_all('docx')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=pymupdf_binaries + docx_binaries,
    # El cacert.pem de certifi: el auto-updater lo usa para verificar el HTTPS
    # de api.github.com desde el .exe (el ssl del binario congelado no ve los
    # CA del sistema). PyInstaller ya trae un hook para certifi, pero se
    # empaqueta explicito para no depender de que el hook siga vigente.
    # A eso se suman los datos de PyMuPDF (fuentes) y las plantillas de docx.
    datas=collect_data_files('certifi') + pymupdf_datas + docx_datas,
    # main.py importa la GUI de forma perezosa (solo con --gui), asi que el
    # analisis estatico de PyInstaller podria no arrastrar el paquete entero.
    # Se recolecta TODO `gui` en vez de listar pantalla por pantalla: son 23 y
    # olvidar una en esta lista solo se descubre cuando el .exe ya esta en la
    # calle y esa pantalla truena al abrirse.
    # `tools` entero por la misma razon que `gui`: hay modulos que solo se
    # importan DENTRO de una funcion (tools.minisign_verify lo importa el
    # updater al verificar la firma, tools.office_to_pdf lo importa el menu de
    # PDF al elegir la opcion). Si el analisis estatico no los arrastra, el
    # fallo aparece recien en la calle y justo en el peor momento: al
    # verificar una actualizacion.
    hiddenimports=(collect_submodules('gui') + collect_submodules('tools')
                   + pymupdf_hidden + docx_hidden + ['fitz']),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SalvaGodinez',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    # App de VENTANA (sin consola). En Windows 11 no se puede esconder la
    # consola de forma confiable (ShowWindow no la oculta con Windows Terminal),
    # asi que no se crea ninguna: la GUI abre limpia. El modo texto (--consola,
    # fallback, o un crash) crea/adjunta una consola on-demand via
    # utils.asegurar_consola_texto().
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='SalvaGodinez.ico',
)
