import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

from streamer_sidekick.core.paths import user_config_path


DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "hub": {
        "start_minimized": False,
        "close_to_tray": True,
    },
    "marker": {
        "folder": "",
        "active_file": "",
        "custom_hotkeys": [],
    },
    "counter": {
        "presets_folder": "",
        "last_preset": "",
    },
    "hotkeys": {
        "hub.show": {"sequence": "Ctrl+Alt+H", "enabled": True},
        "marker.open_event": {"sequence": "Ctrl+Alt+M", "enabled": True},
        "marker.new_game": {"sequence": "Ctrl+Alt+G", "enabled": True},
        "counter.reset_all": {"sequence": "Ctrl+Alt+R", "enabled": True},
        "counter.close_overlays": {"sequence": "Ctrl+Alt+Shift+C", "enabled": True},
    },
}


class ConfigStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or user_config_path()
        self._data = self._load()

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    def get(self, dotted_key: str, default: Any = None) -> Any:
        current: Any = self._data
        for part in dotted_key.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def set(self, dotted_key: str, value: Any) -> None:
        parts = dotted_key.split(".")
        current = self._data
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(self._data, file, indent=2, ensure_ascii=False)

    def reload(self) -> None:
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        data = deepcopy(DEFAULT_CONFIG)
        if not self.path.exists():
            return data

        try:
            with self.path.open("r", encoding="utf-8") as file:
                existing = json.load(file)
        except (OSError, json.JSONDecodeError):
            return data

        return _deep_merge(data, existing)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base
