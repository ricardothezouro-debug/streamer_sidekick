import time
from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal

from streamer_sidekick.core.config import ConfigStore
from streamer_sidekick.core import hotkey_backend


@dataclass(frozen=True)
class HotkeyDefinition:
    key: str
    module_id: str
    label: str
    description: str
    default_sequence: str


DEFAULT_HOTKEYS = [
    HotkeyDefinition("hub.show", "hub", "Abrir hub", "Mostra a janela principal.", "Ctrl+Alt+H"),
    HotkeyDefinition("marker.open_event", "marker", "Marcar evento", "Abre a janela de anotacao rapida.", "Ctrl+Alt+M"),
    HotkeyDefinition("marker.new_game", "marker", "Novo jogo", "Cria ou troca o arquivo ativo do marcador.", "Ctrl+Alt+G"),
    HotkeyDefinition("counter.reset_all", "counter", "Resetar contadores", "Zera todos os overlays abertos.", "Ctrl+Alt+R"),
    HotkeyDefinition("counter.close_overlays", "counter", "Fechar overlays", "Fecha janelas de contador abertas.", "Ctrl+Alt+Shift+C"),
]


class HotkeyManager(QObject):
    changed = Signal()
    status_changed = Signal(str)
    action_requested = Signal(str)

    def __init__(self, config: ConfigStore) -> None:
        super().__init__()
        self.config = config
        self.definitions = {item.key: item for item in DEFAULT_HOTKEYS}
        self._callbacks: dict[str, Callable[[], None]] = {}
        self._registered: list[tuple[str, object]] = []
        self._last_fire: dict[str, float] = {}
        self._debounce_seconds = 0.6
        self.action_requested.connect(self._dispatch_requested)

    def all_bindings(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        stored = self.config.get("hotkeys", {})
        for key, definition in self.definitions.items():
            item = stored.get(key, {})
            rows.append(
                {
                    "key": key,
                    "module_id": definition.module_id,
                    "label": definition.label,
                    "description": definition.description,
                    "sequence": item.get("sequence", definition.default_sequence),
                    "enabled": item.get("enabled", True),
                }
            )
        for custom in self._custom_marker_hotkeys():
            key = custom["key"]
            item = stored.get(key, {})
            message = custom["message"]
            rows.append(
                {
                    "key": key,
                    "module_id": "marker",
                    "label": f"Mensagem: {message}",
                    "description": "Salva uma mensagem pre-setada no arquivo ativo do marcador.",
                    "sequence": item.get("sequence", custom["sequence"]),
                    "enabled": item.get("enabled", True),
                    "custom": True,
                }
            )
        return rows

    def set_binding(self, key: str, sequence: str, enabled: bool = True) -> Optional[str]:
        conflict = self.find_conflict(key, sequence)
        if conflict:
            return conflict
        hotkeys = self.config.data.setdefault("hotkeys", {})
        hotkeys[key] = {"sequence": sequence, "enabled": enabled}
        self.config.save()
        self.changed.emit()
        return None

    def set_enabled(self, key: str, enabled: bool) -> None:
        hotkeys = self.config.data.setdefault("hotkeys", {})
        current = hotkeys.get(key, {})
        sequence = current.get("sequence", self._default_sequence_for_key(key))
        hotkeys[key] = {"sequence": sequence, "enabled": enabled}
        self.config.save()
        self.changed.emit()

    def find_conflict(self, current_key: str, sequence: str) -> Optional[str]:
        normalized = _normalize_sequence(sequence)
        if not normalized:
            return None
        for binding in self.all_bindings():
            if binding["key"] == current_key or not binding["enabled"]:
                continue
            if _normalize_sequence(str(binding["sequence"])) == normalized:
                return str(binding["label"])
        return None

    def register_callback(self, key: str, callback: Callable[[], None]) -> None:
        self._callbacks[key] = callback

    def unregister_callback(self, key: str) -> None:
        self._callbacks.pop(key, None)

    def start_global_hotkeys(self) -> None:
        if not hotkey_backend.is_available():
            self.status_changed.emit(
                f"Backend de hotkeys ({hotkey_backend.backend_name()}) nao encontrado."
            )
            return

        self.stop_global_hotkeys()
        for binding in self.all_bindings():
            key = str(binding["key"])
            sequence = str(binding["sequence"])
            if not binding["enabled"] or not sequence or key not in self._callbacks:
                continue
            try:
                # Valida antes de registrar: assim um atalho escrito errado nao
                # chega a mexer nos que ja estao funcionando.
                hotkey_backend.validate(sequence)
                handle = hotkey_backend.register(sequence, self._wrap_callback(key))
                self._registered.append((sequence, handle))
            except Exception as exc:
                self.status_changed.emit(f"Nao foi possivel registrar {sequence}: {exc}")

    def stop_global_hotkeys(self) -> None:
        for _sequence, handle in self._registered:
            hotkey_backend.unregister(handle)
        self._registered.clear()

    def keyboard_available(self) -> bool:
        return hotkey_backend.is_available()

    def registered_sequences(self) -> list[str]:
        return [sequence for sequence, _handle in self._registered]

    def _default_sequence_for_key(self, key: str) -> str:
        definition = self.definitions.get(key)
        if definition is not None:
            return definition.default_sequence
        for custom in self._custom_marker_hotkeys():
            if custom["key"] == key:
                return custom["sequence"]
        return ""

    def _custom_marker_hotkeys(self) -> list[dict[str, str]]:
        items = self.config.get("marker.custom_hotkeys", [])
        if not isinstance(items, list):
            return []

        rows: list[dict[str, str]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()
            message = str(item.get("message") or "").strip()
            sequence = str(item.get("sequence") or "").strip()
            if key and message and sequence:
                rows.append({"key": key, "message": message, "sequence": sequence})
        return rows

    def _wrap_callback(self, key: str) -> Callable[[], None]:
        def callback() -> None:
            now = time.monotonic()
            last = self._last_fire.get(key, 0.0)
            if now - last < self._debounce_seconds:
                return
            self._last_fire[key] = now
            self.action_requested.emit(key)

        return callback

    def _dispatch_requested(self, key: str) -> None:
        action = self._callbacks.get(key)
        if action:
            action()


def _normalize_sequence(sequence: str) -> str:
    return sequence.strip().lower().replace(" ", "")
