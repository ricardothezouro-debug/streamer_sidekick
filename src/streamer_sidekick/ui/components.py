"""Componentes visuais do Sidekick OS (DESIGN.md, seção Components).

Nomes e assinaturas antigos (``NeonPanel``, ``ModuleCard``, ``NeonIcon``,
``neon_qicon``, ``NeonProgressBar``…) foram mantidos: plugins de terceiros os
importam. O visual por baixo é o novo.
"""
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from streamer_sidekick.core.modules import ModuleInfo
from streamer_sidekick.ui import icons, tokens

# Compatibilidade: constantes antigas, agora apontando para os tokens.
VOID_BLACK = tokens.hex_("canvas")
GRAPHITE = tokens.hex_("surface-raised")
SOFT_WHITE = tokens.hex_("ink")
ELECTRIC_CYAN = tokens.hex_("primary")
NEON_MAGENTA = tokens.hex_("brand")
ACID_LIME = tokens.hex_("success")
PANEL_BORDER = tokens.hex_("hairline")
MUTED = tokens.hex_("ink-muted")
BRAND_ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "brand"

# icon_id antigo -> ícone de interface / ícone de marca
# Plugins oficiais desenhados no próprio sistema de ícones: o hub usa o desenho dele
# em vez do icon.png do pacote, para combinar com o resto da interface.
_OFFICIAL_PLUGIN_ICONS = {"clipit": "clip", "launcher": "power", "subtitler": "captions"}
_UI_ALIASES = {"document": "marker", "plugin": "plugins", "bot": "home", **_OFFICIAL_PLUGIN_ICONS}
_BRAND_ALIASES = {"marker": "marker", "document": "marker", "counter": "counter", "home": "sidekick",
                  "plugins": "puzzle", "plugin": "puzzle", "platinas": "trophy", "backup": "floppy",
                  **_OFFICIAL_PLUGIN_ICONS}


def _chamfer_path(rect: QRectF, cut: float) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(rect.left(), rect.top())
    path.lineTo(rect.right() - cut, rect.top())
    path.lineTo(rect.right(), rect.top() + cut)
    path.lineTo(rect.right(), rect.bottom())
    path.lineTo(rect.left(), rect.bottom())
    path.closeSubpath()
    return path


def hud_font(size: int = 20) -> QFont:
    f = QFont(tokens.family("hud"))
    f.setPixelSize(size)
    f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 108)
    return f


class NeonPanel(QFrame):
    """Painel-janela (``panel-window``): chanfro, sombra dura e barra de título opcional.

    ``accent`` e ``grid`` são aceitos por compatibilidade e ignorados: no Sidekick OS
    a cor tem papel, e o destaque é ``featured=True`` (um por tela).
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        accent: str = ELECTRIC_CYAN,
        grid: bool = False,
        title: str = "",
        meta: str = "",
        featured: bool = False,
    ) -> None:
        super().__init__(parent)
        self.accent = QColor(accent)
        self.grid = grid
        self._title = title
        self._meta = meta
        self._featured = featured
        self.setObjectName("NeonPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._apply_margins()

    def _apply_margins(self) -> None:
        top = tokens.PANEL_TITLEBAR if self._title else 0
        shadow = tokens.PANEL_SHADOW
        self.setContentsMargins(0, top, shadow, shadow)

    def set_title(self, title: str, meta: str = "") -> None:
        self._title = title
        self._meta = meta
        self._apply_margins()
        self._sync_tooltip()
        self.update()

    def set_meta(self, meta: str) -> None:
        self._meta = meta
        self._sync_tooltip()
        self.update()

    def set_featured(self, featured: bool) -> None:
        self._featured = featured
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        shadow = tokens.PANEL_SHADOW
        cut = tokens.PANEL_CHAMFER
        rect = QRectF(0.5, 0.5, self.width() - shadow - 1.0, self.height() - shadow - 1.0)

        painter.fillPath(_chamfer_path(rect.translated(shadow, shadow), cut), tokens.color("shadow-hard", 178))
        path = _chamfer_path(rect, cut)
        painter.fillPath(path, tokens.color("surface"))

        if self._title:
            bar = QRectF(rect.left(), rect.top(), rect.width(), tokens.PANEL_TITLEBAR)
            painter.fillPath(_chamfer_path(bar, cut), tokens.color("surface-raised"))
            painter.setPen(QPen(tokens.color("hairline"), 1))
            painter.drawLine(QPointF(bar.left(), bar.bottom()), QPointF(bar.right(), bar.bottom()))

        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self._featured:
            painter.setPen(QPen(tokens.color("primary", 50), 5))
            painter.drawPath(path)
            painter.setPen(QPen(tokens.color("primary"), 1.2))
            painter.drawPath(path)
            painter.fillRect(QRectF(rect.left(), rect.top(), rect.width() - cut, 2), tokens.color("brand"))
        else:
            painter.setPen(QPen(tokens.color("hairline"), 1))
            painter.drawPath(path)

        if self._title:
            title, meta, bar = self._titlebar_texts(rect)
            painter.setFont(hud_font(20))
            painter.setPen(tokens.color("ink-muted"))
            painter.drawText(bar, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), title)
            if meta:
                painter.setPen(tokens.color("ink-faint"))
                painter.drawText(bar, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), meta)
        # Sem super().paintEvent: o QFrame desenharia a borda retangular do QSS por cima do chanfro.

    def _titlebar_texts(self, rect: QRectF) -> tuple[str, str, QRectF]:
        """Título e metadado que cabem na barra (com "…"). O metadado ocupa no máximo 40%."""
        metrics = QFontMetrics(hud_font(20))
        bar = QRectF(rect.left() + 12, rect.top(), rect.width() - 24 - tokens.PANEL_CHAMFER, tokens.PANEL_TITLEBAR)
        meta = ""
        meta_w = 0
        if self._meta:
            meta = metrics.elidedText(self._meta, Qt.TextElideMode.ElideRight, int(bar.width() * 0.4))
            meta_w = metrics.horizontalAdvance(meta) + 12
        title = metrics.elidedText(self._title.upper(), Qt.TextElideMode.ElideRight, int(max(0, bar.width() - meta_w)))
        return title, meta, bar

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_tooltip()

    def _sync_tooltip(self) -> None:
        if not self._title:
            return
        shadow = tokens.PANEL_SHADOW
        rect = QRectF(0.5, 0.5, self.width() - shadow - 1.0, self.height() - shadow - 1.0)
        title, meta, _bar = self._titlebar_texts(rect)
        clipped = title != self._title.upper() or meta != self._meta
        full = f"{self._title} · {self._meta}" if self._meta else self._title
        self.setToolTip(full if clipped else "")


class PanelWindow(NeonPanel):
    """Nome do DESIGN.md para o painel-janela com barra de título."""

    def __init__(self, title: str = "", meta: str = "", featured: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, title=title, meta=meta, featured=featured)


class SectionHeader(QWidget):
    """Rótulo de seção em HUD: ``NÚMERO  TÍTULO ─────``."""

    def __init__(self, number: str, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        if number:
            number_label = QLabel(number)
            number_label.setObjectName("Kicker")
            layout.addWidget(number_label)
        title_label = QLabel(title.upper())
        title_label.setObjectName("HudLabel")
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {tokens.hex_('hairline')};")
        layout.addWidget(title_label)
        layout.addWidget(line, 1, Qt.AlignmentFlag.AlignVCenter)


class ElidedLabel(QLabel):
    """Rótulo que termina em "…" em vez de cortar, em 1 ou mais linhas.

    Nunca encolhe a ponto de ficar ilegível (``minimumSizeHint`` reserva umas 8
    letras) e, sempre que algo some, o texto inteiro vai para o tooltip.
    ``mode=Qt.TextElideMode.ElideMiddle`` serve para caminhos de arquivo.
    """

    def __init__(self, text: str = "", lines: int = 1, parent: Optional[QWidget] = None,
                 mode: Qt.TextElideMode = Qt.TextElideMode.ElideRight) -> None:
        super().__init__(parent)
        self._full = text or ""
        self._lines = max(1, lines)
        self._mode = mode
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setWordWrap(False)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._refresh()

    def full_text(self) -> str:
        return self._full

    def setText(self, text: str) -> None:  # noqa: N802 (API do Qt)
        self._full = text or ""
        self.updateGeometry()
        self._refresh()

    def _height(self) -> int:
        m = self.contentsMargins()
        return self.fontMetrics().lineSpacing() * self._lines + 2 + m.top() + m.bottom()

    def sizeHint(self) -> QSize:
        fm = self.fontMetrics()
        m = self.contentsMargins()
        width = min(fm.horizontalAdvance(self._full) + 4, 420) + m.left() + m.right()
        return QSize(width, self._height())

    def minimumSizeHint(self) -> QSize:
        fm = self.fontMetrics()
        m = self.contentsMargins()
        floor = min(fm.horizontalAdvance(self._full), fm.horizontalAdvance(self._full[:8] + "…"))
        return QSize(floor + 4 + m.left() + m.right(), self._height())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (event.Type.FontChange, event.Type.StyleChange):
            self._refresh()

    def _refresh(self) -> None:
        fm = self.fontMetrics()
        width = max(16, self.contentsRect().width())
        if self._lines == 1:
            lines = [fm.elidedText(self._full, self._mode, width)]
        else:
            words, lines, current = self._full.split(), [], ""
            for word in words:
                test = (current + " " + word).strip()
                if current and fm.horizontalAdvance(test) > width:
                    lines.append(current)
                    current = word
                else:
                    current = test
            if current:
                lines.append(current)
            if len(lines) > self._lines:
                head = lines[: self._lines - 1]
                lines = head + [" ".join(lines[self._lines - 1:])]
            # Elide cada linha: uma palavra sozinha mais larga que o rótulo também ganha "…".
            lines = [fm.elidedText(line, Qt.TextElideMode.ElideRight, width) for line in lines]
        shown = "\n".join(lines)
        QLabel.setText(self, shown)
        self.setToolTip(self._full if " ".join(shown.split()) != " ".join(self._full.split()) else "")
        self.setAccessibleName(self._full)
        self.setFixedHeight(self._height())


class StatusChip(QWidget):
    """Ponto colorido + rótulo curto em pílula (``status-chip``). Nunca parece campo de texto."""

    STATES = {"ok": "success", "warn": "warning", "error": "danger", "neutral": "ink-faint", "live": "brand",
              "info": "primary"}

    PAD_LEFT = 25  # ponto + respiro
    PAD_RIGHT = 10

    def __init__(self, text: str = "", state: str = "neutral", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._text = text
        self._state = state
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self._sync_accessibility()

    def set_text(self, text: str, state: Optional[str] = None) -> None:
        self._text = text
        if state:
            self._state = state
        self.updateGeometry()
        self._sync_accessibility()
        self.update()

    def set_state(self, state: str) -> None:
        self._state = state
        self.update()

    def text(self) -> str:
        return self._text

    def _font(self) -> QFont:
        return tokens.font("caption")

    def _shown(self) -> str:
        fm = QFontMetrics(self._font())
        return fm.elidedText(self._text, Qt.TextElideMode.ElideRight,
                             max(0, self.width() - self.PAD_LEFT - self.PAD_RIGHT))

    def _sync_accessibility(self) -> None:
        self.setAccessibleName(self._text)
        self.setToolTip(self._text if self._shown() != self._text else "")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_accessibility()

    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self._font())
        return QSize(fm.horizontalAdvance(self._text) + self.PAD_LEFT + self.PAD_RIGHT + 2, 26)

    def minimumSizeHint(self) -> QSize:
        fm = QFontMetrics(self._font())
        floor = min(fm.horizontalAdvance(self._text), fm.horizontalAdvance("Mmmmm…"))
        return QSize(floor + self.PAD_LEFT + self.PAD_RIGHT + 2, 26)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(tokens.color("surface-raised"))
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        dot = tokens.color(self.STATES.get(self._state, "ink-faint"))
        painter.setBrush(dot)
        painter.drawEllipse(QPointF(14, rect.center().y()), 4, 4)
        painter.setFont(self._font())
        painter.setPen(tokens.color("ink-muted"))
        text_rect = rect.adjusted(self.PAD_LEFT, 0, -self.PAD_RIGHT, 0)
        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), self._shown())


def guess_state(status: str) -> str:
    """Estado do chip a partir do texto livre que os módulos devolvem."""
    low = (status or "").strip().lower()
    if not low:
        return "neutral"
    if low.startswith(("erro", "falha", "falhou")):
        return "error"
    if low.startswith(("nenhum", "nenhuma", "sem ", "desligado", "indisponível", "inativo")):
        return "neutral"
    if "ao vivo" in low or "gravando" in low:
        return "live"
    return "ok"


def _has_own_tile(pixmap: QPixmap) -> bool:
    """O PNG já vem com o próprio quadrado de fundo (opaco perto das bordas)?

    Ícones de plugin costumam trazer um "app icon" pronto. Desenhar o nosso quadro
    em volta vira caixa dentro de caixa; nesse caso o PNG ocupa o quadro inteiro.
    Amostra o meio de cada borda, um pouco para dentro (os cantos são arredondados).
    """
    image = pixmap.toImage()
    w, h = image.width(), image.height()
    if w < 8 or h < 8:
        return False
    inset_x, inset_y = max(1, w // 20), max(1, h // 20)
    points = [(w // 2, inset_y), (w // 2, h - 1 - inset_y), (inset_x, h // 2), (w - 1 - inset_x, h // 2)]
    opaque = sum(1 for x, y in points if image.pixelColor(x, y).alpha() > 200)
    return opaque >= 3


class IconBox(QWidget):
    """Quadro de 56 px em sunken com o ícone do módulo/plugin (DESIGN.md: module-card)."""

    def __init__(self, brand: str = "", pixmap: Optional[QPixmap] = None, size: int = 56,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._brand = brand
        self._pixmap = pixmap
        self._tiled = pixmap is not None and not pixmap.isNull() and _has_own_tile(pixmap)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        radius = tokens.RADII["md"]
        if self._tiled:
            # O ícone já tem o próprio fundo: ocupa o quadro inteiro, recortado no nosso raio.
            clip = QPainterPath()
            clip.addRoundedRect(rect, radius, radius)
            painter.setClipPath(clip)
            painter.drawPixmap(rect, self._pixmap, QRectF(self._pixmap.rect()))
            painter.setClipping(False)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(tokens.color("hairline-strong"), 1))
            painter.drawRoundedRect(rect, radius, radius)
            return
        painter.setBrush(tokens.color("sunken"))
        painter.setPen(QPen(tokens.color("hairline-strong"), 1))
        painter.drawRoundedRect(rect, radius, radius)
        if self._pixmap is not None and not self._pixmap.isNull():
            inner = rect.adjusted(8, 8, -8, -8)
            _draw_pixmap_fit(painter, self._pixmap, inner)
        elif self._brand:
            size = (min(self.width(), self.height()) - 8) // 12 * 12  # múltiplo de 12
            x = (self.width() - size) / 2
            y = (self.height() - size) / 2
            icons.draw_brand(painter, self._brand, x, y, size, tokens.color)


def paint_wallpaper(p: QPainter, r: QRectF, name: str) -> None:
    """Papel de parede do Sidekick OS (céu degradê, brilho no horizonte, grid, scanlines)."""
    spec = tokens.WALLPAPERS.get(name) or tokens.WALLPAPERS[tokens.DEFAULT_WALLPAPER]
    if spec.get("flat"):
        p.fillRect(r, tokens.color("canvas"))
        return
    hy = r.top() + r.height() * spec["horizon_at"]
    sky = QLinearGradient(0, r.top(), 0, hy)
    sky.setColorAt(0.0, QColor(spec["top"]))
    sky.setColorAt(0.65, QColor(spec["mid"]))
    sky.setColorAt(1.0, QColor(spec["horizon"]))
    p.fillRect(QRectF(r.left(), r.top(), r.width(), hy - r.top()), sky)
    floor = QLinearGradient(0, hy, 0, r.bottom())
    floor.setColorAt(0.0, tokens.color("canvas"))
    floor.setColorAt(1.0, tokens.color("sunken"))
    p.fillRect(QRectF(r.left(), hy, r.width(), r.bottom() - hy), floor)

    glow = QRadialGradient(QPointF(r.center().x(), hy), r.width() * 0.55)
    glow.setColorAt(0.0, tokens.color("brand", spec["glow"]))
    glow.setColorAt(1.0, tokens.color("brand", 0))
    p.fillRect(QRectF(r.left(), hy - r.height() * 0.40, r.width(), r.height() * 0.45), glow)

    p.setPen(QPen(tokens.color("primary", spec["grid"]), 1))
    cx = r.center().x()
    span = r.width() / 7
    for i in range(-30, 31):
        p.drawLine(QPointF(cx + i * span * 0.1, hy), QPointF(cx + i * span, r.bottom()))
    y, step = hy, max(2.0, r.height() * 0.012)
    while y < r.bottom():
        p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
        y += step
        step *= 1.38
    p.setPen(QPen(tokens.color("brand", 200), 1.5))
    p.drawLine(QPointF(r.left(), hy), QPointF(r.right(), hy))
    if spec.get("scanlines"):
        p.setPen(QPen(QColor(0, 0, 0, 38), 1))
        yy = r.top()
        while yy < hy:
            p.drawLine(QPointF(r.left(), yy), QPointF(r.right(), yy))
            yy += 3


class WallpaperSurface(QWidget):
    """Área de conteúdo com o papel de parede fixo atrás das páginas.

    O desenho fica em cache (pixmap) e só é refeito quando o tamanho ou o papel
    de parede mudam: rolar a página não redesenha o grid a cada quadro.
    """

    def __init__(self, wallpaper: str = tokens.DEFAULT_WALLPAPER, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._wallpaper = wallpaper if wallpaper in tokens.WALLPAPERS else tokens.DEFAULT_WALLPAPER
        self._cache: Optional[QPixmap] = None

    def wallpaper(self) -> str:
        return self._wallpaper

    def set_wallpaper(self, name: str) -> None:
        name = name if name in tokens.WALLPAPERS else tokens.DEFAULT_WALLPAPER
        if name != self._wallpaper:
            self._wallpaper = name
            self._cache = None
            self.update()

    def resizeEvent(self, event) -> None:
        self._cache = None
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:
        dpr = self.devicePixelRatioF()
        if self._cache is None or self._cache.size() != self.size() * dpr:
            pm = QPixmap(self.size() * dpr)
            pm.setDevicePixelRatio(dpr)
            cp = QPainter(pm)
            cp.setRenderHint(QPainter.RenderHint.Antialiasing)
            paint_wallpaper(cp, QRectF(0, 0, self.width(), self.height()), self._wallpaper)
            cp.end()
            self._cache = pm
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._cache)  # o Qt recorta na área suja (event.rect)


class SynthHero(QWidget):
    """Arte synthwave (sol listrado, horizonte roxo, grid). Só em hero, onboarding e vazios."""

    def __init__(self, height: int = 140, sun: float = 0.42, horizon: float = 0.62,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._sun = sun
        self._horizon = horizon
        self.setFixedHeight(height)
        self.setMinimumWidth(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        paint_synth(painter, QRectF(0, 0, self.width(), self.height()), sun=self._sun, horizon=self._horizon)


def paint_synth(p: QPainter, r: QRectF, cx: float = 0.5, sun: float = 0.42, horizon: float = 0.62,
                border: bool = True) -> None:
    p.save()
    p.setClipRect(r)
    hy = r.top() + r.height() * horizon
    sky = QLinearGradient(0, r.top(), 0, hy)
    sky.setColorAt(0, tokens.color("sunken"))
    sky.setColorAt(1, tokens.color("synth", 120))
    p.fillRect(QRectF(r.left(), r.top(), r.width(), hy - r.top()), sky)
    x0, rad = r.left() + r.width() * cx, r.height() * sun
    sun_grad = QLinearGradient(0, hy - rad, 0, hy)
    sun_grad.setColorAt(0, tokens.color("synth-sun-top"))
    sun_grad.setColorAt(1, tokens.color("synth-sun-bottom"))
    p.setBrush(sun_grad)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPie(QRectF(x0 - rad, hy - rad, rad * 2, rad * 2), 0, 180 * 16)
    clip = QPainterPath()
    clip.moveTo(x0, hy)
    clip.arcTo(QRectF(x0 - rad, hy - rad, rad * 2, rad * 2), 0, 180)
    clip.closeSubpath()
    p.save()
    p.setClipPath(clip, Qt.ClipOperation.IntersectClip)
    for i in range(5):
        top = hy - rad * 0.52 + i * rad * 0.105
        p.fillRect(QRectF(x0 - rad, top, rad * 2, rad * (0.018 + i * 0.012)), sky)
    p.restore()
    p.fillRect(QRectF(r.left(), hy, r.width(), r.bottom() - hy), tokens.color("sunken"))
    p.setPen(QPen(tokens.color("primary", 95), 1.0))
    p.drawLine(QPointF(r.left(), hy), QPointF(r.right(), hy))
    span = r.width() / 9
    for i in range(-22, 23):
        p.drawLine(QPointF(x0 + i * span * 0.12, hy), QPointF(x0 + i * span, r.bottom()))
    y, step = hy, r.height() * 0.018
    while y < r.bottom():
        p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
        y += step
        step *= 1.42
    p.restore()
    if border:
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(tokens.color("hairline"), 1))
        p.drawRect(r.adjusted(0.5, 0.5, -0.5, -0.5))


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
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

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
        family = tokens.family("display")
        while size > floor:
            font = QFont(family)
            font.setPixelSize(size)
            font.setWeight(QFont.Weight.Bold)
            metrics = QFontMetrics(font)
            total = sum(metrics.horizontalAdvance(text) for _, text in segments)
            if total <= available:
                break
            size -= 1

        font = QFont(family)
        font.setPixelSize(size)
        font.setWeight(QFont.Weight.Bold)
        metrics = QFontMetrics(font)
        if sum(metrics.horizontalAdvance(text) for _, text in segments) > available:
            return  # nem no menor tamanho cabe: melhor só o robô do que o nome cortado
        baseline = int((height + metrics.ascent() - metrics.descent()) / 2)
        cursor = int(text_x)
        painter.setFont(font)
        for color, text in segments:
            painter.setPen(QColor(color))
            painter.drawText(cursor, baseline, text)
            cursor += metrics.horizontalAdvance(text)


class BrandIcon(QWidget):
    def __init__(self, size: int = 96, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        icon = _asset_pixmap("brand_icon.png")
        if icon is not None:
            _draw_pixmap_fit(painter, icon, QRectF(0, 0, self.width(), self.height()))
            return
        painter.scale(self.width() / 100, self.height() / 100)
        _draw_bot_icon(painter, QRectF(6, 8, 88, 84), 7)


class NeonIcon(QWidget):
    """Ícone por ``icon_id``. Em 48 px ou mais usa o ícone de marca (pixel) quando existe;
    abaixo disso, o ícone de interface. ``accent`` é aceito por compatibilidade."""

    def __init__(self, icon_id: str, accent: str = ELECTRIC_CYAN, size: int = 54, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.icon_id = icon_id
        self.accent = QColor(accent)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        size = min(self.width(), self.height())
        brand = _BRAND_ALIASES.get(self.icon_id, self.icon_id)
        if size >= 48 and icons.has_brand(brand):
            px = size // 12 * 12
            icons.draw_brand(painter, brand, (self.width() - px) / 2, (self.height() - px) / 2, px, tokens.color)
            return
        name = _ui_name(self.icon_id)
        icons.draw_ui(painter, name, (self.width() - size) / 2, (self.height() - size) / 2, size,
                      tokens.color("primary"))


def _ui_name(icon_id: str) -> str:
    name = _UI_ALIASES.get(icon_id, icon_id)
    return name if icons.has_ui(name) else "plugins"


def neon_qicon(icon_id: str, size: int = 22, color: str = "ink-muted") -> QIcon:
    """Ícone de interface como QIcon (barra lateral, botões)."""
    return icons.ui_icon(_ui_name(icon_id), size, color)


def nav_qicon(icon_id: str, active: bool = False, size: int = 22) -> QIcon:
    return neon_qicon(icon_id, size, "primary" if active else "ink-muted")


def _module_brand(module: ModuleInfo) -> str:
    return _BRAND_ALIASES.get(module.module_id, "puzzle")


class ModuleTile(QFrame):
    """Card de módulo/plugin (``module-card``)."""

    opened = Signal(str)

    #: Largura mínima: ícone (56) + respiro (14) + ~180 de texto + margens (32).
    #: Abaixo disso título e status começariam a virar "…".
    MIN_WIDTH = 284

    def __init__(self, module: ModuleInfo, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.module = module
        self.setObjectName("ModuleCard")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMinimumHeight(184)
        self.setMinimumWidth(self.MIN_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 14)
        root.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(14)
        icon = _make_module_icon(module)
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        self.title_label = ElidedLabel(module.title, lines=1)
        self.title_label.setObjectName("CardTitle")
        # Descrição inteira, quebrando linha: o card cresce em vez de cortar o texto.
        self.subtitle_label = QLabel(module.subtitle)
        self.subtitle_label.setObjectName("Muted")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.subtitle_label)
        title_box.addStretch(1)
        header.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        header.addLayout(title_box, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.status_chip = StatusChip(module.status, guess_state(module.status))
        open_button = QPushButton("Abrir")
        open_button.setObjectName("GhostButton")
        open_button.setAccessibleName(f"Abrir {module.title}")
        open_button.setToolTip(f"Abrir {module.title}")
        open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        open_button.clicked.connect(lambda: self.opened.emit(module.module_id))
        footer.addWidget(self.status_chip, 1, Qt.AlignmentFlag.AlignLeft)
        footer.addWidget(open_button, 0)

        root.addLayout(header)
        root.addStretch(1)
        root.addLayout(footer)

    def set_status(self, text: str) -> None:
        self.status_chip.set_text(text, guess_state(text))


class FutureModuleTile(NeonPanel):
    def __init__(self, title: str, body: str, icon_id: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("FuturePanel")
        self.setMinimumHeight(190)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(NeonIcon(icon_id, size=48), 0, Qt.AlignmentFlag.AlignLeft)
        name = QLabel(title)
        name.setObjectName("CardTitle")
        text = QLabel(body)
        text.setObjectName("Muted")
        text.setWordWrap(True)
        layout.addWidget(name)
        layout.addWidget(text)
        layout.addStretch(1)
        layout.addWidget(StatusChip("Em breve", "neutral"), 0, Qt.AlignmentFlag.AlignLeft)


class AddPluginTile(QFrame):
    """Card "+" que abre o marketplace de plugins."""

    clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("AddPluginCard")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMinimumHeight(184)
        self.setMinimumWidth(ModuleTile.MIN_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Funciona como botão: recebe foco por Tab e abre com Enter/Espaço.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Adicionar plugin")
        self.setToolTip("Abrir o marketplace de plugins")
        radius = tokens.RADII["sm"]
        self.setStyleSheet(
            f"QFrame#AddPluginCard {{ background: {tokens.hex_('surface')};"
            f" border: 1px dashed {tokens.hex_('hairline-strong')}; border-radius: {radius}px; }}"
            f"QFrame#AddPluginCard:hover {{ border-color: {tokens.hex_('success')}; }}"
            f"QFrame#AddPluginCard:focus {{ border: 1px solid {tokens.hex_('primary')}; }}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(6)

        plus = QLabel("+")
        plus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plus.setStyleSheet(
            f"font-family: '{tokens.family('hud')}'; font-size: 56px; color: {tokens.hex_('success')};"
            " background: transparent; border: 0;"
        )
        title = QLabel("Adicionar plugin")
        title.setObjectName("CardTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Explore e instale novas ferramentas")
        subtitle.setObjectName("Muted")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)

        self.badge = StatusChip("", "ok")
        self.badge.setVisible(False)

        root.addStretch(1)
        root.addWidget(plus)
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignHCenter)
        root.addStretch(1)

    def mouseReleaseEvent(self, event) -> None:
        # Dispara ao soltar (como um botão), e só se o cursor ainda estiver no card.
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def set_update_badge(self, count: int) -> None:
        if count > 0:
            text = "1 atualização" if count == 1 else f"{count} atualizações"
            self.badge.set_text(text, "ok")
            self.badge.setVisible(True)
            self.setAccessibleName(f"Adicionar plugin ({text} de plugins)")
        else:
            self.badge.setVisible(False)
            self.setAccessibleName("Adicionar plugin")


ModuleCard = ModuleTile


class NeonProgressBar(QWidget):
    """Progresso em blocos (``segmented-progress``). API antiga mantida: ``setValue(0..100)``
    e ``setIndeterminate``. No modo indeterminado um grupo de blocos corre a barra."""

    SEGMENT_W = 10
    GAP = 3

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._value = 0.0
        self._indeterminate = False
        self._phase = 0
        self.setMinimumHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._timer = QTimer(self)
        self._timer.setInterval(90)
        self._timer.timeout.connect(self._tick)

    def _tick(self) -> None:
        self._phase += 1
        self.update()

    def setValue(self, value: float) -> None:  # noqa: N802 (API do Qt)
        self._indeterminate = False
        self._timer.stop()
        self._value = max(0.0, min(1.0, value / 100.0))
        self.setAccessibleName(f"Progresso: {int(round(self._value * 100))}%")
        self.update()

    def setIndeterminate(self, on: bool = True) -> None:  # noqa: N802
        self._indeterminate = bool(on)
        self.setAccessibleName("Progresso: em andamento" if self._indeterminate else "")
        self._sync_timer()
        self.update()

    def _sync_timer(self) -> None:
        # Só anima quando indeterminado e visível: nada de timer rodando à toa.
        if self._indeterminate and self.isVisible():
            self._timer.start()
        else:
            self._timer.stop()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_timer()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._timer.stop()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        label_w = 0 if self._indeterminate else 52
        track_w = max(0, self.width() - label_w)
        step = self.SEGMENT_W + self.GAP
        count = max(1, (track_w + self.GAP) // step)
        h = min(16, self.height() - 4)
        y = (self.height() - h) / 2
        lit: set = set()
        filled = 0
        if self._indeterminate:
            head = self._phase % (count + 4)  # grupo de 4 blocos correndo
            lit = {head - j for j in range(4)}
        else:
            filled = round(count * self._value)
        for i in range(count):
            rect = QRectF(i * step, y, self.SEGMENT_W, h)
            on = (i in lit) if self._indeterminate else (i < filled)
            painter.fillRect(rect, tokens.color("success") if on else tokens.color("hairline"))
        if not self._indeterminate:
            painter.setPen(tokens.color("ink"))
            painter.setFont(hud_font(22))
            painter.drawText(QRectF(track_w, 0, label_w, self.height()),
                             int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                             f"{int(round(self._value * 100))}%")


SegmentedProgress = NeonProgressBar


def _load_pixmap(path: str, size: int) -> Optional[QPixmap]:
    if not path or not Path(path).exists():
        return None
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return None
    return pixmap.scaled(
        size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
    )


def _make_module_icon(module: ModuleInfo, accent: str = "", size: int = 56) -> QWidget:
    """Quadro do ícone do card: ícone de marca dos oficiais, PNG do plugin quando existir,
    senão o ícone de marca genérico."""
    if module.module_id in _OFFICIAL_PLUGIN_ICONS:
        return IconBox(brand=_module_brand(module), size=size)
    pixmap = _load_pixmap(getattr(module, "icon", "") or "", 96)
    return IconBox(brand="" if pixmap is not None else _module_brand(module), pixmap=pixmap, size=size)


def plugin_qicon(icon_path: str, fallback_id: str = "plugin", size: int = 18) -> QIcon:
    """QIcon para a subnav: ícone de interface dos oficiais (``fallback_id`` = id do plugin),
    PNG do plugin quando existir, senão o ícone de interface genérico."""
    if fallback_id in _OFFICIAL_PLUGIN_ICONS:
        return neon_qicon(fallback_id, size)
    pixmap = _load_pixmap(icon_path or "", size * 2)
    if pixmap is not None:
        return QIcon(pixmap)
    return neon_qicon(fallback_id, size)


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
    """Mantido por compatibilidade; o painel novo usa ``_chamfer_path``."""
    return _chamfer_path(rect, cut)


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
    """Desenho vetorial do robô: só é usado se o PNG de marca não existir."""
    painter.save()
    painter.setPen(_gradient_pen(rect, width))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    cx = rect.center().x()
    top = rect.top()
    left = rect.left()
    right = rect.right()
    painter.drawEllipse(QRectF(cx - 6, top + 2, 12, 12))
    painter.drawLine(QPointF(cx, top + 14), QPointF(cx, top + 27))
    painter.drawRoundedRect(QRectF(left + 24, top + 43, rect.width() - 48, 34), 12, 12)
    painter.restore()
