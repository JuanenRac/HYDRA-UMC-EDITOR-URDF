# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('C:/Users/juane/Documents/GitHub/HYDRA-UMC-EDITOR-URDF/.venv/Lib/site-packages/PySide6/plugins/platforms', 'PySide6/plugins/platforms'), ('C:/Users/juane/Documents/GitHub/HYDRA-UMC-EDITOR-URDF/.venv/Lib/site-packages/PySide6/plugins/styles', 'PySide6/plugins/styles'), ('C:/Users/juane/Documents/GitHub/HYDRA-UMC-EDITOR-URDF/.venv/Lib/site-packages/PySide6/plugins/imageformats', 'PySide6/plugins/imageformats'), ('C:/Users/juane/Documents/GitHub/HYDRA-UMC-EDITOR-URDF/.venv/Lib/site-packages/PySide6/plugins/iconengines', 'PySide6/plugins/iconengines')],
    hiddenimports=['PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets', 'OpenGL.platform.win32'],
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
    name='HYDRA-UMC_EDITOR-URDF',
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
