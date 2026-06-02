from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from streamer_sidekick.core.modules import ModuleInfo


VOID_BLACK = "#0A0B12"
GRAPHITE = "#141826"
SOFT_WHITE = "#F3F6FF"
ELECTRIC_CYAN = "#37F2FF"
NEON_MAGENTA = "#FF4FD8"
ACID_LIME = "#B9FF43"
PANEL_BORDER = "#273140"
MUTED = "#A8B0BC"
BRAND_ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "brand"


class NeonPanel(QFrame):
    def __init__(self, parent: Optional[QWidget] = None, accent: str = ELECTRIC_CYAN, grid: bool = False) -> None:
        super().__init__(parent)
        self.accent = QColor(accent)
        self.grid = grid
        self.setObjectName("NeonPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0.8, 0.8, self.width() - 1.6, self.height() - 1.6)
        path = _cut_corner_path(rect, 14, 12)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(13, 18, 27, 236))
        painter.drawPath(path)

        if self.grid:
            self._draw_micro_grid(painter, rect)

        border = QLinearGradient(rect.topLeft(), rect.bottomRight())
        border.setColorAt(0.0, QColor(ELECTRIC_CYAN))
        border.setColorAt(0.46, QColor(PANEL_BORDER))
        border.setColorAt(0.74, QColor(NEON_MAGENTA))
        border.setColorAt(1.0, QColor(PANEL_BORDER))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QBrush(border), 1.1))
        painter.drawPath(path)

        glow = QLinearGradient(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        glow.setColorAt(0.05, QColor(0, 0, 0, 0))
        glow.setColorAt(0.35, QColor(ELECTRIC_CYAN))
        glow.setColorAt(0.58, QColor(NEON_MAGENTA))
        glow.setColorAt(0.95, QColor(0, 0, 0, 0))
        painter.setPen(QPen(QBrush(glow), 1.8))
        y = rect.bottom() - 1.5
        painter.drawLine(QPointF(rect.left() + 18, y), QPointF(rect.right() - 18, y))

        super().paintEvent(event)

    def _draw_micro_grid(self, painter: QPainter, rect: QRectF) -> None:
        return


class SectionHeader(QWidget):
    def __init__(self, number: str, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        number_label = QLabel(number)
        number_label.setObjectName("Kicker")
        divider = QLabel("|")
        divider.setObjectName("AccentDivider")
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")

        layout.addWidget(number_label)
        layout.addWidget(divider)
        layout.addWidget(title_label)
        layout.addStretch(1)


class BrandLogo(QWidget):
    def __init__(self, compact: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.compact = compact
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(54 if compact else 94)

    def sizeHint(self) -> QSize:
        return QSize(210 if self.compact else 560, 58 if self.compact else 104)

    def minimumSizeHint(self) -> QSize:
        return QSize(148 if self.compact else 280, 52 if self.compact else 84)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        logo = _asset_pixmap("brand_logo.png")
        if logo is not None:
            _draw_pixmap_fit(painter, logo, QRectF(0, 2, self.width(), self.height() - 4))
            return

        height = self.height()
        icon_size = min(height - 4, 48 if self.compact else 86)
        icon_rect = QRectF(0, (height - icon_size) / 2, icon_size, icon_size)
        _draw_bot_icon(painter, icon_rect.adjusted(2, 2, -2, -2), 5.8 if self.compact else 6.4)

        text_x = icon_rect.right() + (8 if self.compact else 16)
        available = max(0, int(self.width() - text_x - 2))
        if available < 70:
            return

        segments = [(SOFT_WHITE, "Streamer"), (NEON_MAGENTA, "Side"), (ELECTRIC_CYAN, "kick")]
        size = 22 if self.compact else 40
        floor = 13 if self.compact else 24
        while size > floor:
            font = QFont("Bahnschrift", size, QFont.Weight.Bold)
            metrics = QFontMetrics(font)
            total = sum(metrics.horizontalAdvance(text) for _, text in segments)
            if total <= available:
                break
            size -= 1

        font = QFont("Bahnschrift", size, QFont.Weight.Bold)
        metrics = QFontMetrics(font)
        total_width = sum(metrics.horizontalAdvance(text) for _, text in segments)
        baseline = int((height + metrics.ascent() - metrics.descent()) / 2)
        cursor = int(text_x)
        painter.setFont(font)
        if total_width > available and total_width > 0:
            painter.save()
            painter.translate(cursor, 0)
            painter.scale(available / total_width, 1)
            cursor = 0
        for color, text in segments:
            painter.setPen(QColor(color))
            painter.drawText(cursor, baseline, text)
            cursor += metrics.horizontalAdvance(text)
        if total_width > available and total_width > 0:
            painter.restore()


class BrandIcon(QWidget):
    def __init__(self, size: int = 96, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        icon = _asset_pixmap("brand_icon.png")
        if icon is not None:
            _draw_pixmap_fit(painter, icon, QRectF(0, 0, self.width(), self.height()))
            return
        painter.scale(self.width() / 100, self.height() / 100)
        _draw_bot_icon(painter, QRectF(6, 8, 88, 84), 7)


class NeonIcon(QWidget):
    def __init__(self, icon_id: str, accent: str = ELECTRIC_CYAN, size: int = 54, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.icon_id = icon_id
        self.accent = QColor(accent)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        asset_name = {
            "marker": "marker_icon.png",
            "document": "marker_icon.png",
            "counter": "counter_icon.png",
            "home": "brand_icon.png",
        }.get(self.icon_id)
        if asset_name:
            asset = _asset_pixmap(asset_name)
            if asset is not None:
                _draw_pixmap_fit(painter, asset, QRectF(0, 0, self.width(), self.height()))
                return

        painter.scale(self.width() / 100, self.height() / 100)
        pen = _gradient_pen(QRectF(0, 0, 100, 100), 6)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self.icon_id in {"marker", "document"}:
            self._draw_document(painter)
        elif self.icon_id == "counter":
            self._draw_counter(painter)
        elif self.icon_id == "hotkey":
            self._draw_keyboard(painter)
        elif self.icon_id == "folder":
            self._draw_folder(painter)
        elif self.icon_id == "settings":
            self._draw_settings(painter)
        elif self.icon_id == "diagnostics":
            self._draw_pulse(painter)
        elif self.icon_id == "backup":
            self._draw_layers(painter)
        elif self.icon_id == "alert":
            self._draw_alert(painter)
        elif self.icon_id == "about":
            self._draw_profile(painter)
        elif self.icon_id == "home":
            _draw_bot_icon(painter, QRectF(8, 8, 84, 84), 5)
        else:
            self._draw_chip(painter)

    def _draw_document(self, painter: QPainter) -> None:
        painter.setPen(_gradient_pen(QRectF(12, 8, 78, 84), 5.4))
        path = QPainterPath()
        path.moveTo(24, 14)
        path.lineTo(58, 14)
        path.lineTo(76, 32)
        path.lineTo(76, 84)
        path.lineTo(24, 84)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(58, 14, 58, 34)
        painter.drawLine(58, 34, 76, 34)
        painter.drawLine(36, 48, 60, 48)
        painter.drawLine(36, 61, 56, 61)
        painter.drawLine(36, 74, 48, 74)
        painter.drawEllipse(QRectF(58, 58, 30, 30))
        painter.drawLine(73, 67, 73, 75)
        painter.drawLine(73, 75, 80, 75)

    def _draw_counter(self, painter: QPainter) -> None:
        painter.setPen(_gradient_pen(QRectF(12, 12, 76, 76), 5.4))
        painter.drawRoundedRect(QRectF(16, 18, 68, 64), 8, 8)
        painter.drawLine(16, 34, 84, 34)
        for x in (28, 40, 52):
            painter.drawEllipse(QRectF(x, 24, 3, 3))
        self._draw_digit(painter, QRectF(28, 44, 20, 26), "0")
        self._draw_digit(painter, QRectF(54, 44, 20, 26), "5")

    def _draw_digit(self, painter: QPainter, rect: QRectF, value: str) -> None:
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        mid = y + h / 2
        segments = {
            "0": ("top", "upper_left", "upper_right", "lower_left", "lower_right", "bottom"),
            "5": ("top", "upper_left", "middle", "lower_right", "bottom"),
        }.get(value, ())
        if "top" in segments:
            painter.drawLine(QPointF(x + 3, y), QPointF(x + w - 3, y))
        if "middle" in segments:
            painter.drawLine(QPointF(x + 3, mid), QPointF(x + w - 3, mid))
        if "bottom" in segments:
            painter.drawLine(QPointF(x + 3, y + h), QPointF(x + w - 3, y + h))
        if "upper_left" in segments:
            painter.drawLine(QPointF(x, y + 3), QPointF(x, mid - 3))
        if "upper_right" in segments:
            painter.drawLine(QPointF(x + w, y + 3), QPointF(x + w, mid - 3))
        if "lower_left" in segments:
            painter.drawLine(QPointF(x, mid + 3), QPointF(x, y + h - 3))
        if "lower_right" in segments:
            painter.drawLine(QPointF(x + w, mid + 3), QPointF(x + w, y + h - 3))

    def _draw_keyboard(self, painter: QPainter) -> None:
        painter.drawRoundedRect(QRectF(14, 28, 72, 44), 7, 7)
        for row, y in enumerate([42, 56]):
            for x in [26, 40, 54, 68]:
                width = 8 if row == 0 else 10
                painter.drawLine(x, y, x + width, y)

    def _draw_folder(self, painter: QPainter) -> None:
        path = QPainterPath()
        path.moveTo(14, 34)
        path.lineTo(38, 34)
        path.lineTo(46, 26)
        path.lineTo(70, 26)
        path.lineTo(86, 42)
        path.lineTo(80, 76)
        path.lineTo(16, 76)
        path.closeSubpath()
        painter.drawPath(path)

    def _draw_settings(self, painter: QPainter) -> None:
        for y in [30, 50, 70]:
            painter.drawLine(20, y, 80, y)
        painter.drawEllipse(QRectF(34, 24, 12, 12))
        painter.drawEllipse(QRectF(56, 44, 12, 12))
        painter.drawEllipse(QRectF(42, 64, 12, 12))

    def _draw_pulse(self, painter: QPainter) -> None:
        painter.drawLine(14, 58, 30, 58)
        painter.drawLine(30, 58, 42, 34)
        painter.drawLine(42, 34, 56, 72)
        painter.drawLine(56, 72, 68, 48)
        painter.drawLine(68, 48, 86, 48)
        painter.drawEllipse(QRectF(20, 18, 60, 60))

    def _draw_layers(self, painter: QPainter) -> None:
        for offset in [0, 12, 24]:
            path = QPainterPath()
            path.moveTo(50, 18 + offset)
            path.lineTo(78, 32 + offset)
            path.lineTo(50, 46 + offset)
            path.lineTo(22, 32 + offset)
            path.closeSubpath()
            painter.drawPath(path)

    def _draw_alert(self, painter: QPainter) -> None:
        path = QPainterPath()
        path.moveTo(50, 14)
        path.lineTo(86, 80)
        path.lineTo(14, 80)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(50, 36, 50, 58)
        painter.drawPoint(50, 68)

    def _draw_profile(self, painter: QPainter) -> None:
        painter.drawEllipse(QRectF(37, 18, 26, 26))
        path = QPainterPath()
        path.moveTo(24, 82)
        path.cubicTo(28, 58, 72, 58, 76, 82)
        painter.drawPath(path)

    def _draw_chip(self, painter: QPainter) -> None:
        painter.drawRoundedRect(QRectF(24, 24, 52, 52), 10, 10)
        painter.drawLine(36, 42, 64, 42)
        painter.drawLine(36, 58, 56, 58)


class ModuleTile(NeonPanel):
    opened = Signal(str)

    def __init__(self, module: ModuleInfo, parent: Optional[QWidget] = None) -> None:
        accent = ELECTRIC_CYAN if module.module_id == "marker" else NEON_MAGENTA if module.module_id == "counter" else ACID_LIME
        super().__init__(parent, accent=accent, grid=False)
        self.module = module
        self.setMinimumHeight(230)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)

        header = QHBoxLayout()
        icon = NeonIcon(module.module_id, accent=accent, size=96)
        title_box = QVBoxLayout()
        title = QLabel(module.title)
        title.setObjectName("CardTitle")
        subtitle = QLabel(module.subtitle)
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        header.addLayout(title_box, 1)

        status = QLabel(module.status)
        status.setObjectName("StatusPill")
        status.setWordWrap(True)

        actions = QHBoxLayout()
        actions.addStretch(1)
        open_button = QPushButton("Abrir")
        open_button.setObjectName("PrimaryButton")
        open_button.clicked.connect(lambda: self.opened.emit(module.module_id))
        actions.addWidget(open_button)

        root.addLayout(header)
        root.addStretch(1)
        root.addWidget(status)
        root.addLayout(actions)


class FutureModuleTile(NeonPanel):
    def __init__(self, title: str, body: str, icon_id: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, accent=ACID_LIME, grid=False)
        self.setObjectName("FuturePanel")
        self.setMinimumHeight(210)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(NeonIcon(icon_id, accent=ACID_LIME, size=54), 0, Qt.AlignmentFlag.AlignLeft)
        name = QLabel(title)
        name.setObjectName("CardTitle")
        text = QLabel(body)
        text.setObjectName("Muted")
        text.setWordWrap(True)
        pill = QLabel("Em breve")
        pill.setObjectName("StatusPill")
        layout.addWidget(name)
        layout.addWidget(text)
        layout.addStretch(1)
        layout.addWidget(pill)


ModuleCard = ModuleTile


def neon_qicon(icon_id: str, size: int = 22) -> QIcon:
    icon = NeonIcon(icon_id, size=size)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    icon.render(pixmap)
    return QIcon(pixmap)


def _asset_pixmap(name: str) -> Optional[QPixmap]:
    path = BRAND_ASSET_DIR / name
    if not path.exists():
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None
    return pixmap


def _draw_pixmap_fit(painter: QPainter, pixmap: QPixmap, rect: QRectF) -> None:
    max_size = QSize(max(1, int(rect.width())), max(1, int(rect.height())))
    scaled = pixmap.scaled(max_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    x = int(rect.left() + (rect.width() - scaled.width()) / 2)
    y = int(rect.top() + (rect.height() - scaled.height()) / 2)
    painter.drawPixmap(x, y, scaled)


def _cut_corner_path(rect: QRectF, radius: float, cut: float) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(rect.left() + radius, rect.top())
    path.lineTo(rect.right() - cut, rect.top())
    path.lineTo(rect.right(), rect.top() + cut)
    path.lineTo(rect.right(), rect.bottom() - radius)
    path.quadTo(rect.right(), rect.bottom(), rect.right() - radius, rect.bottom())
    path.lineTo(rect.left() + cut, rect.bottom())
    path.lineTo(rect.left(), rect.bottom() - cut)
    path.lineTo(rect.left(), rect.top() + radius)
    path.quadTo(rect.left(), rect.top(), rect.left() + radius, rect.top())
    return path


def _gradient_pen(rect: QRectF, width: float, include_lime: bool = False) -> QPen:
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0.0, QColor(ELECTRIC_CYAN))
    gradient.setColorAt(0.52, QColor(ELECTRIC_CYAN))
    gradient.setColorAt(0.78, QColor(NEON_MAGENTA))
    gradient.setColorAt(1.0, QColor(ACID_LIME if include_lime else NEON_MAGENTA))
    pen = QPen(QBrush(gradient), width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _draw_bot_icon(painter: QPainter, rect: QRectF, width: float) -> None:
    painter.save()
    painter.setPen(_gradient_pen(rect, width))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    cx = rect.center().x()
    top = rect.top()
    left = rect.left()
    right = rect.right()
    painter.drawEllipse(QRectF(cx - 6, top + 2, 12, 12))
    painter.drawLine(cx, top + 14, cx, top + 27)
    painter.drawLine(cx, top + 27, left + 22, top + 43)
    painter.drawLine(cx, top + 27, right - 22, top + 43)
    painter.drawRoundedRect(QRectF(left + 24, top + 43, rect.width() - 48, 34), 12, 12)
    painter.drawRoundedRect(QRectF(left + 7, top + 50, 16, 29), 7, 7)
    painter.drawRoundedRect(QRectF(right - 23, top + 50, 16, 29), 7, 7)
    painter.drawArc(QRectF(right - 37, top + 55, 30, 40), -72 * 16, 125 * 16)
    painter.drawRoundedRect(QRectF(right - 50, top + 84, 21, 9), 5, 5)
    painter.drawLine(left + 38, top + 62, left + 46, top + 54)
    painter.drawLine(left + 46, top + 54, left + 54, top + 62)
    painter.drawLine(right - 54, top + 62, right - 46, top + 54)
    painter.drawLine(right - 46, top + 54, right - 38, top + 62)
    painter.restore()
