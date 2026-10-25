import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

from streamer_sidekick.core import events
from streamer_sidekick.core.paths import user_config_path

# Preferências (GLOSSARY.md): o que faz sentido em qualquer PC. Só elas publicam
# preferences.changed; configuração da máquina (pastas, iniciar com o sistema…) nunca.
PREFERENCE_KEYS = frozenset({
    "hub.favorites",
    "hub.wallpaper",
    "hub.start_minimized",
    "hub.close_to_tray",
    "marker.active_file",
    "marker.custom_hotkeys",
})
_MISSING = object()


def is_preference(dotted_key: str) -> bool:
    return dotted_key in PREFERENCE_KEYS or dotted_key.startswith("hotkeys.")


DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "hub": {
        "start_minimized": False,
        "close_to_tray": True,
        "run_at_startup": False,
        "onboarded": False,
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
        # Como as preferências estavam na última gravação. Comparar com o valor
        # "antigo" lido na hora não serve: quem chama pode ter alterado a própria
        # lista antes do set().
        self._saved = deepcopy(self._data)

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
        self._write(dotted_key.split("."), value)

    def set_in(self, section: str, key: str, value: Any) -> None:
        """Grava ``value`` em ``[section][key]`` mesmo que ``key`` tenha ponto
        (ids de atalho como ``marker.open_event``)."""
        self._write([section, key], value)

    def remove_in(self, section: str, key: str) -> None:
        """Apaga ``[section][key]``, se existir (ex.: o atalho de uma mensagem rápida removida)."""
        container = self._data.get(section)
        if not isinstance(container, dict) or key not in container:
            return
        del container[key]
        self.save()
        saved = self._saved.get(section)
        if isinstance(saved, dict):
            saved.pop(key, None)
        dotted_key = f"{section}.{key}"
        if is_preference(dotted_key):
            events.publish("preferences.changed", {"key": dotted_key})

    def _write(self, parts: list[str], value: Any) -> None:
        current = self._data
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
        self.save()
        dotted_key = ".".join(parts)
        if is_preference(dotted_key):
            before = _lookup(self._saved, parts)
            _store(self._saved, parts, deepcopy(value))
            if before != value:
                events.publish("preferences.changed", {"key": dotted_key})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(self._data, file, indent=2, ensure_ascii=False)

    def reload(self) -> None:
        self._data = self._load()
        self._saved = deepcopy(self._data)

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


def _lookup(data: dict[str, Any], parts: list[str]) -> Any:
    current: Any = data
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _store(data: dict[str, Any], parts: list[str], value: Any) -> None:
    current = data
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base
