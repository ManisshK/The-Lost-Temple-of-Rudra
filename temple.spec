# temple.spec — PyInstaller spec for The Lost Temple of Rudra
# Usage: pyinstaller temple.spec

import os

block_cipher = None
root = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(root, 'src', 'main.py')],
    pathex=[root, os.path.join(root, 'src')],
    binaries=[],
    datas=[
        (os.path.join(root, 'config'), 'config'),
        (os.path.join(root, 'assets'), 'assets'),
        (os.path.join(root, 'data'),   'data'),
    ],
    hiddenimports=[
        'world', 'engine', 'ai', 'ui', 'utils',
        'tkinter', 'tkinter.font', 'tkinter.ttk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pygame'],   # exclude unless audio is wanted
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TheLostTempleOfRudra',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no console window — GUI only
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(root, 'assets', 'icons', 'temple.ico')
    if os.path.isfile(os.path.join(root, 'assets', 'icons', 'temple.ico'))
    else None,
)
