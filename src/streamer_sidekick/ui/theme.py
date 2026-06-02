from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication


TITLE_FONT = "Bahnschrift"
BODY_FONT = "Segoe UI"
MONO_FONT = "Consolas"


def apply_theme(app: QApplication) -> None:
    _load_optional_fonts()
    app.setFont(QFont(BODY_FONT, 10))
    app.setStyleSheet(
        f"""
        QWidget {{
            background: #0A0B12;
            color: #F3F6FF;
            font-family: "{BODY_FONT}";
            font-size: 14px;
            letter-spacing: 0px;
        }}

        QLabel {{
            background: transparent;
        }}

        QMainWindow, QStackedWidget {{
            background: #0A0B12;
        }}

        QWidget#ContentSurface {{
            background: #0A0B12;
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
            width: 12px;
            margin: 2px;
        }}

        QScrollBar::handle:vertical {{
            background: #273140;
            border-radius: 5px;
            min-height: 36px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: #37F2FF;
        }}

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
            border: 0;
            background: transparent;
        }}

        QLabel#PageTitle {{
            font-family: "{TITLE_FONT}";
            font-size: 38px;
            font-weight: 700;
            color: #F3F6FF;
        }}

        QLabel#SectionTitle {{
            font-size: 18px;
            font-weight: 700;
            color: #F3F6FF;
        }}

        QLabel#Muted {{
            color: #A8B0BC;
        }}

        QLabel#Kicker {{
            font-family: "{MONO_FONT}";
            color: #37F2FF;
            font-size: 18px;
            font-weight: 700;
        }}

        QLabel#AccentDivider {{
            color: #FF4FD8;
            font-size: 18px;
            font-weight: 700;
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

        QFrame#Sidebar {{
            background: #080A10;
            border-right: 1px solid #273140;
        }}

        QPushButton {{
            background: #111722;
            border: 1px solid #273140;
            border-radius: 8px;
            padding: 10px 14px;
            color: #F3F6FF;
            font-weight: 600;
        }}

        QPushButton:hover {{
            background: #151E2C;
            border-color: #37F2FF;
            color: #FFFFFF;
        }}

        QPushButton:pressed {{
            background: #0D121B;
            border-color: #FF4FD8;
        }}

        QPushButton#PrimaryButton {{
            background: #14383F;
            border-color: #37F2FF;
            color: #FFFFFF;
        }}

        QPushButton#PrimaryButton:hover {{
            background: #174A52;
            border-color: #FF4FD8;
        }}

        QPushButton#NavButton {{
            text-align: left;
            background: transparent;
            border: 1px solid transparent;
            border-radius: 8px;
            padding: 11px 14px;
            color: #A8B0BC;
        }}

        QPushButton#NavButton:hover {{
            background: #101722;
            border-color: #273140;
            color: #F3F6FF;
        }}

        QPushButton#NavButton[active="true"] {{
            background: #101B28;
            border-color: #37F2FF;
            color: #FFFFFF;
        }}

        QWidget#PluginSubnav {{
            background: transparent;
        }}

        QPushButton#SubNavButton {{
            text-align: left;
            background: transparent;
            border: 1px solid transparent;
            border-radius: 7px;
            padding: 8px 10px;
            color: #A8B0BC;
            font-size: 13px;
            font-weight: 600;
        }}

        QPushButton#SubNavButton:hover {{
            background: #0E1621;
            border-color: #273140;
            color: #F3F6FF;
        }}

        QPushButton#SubNavButton[active="true"] {{
            background: #101B28;
            border-color: #FF4FD8;
            color: #FFFFFF;
        }}

        QMenu {{
            background: #080B12;
            border: 1px solid #273140;
            color: #F3F6FF;
            padding: 6px;
        }}

        QMenu::item {{
            background: transparent;
            border-radius: 6px;
            padding: 8px 28px 8px 12px;
        }}

        QMenu::item:selected {{
            background: #14383F;
            color: #FFFFFF;
        }}

        QMenu::item:disabled {{
            color: #687180;
        }}

        QMenu::separator {{
            height: 1px;
            background: #273140;
            margin: 5px 4px;
        }}

        QFrame#ModuleCard, QFrame#NeonPanel {{
            background: #0D121B;
            border: 1px solid #273140;
            border-radius: 10px;
        }}

        QLabel#CardTitle {{
            font-family: "{TITLE_FONT}";
            font-size: 24px;
            font-weight: 700;
            color: #F3F6FF;
        }}

        QLabel#StatusPill {{
            background: #0A0B12;
            border: 1px solid #273140;
            border-radius: 8px;
            padding: 7px 10px;
            color: #C7D0DD;
            font-weight: 600;
        }}

        QLabel#ModuleStatusText {{
            color: #D9E4EF;
            font-size: 13px;
            font-weight: 600;
            padding-top: 4px;
        }}

        QLineEdit, QKeySequenceEdit, QComboBox, QSpinBox {{
            background: #0B111A;
            border: 1px solid #273140;
            border-radius: 8px;
            padding: 9px 10px;
            color: #F3F6FF;
            min-height: 20px;
        }}

        QLineEdit:focus, QKeySequenceEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border-color: #37F2FF;
            background: #0D1621;
        }}

        QKeySequenceEdit[recording="true"] {{
            background: #10242A;
            border: 1px solid #37F2FF;
            color: #FFFFFF;
        }}

        QLabel#CaptureStatus {{
            background: #0B111A;
            border: 1px solid #273140;
            border-radius: 8px;
            padding: 8px 10px;
            color: #A8B0BC;
            font-weight: 600;
        }}

        QLabel#CaptureStatus[recording="true"] {{
            background: #10242A;
            border-color: #37F2FF;
            color: #37F2FF;
        }}

        QListWidget {{
            background: #0B111A;
            border: 1px solid #273140;
            border-radius: 8px;
            padding: 8px;
            color: #F3F6FF;
        }}

        QListWidget::item {{
            border-radius: 6px;
            padding: 9px 10px;
        }}

        QListWidget::item:hover {{
            background: #111B28;
            color: #FFFFFF;
        }}

        QListWidget::item:selected {{
            background: #142632;
            color: #FFFFFF;
            border: 1px solid #37F2FF;
        }}

        QCheckBox {{
            spacing: 8px;
            color: #D9E4EF;
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 5px;
            border: 1px solid #596373;
            background: #0B111A;
        }}

        QCheckBox::indicator:checked {{
            background: #14383F;
            border-color: #37F2FF;
        }}

        QTabWidget::pane {{
            border: 1px solid #273140;
            border-radius: 8px;
            background: #0D121B;
        }}

        QTabBar::tab {{
            background: #0B111A;
            border: 1px solid #273140;
            padding: 9px 14px;
            color: #A8B0BC;
        }}

        QTabBar::tab:selected {{
            color: #FFFFFF;
            border-color: #37F2FF;
            background: #101B28;
        }}

        QHeaderView::section {{
            background: #101722;
            color: #D9E4EF;
            border: 0;
            border-bottom: 1px solid #273140;
            padding: 8px;
            font-weight: 700;
        }}
        """
    )


def _load_optional_fonts() -> None:
    # Future-ready: drop .ttf/.otf files in assets/fonts and they will be registered.
    # The current build uses Windows fallbacks so the app remains portable today.
    try:
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        fonts = root / "assets" / "fonts"
        if not fonts.exists():
            return
        for file in fonts.glob("*.*"):
            if file.suffix.lower() in {".ttf", ".otf"}:
                QFontDatabase.addApplicationFont(str(file))
    except Exception:
        pass
