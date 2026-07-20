# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    # main.py importa la GUI de forma perezosa (solo con --gui), asi que el
    # analisis estatico de PyInstaller podria no arrastrar el paquete entero.
    # Se recolecta TODO `gui` en vez de listar pantalla por pantalla: son 23 y
    # olvidar una en esta lista solo se descubre cuando el .exe ya esta en la
    # calle y esa pantalla truena al abrirse.
    hiddenimports=collect_submodules('gui'),
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
