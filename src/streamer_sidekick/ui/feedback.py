"""A janela de feedback da aba Sobre.

Assunto, mensagem, e o contexto que vai junto mostrado por inteiro -- o
usuário vê exatamente o que está mandando. "Abrir no Gmail" leva para a tela
de escrever com tudo preenchido; "Outro e-mail" usa o cliente do sistema.
"""
from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QMessageBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from streamer_sidekick.core import feedback
from streamer_sidekick.ui import tokens


class FeedbackDialog(QDialog):
    def __init__(
        self,
        versao: str,
        plugins: Sequence[tuple[str, str]] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.versao = versao
        self.plugins = list(plugins)

        self.setWindowTitle("Enviar feedback")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        title = QLabel("Enviar feedback")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        hint = QLabel(
            "Bug, ideia, elogio, reclamação — tudo vale. Ao enviar, abre o seu "
            "Gmail com o e-mail pronto; você só confirma lá."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.subject = QLineEdit()
        self.subject.setPlaceholderText("Ex.: o contador não abre…")
        subject_label = QLabel("Assunto")
        subject_label.setBuddy(self.subject)
        layout.addWidget(subject_label)
        layout.addWidget(self.subject)

        self.message = QPlainTextEdit()
        self.message.setAccessibleName("Mensagem")
        message_label = QLabel("Mensagem")
        message_label.setBuddy(self.message)
        layout.addWidget(message_label)
        self.message.setPlaceholderText(
            "O que aconteceu? O que você esperava? Se for um bug, o que "
            "apareceu na tela?"
        )
        self.message.setMinimumHeight(160)
        layout.addWidget(self.message)

        context_title = QLabel("Vai junto, para eu conseguir te ajudar:")
        context_title.setObjectName("Muted")
        layout.addWidget(context_title)
        context = QLabel(feedback.contexto(versao, self.plugins).replace("—\n", ""))
        context.setObjectName("Caption")
        context.setStyleSheet(
            f"background: {tokens.hex_('surface-raised')}; border-radius: {tokens.RADII['sm']}px;"
            " padding: 10px 12px;"
        )
        context.setWordWrap(True)
        context.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(context)

        buttons = QHBoxLayout()
        other = QPushButton("Outro e-mail")
        other.setToolTip("Usa o programa de e-mail padrão do sistema, em vez do Gmail.")
        other.clicked.connect(self._open_mailto)
        buttons.addWidget(other)
        buttons.addStretch(1)
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        send = QPushButton("Abrir no Gmail")
        send.setObjectName("PrimaryButton")
        send.setDefault(True)
        send.clicked.connect(self._open_gmail)
        buttons.addWidget(send)
        layout.addLayout(buttons)

        # Sem mensagem não há o que mandar: os dois envios esperam o texto.
        self._send_buttons = (send, other)
        self.message.textChanged.connect(self._sync_send)
        self._sync_send()

        self.subject.setFocus()

    def _sync_send(self) -> None:
        has_text = bool(self.message.toPlainText().strip())
        for button in self._send_buttons:
            button.setEnabled(has_text)
            button.setToolTip("" if has_text else "Escreva a mensagem primeiro.")

    # -- destinos ---------------------------------------------------------
    def _open(self, url: str) -> None:
        if QDesktopServices.openUrl(QUrl(url)):
            self.accept()
            return
        QMessageBox.warning(
            self,
            "Enviar feedback",
            "Não consegui abrir o navegador nem o e-mail. Copie a mensagem e envie para "
            f"{feedback.DESTINATARIO}.",
        )

    def _open_gmail(self) -> None:
        self._open(feedback.gmail_url(
            self.subject.text(), self.message.toPlainText(), self.versao, self.plugins
        ))

    def _open_mailto(self) -> None:
        self._open(feedback.mailto_url(
            self.subject.text(), self.message.toPlainText(), self.versao, self.plugins
        ))
