# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — Best Brand Co. desktop app
# Build: pyinstaller bestbrand.spec

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['desktop_app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets',            'assets'),
        ('ui',                'ui'),
        ('trading',           'trading'),
        ('analysis',          'analysis'),
        ('agents',            'agents'),
        ('bot',               'bot'),
        ('predictions',       'predictions'),
        ('pine_script_alerts','pine_script_alerts'),
        ('config.py',         '.'),
        ('registry.py',       '.'),
        ('main.py',           '.'),
        ('.env.example',      '.'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
        'tkinter',
        'tkinter.ttk',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'matplotlib.backends.backend_agg',
        'pandas',
        'numpy',
        'scipy',
        'scipy.stats',
        'web3',
        'eth_account',
        'fastapi',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'apscheduler',
        'apscheduler.schedulers.background',
        'loguru',
        'telegram',
        'telegram.ext',
        'hyperliquid',
        'dotenv',
        'aiohttp',
        'asyncio',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='BestBrand',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no black terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',  # Windows icon (add assets/icon.ico)
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BestBrand',
)

# macOS .app bundle
app = BUNDLE(
    coll,
    name='BestBrand.app',
    icon='assets/icon.icns',   # Mac icon (add assets/icon.icns)
    bundle_identifier='ca.bestbrand.app',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleDisplayName': 'Best Brand Co.',
        'CFBundleVersion': '2.0.0',
        'CFBundleShortVersionString': '2.0.0',
        'NSHighResolutionCapable': True,
    },
)
