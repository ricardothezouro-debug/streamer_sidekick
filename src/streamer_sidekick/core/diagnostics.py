from dataclasses import dataclass
from pathlib import Path
from typing import Any

from streamer_sidekick.core import hotkey_backend
from streamer_sidekick.core.platform_utils import accessibility_trusted
from streamer_sidekick.core.config import ConfigStore
from streamer_sidekick.core.hotkeys import HotkeyManager
from streamer_sidekick.modules.counter.service import CounterService
from streamer_sidekick.modules.marker.service import MarkerService


@dataclass(frozen=True)
class DiagnosticItem:
    status: str
    title: str
    detail: str


class DiagnosticService:
    def __init__(
        self,
        config: ConfigStore,
        hotkeys: HotkeyManager,
        marker: MarkerService,
        counter: CounterService,
    ) -> None:
        self.config = config
        self.hotkeys = hotkeys
        self.marker = marker
        self.counter = counter

    def run(self) -> list[DiagnosticItem]:
        items: list[DiagnosticItem] = []
        items.extend(self._config_items())
        items.extend(self._marker_items())
        items.extend(self._counter_items())
        items.extend(self._hotkey_items())
        return items

    def _config_items(self) -> list[DiagnosticItem]:
        parent = self.config.path.parent
        if _is_writable_folder(parent):
            return [DiagnosticItem("ok", "Configuracao", f"Arquivo central em {self.config.path}")]
        return [DiagnosticItem("error", "Configuracao", f"Sem permissao de escrita em {parent}")]

    def _marker_items(self) -> list[DiagnosticItem]:
        items: list[DiagnosticItem] = []
        folder = self.marker.folder()
        files = self.marker.files()
        active = self.marker.active_file()

        if _is_writable_folder(folder):
            items.append(DiagnosticItem("ok", "Pasta do Marcador", f"{len(files)} arquivos em {folder}"))
        else:
            items.append(DiagnosticItem("error", "Pasta do Marcador", f"Sem permissao de escrita em {folder}"))

        if active.exists():
            items.append(DiagnosticItem("ok", "Arquivo ativo", f"{active.name} com {self.marker.marker_count()} marcacoes"))
        else:
            items.append(DiagnosticItem("warn", "Arquivo ativo", f"{active.name} ainda nao existe; sera criado ao salvar"))
        return items

    def _counter_items(self) -> list[DiagnosticItem]:
        items: list[DiagnosticItem] = []
        folder = self.counter.presets_folder()
        presets = self.counter.presets()

        if _is_writable_folder(folder):
            items.append(DiagnosticItem("ok", "Pasta do Contador", f"{len(presets)} presets em {folder}"))
        else:
            items.append(DiagnosticItem("error", "Pasta do Contador", f"Sem permissao de escrita em {folder}"))

        if not presets:
            items.append(DiagnosticItem("warn", "Presets", "Nenhum preset encontrado"))
            return items

        invalid = 0
        warnings: list[str] = []
        for preset in presets:
            try:
                configs = self.counter.load_preset(preset)
            except (OSError, ValueError):
                invalid += 1
                continue
            warnings.extend(_counter_config_warnings(preset.name, configs))

        if invalid:
            items.append(DiagnosticItem("error", "Presets invalidos", f"{invalid} arquivos nao puderam ser lidos"))
        else:
            items.append(DiagnosticItem("ok", "Presets", "Todos os presets foram lidos"))

        for warning in warnings[:8]:
            items.append(DiagnosticItem("warn", "Preset", warning))
        if len(warnings) > 8:
            items.append(DiagnosticItem("warn", "Preset", f"Mais {len(warnings) - 8} avisos ocultos"))
        return items

    def _hotkey_items(self) -> list[DiagnosticItem]:
        items: list[DiagnosticItem] = []
        if not self.hotkeys.keyboard_available():
            return [
                DiagnosticItem(
                    "error",
                    "Hotkeys",
                    f"Backend de hotkeys ({hotkey_backend.backend_name()}) nao esta disponivel",
                )
            ]

        # No macOS os atalhos registram normalmente mas nunca disparam sem a
        # permissao de Acessibilidade -- e nada mais no app diz isso.
        trusted = accessibility_trusted()
        if trusted is False:
            items.append(
                DiagnosticItem(
                    "error",
                    "Acessibilidade (macOS)",
                    "Permissao nao concedida: os atalhos globais nao vao disparar. "
                    "Use o botao \"Conceder permissao\" acima -- ele cadastra esta "
                    "copia do app. Se voce ja ligou a chave nos Ajustes e mesmo "
                    "assim aparece aqui, a entrada da lista e de uma versao "
                    "antiga: remova com \"-\" e conceda de novo.",
                )
            )
        elif trusted is True:
            items.append(
                DiagnosticItem("ok", "Acessibilidade (macOS)", "Permissao concedida")
            )

        # Se o layout do teclado nao pode ser lido na thread principal, criar um
        # listener e capaz de derrubar o app -- melhor dizer isso do que morrer.
        if not hotkey_backend.keycode_snapshot_ok():
            items.append(
                DiagnosticItem(
                    "warn",
                    "Layout do teclado",
                    "Nao foi possivel ler o layout na thread principal. Os atalhos "
                    "podem nao responder; reabrir o app costuma resolver.",
                )
            )

        enabled = [binding for binding in self.hotkeys.all_bindings() if binding["enabled"] and binding["sequence"]]
        registered = self.hotkeys.registered_sequences()
        if registered:
            items.append(DiagnosticItem("ok", "Hotkeys globais", f"{len(registered)} atalhos registrados"))
        elif enabled:
            items.append(DiagnosticItem("warn", "Hotkeys globais", "Existem atalhos ativos, mas nenhum registrado agora"))
        else:
            items.append(DiagnosticItem("warn", "Hotkeys globais", "Nenhum atalho global ativo"))

        duplicates = _duplicate_sequences(enabled)
        for sequence, labels in duplicates.items():
            items.append(DiagnosticItem("error", "Conflito de hotkey", f"{sequence}: {', '.join(labels)}"))
        return items


def _counter_config_warnings(preset_name: str, configs: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    titles: dict[str, str] = {}
    hotkeys: dict[str, str] = {}
    marker_files: set[str] = set()

    for index, config in enumerate(configs, start=1):
        title = str(config.get("titulo") or f"Contador {index}").strip()
        normalized_title = title.casefold()
        if normalized_title in titles:
            warnings.append(f"{preset_name}: titulo repetido {title}")
        titles[normalized_title] = title

        hotkey = str(config.get("hotkey") or "").strip()
        normalized_hotkey = _normalize_sequence(hotkey)
        if normalized_hotkey:
            if normalized_hotkey in hotkeys:
                warnings.append(f"{preset_name}: hotkey {hotkey} repetida em {hotkeys[normalized_hotkey]} e {title}")
            hotkeys[normalized_hotkey] = title

        marker_text = str(config.get("marcacao") or "").strip()
        if marker_text and not hotkey:
            warnings.append(f"{preset_name}: {title} marca txt sem hotkey")

        marker_file = str(config.get("marker_file") or "").strip()
        if marker_file:
            marker_files.add(marker_file.casefold())

    if len(marker_files) > 1:
        warnings.append(f"{preset_name}: contadores vinculados a txts diferentes")
    return warnings


def _duplicate_sequences(bindings: list[dict[str, object]]) -> dict[str, list[str]]:
    seen: dict[str, tuple[str, list[str]]] = {}
    for binding in bindings:
        sequence = str(binding["sequence"])
        normalized = _normalize_sequence(sequence)
        if not normalized:
            continue
        if normalized not in seen:
            seen[normalized] = (sequence, [])
        seen[normalized][1].append(str(binding["label"]))

    return {sequence: labels for sequence, labels in seen.values() if len(labels) > 1}


def _is_writable_folder(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".streamer_sidekick_write_test.tmp"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _normalize_sequence(sequence: str) -> str:
    return str(sequence).strip().casefold().replace(" ", "")
