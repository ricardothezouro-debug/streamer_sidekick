# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


ROOT = Path.cwd()
SRC = ROOT / "src"
APP_ICON = SRC / "streamer_sidekick" / "assets" / "brand" / "app_icon.ico"


a = Analysis(
    [str(SRC / "streamer_sidekick" / "__main__.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[
        (str(SRC / "streamer_sidekick" / "assets"), "streamer_sidekick/assets"),
    ],
    hiddenimports=[
        "keyboard",
        "pyautogui",
    ],
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
    [],
    exclude_binaries=True,
    name="StreamerSidekick",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(APP_ICON),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="StreamerSidekick",
)
