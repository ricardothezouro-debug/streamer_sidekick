# Streamer Sidekick

Streamer Sidekick is a Python desktop hub for stream helper tools.

## License

Streamer Sidekick is licensed under the PolyForm Noncommercial License
1.0.0. It is free for personal and non-commercial use.

Commercial resale, paid redistribution, or selling modified versions
requires written permission from the copyright holder. See `LICENSE` and
`NOTICE`.

Current modules:

- Marker: fast timestamped notes for gameplay and live events.
- Counter: OBS-friendly counter overlays and presets.

Initial goals:

- One modern PySide6 hub.
- Central config in the user app data folder.
- Central hotkey registry with conflict checks.
- Modular structure for future streamer tools.

## Platforms

Streamer Sidekick roda no Windows e no macOS (e, com esforco menor, em
Linux). A camada de atalhos globais escolhe o backend certo por sistema:

- Windows: pacote `keyboard`.
- macOS / Linux: pacote `pynput`.

No **macOS** os atalhos globais exigem que o app receba permissao em
`Ajustes do Sistema > Privacidade e Seguranca > Acessibilidade`. Sem essa
permissao a interface funciona, mas os atalhos globais nao disparam.

Os dados do app ficam em:

- Windows: `%APPDATA%\StreamerSidekick`
- macOS: `~/Library/Application Support/StreamerSidekick`
- Linux: `~/.config/StreamerSidekick`

Run during development (Windows):

```powershell
.\.venv\Scripts\activate
python -m streamer_sidekick
```

Run during development (macOS / Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m streamer_sidekick
```

Build the Windows executable:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\scripts\build_exe.ps1
```

The executable is generated at:

```text
dist\StreamerSidekick\StreamerSidekick.exe
```

Create a portable release zip:

```powershell
.\scripts\package_portable.ps1
```

Create a Windows installer after installing Inno Setup:

```powershell
.\scripts\build_installer.ps1
```

Build the macOS app bundle (run on a Mac):

```bash
pip install -r requirements-build.txt
chmod +x scripts/build_app_macos.sh
./scripts/build_app_macos.sh
```

The bundle is generated at `dist/Streamer Sidekick.app`.
