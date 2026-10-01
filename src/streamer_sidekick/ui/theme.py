"""Tema global do app (Sidekick OS), gerado a partir de ``ui/tokens.py``.

Os ``objectName``s estilizados aqui são API pública: plugins e guias usam
``PageTitle``, ``SectionTitle``, ``CardTitle``, ``Muted``, ``Kicker``,
``StatusPill``, ``PrimaryButton`` e ``NeonPanel``. Não renomeie.
"""
import tempfile
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QFont, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QApplication

from streamer_sidekick.ui import tokens

# Compatibilidade: nomes antigos, agora resolvidos para as fontes embarcadas.
TITLE_FONT = "Chakra Petch"
BODY_FONT = "IBM Plex Sans"
MONO_FONT = "IBM Plex Mono"
HUD_FONT = "VT323"


def apply_theme(app: QApplication) -> None:
    global TITLE_FONT, BODY_FONT, MONO_FONT, HUD_FONT
    tokens.load_fonts()
    TITLE_FONT = tokens.family("display")
    BODY_FONT = tokens.family("body")
    MONO_FONT = tokens.family("mono")
    HUD_FONT = tokens.family("hud")
    base = QFont(BODY_FONT)
    base.setPixelSize(14)
    app.setFont(base)
    app.setPalette(build_palette())
    app.setStyleSheet(build_stylesheet())


def build_palette() -> QPalette:
    """Paleta coerente com o QSS.

    O fundo das janelas vem daqui (inclusive janelas de plugins que não definem
    estilo). Widgets internos ficam transparentes, então nada pinta uma faixa de
    canvas por cima da superfície dos painéis.
    """
    t = tokens.color
    pal = QPalette()
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        pal.setColor(group, QPalette.ColorRole.Window, t("canvas"))
        pal.setColor(group, QPalette.ColorRole.WindowText, t("ink"))
        pal.setColor(group, QPalette.ColorRole.Base, t("sunken"))
        pal.setColor(group, QPalette.ColorRole.AlternateBase, t("surface"))
        pal.setColor(group, QPalette.ColorRole.Text, t("ink"))
        pal.setColor(group, QPalette.ColorRole.PlaceholderText, t("ink-faint"))
        pal.setColor(group, QPalette.ColorRole.Button, t("surface-raised"))
        pal.setColor(group, QPalette.ColorRole.ButtonText, t("ink"))
        pal.setColor(group, QPalette.ColorRole.Highlight, t("primary-tint"))
        pal.setColor(group, QPalette.ColorRole.HighlightedText, t("ink"))
        pal.setColor(group, QPalette.ColorRole.ToolTipBase, t("surface-raised"))
        pal.setColor(group, QPalette.ColorRole.ToolTipText, t("ink"))
        pal.setColor(group, QPalette.ColorRole.Link, t("primary"))
        pal.setColor(group, QPalette.ColorRole.BrightText, t("ink"))
    disabled = QPalette.ColorGroup.Disabled
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        pal.setColor(disabled, role, t("ink-faint"))
    pal.setColor(disabled, QPalette.ColorRole.Window, t("canvas"))
    pal.setColor(disabled, QPalette.ColorRole.Base, t("surface"))
    pal.setColor(disabled, QPalette.ColorRole.Button, t("surface"))
    return pal


def build_stylesheet() -> str:
    c = tokens.COLORS
    check = _indicator_image("check")
    arrow = _indicator_image("arrow")
    return f"""
        /* Sem background no QWidget genérico: o fundo das janelas vem da paleta
           (build_palette) e os widgets internos ficam transparentes. */
        QWidget {{
            color: {c['ink']};
            font-family: "{BODY_FONT}";
            font-size: 14px;
        }}

        QLabel, QCheckBox, QRadioButton {{
            background: transparent;
        }}

        QMainWindow, QDialog, QMessageBox, QWidget#GuideWindow {{
            background: {c['canvas']};
        }}

        QWidget#ContentSurface {{
            background: {c['canvas']};
        }}

        QScrollArea#PageScroll {{
            background: transparent;
            border: 0;
        }}

        QScrollArea#PageScroll > QWidget > QWidget {{
            background: transparent;
        }}

        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 2px;
        }}

        QScrollBar::handle:vertical {{
            background: {c['hairline-strong']};
            border-radius: 2px;
            min-height: 36px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {c['primary']};
        }}

        QScrollBar:horizontal {{
            background: transparent;
            height: 10px;
            margin: 2px;
        }}

        QScrollBar::handle:horizontal {{
            background: {c['hairline-strong']};
            border-radius: 2px;
            min-width: 36px;
        }}

        QScrollBar::add-line, QScrollBar::sub-line,
        QScrollBar::add-page, QScrollBar::sub-page {{
            height: 0;
            width: 0;
            border: 0;
            background: transparent;
        }}

        /* ---------- tipografia (API de objectName) ---------- */

        QLabel#PageTitle {{
            font-family: "{TITLE_FONT}";
            font-size: 32px;
            font-weight: 700;
            color: {c['ink']};
        }}

        QLabel#SectionTitle {{
            font-family: "{TITLE_FONT}";
            font-size: 20px;
            font-weight: 600;
            color: {c['ink']};
        }}

        QLabel#CardTitle {{
            font-family: "{TITLE_FONT}";
            font-size: 18px;
            font-weight: 600;
            color: {c['ink']};
        }}

        QLabel#Muted {{
            color: {c['ink-muted']};
        }}

        QLabel#Caption {{
            color: {c['ink-faint']};
            font-size: 12px;
        }}

        QLabel#Kicker, QLabel#HudLabel {{
            font-family: "{HUD_FONT}";
            color: {c['primary']};
            font-size: 20px;
            letter-spacing: 1px;
        }}

        QLabel#HudLabel {{
            color: {c['ink-muted']};
        }}

        QLabel#AccentDivider {{
            color: {c['hairline-strong']};
            font-size: 18px;
        }}

        QLabel#Numeric {{
            font-family: "{HUD_FONT}";
            font-size: 24px;
            color: {c['ink']};
        }}

        QLabel#BrandTitle {{
            font-family: "{TITLE_FONT}";
            font-size: 34px;
            font-weight: 700;
        }}

        QLabel#BrandTitleCompact {{
            font-family: "{TITLE_FONT}";
            font-size: 22px;
            font-weight: 700;
        }}

        QLabel#StatusPill {{
            background: {c['surface-raised']};
            border: 0;
            border-radius: 11px;
            padding: 4px 12px;
            color: {c['ink-muted']};
            font-size: 13px;
        }}

        QLabel#ModuleStatusText {{
            color: {c['ink-muted']};
            font-size: 13px;
            padding-top: 4px;
        }}

        QLabel#SidebarStatus {{
            font-family: "{HUD_FONT}";
            font-size: 18px;
            letter-spacing: 1px;
            color: {c['ink-faint']};
        }}

        /* ---------- estrutura ---------- */

        QFrame#Sidebar {{
            background: {c['sunken']};
            border-right: 1px solid {c['hairline']};
        }}

        QFrame#Sidebar QWidget {{
            background: transparent;
        }}

        QFrame#ModuleCard {{
            background: {c['surface']};
            border: 1px solid {c['hairline']};
            border-radius: 4px;
        }}

        QFrame#ModuleCard:hover {{
            border-color: {c['hairline-strong']};
        }}

        /* QFrame comum com objectName NeonPanel (plugins, guias, linhas de catálogo).
           O ponto restringe à classe exata: a classe NeonPanel se pinta sozinha. */
        .QFrame#NeonPanel {{
            background: {c['surface']};
            border: 1px solid {c['hairline']};
            border-radius: 4px;
        }}

        /* ---------- botões ---------- */

        QPushButton {{
            background: {c['surface-raised']};
            border: 1px solid {c['hairline-strong']};
            border-radius: 4px;
            padding: 8px 16px;
            min-height: 18px;
            color: {c['ink']};
            font-size: 13px;
            font-weight: 600;
        }}

        QPushButton:hover {{
            border-color: {c['primary']};
        }}

        QPushButton:pressed {{
            background: {c['surface']};
            padding-top: 9px;
            padding-bottom: 7px;
        }}

        QPushButton:focus {{
            border-color: {c['primary']};
        }}

        QPushButton:disabled {{
            background: {c['surface']};
            border-color: {c['hairline']};
            color: {c['ink-faint']};
        }}

        QPushButton#PrimaryButton {{
            background: {c['primary']};
            border: 1px solid {c['primary']};
            color: {c['on-primary']};
        }}

        QPushButton#PrimaryButton:hover {{
            background: {c['primary-hover']};
            border-color: {c['primary-hover']};
        }}

        QPushButton#PrimaryButton:focus {{
            border: 2px solid {c['ink']};
        }}

        QPushButton#PrimaryButton:disabled {{
            background: {c['hairline']};
            border-color: {c['hairline']};
            color: {c['ink-faint']};
        }}

        QPushButton#GhostButton {{
            background: transparent;
            border: 1px solid transparent;
            color: {c['primary']};
            padding: 8px 10px;
        }}

        QPushButton#GhostButton:hover {{
            background: {c['surface-raised']};
            color: {c['primary-hover']};
        }}

        QPushButton#DangerButton {{
            background: transparent;
            border: 1px solid {c['danger']};
            color: {c['danger']};
        }}

        QPushButton#DangerButton:hover {{
            background: {c['surface-raised']};
        }}

        QPushButton#NavButton, QPushButton#SubNavButton {{
            text-align: left;
            background: transparent;
            border: 0;
            border-left: 3px solid transparent;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
            color: {c['ink-muted']};
            font-weight: 600;
        }}

        QPushButton#NavButton {{
            padding: 10px 12px 10px 13px;
            font-size: 15px;
        }}

        QPushButton#SubNavButton {{
            padding: 7px 10px;
            font-size: 14px;
        }}

        QPushButton#NavButton:hover, QPushButton#SubNavButton:hover {{
            background: {c['surface-raised']};
            color: {c['ink']};
        }}

        QPushButton#NavButton[active="true"], QPushButton#SubNavButton[active="true"] {{
            background: {c['surface-raised']};
            border-left: 3px solid {c['brand']};
            color: {c['ink']};
        }}

        QWidget#PluginSubnav {{
            background: transparent;
        }}

        /* ---------- menus e dicas ---------- */

        QMenu {{
            background: {c['surface-raised']};
            border: 1px solid {c['hairline-strong']};
            color: {c['ink']};
            padding: 6px;
        }}

        QMenu::item {{
            background: transparent;
            border-radius: 2px;
            padding: 8px 28px 8px 12px;
        }}

        QMenu::item:selected {{
            background: {c['primary-tint']};
            color: {c['ink']};
        }}

        QMenu::item:disabled {{
            color: {c['ink-faint']};
        }}

        QMenu::separator {{
            height: 1px;
            background: {c['hairline']};
            margin: 5px 4px;
        }}

        QToolTip {{
            background: {c['surface-raised']};
            border: 1px solid {c['hairline-strong']};
            color: {c['ink']};
            padding: 6px 8px;
        }}

        /* ---------- campos ---------- */

        QLineEdit, QKeySequenceEdit, QComboBox, QSpinBox, QPlainTextEdit, QTextEdit {{
            background: {c['sunken']};
            border: 1px solid {c['control-border']};
            border-radius: 4px;
            padding: 8px 10px;
            color: {c['ink']};
            min-height: 18px;
            selection-background-color: {c['primary-tint']};
            selection-color: {c['ink']};
        }}

        QLineEdit:focus, QKeySequenceEdit:focus, QComboBox:focus, QSpinBox:focus,
        QPlainTextEdit:focus, QTextEdit:focus {{
            border-color: {c['primary']};
        }}

        QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
            background: {c['surface']};
            border-color: {c['hairline']};
            color: {c['ink-faint']};
        }}

        QComboBox::drop-down {{
            border: 0;
            width: 26px;
        }}

        QComboBox::down-arrow {{
            image: url("{arrow}");
            width: 12px;
            height: 12px;
        }}

        QComboBox QAbstractItemView {{
            background: {c['surface-raised']};
            border: 1px solid {c['hairline-strong']};
            selection-background-color: {c['primary-tint']};
            color: {c['ink']};
        }}

        QKeySequenceEdit[recording="true"] {{
            background: {c['primary-tint']};
            border: 1px solid {c['primary']};
            color: {c['ink']};
        }}

        QLabel#CaptureStatus {{
            background: {c['surface-raised']};
            border: 0;
            border-radius: 4px;
            padding: 8px 12px;
            color: {c['ink-muted']};
            font-weight: 600;
        }}

        QLabel#CaptureStatus[recording="true"] {{
            background: {c['primary-tint']};
            color: {c['primary']};
        }}

        /* ---------- listas, abas e tabelas ---------- */

        QListWidget, QListView, QTreeView, QTableView {{
            background: {c['sunken']};
            border: 1px solid {c['hairline']};
            border-radius: 4px;
            padding: 6px;
            color: {c['ink']};
        }}

        QListWidget::item {{
            border-radius: 2px;
            padding: 8px 10px;
            border-left: 2px solid transparent;
        }}

        QListWidget::item:hover {{
            background: {c['surface-raised']};
        }}

        QListWidget::item:selected {{
            background: {c['primary-tint']};
            color: {c['ink']};
            border-left: 2px solid {c['primary']};
        }}

        QCheckBox, QRadioButton {{
            spacing: 10px;
            color: {c['ink']};
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 3px;
            border: 1px solid {c['control-border']};
            background: {c['sunken']};
        }}

        QCheckBox::indicator:hover {{
            border-color: {c['primary']};
        }}

        QCheckBox::indicator:checked {{
            background: {c['primary']};
            border-color: {c['primary']};
            image: url("{check}");
        }}

        QTabWidget::pane {{
            border: 0;
            border-top: 1px solid {c['hairline']};
            background: transparent;
        }}

        QTabBar::tab {{
            background: transparent;
            border: 0;
            border-bottom: 2px solid transparent;
            padding: 8px 14px;
            color: {c['ink-muted']};
            font-weight: 600;
        }}

        QTabBar::tab:hover {{
            color: {c['ink']};
        }}

        QTabBar::tab:selected {{
            color: {c['ink']};
            border-bottom: 2px solid {c['primary']};
        }}

        QHeaderView::section {{
            background: {c['surface-raised']};
            color: {c['ink-muted']};
            border: 0;
            border-bottom: 1px solid {c['hairline']};
            padding: 8px;
            font-weight: 600;
        }}

        QProgressBar {{
            background: {c['sunken']};
            border: 1px solid {c['hairline']};
            border-radius: 2px;
            color: {c['ink']};
            text-align: center;
        }}

        QProgressBar::chunk {{
            background: {c['success']};
        }}
    """


def _indicator_image(kind: str) -> str:
    """Gera (uma vez) o PNG do check do QCheckBox e da seta do QComboBox.

    QSS só aceita imagem por caminho; o arquivo vai para a pasta temporária.
    """
    folder = Path(tempfile.gettempdir()) / "streamer_sidekick_theme"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{kind}.png"
    size = 36  # desenhado em 2x e reduzido pelo QSS
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if kind == "check":
        pen = QPen(tokens.color("on-primary"), 4.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap,
                   Qt.PenJoinStyle.MiterJoin)
        p.setPen(pen)
        path_ = QPainterPath(QPointF(8, 19))
        path_.lineTo(15, 26)
        path_.lineTo(28, 11)
        p.drawPath(path_)
    else:
        pen = QPen(tokens.color("ink-muted"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap,
                   Qt.PenJoinStyle.MiterJoin)
        p.setPen(pen)
        path_ = QPainterPath(QPointF(8, 13))
        path_.lineTo(18, 23)
        path_.lineTo(28, 13)
        p.drawPath(path_)
    p.end()
    pm.save(str(path), "PNG")
    return path.as_posix()


def _load_optional_fonts() -> None:
    """Compatibilidade: as fontes agora são carregadas por ``tokens.load_fonts``."""
    tokens.load_fonts()
