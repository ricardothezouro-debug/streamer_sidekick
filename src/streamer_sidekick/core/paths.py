import os
import sys
from pathlib import Path


APP_NAME = "StreamerSidekick"


def _platform_candidates() -> list[Path]:
    """Diretorios de dados preferenciais por sistema operacional."""
    home = Path.home()
    if sys.platform == "win32":
        candidates: list[Path] = []
        if os.getenv("APPDATA"):
            candidates.append(Path(os.getenv("APPDATA", "")) / APP_NAME)
        if os.getenv("LOCALAPPDATA"):
            candidates.append(Path(os.getenv("LOCALAPPDATA", "")) / APP_NAME)
        return candidates
    if sys.platform == "darwin":
        return [home / "Library" / "Application Support" / APP_NAME]
    # Linux e outros: segue o XDG Base Directory.
    xdg = os.getenv("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else home / ".config"
    return [base / APP_NAME]


def app_data_dir() -> Path:
    candidates: list[Path] = _platform_candidates()
    candidates.append(Path.cwd() / ".streamer_sidekick")

    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError:
            continue

    fallback = Path.cwd() / ".streamer_sidekick"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def user_config_path() -> Path:
    return app_data_dir() / "config.json"


def user_data_dir(name: str) -> Path:
    path = app_data_dir() / name
    path.mkdir(parents=True, exist_ok=True)
    return path
