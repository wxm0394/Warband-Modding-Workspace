# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Exclude unused heavy PyQt5 modules and standard libraries to minimize bundle size
excludes = [
    'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebEngineCore',
    'PyQt5.Qt3DCore', 'PyQt5.Qt3DRender', 'PyQt5.Qt3DInput',
    'PyQt5.QtQuick', 'PyQt5.QtQml', 'PyQt5.QtDesigner', 'PyQt5.QtSql',
    'PyQt5.QtNetwork', 'PyQt5.QtTest', 'PyQt5.QtSensors', 'PyQt5.QtSerialPort',
    'PyQt5.QtLocation', 'PyQt5.QtPositioning', 'PyQt5.QtMultimedia',
    'tkinter', 'unittest', 'email', 'http', 'xml', 'pydoc'
]

a = Analysis(
    ['map_editor.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name='WarbandMapEditor',
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
