# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['pygame', 'PIL']
hiddenimports += collect_submodules('PIL')


a = Analysis(
    ['c:\\br_proj\\fixed203_app_2026-04-25_portable_build.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('method_a_config.json', '.'), ('method_b_config.json', '.'), ('method_c_config.json', '.'), ('method_d_config.json', '.')],
    hiddenimports=hiddenimports,
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
    name='fixed203_portable_upx_onefile',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
