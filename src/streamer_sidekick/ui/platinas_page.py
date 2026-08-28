"""Aba 'Platinas': marketplace curado de guias de platina (por jogo).

Mesma engine de plugins, categoria ``platina``. A página tem busca, instala/abre/
remove guias e navega internamente para o guia aberto (sem poluir o menu do hub).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from streamer_sidekick.core.plugins import (
    CATEGORY_PLATINA,
    CatalogEntry,
    InstalledPlugin,
    PluginManager,
)
from streamer_sidekick.ui.plugin_marketplace import _CatalogWorker, _InstallWorker


class _PlatinaRow(QFrame):
    """Linha de um guia no marketplace de platinas."""

    install_requested = Signal(object)  # CatalogEntry
    open_requested = Signal(object)  # CatalogEntry
    remove_requested = Signal(str)  # id

    def __init__(self, entry: CatalogEntry, manager: PluginManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.entry = entry
        self.manager = manager
        self.setObjectName("NeonPanel")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        icon = self._icon_widget()
        if icon is not None:
            layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignVCenter)

        text_box = QVBoxLayout()
        text_box.setSpacing(4)
        self.name_label = QLabel(entry.name)
        self.name_label.setObjectName("CardTitle")
        self.desc_label = QLabel(entry.description)
        self.desc_label.setObjectName("Muted")
        self.desc_label.setWordWrap(True)
        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")
        text_box.addWidget(self.name_label)
        text_box.addWidget(self.desc_label)
        text_box.addWidget(self.status_label)

        self.action_button = QPushButton("")
        self.action_button.setObjectName("PrimaryButton")
        self.action_button.setMinimumWidth(110)
        self.action_button.clicked.connect(self._on_action)

        self.remove_button = QPushButton("Remover")
        self.remove_button.setMinimumWidth(90)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self.entry.id))
        self.remove_button.setVisible(False)

        layout.addLayout(text_box, 1)
        layout.addWidget(self.action_button, 0)
        layout.addWidget(self.remove_button, 0)
        self.refresh_state()

    def _icon_widget(self) -> Optional[QWidget]:
        installed = self.manager.get(self.entry.id)
        path = installed.icon_path if (installed and installed.icon_path) else ""
        if path and Path(path).exists():
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                label = QLabel()
                label.setFixedSize(40, 40)
                label.setPixmap(
                    pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
                )
                return label
        return None

    def _on_action(self) -> None:
        installed = self.manager.get(self.entry.id)
        if installed is None:
            self.install_requested.emit(self.entry)
        elif self.manager.has_update(self.entry):
            self.install_requested.emit(self.entry)  # atualizar = reinstalar
        else:
            self.open_requested.emit(self.entry)

    def refresh_state(self) -> None:
        installed = self.manager.get(self.entry.id)
        incompatibility = self.manager.incompatibility_reason(self.entry)
        self.remove_button.setVisible(installed is not None)
        self.status_label.setStyleSheet("")
        if installed is None and incompatibility:
            self.action_button.setText("Incompatível")
            self.action_button.setEnabled(False)
            self.status_label.setStyleSheet("color: #FF4FD8;")
            self.status_label.setText(incompatibility)
        elif installed is None:
            self.action_button.setText("Instalar")
            self.action_button.setEnabled(True)
            self.status_label.setText("")
        elif self.manager.has_update(self.entry):
            self.action_button.setText("Atualizar")
            self.action_button.setEnabled(True)
            self.status_label.setStyleSheet("color: #B9FF43;")
            self.status_label.setText(f"v{installed.version} → v{self.entry.version}")
        else:
            self.action_button.setText("Abrir")
            self.action_button.setEnabled(True)
            self.status_label.setText(f"Instalado (v{installed.version})")

    def set_busy(self, message: str) -> None:
        self.action_button.setEnabled(False)
        self.action_button.setText("...")
        self.remove_button.setEnabled(False)
        self.status_label.setStyleSheet("")
        self.status_label.setText(message)


class PlatinasPage(QWidget):
    """Página autocontida: navega entre a lista (browse) e o guia aberto."""

    def __init__(self, manager: PluginManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._rows: list[_PlatinaRow] = []
        self._install_worker: Optional[_InstallWorker] = None
        self._active_row: Optional[_PlatinaRow] = None
        self._current_guide: Optional[InstalledPlugin] = None
        self._windows: list[QWidget] = []  # janelas de guia abertas (mantém referência)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        self.browse_index = self.stack.addWidget(self._build_browse())
        self.guide_index = self.stack.addWidget(self._build_guide_host())
        self.stack.setCurrentIndex(self.browse_index)

        self._load_catalog()

    # ---- browse --------------------------------------------------------

    def _build_browse(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 22, 0)
        layout.setSpacing(14)

        title = QLabel("Guias de Platina")
        title.setObjectName("PageTitle")
        intro = QLabel("Marketplace curado de guias por jogo. Pesquise, instale e acompanhe seus troféus.")
        intro.setObjectName("Muted")
        intro.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(intro)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Pesquisar jogo…")
        self.search.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search)

        self.status_label = QLabel("Carregando catálogo…")
        self.status_label.setObjectName("Muted")
        layout.addWidget(self.status_label)

        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(12)
        self.rows_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("PageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.rows_container)
        layout.addWidget(scroll, 1)
        return page

    def _build_guide_host(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 22, 0)
        layout.setSpacing(10)

        header = QHBoxLayout()
        back = QPushButton("← Voltar aos guias")
        back.clicked.connect(self._show_browse)
        header.addWidget(back, 0)
        header.addStretch(1)
        self.popout_button = QPushButton("⤢ Abrir em janela")
        self.popout_button.setToolTip(
            "Abre este guia numa janela separada, que você pode manter aberta "
            "ao lado do jogo ou de outra parte do app."
        )
        self.popout_button.clicked.connect(self._open_in_window)
        header.addWidget(self.popout_button, 0)
        layout.addLayout(header)

        self.guide_host = QWidget()
        self.guide_host_layout = QVBoxLayout(self.guide_host)
        self.guide_host_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.guide_host, 1)
        return page

    def _load_catalog(self) -> None:
        self.status_label.setText("Carregando catálogo…")
        self._catalog_worker = _CatalogWorker(self.manager, CATEGORY_PLATINA)
        self._catalog_worker.loaded.connect(self._on_catalog_loaded)
        self._catalog_worker.start()

    def _on_catalog_loaded(self, entries: list) -> None:
        for row in self._rows:
            row.deleteLater()
        self._rows.clear()
        if not entries:
            self.status_label.setText("Nenhum guia disponível no momento (ou sem conexão).")
            return
        self.status_label.setText(f"{len(entries)} guia(s) no catálogo.")
        for entry in entries:
            row = _PlatinaRow(entry, self.manager)
            row.install_requested.connect(self._on_install_requested)
            row.open_requested.connect(lambda e: self._open_guide_by_id(e.id))
            row.remove_requested.connect(self._on_remove_requested)
            self._rows.append(row)
            self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
        self._apply_filter()

    def _apply_filter(self) -> None:
        query = self.search.text().strip().lower()
        for row in self._rows:
            text = f"{row.entry.name} {row.entry.description}".lower()
            row.setVisible(query in text)

    # ---- instalar / abrir / remover ------------------------------------

    def _on_install_requested(self, entry: CatalogEntry) -> None:
        if self._install_worker is not None and self._install_worker.isRunning():
            return
        row = next((r for r in self._rows if r.entry.id == entry.id), None)
        if row is None:
            return
        self._active_row = row
        row.set_busy("Baixando…")
        worker = _InstallWorker(self.manager, entry)
        worker.progress.connect(row.set_busy)
        worker.finished_ok.connect(self._on_install_finished)
        worker.failed.connect(self._on_install_failed)
        self._install_worker = worker
        worker.start()

    def _on_install_finished(self, plugin: object) -> None:
        for row in self._rows:
            row.refresh_state()
        self._active_row = None
        if isinstance(plugin, InstalledPlugin):
            self._open_guide(plugin)

    def _on_install_failed(self, message: str) -> None:
        if self._active_row is not None:
            self._active_row.refresh_state()
            self._active_row.status_label.setStyleSheet("color: #FF4FD8;")
            self._active_row.status_label.setText(f"Falhou: {message}")
        self._active_row = None

    def _on_remove_requested(self, plugin_id: str) -> None:
        plugin = self.manager.get(plugin_id)
        name = plugin.name if plugin else plugin_id
        answer = QMessageBox.question(
            self, "Remover guia",
            f"Remover {name}? Os arquivos do guia serão apagados "
            "(seu progresso, guardado à parte, é preservado).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.manager.uninstall(plugin_id)
        for row in self._rows:
            row.refresh_state()

    def _open_guide_by_id(self, plugin_id: str) -> None:
        plugin = self.manager.get(plugin_id)
        if plugin is not None:
            self._open_guide(plugin)

    def _open_guide(self, plugin: InstalledPlugin) -> None:
        self._current_guide = plugin
        while self.guide_host_layout.count():
            item = self.guide_host_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.guide_host_layout.addWidget(self._build_guide_widget(plugin))
        self.stack.setCurrentIndex(self.guide_index)

    def _open_in_window(self) -> None:
        """Abre o guia atual numa janela separada e devolve a área principal à lista.

        Assim existe só uma instância viva do guia (a da janela), sem duas cópias
        disputando o mesmo arquivo de progresso — e o hub fica livre para navegar.
        """
        plugin = self._current_guide
        if plugin is None:
            return
        window = QWidget()  # top-level (sem parent) → janela independente
        window.setObjectName("GuideWindow")
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        window.setWindowTitle(f"{plugin.name} — Streamer Sidekick")
        icon = QGuiApplication.windowIcon()
        if not icon.isNull():
            window.setWindowIcon(icon)
        layout = QVBoxLayout(window)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(self._build_guide_widget(plugin))
        window.resize(960, 820)
        window.destroyed.connect(lambda: self._forget_window(window))
        self._windows.append(window)
        window.show()
        window.raise_()
        window.activateWindow()
        self._show_browse()

    def _forget_window(self, window: QWidget) -> None:
        try:
            self._windows.remove(window)
        except ValueError:
            pass

    def _build_guide_widget(self, plugin: InstalledPlugin) -> QWidget:
        if not plugin.loaded or plugin.build_page is None:
            return self._error_widget(plugin, plugin.error or "guia não carregado")
        try:
            return plugin.build_page()
        except Exception as exc:  # guia de terceiro: nao pode derrubar o hub
            return self._error_widget(plugin, str(exc))

    def _error_widget(self, plugin: InstalledPlugin, message: str) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        title = QLabel(plugin.name)
        title.setObjectName("SectionTitle")
        detail = QLabel(f"Não foi possível abrir este guia:\n{message}")
        detail.setObjectName("Muted")
        detail.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(detail)
        layout.addStretch(1)
        return box

    def _show_browse(self) -> None:
        self.stack.setCurrentIndex(self.browse_index)

    def refresh(self) -> None:
        """Chamado ao entrar na aba: recarrega o catálogo se ainda vazio."""
        self._show_browse()
        if not self._rows:
            self._load_catalog()
