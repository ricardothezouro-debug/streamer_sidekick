"""UI de auto-atualização do app: checagem em background e diálogo de update."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from streamer_sidekick.ui.components import NeonProgressBar

from streamer_sidekick.core import app_update
from streamer_sidekick.core.app_update import AppRelease


class AppUpdateCheckWorker(QThread):
    """Checa por atualização do app sem travar a UI."""

    result = Signal(object)  # AppRelease ou None

    def run(self) -> None:
        try:
            release = app_update.check_for_update()
        except Exception:
            release = None
        self.result.emit(release)


class _AppInstallWorker(QThread):
    progress = Signal(str)
    progress_value = Signal(float)  # 0..1 durante o download; -1 = indeterminado
    finished_ok = Signal()
    failed = Signal(str)

    def __init__(self, release: AppRelease) -> None:
        super().__init__()
        self._release = release

    def run(self) -> None:
        def report(message: str, fraction) -> None:
            self.progress.emit(message)
            self.progress_value.emit(fraction if fraction is not None else -1.0)

        try:
            app_update.download_and_apply(self._release, progress=report)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished_ok.emit()


class AppUpdateDialog(QDialog):
    """Mostra a versão nova + novidades e aplica a atualização.

    ``on_quit`` é chamado após o updater ser disparado, para o app encerrar e
    liberar os arquivos (o updater espera o processo sair antes de copiar).
    """

    def __init__(
        self,
        release: AppRelease,
        on_quit: Callable[[], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.release = release
        self._on_quit = on_quit
        self._worker: Optional[_AppInstallWorker] = None

        self.setWindowTitle("Atualização disponível")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        title = QLabel(f"Streamer Sidekick {release.version} disponível")
        title.setObjectName("PageTitle")
        title.setWordWrap(True)
        current = QLabel(f"Você está na versão {app_update.current_version()}.")
        current.setObjectName("Muted")
        layout.addWidget(title)
        layout.addWidget(current)

        if release.notes:
            notes_title = QLabel("Novidades")
            notes_title.setObjectName("SectionTitle")
            # Notas longas rolam dentro da caixa: os botões nunca saem da tela.
            notes = QTextBrowser()
            notes.setPlainText(release.notes)
            notes.setOpenExternalLinks(True)
            notes.setMaximumHeight(240)
            notes.setMinimumHeight(64)
            layout.addWidget(notes_title)
            layout.addWidget(notes)

        self.progress_bar = NeonProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        actions = QHBoxLayout()
        self.releases_button = QPushButton("Abrir página de releases")
        self.releases_button.setObjectName("GhostButton")
        self.releases_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/ricardothezouro-debug/streamer_sidekick/releases/latest"))
        )
        self.releases_button.setVisible(False)
        actions.addWidget(self.releases_button)
        actions.addStretch(1)
        self.later_button = QPushButton("Depois")
        self.later_button.clicked.connect(self.reject)
        self.update_button = QPushButton("Atualizar agora")
        self.update_button.setObjectName("PrimaryButton")
        self.update_button.clicked.connect(self._start_update)
        actions.addWidget(self.later_button)
        actions.addWidget(self.update_button)
        layout.addLayout(actions)

    def _start_update(self) -> None:
        if not app_update.can_self_update():
            QMessageBox.information(
                self,
                "Atualização",
                "A atualização automática só funciona no app empacotado "
                "(portable no Windows, .app no macOS).\n\n"
                "Baixe a versão nova manualmente na página de releases do projeto "
                "(ou, rodando do código, use git pull).",
            )
            self.releases_button.setVisible(True)
            return

        self.update_button.setEnabled(False)
        self.later_button.setEnabled(False)
        self.status_label.setText("Iniciando…")
        self.progress_bar.setVisible(True)
        self.progress_bar.setIndeterminate(True)  # indeterminado até começar o download

        worker = _AppInstallWorker(self.release)
        worker.progress.connect(self.status_label.setText)
        worker.progress_value.connect(self._on_progress_value)
        worker.finished_ok.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        self._worker = worker
        worker.start()

    def _on_progress_value(self, fraction: float) -> None:
        if fraction < 0:
            # Fase sem porcentagem: barra "correndo" (animação indeterminada).
            self.progress_bar.setIndeterminate(True)
        else:
            self.progress_bar.setValue(fraction * 100)

    def _on_finished(self) -> None:
        # Updater disparado: encerra o app para liberar os arquivos.
        self.progress_bar.setIndeterminate(True)
        self.status_label.setText("Aplicando atualização… o app vai reabrir sozinho.")
        self._on_quit()

    def _on_failed(self, message: str) -> None:
        self.update_button.setEnabled(True)
        self.later_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(
            "Não foi possível atualizar. Verifique a conexão e tente de novo, "
            "ou baixe a versão nova na página de releases."
        )
        self.status_label.setToolTip(f"Detalhe: {message}")
        self.releases_button.setVisible(True)

    def _busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def reject(self) -> None:  # Esc e "Depois"
        if self._busy():
            return  # não deixa fechar no meio do download/aplicação
        super().reject()

    def closeEvent(self, event) -> None:  # o X da janela
        if self._busy():
            event.ignore()
            return
        super().closeEvent(event)


class AppUpdatedDialog(QDialog):
    """Confirmação neon mostrada uma vez após o app ser atualizado."""

    def __init__(self, version: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Atualizado")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        title = QLabel(f"Atualizado para a v{version}")
        title.setObjectName("PageTitle")
        title.setWordWrap(True)
        message = QLabel(
            "O Streamer Sidekick foi atualizado com sucesso. Confira as novidades na "
            "tela Sobre e bons streams!"
        )
        message.setObjectName("Muted")
        message.setWordWrap(True)

        row = QHBoxLayout()
        row.addStretch(1)
        ok = QPushButton("Fechar")
        ok.setObjectName("PrimaryButton")
        ok.clicked.connect(self.accept)
        row.addWidget(ok)

        layout.addWidget(title)
        layout.addWidget(message)
        layout.addLayout(row)
