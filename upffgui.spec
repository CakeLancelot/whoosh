# -*- mode: python ; coding: utf-8 -*-

import site
import os

# Combine both system and user site-packages (handle multiple Python setups)
site_packages_dirs = site.getsitepackages() + [site.getusersitepackages()]

def find_file(filename):
    for base in site_packages_dirs:
        candidate = os.path.join(base, 'unitypack', filename)
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(f"{filename} not found in any site-packages directory.")

added_files = [
    (find_file('classes.json'), 'unitypack'),
    (find_file('strings.dat'), 'unitypack'),
    (find_file('structs.dat'), 'unitypack')
]

a = Analysis(
    ['upffgui.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[],
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
    name='upffgui',
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
)
