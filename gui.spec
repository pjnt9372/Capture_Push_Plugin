# -*- mode: python ; coding: utf-8 -*-

# gui.spec - PyInstaller spec file for gui.py
# This file can be used to optimize the build process.

block_cipher = None


a = Analysis(
    ['gui\\gui.py'],  # Main script
    pathex=[],  # Additional paths (usually not needed if run from project root)
    binaries=[],  # Additional binary files if needed
    datas=[],  # Data files (e.g., images, configs) - you might need to add some here if gui.py needs them
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unused PySide6 modules to reduce size
        'PySide6.Qt3DAnimation',
        'PySide6.Qt3DCore',
        'PySide6.Qt3DExtras',
        'PySide6.Qt3DInput',
        'PySide6.Qt3DLogic',
        'PySide6.Qt3DRender',
        'PySide6.QtCharts',
        'PySide6.QtDataVisualization',
        'PySide6.QtHelp',
        'PySide6.QtLocation',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtOpenGL',
        'PySide6.QtPdf',
        'PySide6.QtPdfWidgets',
        'PySide6.QtPositioning',
        'PySide6.QtQuick',
        'PySide6.QtQuick3D',
        'PySide6.QtQuickControls2',
        'PySide6.QtQuickParticles',
        'PySide6.QtQuickShapes',
        'PySide6.QtQuickTemplates2',
        'PySide6.QtQuickWidgets',
        'PySide6.QtScxml',
        'PySide6.QtSensors',
        'PySide6.QtSerialPort',
        'PySide6.QtSql',
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
        'PySide6.QtTest',
        'PySide6.QtUiTools',
        'PySide6.QtWebChannel',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebSockets',
        'PySide6.QtXml',
        'PySide6.QtNfc',
        'PySide6.QtBluetooth',
        'PySide6.QtTextToSpeech',
        'PySide6.QtGamepad',
        'PySide6.QtNetworkAuth',
        'PySide6.QtRemoteObjects',
        'PySide6.QtStateMachine',
        # Add more as needed based on your analysis
    ],
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
    name='gui',  # Name of the executable
    debug=False,  # Set to True for debugging
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Enable UPX compression (requires UPX to be installed)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False to hide console window (useful for GUI apps)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None, # Add icon path here if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,  # Apply UPX to the collected directory if using --onedir
    upx_exclude=[],
    name='gui', # Name of the output directory for --onedir
)