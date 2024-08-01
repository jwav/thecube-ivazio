# cubegui.spec
# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

block_cipher = None

# Determine if console should be enabled
console_enabled = os.getenv('CUBEGUI_ENABLE_CONSOLE', 'True').lower() == 'true'

# Determine the paths
pathex = [Path('.').resolve(), Path('..').resolve(), (Path('..') / '..').resolve()]

# Define data paths relative to the current script location
datas = [
    (str(Path('..') / 'config'), 'config'),  # The config directory is one level up from the current script
    (str(Path('images')), 'cubegui/images'),  # The images directory is in the current script's directory
    (str(Path('logs')), 'cubegui/logs'),  # The logs directory is in the current script's directory
    (str(Path('..') / 'scoresheets'), 'scoresheets'),  # The scoresheets directory is one level up from the current script
    (str(Path('..') / 'saves'), 'saves'),  # The saves directory is one level up from the current script
    (str(Path('..') / 'sounds'), 'sounds'),  # The sounds directory is one level up from the current script
    (str(Path('..') / 'tests'), 'tests'),  # The tests directory is one level up from the current script
]

a = Analysis(
    ['cubegui.py'],  # Your main script
    pathex=[str(path) for path in pathex],  # Convert Path objects to strings
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='cubegui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=console_enabled,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='cubegui'
)
