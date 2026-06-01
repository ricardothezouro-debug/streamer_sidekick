from datetime import datetime
import json
import os
from pathlib import Path
from typing import Optional

from streamer_sidekick.core.config import ConfigStore
from streamer_sidekick.core.modules import ModuleInfo
from streamer_sidekick.core.paths import user_data_dir


class MarkerService:
    def __init__(self, config: ConfigStore) -> None:
        self.config = config

    def module_info(self) -> ModuleInfo:
        active_file = self.active_file_name() or "Nenhum arquivo ativo"
        return ModuleInfo(
            module_id="marker",
            title="Marcador",
            subtitle="Registre eventos da live com horario e arquivo por jogo.",
            status=active_file,
            accent="#47d6a7",
        )

    def folder(self) -> Path:
        configured = self.config.get("marker.folder", "")
        if configured:
            path = Path(configured)
        else:
            path = self._legacy_folder() or user_data_dir("markers")
            self.config.set("marker.folder", str(path))
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError:
            fallback = user_data_dir("markers")
            self.config.set("marker.folder", str(fallback))
            return fallback

    def files(self) -> list[Path]:
        return sorted(
            [path for path in self.folder().glob("*.txt") if path.name != "ultimo_jogo.txt"],
            key=lambda item: item.name.lower(),
        )

    def active_file_name(self) -> str:
        configured = self.config.get("marker.active_file", "")
        if configured:
            return configured

        legacy = self.folder() / "ultimo_jogo.txt"
        if legacy.exists():
            name = legacy.read_text(encoding="utf-8").strip()
            if name:
                return f"{name}.txt" if not name.endswith(".txt") else name
        return ""

    def active_file(self) -> Path:
        name = self.active_file_name() or "default.txt"
        return self.folder() / name

    def set_active_file(self, file_name: str) -> None:
        cleaned = self.normalize_file_name(file_name)
        self.config.set("marker.active_file", cleaned)
        (self.folder() / "ultimo_jogo.txt").write_text(cleaned.removesuffix(".txt"), encoding="utf-8")

    def marker_file(self, file_name: str) -> Path:
        return self.folder() / self.normalize_file_name(file_name)

    def create_file(self, name: str) -> Path:
        safe_name = _safe_file_name(name) or "default"
        file_path = self.marker_file(safe_name)
        file_path.touch(exist_ok=True)
        return file_path

    def create_game(self, name: str) -> Path:
        safe_name = _safe_file_name(name) or "default"
        self.set_active_file(safe_name)
        file_path = self.active_file()
        file_path.touch(exist_ok=True)
        return file_path

    def save_marker(self, text: str, file_name: str = "") -> Path:
        clean_text = text.strip()
        if not clean_text:
            return self.marker_file(file_name) if file_name else self.active_file()
        target = self.marker_file(file_name) if file_name else self.active_file()
        target.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        with target.open("a", encoding="utf-8") as file:
            file.write(f"{stamp} {clean_text}\n")
        return target

    def normalize_file_name(self, file_name: str) -> str:
        cleaned = Path(file_name).name.strip()
        if not cleaned:
            cleaned = "default"
        if not cleaned.endswith(".txt"):
            cleaned = f"{cleaned}.txt"
        return _safe_file_name(cleaned.removesuffix(".txt")) + ".txt"

    def recent_markers(self, limit: int = 8) -> list[str]:
        target = self.active_file()
        if not target.exists():
            return []

        try:
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return []

        markers = [line.strip() for line in lines if line.strip()]
        return list(reversed(markers[-limit:]))

    def marker_count(self) -> int:
        target = self.active_file()
        if not target.exists():
            return 0

        try:
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return 0

        return sum(1 for line in lines if line.strip())

    def _legacy_folder(self) -> Optional[Path]:
        appdata = os.getenv("APPDATA")
        if not appdata:
            return None

        legacy_config = Path(appdata) / "marcador_config.json"
        if not legacy_config.exists():
            return None

        try:
            data = json.loads(legacy_config.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        folder = data.get("pasta_marcacoes")
        if not folder:
            return None
        return Path(folder)


def _safe_file_name(name: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid else char for char in name.strip())
    return cleaned.strip(". ")
