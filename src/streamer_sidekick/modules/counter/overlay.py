import json
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    import keyboard
except ImportError:
    keyboard = None


class CounterOverlay(QWidget):
    increment_requested = Signal()
    marker_saved = Signal(str)
    closed = Signal(object)

    def __init__(self, config: dict[str, Any], save_file: Path, index: int, marker_service: Optional[Any] = None) -> None:
        super().__init__()
        self.config = config
        self.save_file = save_file
        self.index = index
        self.marker_service = marker_service
        self.value = 0
        self.offset = None
        self._hotkey_handle: Optional[Any] = None

        self.increment_requested.connect(self._handle_hotkey_increment)
        self._load_state()

        self.setWindowTitle(self._window_title())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        width = int(config.get("largura", 800) or 800)
        height = int(config.get("altura", 200) or 200)
        self.resize(width, height)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background: transparent; color: white;")
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.label)

        self._register_hotkey()
        self._update_text()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self.offset is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self.offset = None
        event.accept()

    def closeEvent(self, event) -> None:
        self._remove_hotkey()
        self.closed.emit(self)
        event.accept()

    def increment(self) -> None:
        if self.config.get("infinito", True):
            self.value += 1
        else:
            limit = int(self.config.get("limite", 1) or 1)
            if self.value < limit:
                self.value += 1
        self._update_text()
        self._save_state()

    def reset(self) -> None:
        self.value = 0
        self._update_text()
        self._save_state()

    def _register_hotkey(self) -> None:
        if keyboard is None:
            return

        hotkey = self.config.get("hotkey")
        if not hotkey:
            return

        try:
            self._hotkey_handle = keyboard.add_hotkey(str(hotkey), self.increment_requested.emit, suppress=False)
        except Exception:
            self._hotkey_handle = None

    def _handle_hotkey_increment(self) -> None:
        self.increment()
        marker_text = str(self.config.get("marcacao") or self.config.get("marker_text") or "").strip()
        if marker_text and self.marker_service is not None:
            target = self.marker_service.save_marker(marker_text, self.marker_file())
            self.marker_saved.emit(target.name)

    def _remove_hotkey(self) -> None:
        if keyboard is None or self._hotkey_handle is None:
            return
        try:
            keyboard.remove_hotkey(self._hotkey_handle)
        except Exception:
            pass
        self._hotkey_handle = None

    def _update_text(self) -> None:
        prefix = self.config.get("prefixo", "")
        if self.config.get("infinito", True):
            text = f"{prefix}{self.value}"
        else:
            text = f"{prefix}{self.value}/{self.config.get('limite', 1)}"

        font = self.config.get("fonte", "Arial")
        font_size = int(self.config.get("font_size", 20) or 20)
        icon = self.config.get("icone")

        if icon:
            size = int(self.config.get("icon_size", 32) or 32)
            self.label.setText(
                f'<img src="{icon}" height="{size}"> '
                f'<span style="font-family:{font}; font-size:{font_size}pt; color:white;">{text}</span>'
            )
        else:
            self.label.setText(
                f'<span style="font-family:{font}; font-size:{font_size}pt; color:white;">{text}</span>'
            )

    def _save_state(self) -> None:
        try:
            data: dict[str, Any] = {}
            if self.save_file.exists():
                data = json.loads(self.save_file.read_text(encoding="utf-8"))
            data[self._state_key()] = self.value
            self.save_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except (OSError, json.JSONDecodeError):
            pass

    def _load_state(self) -> None:
        if not self.save_file.exists():
            return
        try:
            data = json.loads(self.save_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        value = data.get(self._state_key())
        if isinstance(value, int):
            self.value = value

    def _state_key(self) -> str:
        title = str(self.config.get("titulo") or "").strip()
        name = title or f"contador{self.index + 1}"
        clean = "".join("_" if char in '<>:"/\\|?*' else char for char in name)
        return f"{clean}_{self.index}"

    def _window_title(self) -> str:
        title = str(self.config.get("titulo") or "").strip()
        return title or f"contador{self.index + 1}"

    def marker_file(self) -> str:
        return str(self.config.get("marker_file") or "").strip()

    def hotkey(self) -> str:
        return str(self.config.get("hotkey") or "").strip()
