# webp_gui.spec

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

qt_material_datas = collect_data_files('qt_material')
qt_material_hidden = collect_submodules('qt_material')

block_cipher = None

a = Analysis(
    ['webp_gui.py'],
    pathex=[],
    binaries=[
        ('magick.exe', '.'),
    ],
    datas=[
        ('Vazir.ttf', '.'),
        ('logo.ico', '.'),
        *qt_material_datas,
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'qt_material',
        'image_converter',
        'concurrent.futures',
        'threading',
        *qt_material_hidden,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='WebP_Converter',
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
    icon='logo.ico',
)