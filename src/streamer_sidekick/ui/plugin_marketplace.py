"""Dialogo de instalacao de plugins (o "+ " da secao Plugins).

Busca o catalogo remoto e lista cada plugin com um botao cujo estado reflete a
situacao: Instalar / Instalado / Atualizar. Download e instalacao rodam em
threads separadas para nao travar a interface.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from streamer_sidekick.core.plugins import CATEGORY_TOOL, CatalogEntry, PluginManager


class _CatalogWorker(QThread):
    loaded = Signal(list)

    def __init__(self, manager: PluginManager, category: str = CATEGORY_TOOL) -> None:
        super().__init__()
        self._manager = manager
        self._category = category

    def run(self) -> None:
        try:
            entries = self._manager.fetch_catalog(self._category)
        except Exception:
            entries = []
        self.loaded.emit(entries)


class _InstallWorker(QThread):
    progress = Signal(str)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, manager: PluginManager, entry: CatalogEntry) -> None:
        super().__init__()
        self._manager = manager
        self._entry = entry

    def run(self) -> None:
        try:
            plugin = self._manager.install(self._entry, progress=self.progress.emit)
        except Exception as exc:  # rede/zip/import: reporta a mensagem ao usuario
            self.failed.emit(str(exc))
            return
        self.finished_ok.emit(plugin)


class _PluginRow(QFrame):
    """Uma linha do catalogo com nome, descricao e botao de acao."""

    install_requested = Signal(object)  # CatalogEntry
    remove_requested = Signal(str)  # plugin id

    def __init__(self, entry: CatalogEntry, manager: PluginManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.entry = entry
        self.manager = manager
        self.setObjectName("NeonPanel")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        text_box = QVBoxLayout()
        text_box.setSpacing(4)
        self.name_label = QLabel(entry.name)
        self.name_label.setObjectName("CardTitle")
        self.desc_label = QLabel(entry.description)
        self.desc_label.setObjectName("Muted")
        self.desc_label.setWordWrap(True)
        self.changelog_label = QLabel("")
        self.changelog_label.setObjectName("Muted")
        self.changelog_label.setWordWrap(True)
        self.changelog_label.setStyleSheet("color: #B9FF43;")
        self.changelog_label.setVisible(False)
        text_box.addWidget(self.name_label)
        text_box.addWidget(self.desc_label)
        text_box.addWidget(self.changelog_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")

        self.action_button = QPushButton("")
        self.action_button.setObjectName("PrimaryButton")
        self.action_button.setMinimumWidth(120)
        self.action_button.clicked.connect(lambda: self.install_requested.emit(self.entry))

        self.remove_button = QPushButton("Remover")
        self.remove_button.setMinimumWidth(96)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self.entry.id))
        self.remove_button.setVisible(False)

        layout.addLayout(text_box, 1)
        layout.addWidget(self.status_label, 0)
        layout.addWidget(self.action_button, 0)
        layout.addWidget(self.remove_button, 0)

        self.refresh_state()

    def refresh_state(self) -> None:
        installed = self.manager.get(self.entry.id)
        self.remove_button.setVisible(installed is not None)
        self.remove_button.setEnabled(installed is not None)
        incompatibility = self.manager.incompatibility_reason(self.entry)
        if installed is None and incompatibility:
            self.action_button.setText("Incompatível")
            self.action_button.setEnabled(False)
            self.status_label.setText("")
            self.changelog_label.setStyleSheet("color: #FF4FD8;")
            self.changelog_label.setText(incompatibility)
            self.changelog_label.setVisible(True)
        elif installed is None:
            self.action_button.setText("Instalar")
            self.action_button.setEnabled(True)
            self.status_label.setText("")
            self.changelog_label.setVisible(False)
        elif self.manager.has_update(self.entry):
            self.action_button.setText("Atualizar")
            self.action_button.setEnabled(True)
            self.status_label.setText(f"v{installed.version} → v{self.entry.version}")
            self.status_label.setStyleSheet("color: #B9FF43;")
            if self.entry.changelog:
                self.changelog_label.setText(f"Novidades: {self.entry.changelog}")
                self.changelog_label.setVisible(True)
            else:
                self.changelog_label.setVisible(False)
        else:
            self.action_button.setText("Instalado")
            self.action_button.setEnabled(False)
            self.status_label.setText(f"v{installed.version}")
            self.status_label.setStyleSheet("")
            self.changelog_label.setVisible(False)

    def set_busy(self, message: str) -> None:
        self.action_button.setEnabled(False)
        self.action_button.setText("...")
        self.remove_button.setEnabled(False)
        self.status_label.setStyleSheet("")
        self.status_label.setText(message)


class PluginMarketplaceDialog(QDialog):
    """Marketplace de plugins. Emite ``plugin_installed`` a cada instalacao."""

    plugin_installed = Signal(object)  # InstalledPlugin
    plugin_removed = Signal(str)  # plugin id

    def __init__(self, manager: PluginManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._rows: list[_PluginRow] = []
        self._install_worker: Optional[_InstallWorker] = None
        self._active_row: Optional[_PluginRow] = None

        self.setWindowTitle("Instalar plugins")
        self.setMinimumSize(560, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        title = QLabel("Plugins disponíveis")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Baixados direto do GitHub. Instale apenas plugins de fontes confiáveis.")
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.status_label = QLabel("Carregando catálogo...")
        self.status_label.setObjectName("Muted")
        layout.addWidget(self.status_label)

        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(12)
        self.rows_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.rows_container)
        layout.addWidget(scroll, 1)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_button = QPushButton("Fechar")
        close_button.clicked.connect(self.accept)
        close_row.addWidget(close_button)
        layout.addLayout(close_row)

        self._catalog_worker = _CatalogWorker(manager)
        self._catalog_worker.loaded.connect(self._on_catalog_loaded)
        self._catalog_worker.start()

    def _on_catalog_loaded(self, entries: list) -> None:
        if not entries:
            self.status_label.setText("Nenhum plugin disponível no momento (ou sem conexão).")
            return
        self.status_label.setText(f"{len(entries)} plugin(s) no catálogo.")
        for entry in entries:
            row = _PluginRow(entry, self.manager)
            row.install_requested.connect(self._on_install_requested)
            row.remove_requested.connect(self._on_remove_requested)
            self._rows.append(row)
            self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)

    def _on_remove_requested(self, plugin_id: str) -> None:
        if self._install_worker is not None and self._install_worker.isRunning():
            return
        plugin = self.manager.get(plugin_id)
        name = plugin.name if plugin is not None else plugin_id
        answer = QMessageBox.question(
            self,
            "Remover plugin",
            f"Remover {name}? Os arquivos do plugin serão apagados.\n"
            "A configuração pessoal dele (fora da pasta do plugin) é preservada.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if not self.manager.uninstall(plugin_id):
            self.status_label.setText("Não foi possível remover o plugin.")
            return
        row = next((r for r in self._rows if r.entry.id == plugin_id), None)
        if row is not None:
            row.refresh_state()
        self.status_label.setText(f"{name} removido.")
        self.plugin_removed.emit(plugin_id)

    def _on_install_requested(self, entry: CatalogEntry) -> None:
        if self._install_worker is not None and self._install_worker.isRunning():
            return
        row = next((r for r in self._rows if r.entry.id == entry.id), None)
        if row is None:
            return
        self._active_row = row
        row.set_busy("Iniciando...")

        worker = _InstallWorker(self.manager, entry)
        worker.progress.connect(row.set_busy)
        worker.finished_ok.connect(self._on_install_finished)
        worker.failed.connect(self._on_install_failed)
        self._install_worker = worker
        worker.start()

    def _on_install_finished(self, plugin: object) -> None:
        if self._active_row is not None:
            self._active_row.refresh_state()
        self._refresh_all_rows()
        self.plugin_installed.emit(plugin)
        self._active_row = None

    def _on_install_failed(self, message: str) -> None:
        if self._active_row is not None:
            self._active_row.status_label.setStyleSheet("color: #FF4FD8;")
            self._active_row.status_label.setText("Falhou")
            self._active_row.action_button.setEnabled(True)
            self._active_row.action_button.setText("Tentar de novo")
        self.status_label.setText(f"Erro na instalação: {message}")
        self._active_row = None

    def _refresh_all_rows(self) -> None:
        for row in self._rows:
            row.refresh_state()
