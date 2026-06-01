from typing import Optional

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from streamer_sidekick.core.modules import ModuleInfo


class ModuleCard(QFrame):
    opened = Signal(str)

    def __init__(self, module: ModuleInfo, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.module = module
        self.setObjectName("ModuleCard")
        self.setMinimumHeight(190)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)

        top = QHBoxLayout()
        title_box = QVBoxLayout()

        title = QLabel(module.title)
        title.setObjectName("CardTitle")
        subtitle = QLabel(module.subtitle)
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        status = QLabel(module.status)
        status.setObjectName("ModuleStatusText")
        status.setWordWrap(True)

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_box.addWidget(status)

        top.addLayout(title_box, 1)
        top.addWidget(ModuleIconBadge(module.module_id, module.accent), 0, Qt.AlignmentFlag.AlignTop)

        accent = QFrame()
        accent.setFixedHeight(4)
        accent.setStyleSheet(f"background: {module.accent}; border-radius: 2px;")

        actions = QHBoxLayout()
        actions.addStretch(1)
        open_button = QPushButton("Abrir modulo")
        open_button.setObjectName("PrimaryButton")
        open_button.clicked.connect(lambda: self.opened.emit(module.module_id))
        actions.addWidget(open_button)

        root.addLayout(top)
        root.addStretch(1)
        root.addWidget(accent)
        root.addLayout(actions)


class ModuleIconBadge(QWidget):
    def __init__(self, module_id: str, accent: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.module_id = module_id
        self.accent = QColor(accent)
        self.setFixedSize(90, 82)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        painter.setPen(QPen(QColor("#303946"), 1.2))
        painter.setBrush(QColor("#11161c"))
        painter.drawRoundedRect(rect, 8, 8)

        if self.module_id == "marker":
            self._draw_marker_icon(painter)
        elif self.module_id == "counter":
            self._draw_counter_icon(painter)
        else:
            self._draw_default_icon(painter)

    def _draw_marker_icon(self, painter: QPainter) -> None:
        pen = QPen(self.accent, 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.drawLine(31, 22, 31, 60)
        painter.drawLine(31, 24, 58, 29)
        painter.drawLine(58, 29, 47, 40)
        painter.drawLine(47, 40, 31, 36)
        painter.drawLine(25, 60, 43, 60)

        painter.setBrush(self.accent)
        painter.drawEllipse(QRectF(27, 18, 8, 8))

    def _draw_counter_icon(self, painter: QPainter) -> None:
        pen = QPen(self.accent, 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.drawArc(QRectF(24, 22, 42, 42), 25 * 16, 310 * 16)
        painter.drawLine(45, 45, 58, 33)
        painter.drawLine(35, 62, 55, 62)

        tick_pen = QPen(QColor("#8fc8ff"), 2)
        tick_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(tick_pen)
        painter.drawLine(29, 45, 34, 45)
        painter.drawLine(45, 25, 45, 30)
        painter.drawLine(61, 45, 56, 45)

    def _draw_default_icon(self, painter: QPainter) -> None:
        pen = QPen(self.accent, 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(27, 24, 36, 34), 6, 6)
        painter.drawLine(35, 36, 55, 36)
        painter.drawLine(35, 47, 48, 47)
