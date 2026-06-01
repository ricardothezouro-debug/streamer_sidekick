from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Iterable
import zipfile

from streamer_sidekick.core.config import ConfigStore
from streamer_sidekick.modules.counter.service import CounterService
from streamer_sidekick.modules.marker.service import MarkerService


class BackupError(Exception):
    pass


@dataclass(frozen=True)
class BackupSummary:
    marker_files: int
    counter_files: int
    config_saved: bool


class BackupService:
    FORMAT_VERSION = 1

    def __init__(self, config: ConfigStore, marker: MarkerService, counter: CounterService) -> None:
        self.config = config
        self.marker = marker
        self.counter = counter

    def default_file_name(self) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"streamer_sidekick_backup_{stamp}.zip"

    def export_backup(self, target: Path) -> BackupSummary:
        target = target.with_suffix(".zip") if target.suffix.lower() != ".zip" else target
        target.parent.mkdir(parents=True, exist_ok=True)

        marker_folder = self.marker.folder()
        counter_folder = self.counter.presets_folder()
        skip_path = _safe_resolve(target)

        marker_files = list(_folder_files(marker_folder, skip_path))
        counter_files = list(_folder_files(counter_folder, skip_path))
        manifest = {
            "app": "StreamerSidekick",
            "format": self.FORMAT_VERSION,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "config_path": str(self.config.path),
            "marker_folder": str(marker_folder),
            "counter_presets_folder": str(counter_folder),
        }

        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
            archive.writestr("config/config.json", json.dumps(self.config.data, indent=2, ensure_ascii=False))
            _write_files(archive, marker_folder, marker_files, "markers")
            _write_files(archive, counter_folder, counter_files, "counter_presets")

        return BackupSummary(
            marker_files=len(marker_files),
            counter_files=len(counter_files),
            config_saved=True,
        )

    def restore_backup(self, source: Path) -> BackupSummary:
        if not source.exists():
            raise BackupError("Arquivo de backup nao encontrado.")

        try:
            archive = zipfile.ZipFile(source, "r")
        except zipfile.BadZipFile as exc:
            raise BackupError("Esse arquivo nao parece ser um backup valido.") from exc

        with archive:
            manifest = self._read_manifest(archive)
            if manifest.get("app") != "StreamerSidekick" or manifest.get("format") != self.FORMAT_VERSION:
                raise BackupError("Backup incompativel com esta versao do Streamer Sidekick.")

            config_saved = self._restore_config(archive)
            self.config.reload()

            marker_folder = self.marker.folder()
            counter_folder = self.counter.presets_folder()
            marker_count = _restore_prefix(archive, "markers", marker_folder)
            counter_count = _restore_prefix(archive, "counter_presets", counter_folder)

        return BackupSummary(
            marker_files=marker_count,
            counter_files=counter_count,
            config_saved=config_saved,
        )

    def _read_manifest(self, archive: zipfile.ZipFile) -> dict[str, object]:
        try:
            with archive.open("manifest.json") as file:
                data = json.load(file)
        except (KeyError, OSError, json.JSONDecodeError) as exc:
            raise BackupError("Manifesto do backup nao encontrado ou invalido.") from exc
        return data if isinstance(data, dict) else {}

    def _restore_config(self, archive: zipfile.ZipFile) -> bool:
        try:
            with archive.open("config/config.json") as file:
                data = json.load(file)
        except KeyError:
            return False
        except (OSError, json.JSONDecodeError) as exc:
            raise BackupError("Configuracao do backup esta invalida.") from exc

        if not isinstance(data, dict):
            raise BackupError("Configuracao do backup esta invalida.")

        self.config.path.parent.mkdir(parents=True, exist_ok=True)
        self.config.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True


def _folder_files(folder: Path, skip_path: Path | None) -> Iterable[Path]:
    if not folder.exists():
        return []

    files: list[Path] = []
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        if skip_path is not None and _safe_resolve(path) == skip_path:
            continue
        files.append(path)
    return files


def _write_files(archive: zipfile.ZipFile, base: Path, files: Iterable[Path], prefix: str) -> None:
    for path in files:
        relative = path.relative_to(base).as_posix()
        archive.write(path, f"{prefix}/{relative}")


def _restore_prefix(archive: zipfile.ZipFile, prefix: str, target_folder: Path) -> int:
    count = 0
    root = _safe_resolve(target_folder)
    target_folder.mkdir(parents=True, exist_ok=True)

    for info in archive.infolist():
        if info.is_dir() or not info.filename.startswith(f"{prefix}/"):
            continue

        relative = Path(info.filename.removeprefix(f"{prefix}/"))
        target = target_folder / relative
        resolved = _safe_resolve(target)
        if root is not None and (resolved is None or not _is_relative_to(resolved, root)):
            raise BackupError("Backup contem caminho de arquivo inseguro.")

        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as source, target.open("wb") as destination:
            destination.write(source.read())
        count += 1
    return count


def _safe_resolve(path: Path) -> Path | None:
    try:
        return path.resolve()
    except OSError:
        return None


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
