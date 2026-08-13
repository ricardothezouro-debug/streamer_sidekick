# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


ROOT = Path.cwd()
SRC = ROOT / "src"

# No macOS o icone do bundle precisa ser .icns. Se ainda nao existir, o build
# segue sem icone customizado (o PyInstaller usa o padrao). Para gerar o .icns
# a partir do PNG, veja scripts/build_app_macos.sh.
ICNS = SRC / "streamer_sidekick" / "assets" / "brand" / "app_icon.icns"
APP_ICON = str(ICNS) if ICNS.exists() else None


a = Analysis(
    [str(SRC / "streamer_sidekick" / "__main__.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[
        (str(SRC / "streamer_sidekick" / "assets"), "streamer_sidekick/assets"),
    ],
    hiddenimports=[
        "pynput",
        "pynput.keyboard",
        "pynput.mouse",
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
    icon=APP_ICON,
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

app = BUNDLE(
    coll,
    name="Streamer Sidekick.app",
    icon=APP_ICON,
    bundle_identifier="com.streamersidekick.app",
    info_plist={
        "CFBundleName": "Streamer Sidekick",
        "CFBundleDisplayName": "Streamer Sidekick",
        "CFBundleShortVersionString": "0.4.1",
        "CFBundleVersion": "0.4.1",
        "NSHighResolutionCapable": True,
        # Texto exibido pelo macOS ao pedir permissao de Acessibilidade,
        # necessaria para os atalhos globais (pynput) e o clique (pyautogui).
        "NSAppleEventsUsageDescription": "Streamer Sidekick usa atalhos globais para marcar eventos e contadores durante a live.",
    },
)
