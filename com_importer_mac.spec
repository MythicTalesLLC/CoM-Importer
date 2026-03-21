# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for City of Mist Importer - macOS
Builds standalone .app bundle for macOS distribution
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
        'PyQt6.QtSql',
        'com_importer.gui',
        'com_importer.gui.tabs',
        'com_importer.gui.dialogs',
        'pytesseract',
        'cv2',
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
    [],
    exclude_binaries=True,
    name='com-importer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='com-importer',
)

app = BUNDLE(
    coll,
    name='CoM-Importer.app',
    icon=None,
    bundle_identifier='com.mythic.com-importer',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'CFBundleShortVersionString': '0.1.0',
        'CFBundleVersion': '1',
        'NSRequiresIPhoneOS': False,
    },
)
