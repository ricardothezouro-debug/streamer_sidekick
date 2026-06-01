import time
from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal

from streamer_sidekick.core.config import ConfigStore

try:
    import keyboard
except ImportError:
    keyboard = None


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
        self._registered: list[str] = []
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
        sequence = current.get("sequence", self.definitions[key].default_sequence)
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

    def start_global_hotkeys(self) -> None:
        if keyboard is None:
            self.status_changed.emit("Pacote keyboard nao encontrado.")
            return

        self.stop_global_hotkeys()
        for binding in self.all_bindings():
            key = str(binding["key"])
            sequence = str(binding["sequence"])
            if not binding["enabled"] or not sequence or key not in self._callbacks:
                continue
            try:
                keyboard.add_hotkey(sequence, self._wrap_callback(key), suppress=False)
                self._registered.append(sequence)
            except Exception as exc:
                self.status_changed.emit(f"Nao foi possivel registrar {sequence}: {exc}")

    def stop_global_hotkeys(self) -> None:
        if keyboard is None:
            return
        for sequence in self._registered:
            try:
                keyboard.remove_hotkey(sequence)
            except Exception:
                pass
        self._registered.clear()

    def keyboard_available(self) -> bool:
        return keyboard is not None

    def registered_sequences(self) -> list[str]:
        return list(self._registered)

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
