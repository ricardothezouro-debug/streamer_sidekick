import json
from pathlib import Path
from typing import Any, Optional

from streamer_sidekick.core import events
from streamer_sidekick.core.config import ConfigStore
from streamer_sidekick.core.modules import ModuleInfo
from streamer_sidekick.modules.counter.icons import CounterIcons, IconError
from streamer_sidekick.core.paths import user_data_dir


class CounterService:
    def __init__(self, config: ConfigStore, icons: Optional[CounterIcons] = None) -> None:
        self.config = config
        self.icons = icons if icons is not None else CounterIcons()

    def module_info(self) -> ModuleInfo:
        count = len(self.presets())
        # Curto para caber no chip do card; a pasta aparece na página do Contador.
        status = ("1 preset" if count == 1 else f"{count} presets") if count else "Nenhum preset ainda"
        return ModuleInfo(
            module_id="counter",
            title="Contador",
            subtitle="Overlays transparentes para OBS com presets e hotkeys.",
            status=status,
            accent="#5ab0ff",
        )

    def presets_folder(self) -> Path:
        configured = self.config.get("counter.presets_folder", "")
        if configured:
            path = Path(configured)
        else:
            path = self._legacy_presets_folder() or user_data_dir("counter_presets")
            self.config.set("counter.presets_folder", str(path))
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError:
            fallback = user_data_dir("counter_presets")
            self.config.set("counter.presets_folder", str(fallback))
            return fallback

    def set_presets_folder(self, folder: str) -> None:
        self.config.set("counter.presets_folder", folder)

    def presets(self) -> list[Path]:
        ignored_names = {"config.json"}
        return sorted(
            [
                path
                for path in self.presets_folder().glob("*.json")
                if not path.name.endswith("_state.json") and path.name not in ignored_names
            ],
            key=lambda item: item.name.lower(),
        )

    def load_preset(self, path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            return []
        counters = [item for item in data if isinstance(item, dict)]
        if self._migrate_icon_paths(counters):
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return counters

    def migrate_icons(self) -> None:
        """Migra os ícones de todos os presets (o app chama ao abrir)."""
        for path in self.presets():
            try:
                self.load_preset(path)
            except (OSError, ValueError):
                continue  # preset quebrado: quem abrir vê o aviso de sempre

    def _migrate_icon_paths(self, counters: list[dict[str, Any]]) -> bool:
        """Presets antigos guardavam o caminho da imagem; agora guardam só o nome
        do arquivo na pasta de ícones (decisão Q32). Se a imagem não existe mais,
        o ícone fica vazio e o resto do preset continua igual."""
        changed = False
        for counter in counters:
            icon = counter.get("icone")
            if not icon or not _is_path(str(icon)):
                continue
            try:
                counter["icone"] = self.icons.import_image(Path(str(icon))) if Path(str(icon)).is_file() else None
            except IconError:
                counter["icone"] = None
            changed = True
        return changed

    def save_preset(self, name: str, counters: list[dict[str, Any]], existing_path: Optional[Path] = None) -> Path:
        safe_name = _safe_file_name(name) or "preset"
        path = existing_path or self.presets_folder() / f"{safe_name}.json"
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")

        normalized = [_normalize_counter_config(counter, index) for index, counter in enumerate(counters)]
        path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")
        self.config.set("counter.last_preset", str(path))
        # Criar, editar, renomear e duplicar passam todos por aqui.
        events.publish("counter.preset_saved", {"preset": path.stem})
        return path

    def delete_preset(self, path: Path) -> None:
        path.unlink(missing_ok=True)
        self.state_file_for(path).unlink(missing_ok=True)

    def state_file_for(self, preset_path: Path) -> Path:
        return preset_path.with_name(f"{preset_path.stem}_state.json")

    def _legacy_presets_folder(self) -> Optional[Path]:
        candidates = [
            Path("D:/python/presets"),
            Path("D:/python/Contador"),
        ]
        for candidate in candidates:
            if candidate.exists():
                presets = [
                    path
                    for path in candidate.glob("*.json")
                    if not path.name.endswith("_state.json") and path.name != "config.json"
                ]
                if presets:
                    return candidate
        return None


def default_counter_config(index: int = 0) -> dict[str, Any]:
    return {
        "titulo": f"Contador {index + 1}",
        "prefixo": "",
        "infinito": True,
        "limite": None,
        "hotkey": "",
        "marcacao": "",
        "marker_file": "",
        "fonte": "Arial",
        "font_size": 48,
        "icone": None,
        "icon_size": 48,
        "largura": 400,
        "altura": 160,
    }


def _normalize_counter_config(counter: dict[str, Any], index: int) -> dict[str, Any]:
    base = default_counter_config(index)
    base.update(counter)
    base["titulo"] = str(base.get("titulo") or f"Contador {index + 1}")
    base["prefixo"] = str(base.get("prefixo") or "")
    base["infinito"] = bool(base.get("infinito", True))
    base["limite"] = None if base["infinito"] else int(base.get("limite") or 1)
    base["hotkey"] = str(base.get("hotkey") or "")
    base["marcacao"] = str(base.get("marcacao") or base.get("marker_text") or "")
    base["marker_file"] = str(base.get("marker_file") or "")
    base["fonte"] = str(base.get("fonte") or "Arial")
    base["font_size"] = int(base.get("font_size") or 48)
    base["icone"] = str(base["icone"]) if base.get("icone") else None
    base["icon_size"] = int(base.get("icon_size") or 48)
    base["largura"] = int(base.get("largura") or 400)
    base["altura"] = int(base.get("altura") or 160)
    return base


def _is_path(icon: str) -> bool:
    return "/" in icon or "\\" in icon or Path(icon).is_absolute()


def _safe_file_name(name: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid else char for char in name.strip())
    return cleaned.strip(". ")
