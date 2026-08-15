# -*- mode: python ; coding: utf-8 -*-

import os
import unitypack
from PyInstaller.utils.hooks import collect_all

# Works for both normal and PEP 660 editable installs of unitypack. For an
# editable install the real package lives outside site-packages behind a
# meta-path finder that PyInstaller's static analysis does not follow, so the
# package's parent directory is added to pathex to make the submodules
# resolvable. For a normal install the parent is site-packages itself, which
# is harmless to add.
unitypack_parent = os.path.dirname(os.path.dirname(os.path.abspath(unitypack.__file__)))

# Modules go into the PYZ; data files (classes.json, strings.dat, structs.dat)
# are placed alongside the package so unitypack.resources can find them via
# os.path.dirname(__file__) at frozen runtime.
up_datas, up_binaries, up_hiddenimports = collect_all('unitypack', include_py_files=False)
up_datas = [d for d in up_datas if not d[0].endswith('.dist-info')]

added_files = [
    ('./res/WhooshIcon.ico', '.')
]

a = Analysis(
    ['whoosh/main.py'],
    pathex=[os.path.dirname(os.path.abspath(SPEC)), unitypack_parent],
    binaries=up_binaries,
    datas=added_files + up_datas,
    hiddenimports=up_hiddenimports,
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
    name='whoosh',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    hide_console='hide-early',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='res/WhooshIcon.ico',
)
