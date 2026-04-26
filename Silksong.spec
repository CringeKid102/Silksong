# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path


project_root = Path.cwd()


# Analysis configuration with better compatibility
a = Analysis(
    ['src\\main.py'],
    pathex=[str(project_root / 'src')],
    binaries=[],
    datas=[(str(project_root / 'assets'), 'assets')],
    # Explicitly include modules that might not be detected
    hiddenimports=['pygame', 'cv2', 'numpy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Exclude unnecessary modules to reduce size and improve compatibility
    excludes=['pygame.docs', 'pygame.examples', 'pygame.tests', 'tkinter', 'matplotlib'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Silksong',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    # Build for 64-bit Windows (most compatible)
    # If you need 32-bit, change to 'x86'
    target_arch='x64',
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Silksong',
)
