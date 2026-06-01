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

Run during development:

```powershell
.\.venv\Scripts\activate
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
