from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


def apply_theme(app: QApplication) -> None:
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(
        """
        QWidget {
            background: #101317;
            color: #e9eef3;
            font-size: 14px;
        }

        QLabel {
            background: transparent;
        }

        QMainWindow, QStackedWidget {
            background: #101317;
        }

        QScrollArea#PageScroll {
            background: transparent;
            border: 0;
        }

        QScrollArea#PageScroll > QWidget > QWidget {
            background: transparent;
        }

        QScrollBar:vertical {
            background: transparent;
            width: 12px;
            margin: 2px;
        }

        QScrollBar::handle:vertical {
            background: #303946;
            border-radius: 5px;
            min-height: 36px;
        }

        QScrollBar::handle:vertical:hover {
            background: #475467;
        }

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0;
            border: 0;
            background: transparent;
        }

        QLabel#PageTitle {
            font-size: 28px;
            font-weight: 700;
            color: #f4f8fb;
        }

        QLabel#SectionTitle {
            font-size: 18px;
            font-weight: 700;
            color: #f4f8fb;
        }

        QLabel#Muted {
            color: #9aa4af;
        }

        QFrame#Sidebar {
            background: #171b20;
            border-right: 1px solid #252c35;
        }

        QPushButton {
            background: #242b34;
            border: 1px solid #303946;
            border-radius: 8px;
            padding: 10px 14px;
            color: #e9eef3;
            font-weight: 600;
        }

        QPushButton:hover {
            background: #2d3641;
            border-color: #475467;
        }

        QPushButton:pressed {
            background: #1f252d;
        }

        QPushButton#PrimaryButton {
            background: #2f8f72;
            border-color: #47d6a7;
            color: #ffffff;
        }

        QPushButton#PrimaryButton:hover {
            background: #36a987;
        }

        QPushButton#NavButton {
            text-align: left;
            background: transparent;
            border: 0;
            border-radius: 8px;
            padding: 11px 14px;
            color: #b7c1cc;
        }

        QPushButton#NavButton:hover {
            background: #222832;
            color: #ffffff;
        }

        QPushButton#NavButton[active="true"] {
            background: #26313d;
            color: #ffffff;
        }

        QMenu {
            background: #11161c;
            border: 1px solid #303946;
            color: #e9eef3;
            padding: 6px;
        }

        QMenu::item {
            background: transparent;
            border-radius: 6px;
            padding: 8px 28px 8px 12px;
        }

        QMenu::item:selected {
            background: #2f8f72;
            color: #ffffff;
        }

        QMenu::item:disabled {
            color: #6f7b87;
        }

        QMenu::separator {
            height: 1px;
            background: #303946;
            margin: 5px 4px;
        }

        QFrame#ModuleCard {
            background: #1d232b;
            border: 1px solid #2b3440;
            border-radius: 8px;
        }

        QLabel#CardTitle {
            font-size: 22px;
            font-weight: 700;
            color: #f4f8fb;
        }

        QLabel#StatusPill {
            background: #11161c;
            border: 1px solid #2f3945;
            border-radius: 8px;
            padding: 5px 9px;
            color: #cbd5df;
        }

        QLabel#ModuleStatusText {
            color: #d8e4ed;
            font-size: 13px;
            font-weight: 600;
            padding-top: 4px;
        }

        QLineEdit, QKeySequenceEdit {
            background: #171d24;
            border: 1px solid #303946;
            border-radius: 8px;
            padding: 9px 10px;
            color: #f4f8fb;
        }

        QKeySequenceEdit[recording="true"] {
            background: #12261f;
            border: 1px solid #47d6a7;
            color: #ffffff;
        }

        QLabel#CaptureStatus {
            background: #151b22;
            border: 1px solid #2b3440;
            border-radius: 8px;
            padding: 8px 10px;
            color: #aab6c2;
            font-weight: 600;
        }

        QLabel#CaptureStatus[recording="true"] {
            background: #12261f;
            border-color: #47d6a7;
            color: #93e6c6;
        }

        QListWidget {
            background: #171d24;
            border: 1px solid #303946;
            border-radius: 8px;
            padding: 8px;
            color: #e9eef3;
        }

        QListWidget::item {
            border-radius: 6px;
            padding: 9px 10px;
        }

        QListWidget::item:hover {
            background: #242d37;
        }

        QListWidget::item:selected {
            background: #263f4b;
            color: #ffffff;
        }

        QCheckBox {
            spacing: 8px;
            color: #d9e1e8;
        }

        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 5px;
            border: 1px solid #475467;
            background: #171d24;
        }

        QCheckBox::indicator:checked {
            background: #2f8f72;
            border-color: #47d6a7;
        }

        QTableWidget {
            background: #171d24;
            border: 1px solid #2b3440;
            border-radius: 8px;
            gridline-color: #27313b;
            selection-background-color: #26313d;
            outline: 0;
        }

        QTableWidget::item {
            padding: 7px 8px;
        }

        QHeaderView::section {
            background: #202731;
            color: #d9e1e8;
            border: 0;
            border-bottom: 1px solid #303946;
            padding: 8px;
            font-weight: 700;
        }
        """
    )
