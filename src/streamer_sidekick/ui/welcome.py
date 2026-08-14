"""Diálogo de boas-vindas, mostrado uma vez na primeira execução."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


_ITEMS = [
    ("Marcador", "anote eventos da live com horário — ótimo para cortar os melhores momentos depois."),
    ("Contador", "overlays de contador transparentes para o OBS, com hotkeys e presets."),
    ("Atalhos", "hotkeys globais que funcionam mesmo com o jogo em foco."),
    ("Plugins (+)", "instale ferramentas extras direto do card \"+\" na aba Plugins."),
    ("Ajuda", "explica cada ferramenta — e os plugins que você instalar aparecem lá também."),
]


class WelcomeDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Bem-vindo")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 22)
        layout.setSpacing(14)

        title = QLabel("Bem-vindo ao Streamer Sidekick")
        title.setObjectName("PageTitle")
        title.setStyleSheet("font-size: 26px;")
        title.setWordWrap(True)
        subtitle = QLabel("Um hub de ferramentas rápidas para a sua live. Um tour de 10 segundos:")
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        for name, desc in _ITEMS:
            row = QHBoxLayout()
            row.setSpacing(10)
            bullet = QLabel("◆")
            bullet.setStyleSheet("color: #37F2FF; font-size: 14px;")
            text = QLabel(
                f"<span style='color:#F3F6FF'><b>{name}</b></span>"
                f"<span style='color:#A8B0BC'> — {desc}</span>"
            )
            text.setWordWrap(True)
            row.addWidget(bullet, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(text, 1)
            layout.addLayout(row)

        actions = QHBoxLayout()
        actions.addStretch(1)
        start = QPushButton("Começar")
        start.setObjectName("PrimaryButton")
        start.clicked.connect(self.accept)
        actions.addWidget(start)
        layout.addLayout(actions)
