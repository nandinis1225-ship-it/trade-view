# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for TRADEVERSE participant backend sidecar."""

import sys
from pathlib import Path

block_cipher = None
root = Path(SPECPATH)
backend = root
seed = backend / "app" / "seed"

datas = []
for name in ("tradeverse_timeline.baked.json", "tradeverse_universe.json"):
    path = seed / name
    if path.is_file():
        datas.append((str(path), str(Path("app/seed"))))

a = Analysis(
    [str(backend / "run_backend.py")],
    pathex=[str(backend)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "psycopg",
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="tradeverse-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
