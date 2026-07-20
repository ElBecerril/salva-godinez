# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    # main.py importa la GUI de forma perezosa (solo con --gui), asi que el
    # analisis estatico de PyInstaller podria no arrastrar el paquete entero.
    # Se listan a mano para que tkinter y las pantallas viajen en el .exe.
    hiddenimports=[
        'gui.app',
        'gui.base',
        'gui.theme',
        'gui.panels.espacio',
        'gui.panels.rescate',
        'gui.panels.sueldo',
    ],
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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='SalvaGodinez.ico',
)
