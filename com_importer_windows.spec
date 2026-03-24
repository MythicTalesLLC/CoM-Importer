# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for City of Mist Importer - Windows
Builds standalone .exe for Windows distribution
"""

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['src/com_importer/gui_main.py'],
    pathex=[str(Path('.').absolute())],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('src/com_importer', 'com_importer'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'com_importer.gui',
        'com_importer.gui.tabs',
        'com_importer.gui.dialogs',
        'pytesseract',
        'PIL',
        'pdf2image',
        'yaml',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
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
    name='com-importer',
    icon='assets/icons/com_importer.ico',
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
