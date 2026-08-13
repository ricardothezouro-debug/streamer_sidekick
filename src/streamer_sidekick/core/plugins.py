"""Sistema de plugins do Streamer Sidekick.

Um plugin e um repositorio (baixado do GitHub como .zip) que expoe um modulo
com duas funcoes, no mesmo contrato dos modulos nativos:

    module_info() -> ModuleInfo   # dados do card (id, titulo, subtitulo, ...)
    build_page(config=None) -> QWidget  # a pagina embutida no hub

Cada plugin instalado vive em ``<app_data>/plugins/<id>/`` junto de um
``plugin.json`` (manifesto) escrito na instalacao. O catalogo de plugins
disponiveis e buscado de um JSON remoto (com fallback embutido no app), o que
permite anunciar plugins novos sem lancar uma versao nova do Sidekick.

O download usa apenas a biblioteca padrao (urllib + zipfile) -- nao exige
``git`` instalado.

Nota de seguranca: instalar um plugin baixa e executa codigo Python. O catalogo
deve apontar apenas para repositorios confiaveis/curados.
"""
from __future__ import annotations

import importlib
import io
import json
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from streamer_sidekick.core.paths import plugins_dir


# URL do catalogo remoto (canonico, no branch principal). Enquanto nao estiver
# no branch, o app usa o catalogo embutido em assets/plugins_catalog.json.
CATALOG_URL = "https://raw.githubusercontent.com/ricardothezouro-debug/streamer_sidekick/main/plugins.json"

_BUNDLED_CATALOG = Path(__file__).resolve().parents[1] / "assets" / "plugins_catalog.json"

MANIFEST_NAME = "plugin.json"
_HTTP_TIMEOUT = 30
_USER_AGENT = "StreamerSidekick-PluginManager"


@dataclass(frozen=True)
class CatalogEntry:
    """Um plugin anunciado no catalogo (ainda nao necessariamente instalado)."""

    id: str
    name: str
    description: str
    repo: str  # "owner/repo" no GitHub
    ref: str = "main"
    version: str = "0.0.0"
    src_subdir: str = "src"
    module: str = ""
    accent: str = "#37F2FF"
    icon: str = ""  # caminho do PNG relativo a raiz do plugin
    changelog: str = ""  # o que ha de novo nesta versao

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Optional["CatalogEntry"]:
        try:
            return CatalogEntry(
                id=str(data["id"]).strip(),
                name=str(data.get("name") or data["id"]).strip(),
                description=str(data.get("description") or "").strip(),
                repo=str(data["repo"]).strip(),
                ref=str(data.get("ref") or "main").strip(),
                version=str(data.get("version") or "0.0.0").strip(),
                src_subdir=str(data.get("src_subdir") or "").strip(),
                module=str(data.get("module") or "").strip(),
                accent=str(data.get("accent") or "#37F2FF").strip(),
                icon=str(data.get("icon") or "").strip(),
                changelog=str(data.get("changelog") or "").strip(),
            )
        except (KeyError, TypeError):
            return None

    def zip_url(self) -> str:
        return f"https://github.com/{self.repo}/archive/refs/heads/{self.ref}.zip"


@dataclass
class InstalledPlugin:
    """Um plugin presente em disco, ja carregado (ou com erro de carga)."""

    id: str
    name: str
    version: str
    path: Path
    accent: str = "#37F2FF"
    icon_path: Optional[str] = None
    module_info: Any = None
    build_page: Optional[Callable[..., Any]] = None
    error: Optional[str] = None

    @property
    def loaded(self) -> bool:
        return self.error is None and self.build_page is not None


def version_tuple(value: str) -> tuple[int, ...]:
    """Converte "1.2.3" em (1, 2, 3) para comparacao. Partes nao numericas viram 0."""
    parts: list[int] = []
    for chunk in str(value).split("."):
        chunk = chunk.strip()
        parts.append(int(chunk) if chunk.isdigit() else 0)
    return tuple(parts) or (0,)


class PluginManager:
    def __init__(self) -> None:
        self._installed: dict[str, InstalledPlugin] = {}

    # ---- Descoberta / carga --------------------------------------------

    def load(self) -> None:
        """Varre a pasta de plugins e carrega cada um."""
        self._installed.clear()
        root = plugins_dir()
        for folder in sorted(root.iterdir()):
            if not folder.is_dir():
                continue
            manifest_path = folder / MANIFEST_NAME
            if not manifest_path.exists():
                continue
            plugin = self._load_one(folder, manifest_path)
            if plugin is not None:
                self._installed[plugin.id] = plugin

    def _load_one(self, folder: Path, manifest_path: Path) -> Optional[InstalledPlugin]:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return InstalledPlugin(
                id=folder.name, name=folder.name, version="0.0.0", path=folder,
                error=f"Manifesto invalido: {exc}",
            )

        plugin_id = str(manifest.get("id") or folder.name).strip()
        name = str(manifest.get("name") or plugin_id).strip()
        version = str(manifest.get("version") or "0.0.0").strip()
        accent = str(manifest.get("accent") or "#37F2FF").strip()
        src_subdir = str(manifest.get("src_subdir") or "").strip()
        module_name = str(manifest.get("module") or "").strip()
        icon_rel = str(manifest.get("icon") or "").strip()

        icon_path: Optional[str] = None
        if icon_rel:
            candidate = folder / icon_rel
            if candidate.exists():
                icon_path = str(candidate)

        plugin = InstalledPlugin(
            id=plugin_id, name=name, version=version, path=folder, accent=accent,
            icon_path=icon_path,
        )

        if not module_name:
            plugin.error = "Manifesto sem campo 'module'."
            return plugin

        src_dir = folder / src_subdir if src_subdir else folder
        try:
            self._import_plugin_module(plugin, src_dir, module_name)
        except Exception as exc:  # import de codigo externo: captura amplo de proposito
            plugin.error = f"Falha ao carregar: {exc}"
        return plugin

    def _import_plugin_module(self, plugin: InstalledPlugin, src_dir: Path, module_name: str) -> None:
        src_str = str(src_dir)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)

        # Remove versoes antigas do pacote do cache (relevante em atualizacoes).
        top_package = module_name.split(".")[0]
        for cached in [m for m in sys.modules if m == top_package or m.startswith(top_package + ".")]:
            del sys.modules[cached]

        module = importlib.import_module(module_name)
        info = module.module_info() if hasattr(module, "module_info") else None
        build_page = getattr(module, "build_page", None)
        if build_page is None:
            plugin.error = "Modulo do plugin nao expoe build_page()."
            return
        plugin.module_info = info
        plugin.build_page = build_page
        if info is not None:
            # Mantem id/nome/accent alinhados com o que o plugin declara.
            plugin.accent = getattr(info, "accent", plugin.accent) or plugin.accent

    # ---- Consultas ------------------------------------------------------

    def installed(self) -> list[InstalledPlugin]:
        return list(self._installed.values())

    def get(self, plugin_id: str) -> Optional[InstalledPlugin]:
        return self._installed.get(plugin_id)

    def is_installed(self, plugin_id: str) -> bool:
        return plugin_id in self._installed

    def installed_version(self, plugin_id: str) -> Optional[str]:
        plugin = self._installed.get(plugin_id)
        return plugin.version if plugin else None

    def has_update(self, entry: CatalogEntry) -> bool:
        current = self.installed_version(entry.id)
        if current is None:
            return False
        return version_tuple(entry.version) > version_tuple(current)

    def updates_available(self, catalog: list[CatalogEntry]) -> list[CatalogEntry]:
        return [entry for entry in catalog if self.has_update(entry)]

    # ---- Catalogo -------------------------------------------------------

    def fetch_catalog(self) -> list[CatalogEntry]:
        """Busca o catalogo remoto; em caso de falha usa o embutido no app."""
        data = self._fetch_remote_catalog()
        if data is None:
            data = self._read_bundled_catalog()
        entries: list[CatalogEntry] = []
        for item in (data or {}).get("plugins", []):
            entry = CatalogEntry.from_dict(item)
            if entry is not None:
                entries.append(entry)
        return entries

    def _fetch_remote_catalog(self) -> Optional[dict[str, Any]]:
        try:
            request = urllib.request.Request(CATALOG_URL, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

    def _read_bundled_catalog(self) -> Optional[dict[str, Any]]:
        try:
            return json.loads(_BUNDLED_CATALOG.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    # ---- Instalacao / remocao ------------------------------------------

    def install(
        self,
        entry: CatalogEntry,
        progress: Optional[Callable[[str], None]] = None,
    ) -> InstalledPlugin:
        """Baixa, extrai e carrega um plugin do catalogo. Lanca excecao em erro."""
        def report(message: str) -> None:
            if progress is not None:
                progress(message)

        report("Baixando do GitHub...")
        payload = self._download_zip(entry.zip_url())

        report("Extraindo arquivos...")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                archive.extractall(tmp_path)
            extracted_root = self._single_top_dir(tmp_path)

            report("Instalando...")
            target = plugins_dir() / entry.id
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
            shutil.move(str(extracted_root), str(target))

        self._write_manifest(entry, plugins_dir() / entry.id)

        report("Carregando plugin...")
        self.load()
        plugin = self._installed.get(entry.id)
        if plugin is None:
            raise RuntimeError("Plugin instalado mas nao pode ser localizado.")
        if plugin.error:
            raise RuntimeError(plugin.error)
        return plugin

    def uninstall(self, plugin_id: str) -> bool:
        plugin = self._installed.get(plugin_id)
        if plugin is None:
            return False
        shutil.rmtree(plugin.path, ignore_errors=True)
        del self._installed[plugin_id]
        return True

    def _download_zip(self, url: str) -> bytes:
        request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT) as response:
            return response.read()

    def _single_top_dir(self, extracted: Path) -> Path:
        entries = [item for item in extracted.iterdir() if item.is_dir()]
        if len(entries) == 1:
            return entries[0]
        # Sem uma unica pasta raiz: usa a propria pasta extraida.
        return extracted

    def _write_manifest(self, entry: CatalogEntry, target: Path) -> None:
        manifest = {
            "id": entry.id,
            "name": entry.name,
            "version": entry.version,
            "src_subdir": entry.src_subdir,
            "module": entry.module,
            "accent": entry.accent,
            "icon": entry.icon,
            "repo": entry.repo,
            "ref": entry.ref,
        }
        (target / MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
