import os
from typing import Optional
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent, QColor, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QApplication,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
    QKeySequenceEdit,
    QStyle,
)

from streamer_sidekick.core.config import ConfigStore
from streamer_sidekick.core.backup import BackupError, BackupService
from streamer_sidekick.core.diagnostics import DiagnosticItem, DiagnosticService
from streamer_sidekick.core.hotkeys import HotkeyManager
from streamer_sidekick.core.modules import ModuleRegistry
from streamer_sidekick.modules.counter.overlay import CounterOverlay
from streamer_sidekick.modules.counter.service import CounterService
from streamer_sidekick.modules.marker.service import MarkerService
from streamer_sidekick.ui.counter_editor import CounterPresetDialog
from streamer_sidekick.ui.components import ModuleCard

try:
    import pyautogui
except ImportError:
    pyautogui = None


class HubWindow(QMainWindow):
    def __init__(
        self,
        config: ConfigStore,
        hotkeys: HotkeyManager,
        modules: ModuleRegistry,
        marker_service: MarkerService,
        counter_service: CounterService,
    ) -> None:
        super().__init__()
        self.config = config
        self.hotkeys = hotkeys
        self.modules = modules
        self.marker_service = marker_service
        self.counter_service = counter_service
        self.backup_service = BackupService(config, marker_service, counter_service)
        self.diagnostic_service = DiagnosticService(config, hotkeys, marker_service, counter_service)
        self.nav_buttons: dict[str, QPushButton] = {}
        self.marker_active_label: Optional[QLabel] = None
        self.marker_folder_label: Optional[QLabel] = None
        self.marker_last_label: Optional[QLabel] = None
        self.marker_files_list: Optional[QListWidget] = None
        self.marker_recent_list: Optional[QListWidget] = None
        self.marker_event_input: Optional[QLineEdit] = None
        self.marker_new_game_input: Optional[QLineEdit] = None
        self.quick_marker_dialog: Optional["QuickMarkerDialog"] = None
        self.quick_game_dialog: Optional["QuickGameDialog"] = None
        self.counter_folder_label: Optional[QLabel] = None
        self.counter_count_label: Optional[QLabel] = None
        self.counter_status_label: Optional[QLabel] = None
        self.counter_preset_list: Optional[QListWidget] = None
        self.counter_active_list: Optional[QListWidget] = None
        self.counter_overlays: list[CounterOverlay] = []
        self.tray_counter_menu: Optional[QMenu] = None
        self.setting_start_minimized: Optional[QCheckBox] = None
        self.setting_close_to_tray: Optional[QCheckBox] = None
        self.setting_marker_folder: Optional[QLineEdit] = None
        self.setting_counter_folder: Optional[QLineEdit] = None
        self.diagnostic_summary_label: Optional[QLabel] = None
        self.diagnostic_list: Optional[QListWidget] = None
        self._last_diagnostics: list[DiagnosticItem] = []
        self._hotkey_status_messages: list[str] = []
        self._quitting = False

        self.setWindowTitle("Streamer Sidekick")
        self.resize(1160, 720)
        self.setMinimumSize(980, 620)

        self.pages = QStackedWidget()
        self.page_indexes: dict[str, int] = {}
        self.setCentralWidget(self._build_shell())
        self._create_tray()
        self._wire_hotkeys()
        self._select_page("home")

    def _build_shell(self) -> QWidget:
        shell = QWidget()
        layout = QHBoxLayout(shell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = self._build_sidebar()
        content = self._build_content()

        layout.addWidget(sidebar)
        layout.addWidget(content, 1)
        return shell

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(236)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 22, 18, 22)
        layout.setSpacing(8)

        brand = QLabel("Streamer\nSidekick")
        brand.setObjectName("PageTitle")
        layout.addWidget(brand)
        layout.addSpacing(18)

        for page_id, label in [
            ("home", "Inicio"),
            ("marker", "Marcador"),
            ("counter", "Contador"),
            ("hotkeys", "Atalhos"),
            ("diagnostics", "Diagnostico"),
            ("settings", "Configuracoes"),
        ]:
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, item=page_id: self._select_page(item))
            self.nav_buttons[page_id] = button
            layout.addWidget(button)

        layout.addStretch(1)

        footer = QLabel("Base modular v0.1")
        footer.setObjectName("Muted")
        layout.addWidget(footer)
        return sidebar

    def _build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.addWidget(self.pages)

        self._add_page("home", self._home_page())
        self._add_page("marker", self._marker_page())
        self._add_page("counter", self._counter_page())
        self._add_page("hotkeys", self._hotkeys_page())
        self._add_page("diagnostics", self._diagnostics_page())
        self._add_page("settings", self._settings_page())
        return content

    def _add_page(self, page_id: str, widget: QWidget) -> None:
        self.page_indexes[page_id] = self.pages.addWidget(widget)

    def _home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)

        title = QLabel("Hub de auxilios para streamer")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Um lugar para abrir, configurar e expandir suas ferramentas de live.")
        subtitle.setObjectName("Muted")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)

        for index, module in enumerate(self.modules.all()):
            card = ModuleCard(module)
            card.opened.connect(self._select_page)
            row = index // 2
            column = index % 2
            grid.addWidget(card, row, column)

        layout.addLayout(grid)
        layout.addStretch(1)
        return page

    def _marker_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(18)

        title = QLabel("Marcador")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        self.marker_active_label = QLabel()
        self.marker_active_label.setObjectName("SectionTitle")
        self.marker_folder_label = QLabel()
        self.marker_folder_label.setObjectName("Muted")
        self.marker_last_label = QLabel("Ultima marcacao: nenhuma nesta sessao")
        self.marker_last_label.setObjectName("Muted")

        top_actions = QHBoxLayout()
        choose_folder = QPushButton("Trocar pasta")
        choose_folder.clicked.connect(self._choose_marker_folder)
        open_folder = QPushButton("Abrir pasta")
        open_folder.clicked.connect(self._open_marker_folder)
        open_active_file = QPushButton("Abrir arquivo")
        open_active_file.clicked.connect(self._open_active_marker_file)
        new_game = QPushButton("Novo jogo")
        new_game.clicked.connect(self._open_new_game_dialog)
        quick_marker = QPushButton("Marcar agora")
        quick_marker.setObjectName("PrimaryButton")
        quick_marker.clicked.connect(self._open_quick_marker)
        top_actions.addWidget(choose_folder)
        top_actions.addWidget(open_folder)
        top_actions.addWidget(open_active_file)
        top_actions.addWidget(new_game)
        top_actions.addWidget(quick_marker)
        top_actions.addStretch(1)

        event_box = self._marker_event_box()
        recent_box = self._marker_recent_box()
        files_box = self._marker_files_box()

        marker_grid = QGridLayout()
        marker_grid.setHorizontalSpacing(18)
        marker_grid.setVerticalSpacing(18)
        marker_grid.addWidget(event_box, 0, 0)
        marker_grid.addWidget(recent_box, 0, 1)
        marker_grid.setColumnStretch(0, 1)
        marker_grid.setColumnStretch(1, 1)

        layout.addWidget(self.marker_active_label)
        layout.addWidget(self.marker_folder_label)
        layout.addWidget(self.marker_last_label)
        layout.addLayout(top_actions)
        layout.addLayout(marker_grid)
        layout.addWidget(files_box, 1)
        layout.addStretch(1)
        self._refresh_marker_page()
        return page

    def _marker_event_box(self) -> QWidget:
        box = QFrame()
        box.setObjectName("ModuleCard")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        title = QLabel("Registro rapido")
        title.setObjectName("SectionTitle")
        self.marker_event_input = QLineEdit()
        self.marker_event_input.setPlaceholderText("Descreva o evento da live")
        self.marker_event_input.returnPressed.connect(self._save_marker_from_page)

        save = QPushButton("Salvar marcacao")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self._save_marker_from_page)

        row = QHBoxLayout()
        row.addWidget(self.marker_event_input, 1)
        row.addWidget(save)

        new_game_title = QLabel("Novo jogo ou arquivo")
        new_game_title.setObjectName("SectionTitle")
        self.marker_new_game_input = QLineEdit()
        self.marker_new_game_input.setPlaceholderText("Nome do jogo")
        self.marker_new_game_input.returnPressed.connect(self._create_marker_game)
        create = QPushButton("Criar")
        create.clicked.connect(self._create_marker_game)

        game_row = QHBoxLayout()
        game_row.addWidget(self.marker_new_game_input, 1)
        game_row.addWidget(create)

        layout.addWidget(title)
        layout.addLayout(row)
        layout.addWidget(new_game_title)
        layout.addLayout(game_row)
        return box

    def _marker_recent_box(self) -> QWidget:
        box = QFrame()
        box.setObjectName("ModuleCard")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Marcacoes recentes")
        title.setObjectName("SectionTitle")
        refresh = QPushButton("Atualizar")
        refresh.clicked.connect(self._refresh_marker_page)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(refresh)

        self.marker_recent_list = QListWidget()
        self.marker_recent_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.marker_recent_list.setMinimumHeight(190)

        layout.addLayout(header)
        layout.addWidget(self.marker_recent_list, 1)
        return box

    def _marker_files_box(self) -> QWidget:
        box = QFrame()
        box.setObjectName("ModuleCard")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Arquivos de marcacao")
        title.setObjectName("SectionTitle")
        refresh = QPushButton("Atualizar")
        refresh.clicked.connect(self._refresh_marker_page)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(refresh)

        self.marker_files_list = QListWidget()
        self.marker_files_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.marker_files_list.itemDoubleClicked.connect(self._set_marker_active_from_item)

        use_selected = QPushButton("Usar selecionado")
        use_selected.clicked.connect(self._set_marker_active_from_selection)
        hint = QLabel("Clique duas vezes em um arquivo, ou selecione e use o botao.")
        hint.setObjectName("Muted")

        layout.addLayout(header)
        layout.addWidget(self.marker_files_list)
        layout.addWidget(hint)
        layout.addWidget(use_selected)
        return box

    def _counter_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(18)

        title = QLabel("Contador")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        self.counter_count_label = QLabel()
        self.counter_count_label.setObjectName("SectionTitle")
        self.counter_folder_label = QLabel()
        self.counter_folder_label.setObjectName("Muted")
        self.counter_status_label = QLabel("Overlays abertos: 0")
        self.counter_status_label.setObjectName("Muted")

        actions = QHBoxLayout()
        create_preset = QPushButton("Criar preset")
        create_preset.clicked.connect(self._create_counter_preset)
        edit_preset = QPushButton("Editar")
        edit_preset.clicked.connect(self._edit_selected_counter_preset)
        duplicate_preset = QPushButton("Duplicar")
        duplicate_preset.clicked.connect(self._duplicate_selected_counter_preset)
        delete_preset = QPushButton("Excluir")
        delete_preset.clicked.connect(self._delete_selected_counter_preset)
        choose_folder = QPushButton("Trocar pasta")
        choose_folder.clicked.connect(self._choose_counter_folder)
        open_preset = QPushButton("Abrir preset")
        open_preset.setObjectName("PrimaryButton")
        open_preset.clicked.connect(self._open_selected_counter_preset)
        reset = QPushButton("Resetar")
        reset.clicked.connect(self._reset_counter_overlays)
        close = QPushButton("Fechar overlays")
        close.clicked.connect(self._close_counter_overlays)
        actions.addWidget(create_preset)
        actions.addWidget(edit_preset)
        actions.addWidget(duplicate_preset)
        actions.addWidget(delete_preset)
        actions.addWidget(choose_folder)
        actions.addWidget(open_preset)
        actions.addWidget(reset)
        actions.addWidget(close)
        actions.addStretch(1)

        active_box = QFrame()
        active_box.setObjectName("ModuleCard")
        active_layout = QVBoxLayout(active_box)
        active_layout.setContentsMargins(18, 16, 18, 16)
        active_layout.setSpacing(12)

        active_header = QHBoxLayout()
        active_title = QLabel("Contadores ativos")
        active_title.setObjectName("SectionTitle")
        reset_selected = QPushButton("Resetar selecionado")
        reset_selected.clicked.connect(self._reset_selected_counter_overlay)
        close_selected = QPushButton("Fechar selecionado")
        close_selected.clicked.connect(self._close_selected_counter_overlay)
        active_header.addWidget(active_title)
        active_header.addStretch(1)
        active_header.addWidget(reset_selected)
        active_header.addWidget(close_selected)
        self.counter_active_list = QListWidget()
        self.counter_active_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        active_hint = QLabel("Selecione um contador ativo para resetar ou fechar apenas ele.")
        active_hint.setObjectName("Muted")
        active_layout.addLayout(active_header)
        active_layout.addWidget(self.counter_active_list)
        active_layout.addWidget(active_hint)

        presets_box = QFrame()
        presets_box.setObjectName("ModuleCard")
        presets_layout = QVBoxLayout(presets_box)
        presets_layout.setContentsMargins(18, 16, 18, 16)
        presets_layout.setSpacing(12)

        presets_header = QHBoxLayout()
        presets_title = QLabel("Presets")
        presets_title.setObjectName("SectionTitle")
        refresh = QPushButton("Atualizar")
        refresh.clicked.connect(self._refresh_counter_page)
        presets_header.addWidget(presets_title)
        presets_header.addStretch(1)
        presets_header.addWidget(refresh)

        self.counter_preset_list = QListWidget()
        self.counter_preset_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.counter_preset_list.itemDoubleClicked.connect(lambda _: self._open_selected_counter_preset())

        hint = QLabel("Clique duas vezes em um preset para abrir novos overlays sem fechar os atuais.")
        hint.setObjectName("Muted")

        presets_layout.addLayout(presets_header)
        presets_layout.addWidget(self.counter_preset_list)
        presets_layout.addWidget(hint)

        layout.addWidget(self.counter_count_label)
        layout.addWidget(self.counter_folder_label)
        layout.addWidget(self.counter_status_label)
        layout.addLayout(actions)
        layout.addWidget(active_box)
        layout.addWidget(presets_box, 1)
        layout.addStretch(1)
        self._refresh_counter_page()
        return page

    def _hotkeys_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(18)

        title = QLabel("Atalhos globais")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Os conflitos sao bloqueados antes de salvar. O novo padrao evita o antigo choque do Ctrl+Alt+N.")
        subtitle.setObjectName("Muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        panel = QFrame()
        panel.setObjectName("ModuleCard")
        grid = QGridLayout(panel)
        grid.setContentsMargins(18, 16, 18, 16)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        headers = ["Modulo", "Acao", "Atalho", "Ativo", ""]
        for column, header in enumerate(headers):
            label = QLabel(header)
            label.setObjectName("SectionTitle")
            grid.addWidget(label, 0, column)

        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 0)
        grid.setColumnStretch(4, 0)

        for row, binding in enumerate(self.hotkeys.all_bindings(), start=1):
            module_label = QLabel(str(binding["module_id"]))
            action_label = QLabel(str(binding["label"]))
            action_label.setMinimumWidth(260)
            sequence_edit = QKeySequenceEdit(QKeySequence(str(binding["sequence"])))
            sequence_edit.setFixedWidth(210)
            enabled = QCheckBox()
            enabled.setChecked(bool(binding["enabled"]))
            save = QPushButton("Salvar")
            save.setFixedWidth(76)
            save.clicked.connect(
                lambda checked=False, key=str(binding["key"]), editor=sequence_edit, checkbox=enabled: self._save_hotkey(
                    key, editor, checkbox
                )
            )

            grid.addWidget(module_label, row, 0)
            grid.addWidget(action_label, row, 1)
            grid.addWidget(sequence_edit, row, 2)
            grid.addWidget(enabled, row, 3, alignment=Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(save, row, 4)

        layout.addWidget(panel)
        layout.addStretch(1)
        return page

    def _diagnostics_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(18)

        title = QLabel("Diagnostico")
        title.setObjectName("PageTitle")
        self.diagnostic_summary_label = QLabel()
        self.diagnostic_summary_label.setObjectName("Muted")

        actions = QHBoxLayout()
        refresh = QPushButton("Atualizar")
        refresh.clicked.connect(self._refresh_diagnostics_page)
        copy = QPushButton("Copiar relatorio")
        copy.clicked.connect(self._copy_diagnostics_report)
        actions.addWidget(refresh)
        actions.addWidget(copy)
        actions.addStretch(1)

        panel = QFrame()
        panel.setObjectName("ModuleCard")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 16, 18, 16)
        panel_layout.setSpacing(12)

        self.diagnostic_list = QListWidget()
        self.diagnostic_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        panel_layout.addWidget(self.diagnostic_list)

        layout.addWidget(title)
        layout.addWidget(self.diagnostic_summary_label)
        layout.addLayout(actions)
        layout.addWidget(panel, 1)
        self._refresh_diagnostics_page()
        return page

    def _settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(18)

        title = QLabel("Configuracoes")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        behavior_box = QFrame()
        behavior_box.setObjectName("ModuleCard")
        behavior_layout = QVBoxLayout(behavior_box)
        behavior_layout.setContentsMargins(18, 16, 18, 16)
        behavior_layout.setSpacing(12)

        behavior_title = QLabel("Comportamento")
        behavior_title.setObjectName("SectionTitle")
        self.setting_start_minimized = QCheckBox("Iniciar minimizado na bandeja")
        self.setting_start_minimized.setChecked(bool(self.config.get("hub.start_minimized", False)))
        self.setting_close_to_tray = QCheckBox("Ao clicar no X, minimizar para a bandeja")
        self.setting_close_to_tray.setChecked(bool(self.config.get("hub.close_to_tray", True)))
        behavior_layout.addWidget(behavior_title)
        behavior_layout.addWidget(self.setting_start_minimized)
        behavior_layout.addWidget(self.setting_close_to_tray)

        folders_box = QFrame()
        folders_box.setObjectName("ModuleCard")
        folders_layout = QVBoxLayout(folders_box)
        folders_layout.setContentsMargins(18, 16, 18, 16)
        folders_layout.setSpacing(12)

        folders_title = QLabel("Pastas")
        folders_title.setObjectName("SectionTitle")
        self.setting_marker_folder = QLineEdit(str(self.marker_service.folder()))
        self.setting_counter_folder = QLineEdit(str(self.counter_service.presets_folder()))

        marker_row = QHBoxLayout()
        marker_label = QLabel("Marcador")
        marker_label.setMinimumWidth(90)
        marker_button = QPushButton("Escolher")
        marker_button.clicked.connect(self._choose_settings_marker_folder)
        marker_row.addWidget(marker_label)
        marker_row.addWidget(self.setting_marker_folder, 1)
        marker_row.addWidget(marker_button)

        counter_row = QHBoxLayout()
        counter_label = QLabel("Contador")
        counter_label.setMinimumWidth(90)
        counter_button = QPushButton("Escolher")
        counter_button.clicked.connect(self._choose_settings_counter_folder)
        counter_row.addWidget(counter_label)
        counter_row.addWidget(self.setting_counter_folder, 1)
        counter_row.addWidget(counter_button)

        folders_layout.addWidget(folders_title)
        folders_layout.addLayout(marker_row)
        folders_layout.addLayout(counter_row)

        backup_box = QFrame()
        backup_box.setObjectName("ModuleCard")
        backup_layout = QVBoxLayout(backup_box)
        backup_layout.setContentsMargins(18, 16, 18, 16)
        backup_layout.setSpacing(12)

        backup_title = QLabel("Backup")
        backup_title.setObjectName("SectionTitle")
        backup_actions = QHBoxLayout()
        export_backup = QPushButton("Exportar backup")
        export_backup.clicked.connect(self._export_backup)
        restore_backup = QPushButton("Restaurar backup")
        restore_backup.clicked.connect(self._restore_backup)
        backup_actions.addWidget(export_backup)
        backup_actions.addWidget(restore_backup)
        backup_actions.addStretch(1)
        backup_layout.addWidget(backup_title)
        backup_layout.addLayout(backup_actions)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save_button = QPushButton("Salvar configuracoes")
        save_button.setObjectName("PrimaryButton")
        save_button.clicked.connect(self._save_settings)
        save_row.addWidget(save_button)

        layout.addWidget(behavior_box)
        layout.addWidget(folders_box)
        layout.addWidget(backup_box)
        layout.addLayout(save_row)
        layout.addWidget(self._info_block("Dados do app", f"Configuracao central: {self.config.path}"))
        layout.addStretch(1)
        return page

    def _info_block(self, title: str, body: str) -> QWidget:
        box = QFrame()
        box.setObjectName("ModuleCard")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 16, 18, 16)

        heading = QLabel(title)
        heading.setObjectName("SectionTitle")
        text = QLabel(body)
        text.setObjectName("Muted")
        text.setWordWrap(True)

        layout.addWidget(heading)
        layout.addWidget(text)
        return box

    def _select_page(self, page_id: str) -> None:
        if page_id not in self.page_indexes:
            return
        if page_id == "marker":
            self._refresh_marker_page()
        if page_id == "counter":
            self._refresh_counter_page()
        if page_id == "diagnostics":
            self._refresh_diagnostics_page()
        self.pages.setCurrentIndex(self.page_indexes[page_id])
        for item, button in self.nav_buttons.items():
            button.setProperty("active", item == page_id)
            button.style().unpolish(button)
            button.style().polish(button)

    def _refresh_diagnostics_page(self) -> None:
        if self.diagnostic_summary_label is None or self.diagnostic_list is None:
            return

        items = self.diagnostic_service.run()
        overlays = self._live_counter_overlays()
        items.append(DiagnosticItem("ok", "Overlays ativos", f"{len(overlays)} janelas abertas"))
        for message in self._hotkey_status_messages:
            items.append(DiagnosticItem("warn", "Registro de hotkey", message))

        self._last_diagnostics = items
        errors = sum(1 for item in items if item.status == "error")
        warnings = sum(1 for item in items if item.status == "warn")
        ok = sum(1 for item in items if item.status == "ok")

        if errors:
            summary = f"{errors} erros, {warnings} avisos, {ok} ok"
        elif warnings:
            summary = f"{warnings} avisos, {ok} ok"
        else:
            summary = f"Tudo certo: {ok} checagens ok"
        self.diagnostic_summary_label.setText(summary)

        self.diagnostic_list.clear()
        for item in items:
            prefix = {"ok": "OK", "warn": "Aviso", "error": "Erro"}.get(item.status, "Info")
            row = QListWidgetItem(f"{prefix} | {item.title} | {item.detail}")
            row.setToolTip(item.detail)
            if item.status == "error":
                row.setForeground(QColor("#ff7a7a"))
            elif item.status == "warn":
                row.setForeground(QColor("#ffd37a"))
            else:
                row.setForeground(QColor("#93e6c6"))
            self.diagnostic_list.addItem(row)

    def _copy_diagnostics_report(self) -> None:
        if not self._last_diagnostics:
            self._refresh_diagnostics_page()
        QApplication.clipboard().setText(self._diagnostics_report_text())
        QMessageBox.information(self, "Diagnostico", "Relatorio copiado.")

    def _diagnostics_report_text(self) -> str:
        lines = ["Streamer Sidekick - Diagnostico"]
        for item in self._last_diagnostics:
            lines.append(f"{item.status.upper()} | {item.title} | {item.detail}")
        return "\n".join(lines)

    def _save_hotkey(self, key: str, editor: QKeySequenceEdit, checkbox: QCheckBox) -> None:
        sequence = editor.keySequence().toString(QKeySequence.SequenceFormat.NativeText)
        conflict = self.hotkeys.set_binding(key, sequence, checkbox.isChecked())
        if conflict:
            QMessageBox.warning(self, "Conflito de atalho", f"Esse atalho ja esta em uso por: {conflict}")
            return
        self.hotkeys.start_global_hotkeys()
        QMessageBox.information(self, "Atalho salvo", "Atalho atualizado com sucesso.")

    def _create_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), self)
        self.tray.setToolTip("Streamer Sidekick")

        menu = QMenu()
        open_action = QAction("Abrir hub", self)
        open_action.triggered.connect(self._show_from_tray)
        marker_action = QAction("Marcar evento", self)
        marker_action.triggered.connect(self._open_quick_marker)
        new_game_action = QAction("Novo jogo", self)
        new_game_action.triggered.connect(self._open_new_game_dialog)
        self.tray_counter_menu = QMenu("Contadores ativos", self)
        self.tray_counter_menu.aboutToShow.connect(self._refresh_tray_counter_menu)
        reset_counter_action = QAction("Resetar contadores", self)
        reset_counter_action.triggered.connect(self._reset_counter_overlays)
        close_counter_action = QAction("Fechar contadores", self)
        close_counter_action.triggered.connect(self._close_counter_overlays)
        quit_action = QAction("Sair", self)
        quit_action.triggered.connect(self._quit_from_tray)

        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(marker_action)
        menu.addAction(new_game_action)
        menu.addSeparator()
        menu.addMenu(self.tray_counter_menu)
        menu.addAction(reset_counter_action)
        menu.addAction(close_counter_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self._show_from_tray() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    def _wire_hotkeys(self) -> None:
        self.hotkeys.status_changed.connect(self._on_hotkey_status_changed)
        self.hotkeys.register_callback("hub.show", self._show_from_tray)
        self.hotkeys.register_callback("marker.open_event", self._open_quick_marker)
        self.hotkeys.register_callback("marker.new_game", self._open_new_game_dialog)
        self.hotkeys.register_callback("counter.reset_all", self._reset_counter_overlays)
        self.hotkeys.register_callback("counter.close_overlays", self._close_counter_overlays)
        self.hotkeys.start_global_hotkeys()

    def _on_hotkey_status_changed(self, message: str) -> None:
        self._hotkey_status_messages.append(message)
        self._hotkey_status_messages = self._hotkey_status_messages[-8:]
        if self.page_indexes.get("diagnostics") == self.pages.currentIndex():
            self._refresh_diagnostics_page()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_from_tray(self) -> None:
        if self._quitting:
            return
        self._quitting = True
        self.hotkeys.stop_global_hotkeys()
        if self.quick_marker_dialog is not None:
            self.quick_marker_dialog.close()
        if self.quick_game_dialog is not None:
            self.quick_game_dialog.close()
        self._close_counter_overlays()
        self.tray.hide()
        self.close()
        app = QApplication.instance()
        if app is not None:
            app.processEvents()
            app.quit()
        os._exit(0)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._quitting:
            event.accept()
            return
        if self.tray.isVisible() and bool(self.config.get("hub.close_to_tray", True)):
            self.hide()
            event.ignore()
        else:
            event.ignore()
            QTimer.singleShot(0, self._quit_from_tray)

    def _refresh_marker_page(self) -> None:
        if self.marker_active_label is None or self.marker_folder_label is None:
            return

        active_name = self.marker_service.active_file().name
        marker_count = self.marker_service.marker_count()
        self.marker_active_label.setText(f"Arquivo ativo: {active_name}  |  {marker_count} marcacoes")
        self.marker_folder_label.setText(f"Pasta atual: {self.marker_service.folder()}")

        if self.marker_recent_list is not None:
            self.marker_recent_list.clear()
            recent = self.marker_service.recent_markers()
            if recent:
                for line in recent:
                    item = QListWidgetItem(line)
                    item.setToolTip(line)
                    self.marker_recent_list.addItem(item)
            else:
                self.marker_recent_list.addItem("Nenhuma marcacao salva neste arquivo.")

        if self.marker_files_list is None:
            return
        self.marker_files_list.clear()
        current = self.marker_service.active_file().name
        for path in self.marker_service.files():
            label = f"> {path.name}" if path.name == current else path.name
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, path.name)
            self.marker_files_list.addItem(item)

    def _choose_marker_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta de marcacoes", str(self.marker_service.folder()))
        if not folder:
            return
        self.config.set("marker.folder", folder)
        self._refresh_marker_page()

    def _open_marker_folder(self) -> None:
        self._open_path(self.marker_service.folder(), "pasta de marcacoes")

    def _open_active_marker_file(self) -> None:
        path = self.marker_service.active_file()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, "Marcador", f"Nao foi possivel preparar o arquivo ativo: {exc}")
            return
        self._open_path(path, "arquivo ativo")

    def _open_path(self, path: Path, label: str) -> None:
        try:
            os.startfile(str(path))
        except (AttributeError, OSError) as exc:
            QMessageBox.warning(self, "Marcador", f"Nao foi possivel abrir {label}: {exc}")

    def _save_marker_from_page(self) -> None:
        if self.marker_event_input is None:
            return
        text = self.marker_event_input.text().strip()
        if not text:
            return
        target = self.marker_service.save_marker(text)
        self.marker_event_input.clear()
        if self.marker_last_label is not None:
            self.marker_last_label.setText(f"Ultima marcacao salva em: {target.name}")
        self._refresh_marker_page()

    def _create_marker_game(self) -> None:
        if self.marker_new_game_input is None:
            return
        name = self.marker_new_game_input.text().strip()
        if not name:
            return
        target = self.marker_service.create_game(name)
        self.marker_new_game_input.clear()
        if self.marker_last_label is not None:
            self.marker_last_label.setText(f"Arquivo ativo criado: {target.name}")
        self._refresh_marker_page()

    def _set_marker_active_from_item(self, item: QListWidgetItem) -> None:
        name = item.data(Qt.ItemDataRole.UserRole)
        if not name:
            return
        self.marker_service.set_active_file(str(name))
        self._refresh_marker_page()

    def _set_marker_active_from_selection(self) -> None:
        if self.marker_files_list is None:
            return
        items = self.marker_files_list.selectedItems()
        if not items:
            return
        self._set_marker_active_from_item(items[0])

    def _open_quick_marker(self) -> None:
        if self.quick_marker_dialog is not None and self.quick_marker_dialog.isVisible():
            self.quick_marker_dialog.raise_()
            self.quick_marker_dialog.activateWindow()
            return

        self.quick_marker_dialog = QuickMarkerDialog(self.marker_service, self)
        self.quick_marker_dialog.saved.connect(self._on_quick_marker_saved)
        self.quick_marker_dialog.finished.connect(lambda _: self._clear_quick_marker_dialog())
        self.quick_marker_dialog.show()
        self.quick_marker_dialog.focus_text_input()

    def _open_new_game_dialog(self) -> None:
        if self.quick_game_dialog is not None and self.quick_game_dialog.isVisible():
            self.quick_game_dialog.raise_()
            self.quick_game_dialog.activateWindow()
            return

        self.quick_game_dialog = QuickGameDialog(self.marker_service, self)
        self.quick_game_dialog.created.connect(self._on_game_created)
        self.quick_game_dialog.finished.connect(lambda _: self._clear_quick_game_dialog())
        self.quick_game_dialog.show()
        self.quick_game_dialog.focus_text_input()

    def _on_quick_marker_saved(self, file_name: str) -> None:
        if self.marker_last_label is not None:
            self.marker_last_label.setText(f"Ultima marcacao salva em: {file_name}")
        self._refresh_marker_page()

    def _on_game_created(self, file_name: str) -> None:
        if self.marker_last_label is not None:
            self.marker_last_label.setText(f"Arquivo ativo criado: {file_name}")
        self._refresh_marker_page()

    def _clear_quick_marker_dialog(self) -> None:
        self.quick_marker_dialog = None

    def _clear_quick_game_dialog(self) -> None:
        self.quick_game_dialog = None

    def _refresh_counter_page(self) -> None:
        if self.counter_count_label is None or self.counter_folder_label is None:
            return

        presets = self.counter_service.presets()
        self.counter_count_label.setText(f"Presets encontrados: {len(presets)}")
        self.counter_folder_label.setText(f"Pasta de presets: {self.counter_service.presets_folder()}")
        self._update_counter_status()

        if self.counter_preset_list is None:
            return
        self.counter_preset_list.clear()
        for path in presets:
            item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.counter_preset_list.addItem(item)

    def _choose_counter_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta de presets", str(self.counter_service.presets_folder()))
        if not folder:
            return
        self.counter_service.set_presets_folder(folder)
        self._refresh_counter_page()

    def _choose_settings_marker_folder(self) -> None:
        if self.setting_marker_folder is None:
            return
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta de marcacoes", self.setting_marker_folder.text())
        if folder:
            self.setting_marker_folder.setText(folder)

    def _choose_settings_counter_folder(self) -> None:
        if self.setting_counter_folder is None:
            return
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta de presets", self.setting_counter_folder.text())
        if folder:
            self.setting_counter_folder.setText(folder)

    def _export_backup(self) -> None:
        default_path = Path.home() / self.backup_service.default_file_name()
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar backup",
            str(default_path),
            "Backup do Streamer Sidekick (*.zip)",
        )
        if not target:
            return

        path = Path(target)
        if path.suffix.lower() != ".zip":
            path = path.with_suffix(".zip")

        try:
            summary = self.backup_service.export_backup(path)
        except (BackupError, OSError, ValueError) as exc:
            QMessageBox.warning(self, "Backup", f"Nao foi possivel exportar o backup: {exc}")
            return

        QMessageBox.information(
            self,
            "Backup",
            f"Backup salvo em:\n{path}\n\nMarcacoes: {summary.marker_files}\nArquivos do contador: {summary.counter_files}",
        )

    def _restore_backup(self) -> None:
        source, _ = QFileDialog.getOpenFileName(
            self,
            "Restaurar backup",
            str(Path.home()),
            "Backup do Streamer Sidekick (*.zip)",
        )
        if not source:
            return

        answer = QMessageBox.question(
            self,
            "Restaurar backup",
            "Restaurar esse backup agora? Configuracoes e arquivos com o mesmo nome podem ser sobrescritos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._close_counter_overlays()
        try:
            summary = self.backup_service.restore_backup(Path(source))
        except (BackupError, OSError, ValueError) as exc:
            QMessageBox.warning(self, "Backup", f"Nao foi possivel restaurar o backup: {exc}")
            return

        self.hotkeys.start_global_hotkeys()
        self._sync_settings_inputs()
        self._refresh_marker_page()
        self._refresh_counter_page()
        QMessageBox.information(
            self,
            "Backup",
            f"Backup restaurado.\n\nMarcacoes: {summary.marker_files}\nArquivos do contador: {summary.counter_files}",
        )

    def _sync_settings_inputs(self) -> None:
        if self.setting_start_minimized is not None:
            self.setting_start_minimized.setChecked(bool(self.config.get("hub.start_minimized", False)))
        if self.setting_close_to_tray is not None:
            self.setting_close_to_tray.setChecked(bool(self.config.get("hub.close_to_tray", True)))
        if self.setting_marker_folder is not None:
            self.setting_marker_folder.setText(str(self.marker_service.folder()))
        if self.setting_counter_folder is not None:
            self.setting_counter_folder.setText(str(self.counter_service.presets_folder()))

    def _save_settings(self) -> None:
        if (
            self.setting_start_minimized is None
            or self.setting_close_to_tray is None
            or self.setting_marker_folder is None
            or self.setting_counter_folder is None
        ):
            return

        marker_folder = self.setting_marker_folder.text().strip()
        counter_folder = self.setting_counter_folder.text().strip()

        if marker_folder:
            self.config.set("marker.folder", marker_folder)
        if counter_folder:
            self.counter_service.set_presets_folder(counter_folder)

        self.config.set("hub.start_minimized", self.setting_start_minimized.isChecked())
        self.config.set("hub.close_to_tray", self.setting_close_to_tray.isChecked())

        self._refresh_marker_page()
        self._refresh_counter_page()
        QMessageBox.information(self, "Configuracoes", "Configuracoes salvas.")

    def _open_selected_counter_preset(self) -> None:
        preset_path = self._selected_counter_preset_path()
        if preset_path is None:
            return
        try:
            configs = self.counter_service.load_preset(preset_path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Preset invalido", f"Nao foi possivel abrir o preset: {exc}")
            return

        if not configs:
            QMessageBox.warning(self, "Preset vazio", "Esse arquivo nao tem contadores validos.")
            return

        if not self._can_open_counter_configs(configs):
            return

        linked_markers = self._marker_files_from_configs(configs)
        if len(linked_markers) == 1:
            self.marker_service.set_active_file(next(iter(linked_markers)))
            self._refresh_marker_page()

        save_file = self.counter_service.state_file_for(preset_path)
        for index, config in enumerate(configs):
            overlay = CounterOverlay(config, save_file, index, marker_service=self.marker_service)
            overlay.closed.connect(self._on_counter_overlay_closed)
            overlay.marker_saved.connect(self._on_counter_marker_saved)
            overlay.show()
            self.counter_overlays.append(overlay)
        self._update_counter_status()

    def _create_counter_preset(self) -> None:
        dialog = CounterPresetDialog(
            self,
            preset_name="Novo preset",
            reserved_hotkeys=self._reserved_counter_hotkeys(),
            marker_files=self._marker_file_names(),
            create_marker_file=self._create_marker_file_for_counter,
        )
        if not dialog.exec():
            return

        preset_path = self.counter_service.save_preset(dialog.preset_name(), dialog.counter_configs())
        self._refresh_counter_page()
        self._select_counter_preset(preset_path)

    def _edit_selected_counter_preset(self) -> None:
        preset_path = self._selected_counter_preset_path()
        if preset_path is None:
            return

        try:
            configs = self.counter_service.load_preset(preset_path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Preset invalido", f"Nao foi possivel editar o preset: {exc}")
            return

        dialog = CounterPresetDialog(
            self,
            preset_name=preset_path.stem,
            counters=configs,
            reserved_hotkeys=self._reserved_counter_hotkeys(),
            marker_files=self._marker_file_names(),
            create_marker_file=self._create_marker_file_for_counter,
        )
        if not dialog.exec():
            return

        if dialog.preset_name() != preset_path.stem:
            preset_path.unlink(missing_ok=True)
            self.counter_service.state_file_for(preset_path).unlink(missing_ok=True)
            preset_path = None

        saved_path = self.counter_service.save_preset(dialog.preset_name(), dialog.counter_configs(), preset_path)
        self._refresh_counter_page()
        self._select_counter_preset(saved_path)

    def _duplicate_selected_counter_preset(self) -> None:
        preset_path = self._selected_counter_preset_path()
        if preset_path is None:
            return

        try:
            configs = self.counter_service.load_preset(preset_path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Preset invalido", f"Nao foi possivel duplicar o preset: {exc}")
            return

        copy_name = self._counter_preset_copy_name(preset_path.stem)
        saved_path = self.counter_service.save_preset(copy_name, configs)
        self._refresh_counter_page()
        self._select_counter_preset(saved_path)

    def _counter_preset_copy_name(self, base_name: str) -> str:
        existing = {path.stem.casefold() for path in self.counter_service.presets()}
        candidate = f"{base_name} copia"
        number = 2
        while candidate.casefold() in existing:
            candidate = f"{base_name} copia {number}"
            number += 1
        return candidate

    def _marker_file_names(self) -> list[str]:
        return [path.name for path in self.marker_service.files()]

    def _create_marker_file_for_counter(self, name: str) -> str:
        try:
            return self.marker_service.create_file(name).name
        except OSError as exc:
            QMessageBox.warning(self, "Marcador", f"Nao foi possivel criar o txt: {exc}")
            return ""

    def _can_open_counter_configs(self, configs: list[dict[str, object]]) -> bool:
        if not self._can_open_counter_hotkeys(configs):
            return False

        requested = self._marker_files_from_configs(configs)
        if len(requested) > 1:
            QMessageBox.warning(
                self,
                "Marcadores diferentes",
                "Esse preset tem contadores vinculados a marcadores diferentes. "
                "Abra apenas contadores vinculados ao mesmo txt.",
            )
            return False

        active = self._marker_files_from_overlays()
        if active and requested and active != requested:
            active_name = next(iter(active))
            requested_name = next(iter(requested))
            QMessageBox.warning(
                self,
                "Marcador em uso",
                f"Ja existe contador aberto vinculado a {active_name}. "
                f"Feche esses contadores antes de abrir outro vinculado a {requested_name}.",
            )
            return False

        for marker_file in requested:
            try:
                self.marker_service.create_file(marker_file)
            except OSError as exc:
                QMessageBox.warning(self, "Marcador", f"Nao foi possivel preparar {marker_file}: {exc}")
                return False
        return True

    def _can_open_counter_hotkeys(self, configs: list[dict[str, object]]) -> bool:
        requested: dict[str, tuple[str, str]] = {}
        for index, config in enumerate(configs):
            sequence = str(config.get("hotkey") or "").strip()
            normalized = _normalize_hotkey(sequence)
            if not normalized:
                continue

            title = str(config.get("titulo") or f"Contador {index + 1}")
            if normalized in requested:
                previous_sequence, previous_title = requested[normalized]
                QMessageBox.warning(
                    self,
                    "Hotkey repetida",
                    f"O atalho {previous_sequence} esta repetido em {previous_title} e {title}.",
                )
                return False
            requested[normalized] = (sequence, title)

        if not requested:
            return True

        active = self._counter_hotkeys_from_overlays()
        for normalized, (sequence, title) in requested.items():
            if normalized in active:
                QMessageBox.warning(
                    self,
                    "Hotkey em uso",
                    f"O atalho {sequence} ja esta em uso pelo contador aberto: {active[normalized]}. "
                    "Feche esse contador antes de abrir outro com a mesma hotkey.",
                )
                return False

        global_hotkeys = self._global_hotkeys_for_counter_open()
        for normalized, (sequence, title) in requested.items():
            if normalized in global_hotkeys:
                QMessageBox.warning(
                    self,
                    "Hotkey em uso",
                    f"O atalho {sequence} do contador {title} conflita com o atalho global: {global_hotkeys[normalized]}.",
                )
                return False
        return True

    def _counter_hotkeys_from_overlays(self) -> dict[str, str]:
        hotkeys: dict[str, str] = {}
        for overlay in self._live_counter_overlays():
            sequence = overlay.hotkey()
            normalized = _normalize_hotkey(sequence)
            if normalized:
                hotkeys[normalized] = overlay.windowTitle()
        return hotkeys

    def _global_hotkeys_for_counter_open(self) -> dict[str, str]:
        hotkeys: dict[str, str] = {}
        for binding in self.hotkeys.all_bindings():
            if not binding["enabled"]:
                continue
            normalized = _normalize_hotkey(str(binding["sequence"]))
            if normalized:
                hotkeys[normalized] = str(binding["label"])
        return hotkeys

    def _marker_files_from_configs(self, configs: list[dict[str, object]]) -> set[str]:
        files: set[str] = set()
        for config in configs:
            marker_file = str(config.get("marker_file") or "").strip()
            if marker_file:
                files.add(self.marker_service.normalize_file_name(marker_file))
        return files

    def _marker_files_from_overlays(self) -> set[str]:
        files: set[str] = set()
        for overlay in self._live_counter_overlays():
            marker_file = overlay.marker_file()
            if marker_file:
                files.add(self.marker_service.normalize_file_name(marker_file))
        return files

    def _reserved_counter_hotkeys(self) -> dict[str, str]:
        return {
            str(binding["sequence"]): str(binding["label"])
            for binding in self.hotkeys.all_bindings()
            if binding["enabled"] and binding["sequence"]
        }

    def _delete_selected_counter_preset(self) -> None:
        preset_path = self._selected_counter_preset_path()
        if preset_path is None:
            return

        answer = QMessageBox.question(
            self,
            "Excluir preset",
            f"Excluir o preset {preset_path.name} e o estado salvo dele?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.counter_service.delete_preset(preset_path)
        self._refresh_counter_page()

    def _selected_counter_preset_path(self) -> Optional[Path]:
        if self.counter_preset_list is None:
            return None
        items = self.counter_preset_list.selectedItems()
        if not items:
            QMessageBox.information(self, "Preset", "Selecione um preset primeiro.")
            return None
        return Path(str(items[0].data(Qt.ItemDataRole.UserRole)))

    def _select_counter_preset(self, preset_path: Path) -> None:
        if self.counter_preset_list is None:
            return
        target = str(preset_path)
        for row in range(self.counter_preset_list.count()):
            item = self.counter_preset_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == target:
                self.counter_preset_list.setCurrentItem(item)
                return

    def _reset_counter_overlays(self) -> None:
        for overlay in list(self._live_counter_overlays()):
            overlay.reset()
        self._update_counter_status()

    def _reset_selected_counter_overlay(self) -> None:
        overlay = self._selected_counter_overlay()
        if overlay is None:
            return
        overlay.reset()
        self._update_counter_status()

    def _close_selected_counter_overlay(self) -> None:
        overlay = self._selected_counter_overlay()
        if overlay is None:
            return
        overlay.close()

    def _close_counter_overlays(self) -> None:
        for overlay in list(self._live_counter_overlays()):
            overlay.close()
        self.counter_overlays.clear()
        self._update_counter_status()

    def _live_counter_overlays(self) -> list[CounterOverlay]:
        self.counter_overlays = [overlay for overlay in self.counter_overlays if overlay is not None and overlay.isVisible()]
        return self.counter_overlays

    def _update_counter_status(self) -> None:
        if self.counter_status_label is None:
            return
        count = len(self._live_counter_overlays())
        if count:
            titles = ", ".join(overlay.windowTitle() for overlay in self.counter_overlays[:4])
            suffix = "..." if count > 4 else ""
            self.counter_status_label.setText(f"Overlays abertos: {count} ({titles}{suffix})")
        else:
            self.counter_status_label.setText("Overlays abertos: 0")
        self._refresh_counter_active_list()

    def _on_counter_overlay_closed(self, overlay: CounterOverlay) -> None:
        self.counter_overlays = [item for item in self.counter_overlays if item is not overlay]
        self._update_counter_status()

    def _on_counter_marker_saved(self, file_name: str) -> None:
        if self.marker_last_label is not None:
            self.marker_last_label.setText(f"Ultima marcacao salva em: {file_name}")
        self._refresh_marker_page()

    def _refresh_counter_active_list(self) -> None:
        if self.counter_active_list is None:
            return

        selected_id = None
        selected = self.counter_active_list.selectedItems()
        if selected:
            selected_id = selected[0].data(Qt.ItemDataRole.UserRole)

        self.counter_active_list.clear()
        for overlay in self._live_counter_overlays():
            overlay_id = str(id(overlay))
            hotkey = overlay.hotkey()
            hotkey_suffix = f"  |  hotkey: {hotkey}" if hotkey else ""
            marker_file = overlay.marker_file()
            marker_suffix = f"  |  txt: {marker_file}" if marker_file else ""
            item = QListWidgetItem(f"{overlay.windowTitle()}  |  valor: {overlay.value}{hotkey_suffix}{marker_suffix}")
            item.setData(Qt.ItemDataRole.UserRole, overlay_id)
            self.counter_active_list.addItem(item)
            if overlay_id == selected_id:
                self.counter_active_list.setCurrentItem(item)

    def _selected_counter_overlay(self) -> Optional[CounterOverlay]:
        if self.counter_active_list is None:
            return None
        items = self.counter_active_list.selectedItems()
        if not items:
            QMessageBox.information(self, "Contador", "Selecione um contador ativo primeiro.")
            return None

        overlay_id = items[0].data(Qt.ItemDataRole.UserRole)
        for overlay in self._live_counter_overlays():
            if str(id(overlay)) == overlay_id:
                return overlay
        return None

    def _refresh_tray_counter_menu(self) -> None:
        if self.tray_counter_menu is None:
            return

        self.tray_counter_menu.clear()
        overlays = self._live_counter_overlays()
        if not overlays:
            empty = QAction("Nenhum contador aberto", self)
            empty.setEnabled(False)
            self.tray_counter_menu.addAction(empty)
            return

        for overlay in overlays:
            counter_menu = QMenu(f"{overlay.windowTitle()} ({overlay.value})", self)
            reset_action = QAction("Resetar", self)
            reset_action.triggered.connect(lambda checked=False, item=overlay: self._reset_counter_overlay(item))
            close_action = QAction("Fechar", self)
            close_action.triggered.connect(lambda checked=False, item=overlay: self._close_counter_overlay(item))
            counter_menu.addAction(reset_action)
            counter_menu.addAction(close_action)
            self.tray_counter_menu.addMenu(counter_menu)

    def _reset_counter_overlay(self, overlay: CounterOverlay) -> None:
        if overlay not in self._live_counter_overlays():
            return
        overlay.reset()
        self._update_counter_status()

    def _close_counter_overlay(self, overlay: CounterOverlay) -> None:
        if overlay not in self._live_counter_overlays():
            return
        overlay.close()


class QuickMarkerDialog(QDialog):
    saved = Signal(str)

    def __init__(self, marker_service: MarkerService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.marker_service = marker_service
        self.setWindowTitle("Marcar evento")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(430, 132)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        title = QLabel(f"Arquivo: {self.marker_service.active_file().name}")
        title.setObjectName("SectionTitle")
        self.input = QLineEdit()
        self.input.setPlaceholderText("Descreva o evento")
        self.input.returnPressed.connect(self._save)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Salvar")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)

        layout.addWidget(title)
        layout.addWidget(self.input)
        layout.addLayout(buttons)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.focus_text_input()

    def focus_text_input(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.input.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self.input.grabKeyboard()
        for delay in (35, 120, 260):
            QTimer.singleShot(delay, self._refocus_input)
        for delay in (80, 180, 320):
            QTimer.singleShot(delay, self._force_click_input)

    def _refocus_input(self) -> None:
        if not self.isVisible():
            return
        self.raise_()
        self.activateWindow()
        self.input.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self.input.grabKeyboard()

    def _force_click_input(self) -> None:
        if pyautogui is None or not self.isVisible():
            return
        center = self.input.mapToGlobal(self.input.rect().center())
        try:
            pyautogui.click(center.x(), center.y())
        except Exception:
            pass

    def done(self, result: int) -> None:
        self.input.releaseKeyboard()
        super().done(result)

    def _save(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        target = self.marker_service.save_marker(text)
        self.saved.emit(target.name)
        self.accept()


class QuickGameDialog(QDialog):
    created = Signal(str)

    def __init__(self, marker_service: MarkerService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.marker_service = marker_service
        self.setWindowTitle("Novo jogo")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(430, 132)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        title = QLabel("Criar ou trocar arquivo ativo")
        title.setObjectName("SectionTitle")
        self.input = QLineEdit()
        self.input.setPlaceholderText("Nome do jogo ou arquivo")
        self.input.returnPressed.connect(self._create)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        create = QPushButton("Criar")
        create.setObjectName("PrimaryButton")
        create.clicked.connect(self._create)
        buttons.addWidget(cancel)
        buttons.addWidget(create)

        layout.addWidget(title)
        layout.addWidget(self.input)
        layout.addLayout(buttons)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.focus_text_input()

    def focus_text_input(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.input.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self.input.grabKeyboard()
        for delay in (35, 120, 260):
            QTimer.singleShot(delay, self._refocus_input)
        for delay in (80, 180, 320):
            QTimer.singleShot(delay, self._force_click_input)

    def _refocus_input(self) -> None:
        if not self.isVisible():
            return
        self.raise_()
        self.activateWindow()
        self.input.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self.input.grabKeyboard()

    def _force_click_input(self) -> None:
        if pyautogui is None or not self.isVisible():
            return
        center = self.input.mapToGlobal(self.input.rect().center())
        try:
            pyautogui.click(center.x(), center.y())
        except Exception:
            pass

    def done(self, result: int) -> None:
        self.input.releaseKeyboard()
        super().done(result)

    def _create(self) -> None:
        name = self.input.text().strip()
        if not name:
            return
        target = self.marker_service.create_game(name)
        self.created.emit(target.name)
        self.accept()


def _normalize_hotkey(sequence: str) -> str:
    return str(sequence).strip().casefold().replace(" ", "")
