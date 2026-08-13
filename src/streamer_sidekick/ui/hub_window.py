import os
from typing import Optional
from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QCloseEvent, QColor, QDesktopServices, QIcon, QKeySequence, QPixmap
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
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QSystemTrayIcon,
    QToolTip,
    QVBoxLayout,
    QWidget,
    QKeySequenceEdit,
    QStyle,
)

from streamer_sidekick.core.config import ConfigStore
from streamer_sidekick.core.backup import BackupError, BackupService
from streamer_sidekick.core.diagnostics import DiagnosticItem, DiagnosticService
from streamer_sidekick.core.hotkeys import HotkeyManager
from streamer_sidekick.core.modules import ModuleInfo, ModuleRegistry
from streamer_sidekick.core.platform_utils import app_icon_path, open_path
from streamer_sidekick.core.plugins import InstalledPlugin, PluginManager
from streamer_sidekick.core import app_update
from streamer_sidekick.modules.counter.overlay import CounterOverlay
from streamer_sidekick.modules.counter.service import CounterService
from streamer_sidekick.modules.marker.service import MarkerService
from streamer_sidekick.ui.counter_editor import CounterPresetDialog
from streamer_sidekick.ui.components import AddPluginTile, BrandLogo, ModuleCard, NeonPanel, SectionHeader, neon_qicon, plugin_qicon
from streamer_sidekick.ui.plugin_marketplace import PluginMarketplaceDialog, _CatalogWorker
from streamer_sidekick.ui.app_update import AppUpdateCheckWorker, AppUpdateDialog

try:
    import pyautogui
except ImportError:
    pyautogui = None


APP_ICON_PATH = app_icon_path()


class HubWindow(QMainWindow):
    def __init__(
        self,
        config: ConfigStore,
        hotkeys: HotkeyManager,
        modules: ModuleRegistry,
        marker_service: MarkerService,
        counter_service: CounterService,
        plugin_manager: Optional[PluginManager] = None,
    ) -> None:
        super().__init__()
        self.config = config
        self.hotkeys = hotkeys
        self.modules = modules
        self.marker_service = marker_service
        self.counter_service = counter_service
        self.plugin_manager = plugin_manager or PluginManager()
        self.backup_service = BackupService(config, marker_service, counter_service)
        self.diagnostic_service = DiagnosticService(config, hotkeys, marker_service, counter_service)
        self.nav_buttons: dict[str, QPushButton] = {}
        self.plugin_nav_buttons: dict[str, QPushButton] = {}
        self.plugin_subnav: Optional[QWidget] = None
        self.marker_active_label: Optional[QLabel] = None
        self.marker_folder_label: Optional[QLabel] = None
        self.marker_last_label: Optional[QLabel] = None
        self.marker_files_list: Optional[QListWidget] = None
        self.marker_recent_list: Optional[QListWidget] = None
        self.marker_event_input: Optional[QLineEdit] = None
        self.marker_new_game_input: Optional[QLineEdit] = None
        self.marker_custom_hotkey_message_input: Optional[QLineEdit] = None
        self.marker_custom_hotkey_sequence_input: Optional[QKeySequenceEdit] = None
        self.marker_custom_hotkey_status_label: Optional[QLabel] = None
        self.marker_custom_hotkeys_list: Optional[QListWidget] = None
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
        self.hotkeys_grid: Optional[QGridLayout] = None
        self.hotkey_capture_label: Optional[QLabel] = None
        self.diagnostic_summary_label: Optional[QLabel] = None
        self.diagnostic_list: Optional[QListWidget] = None
        self._last_diagnostics: list[DiagnosticItem] = []
        self._hotkey_status_messages: list[str] = []
        self._hotkey_capture_editor: Optional[QKeySequenceEdit] = None
        self._hotkeys_paused_for_capture = False
        self._marker_custom_callback_keys: set[str] = set()
        self.home_modules_layout: Optional[QGridLayout] = None
        self.home_module_cards: list[ModuleCard] = []
        self._home_module_columns = 0
        self.add_plugin_card: Optional[AddPluginTile] = None
        self.plugin_subnav_layout: Optional[QVBoxLayout] = None
        self._plugin_page_ids: set[str] = set()
        self._plugin_page_containers: dict[str, QWidget] = {}
        self._plugin_update_worker: Optional[_CatalogWorker] = None
        self._app_update_worker: Optional[AppUpdateCheckWorker] = None
        self._app_update_shown = False
        self.app_update_status_label: Optional[QLabel] = None
        self.help_layout: Optional[QVBoxLayout] = None
        self._quitting = False

        self.setWindowTitle("Streamer Sidekick")
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.resize(1160, 720)
        self.setMinimumSize(980, 620)

        self.pages = QStackedWidget()
        self.page_indexes: dict[str, int] = {}
        self.setCentralWidget(self._build_shell())
        self._create_tray()
        self._wire_hotkeys()
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self._select_page("home")
        self._check_app_update_async(auto=True)

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
        sidebar.setFixedWidth(232)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 18, 12, 20)
        layout.setSpacing(9)

        layout.addWidget(BrandLogo(compact=True))
        layout.addSpacing(22)

        for page_id, label, icon_id in [
            ("home", "Início", "home"),
            ("plugins", "Plugins", "plugins"),
            ("hotkeys", "Atalhos", "hotkey"),
            ("diagnostics", "Diagnóstico", "diagnostics"),
            ("settings", "Configurações", "settings"),
            ("help", "Ajuda", "help"),
            ("about", "Sobre", "about"),
        ]:
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setIcon(neon_qicon(icon_id, 22))
            button.setIconSize(QSize(22, 22))
            button.setCursor(Qt.PointingHandCursor)
            if page_id == "plugins":
                button.clicked.connect(self._toggle_plugins_menu)
            else:
                button.clicked.connect(lambda checked=False, item=page_id: self._select_page(item))
            self.nav_buttons[page_id] = button
            layout.addWidget(button)
            if page_id == "plugins":
                self.plugin_subnav = self._build_plugin_subnav()
                layout.addWidget(self.plugin_subnav)

        layout.addStretch(1)

        footer = QLabel("Online\nBase modular v0.4")
        footer.setObjectName("Muted")
        layout.addWidget(footer)
        return sidebar

    def _build_plugin_subnav(self) -> QWidget:
        container = QWidget()
        container.setObjectName("PluginSubnav")
        container.setVisible(False)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 2, 0, 4)
        layout.setSpacing(6)

        self.plugin_subnav_layout = layout
        for page_id, label, icon_id in [
            ("marker", "Marcador", "marker"),
            ("counter", "Contador", "counter"),
        ]:
            button = QPushButton(label)
            button.setObjectName("SubNavButton")
            button.setIcon(neon_qicon(icon_id, 18))
            button.setIconSize(QSize(18, 18))
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, item=page_id: self._select_page(item))
            self.plugin_nav_buttons[page_id] = button
            layout.addWidget(button)

        for plugin in self.plugin_manager.installed():
            self._add_plugin_subnav_button(plugin)
        return container

    def _add_plugin_subnav_button(self, plugin: InstalledPlugin) -> None:
        if self.plugin_subnav_layout is None or plugin.id in self.plugin_nav_buttons:
            return
        label = plugin.name
        info = plugin.module_info
        if info is not None:
            label = getattr(info, "title", plugin.name) or plugin.name
        button = QPushButton(label)
        button.setObjectName("SubNavButton")
        button.setIcon(plugin_qicon(plugin.icon_path or "", "plugin", 18))
        button.setIconSize(QSize(18, 18))
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(lambda checked=False, item=plugin.id: self._select_page(item))
        self.plugin_nav_buttons[plugin.id] = button
        self.plugin_subnav_layout.addWidget(button)

    def _build_content(self) -> QWidget:
        content = QWidget()
        content.setObjectName("ContentSurface")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 22, 24)
        layout.addWidget(self.pages)

        self._add_page("home", self._home_page())
        self.page_indexes["plugins"] = self.page_indexes["home"]
        self._add_page("marker", self._marker_page())
        self._add_page("counter", self._counter_page())
        self._add_page("hotkeys", self._hotkeys_page())
        self._add_page("diagnostics", self._diagnostics_page())
        self._add_page("settings", self._settings_page())
        self._add_page("help", self._help_page())
        self._add_page("about", self._about_page())
        for plugin in self.plugin_manager.installed():
            self._add_plugin_page(plugin)
        return content

    def _add_plugin_page(self, plugin: InstalledPlugin) -> bool:
        """Monta a pagina de um plugin dentro de um container fixo no stack.

        O container mantem um indice estavel no QStackedWidget; ao atualizar o
        plugin, so o conteudo do container e trocado (ver _reload_plugin), sem
        remover widgets do stack (o que embaralharia os indices das paginas)."""
        if plugin.id in self._plugin_page_ids:
            return True
        if not plugin.loaded or plugin.build_page is None:
            return False
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._build_plugin_inner_page(plugin))
        self._add_page(plugin.id, container)
        self._plugin_page_containers[plugin.id] = container
        self._plugin_page_ids.add(plugin.id)
        return True

    def _build_plugin_inner_page(self, plugin: InstalledPlugin) -> QWidget:
        if plugin.build_page is None:
            return self._plugin_error_page(plugin, "plugin sem build_page")
        try:
            return plugin.build_page()
        except Exception as exc:  # pagina de terceiro: nao pode derrubar o hub
            return self._plugin_error_page(plugin, str(exc))

    def _reload_plugin(self, plugin: InstalledPlugin) -> None:
        """Recarrega pagina + card + subnav de um plugin ja integrado (pos-update)."""
        container = self._plugin_page_containers.get(plugin.id)
        if container is not None:
            layout = container.layout()
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            layout.addWidget(self._build_plugin_inner_page(plugin))

        # Recria o card (titulo/subtitulo/icone podem ter mudado).
        for index, card in enumerate(self.home_module_cards):
            if getattr(card.module, "module_id", None) == plugin.id:
                new_card = ModuleCard(self._plugin_card_info(plugin))
                new_card.opened.connect(self._select_page)
                self.home_module_cards[index] = new_card
                card.deleteLater()
                self._reflow_home_modules(force=True)
                break

        # Atualiza rotulo/icone do botao da subnav.
        button = self.plugin_nav_buttons.get(plugin.id)
        if button is not None:
            info = plugin.module_info
            button.setText(getattr(info, "title", plugin.name) or plugin.name)
            button.setIcon(plugin_qicon(plugin.icon_path or "", "plugin", 18))

        self._refresh_help_page()

    def _plugin_error_page(self, plugin: InstalledPlugin, message: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 22, 0)
        title = QLabel(f"{plugin.name}")
        title.setObjectName("PageTitle")
        detail = QLabel(f"Não foi possível carregar este plugin:\n{message}")
        detail.setObjectName("Muted")
        detail.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(detail)
        layout.addStretch(1)
        return self._scrollable_page(page)

    def _add_page(self, page_id: str, widget: QWidget) -> None:
        self.page_indexes[page_id] = self.pages.addWidget(widget)

    def _scrollable_page(self, content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName("PageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setViewportMargins(0, 0, 18, 0)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll

    def _home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 22, 0)
        layout.setSpacing(22)

        hero = NeonPanel(accent="#37F2FF", grid=False)
        hero.setMinimumHeight(230)
        hero_layout = QGridLayout(hero)
        hero_layout.setContentsMargins(28, 24, 28, 24)
        hero_layout.setHorizontalSpacing(24)
        hero_layout.setVerticalSpacing(12)

        hero_logo = BrandLogo()
        hero_title = QLabel("Hub de ferramentas para streamers")
        hero_title.setObjectName("PageTitle")
        hero_title.setWordWrap(True)
        hero_subtitle = QLabel("Acesso rápido para marcador, contador e hotkeys de live.")
        hero_subtitle.setObjectName("Muted")
        hero_subtitle.setWordWrap(True)
        hero_status = QLabel("Hotkeys unificadas  |  Estrutura modular  |  OBS-friendly")
        hero_status.setObjectName("StatusPill")
        hero_status.setWordWrap(True)
        hero_status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        hero_layout.addWidget(hero_logo, 0, 0, Qt.AlignmentFlag.AlignLeft)
        hero_layout.addWidget(hero_title, 1, 0)
        hero_layout.addWidget(hero_subtitle, 2, 0)
        hero_layout.addWidget(hero_status, 3, 0)
        hero_layout.setColumnStretch(0, 1)

        layout.addWidget(hero)
        layout.addWidget(SectionHeader("01", "Plugins"))

        modules_layout = QGridLayout()
        modules_layout.setHorizontalSpacing(18)
        modules_layout.setVerticalSpacing(18)
        self.home_modules_layout = modules_layout
        self.home_module_cards = []
        for module in self.modules.all():
            card = ModuleCard(module)
            card.opened.connect(self._select_page)
            self.home_module_cards.append(card)
        for plugin in self.plugin_manager.installed():
            self._append_plugin_card(plugin)

        self.add_plugin_card = AddPluginTile()
        self.add_plugin_card.clicked.connect(self._open_marketplace)

        self._reflow_home_modules(force=True)

        layout.addLayout(modules_layout)
        layout.addStretch(1)
        self._check_plugin_updates_async()
        return self._scrollable_page(page)

    def _plugin_card_info(self, plugin: InstalledPlugin) -> ModuleInfo:
        """ModuleInfo com module_id alinhado ao id do plugin (garante navegacao)."""
        info = plugin.module_info
        return ModuleInfo(
            module_id=plugin.id,
            title=(getattr(info, "title", "") or plugin.name),
            subtitle=(getattr(info, "subtitle", "") or "Plugin instalado."),
            status=(getattr(info, "status", "") or "Pronto"),
            accent=plugin.accent,
            icon=plugin.icon_path or "",
        )

    def _append_plugin_card(self, plugin: InstalledPlugin) -> None:
        card = ModuleCard(self._plugin_card_info(plugin))
        card.opened.connect(self._select_page)
        self.home_module_cards.append(card)

    def _marker_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 22, 0)
        layout.setSpacing(18)

        title = QLabel("Marcador")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        self.marker_active_label = QLabel()
        self.marker_active_label.setObjectName("SectionTitle")
        self.marker_folder_label = QLabel()
        self.marker_folder_label.setObjectName("Muted")
        self.marker_last_label = QLabel("Última marcação: nenhuma nesta sessão")
        self.marker_last_label.setObjectName("Muted")

        top_actions = QGridLayout()
        top_actions.setHorizontalSpacing(12)
        top_actions.setVerticalSpacing(10)
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
        for index, button in enumerate([choose_folder, open_folder, open_active_file, new_game, quick_marker]):
            top_actions.addWidget(button, index // 2, index % 2)
        for column in range(2):
            top_actions.setColumnStretch(column, 1)

        event_box = self._marker_event_box()
        recent_box = self._marker_recent_box()
        custom_hotkeys_box = self._marker_custom_hotkeys_box()
        files_box = self._marker_files_box()

        layout.addWidget(self.marker_active_label)
        layout.addWidget(self.marker_folder_label)
        layout.addWidget(self.marker_last_label)
        layout.addLayout(top_actions)
        layout.addWidget(event_box)
        layout.addWidget(recent_box)
        layout.addWidget(custom_hotkeys_box)
        layout.addWidget(files_box)
        layout.addStretch(1)
        self._refresh_marker_page()
        return self._scrollable_page(page)

    def _marker_event_box(self) -> QWidget:
        box = NeonPanel(accent="#37F2FF")
        box.setMinimumHeight(250)
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("Registro rápido")
        title.setObjectName("SectionTitle")
        self.marker_event_input = QLineEdit()
        self.marker_event_input.setPlaceholderText("Descreva o evento da live")
        self.marker_event_input.returnPressed.connect(self._save_marker_from_page)

        save = QPushButton("Salvar marcação")
        save.setObjectName("PrimaryButton")
        save.setMinimumHeight(42)
        save.setMinimumWidth(150)
        save.clicked.connect(self._save_marker_from_page)

        row = QVBoxLayout()
        row.setSpacing(12)
        row.addWidget(self.marker_event_input)
        row.addWidget(save, 0, Qt.AlignmentFlag.AlignLeft)

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
        layout.addSpacing(10)
        layout.addWidget(new_game_title)
        layout.addLayout(game_row)
        return box

    def _marker_custom_hotkeys_box(self) -> QWidget:
        box = NeonPanel(accent="#FF4FD8")
        box.setMinimumHeight(360)
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Hotkeys de mensagem")
        title.setObjectName("SectionTitle")

        form = QVBoxLayout()
        form.setSpacing(14)
        self.marker_custom_hotkey_message_input = QLineEdit()
        self.marker_custom_hotkey_message_input.setPlaceholderText("Mensagem salva no txt")
        self.marker_custom_hotkey_message_input.setMinimumHeight(42)
        self.marker_custom_hotkey_sequence_input = QKeySequenceEdit()
        self.marker_custom_hotkey_sequence_input.setMinimumWidth(230)
        self.marker_custom_hotkey_sequence_input.setMinimumHeight(42)
        self.marker_custom_hotkey_status_label = QLabel("Pronto para gravar uma nova hotkey de mensagem.")
        self.marker_custom_hotkey_status_label.setObjectName("CaptureStatus")
        self.marker_custom_hotkey_status_label.setMinimumHeight(38)
        add = QPushButton("Adicionar")
        add.setObjectName("PrimaryButton")
        add.setMinimumWidth(130)
        add.setMinimumHeight(42)
        add.clicked.connect(self._add_marker_custom_hotkey)
        shortcut_row = QHBoxLayout()
        shortcut_row.setSpacing(12)
        shortcut_row.addWidget(self.marker_custom_hotkey_sequence_input, 1)
        shortcut_row.addWidget(add, 0)
        form.addWidget(self.marker_custom_hotkey_message_input)
        form.addLayout(shortcut_row)

        self.marker_custom_hotkeys_list = QListWidget()
        self.marker_custom_hotkeys_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.marker_custom_hotkeys_list.setMinimumHeight(125)

        actions = QHBoxLayout()
        remove = QPushButton("Remover selecionada")
        remove.setMinimumWidth(180)
        remove.clicked.connect(self._remove_selected_marker_custom_hotkey)
        actions.addStretch(1)
        actions.addWidget(remove)

        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(self.marker_custom_hotkey_status_label)
        layout.addWidget(self.marker_custom_hotkeys_list)
        layout.addLayout(actions)
        return box

    def _marker_recent_box(self) -> QWidget:
        box = NeonPanel(accent="#37F2FF", grid=False)
        box.setMinimumHeight(235)
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Marcações recentes")
        title.setObjectName("SectionTitle")
        refresh = QPushButton("Atualizar")
        refresh.clicked.connect(self._refresh_marker_page)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(refresh)

        self.marker_recent_list = QListWidget()
        self.marker_recent_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.marker_recent_list.setMinimumHeight(120)
        self.marker_recent_list.setMaximumHeight(150)

        layout.addLayout(header)
        layout.addWidget(self.marker_recent_list, 1)
        return box

    def _marker_files_box(self) -> QWidget:
        box = NeonPanel(accent="#B9FF43")
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Arquivos de marcação")
        title.setObjectName("SectionTitle")
        refresh = QPushButton("Atualizar")
        refresh.clicked.connect(self._refresh_marker_page)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(refresh)

        self.marker_files_list = QListWidget()
        self.marker_files_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.marker_files_list.setMinimumHeight(95)
        self.marker_files_list.itemDoubleClicked.connect(self._set_marker_active_from_item)

        use_selected = QPushButton("Usar selecionado")
        use_selected.clicked.connect(self._set_marker_active_from_selection)
        hint = QLabel("Clique duas vezes em um arquivo, ou selecione e use o botão.")
        hint.setObjectName("Muted")

        layout.addLayout(header)
        layout.addWidget(self.marker_files_list)
        layout.addWidget(hint)
        layout.addWidget(use_selected)
        return box

    def _counter_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 22, 0)
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

        actions_panel = NeonPanel(accent="#FF4FD8")
        actions = QGridLayout(actions_panel)
        actions.setContentsMargins(18, 16, 18, 16)
        actions.setHorizontalSpacing(10)
        actions.setVerticalSpacing(10)
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
        for index, button in enumerate([create_preset, edit_preset, duplicate_preset, delete_preset, choose_folder, open_preset, reset, close]):
            actions.addWidget(button, index // 2, index % 2)
        for column in range(2):
            actions.setColumnStretch(column, 1)

        active_box = NeonPanel(accent="#37F2FF", grid=False)
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
        active_actions = QHBoxLayout()
        active_actions.setSpacing(10)
        active_actions.addWidget(reset_selected)
        active_actions.addWidget(close_selected)
        active_actions.addStretch(1)
        self.counter_active_list = QListWidget()
        self.counter_active_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        active_hint = QLabel("Selecione um contador ativo para resetar ou fechar apenas ele.")
        active_hint.setObjectName("Muted")
        active_layout.addLayout(active_header)
        active_layout.addLayout(active_actions)
        active_layout.addWidget(self.counter_active_list)
        active_layout.addWidget(active_hint)

        presets_box = NeonPanel(accent="#B9FF43")
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
        layout.addWidget(actions_panel)
        layout.addWidget(active_box)
        layout.addWidget(presets_box)
        layout.addStretch(1)
        self._refresh_counter_page()
        return self._scrollable_page(page)

    def _hotkeys_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 22, 0)
        layout.setSpacing(18)

        title = QLabel("Atalhos globais")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Os conflitos são bloqueados antes de salvar. O novo padrão evita o antigo choque do Ctrl+Alt+N.")
        subtitle.setObjectName("Muted")
        self.hotkey_capture_label = QLabel("Pronto para gravar atalhos.")
        self.hotkey_capture_label.setObjectName("CaptureStatus")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.hotkey_capture_label)

        panel = NeonPanel(accent="#37F2FF", grid=False)
        grid = QGridLayout(panel)
        grid.setContentsMargins(18, 18, 18, 18)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)
        self.hotkeys_grid = grid

        self._refresh_hotkeys_page()

        layout.addWidget(panel)
        layout.addStretch(1)
        return self._scrollable_page(page)

    def _diagnostics_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 22, 0)
        layout.setSpacing(18)

        title = QLabel("Diagnóstico")
        title.setObjectName("PageTitle")
        self.diagnostic_summary_label = QLabel()
        self.diagnostic_summary_label.setObjectName("Muted")

        actions = QHBoxLayout()
        refresh = QPushButton("Atualizar")
        refresh.clicked.connect(self._refresh_diagnostics_page)
        copy = QPushButton("Copiar relatório")
        copy.clicked.connect(self._copy_diagnostics_report)
        actions.addWidget(refresh)
        actions.addWidget(copy)
        actions.addStretch(1)

        panel = NeonPanel(accent="#B9FF43", grid=False)
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
        return self._scrollable_page(page)

    def _settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 22, 0)
        layout.setSpacing(18)

        title = QLabel("Configurações")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        behavior_box = NeonPanel(accent="#37F2FF")
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

        folders_box = NeonPanel(accent="#FF4FD8")
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

        backup_box = NeonPanel(accent="#B9FF43")
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
        save_button = QPushButton("Salvar configurações")
        save_button.setObjectName("PrimaryButton")
        save_button.clicked.connect(self._save_settings)
        save_row.addWidget(save_button)

        layout.addWidget(behavior_box)
        layout.addWidget(folders_box)
        layout.addWidget(backup_box)
        layout.addLayout(save_row)
        layout.addWidget(self._info_block("Dados do app", f"Configuração central: {self.config.path}"))
        layout.addStretch(1)
        return self._scrollable_page(page)

    def _about_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 22, 0)
        layout.setSpacing(18)

        title = QLabel("Sobre")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        app_panel = NeonPanel(accent="#37F2FF")
        app_layout = QVBoxLayout(app_panel)
        app_layout.setContentsMargins(22, 20, 22, 20)
        app_layout.setSpacing(12)

        app_title = QLabel("Streamer Sidekick")
        app_title.setObjectName("SectionTitle")
        app_text = QLabel(
            "Um hub modular para reunir ferramentas rápidas de live e pós-produção. "
            "Hoje ele centraliza o Marcador e o Contador, com hotkeys configuráveis, "
            "integração com a bandeja do Windows e uma base preparada para receber novos plugins."
        )
        app_text.setObjectName("Muted")
        app_text.setWordWrap(True)
        app_layout.addWidget(app_title)
        app_layout.addWidget(app_text)

        version_label = QLabel(f"Versão {app_update.current_version()}")
        version_label.setObjectName("StatusPill")
        app_layout.addWidget(version_label)

        update_row = QHBoxLayout()
        check_update_button = QPushButton("Verificar atualizações")
        check_update_button.clicked.connect(lambda: self._check_app_update_async(auto=False))
        self.app_update_status_label = QLabel("")
        self.app_update_status_label.setObjectName("Muted")
        self.app_update_status_label.setWordWrap(True)
        update_row.addWidget(check_update_button, 0)
        update_row.addWidget(self.app_update_status_label, 1)
        app_layout.addLayout(update_row)

        donate_panel = NeonPanel(accent="#B9FF43")
        donate_layout = QVBoxLayout(donate_panel)
        donate_layout.setContentsMargins(22, 20, 22, 20)
        donate_layout.setSpacing(12)
        donate_title = QLabel("Apoie o projeto")
        donate_title.setObjectName("SectionTitle")
        donate_text = QLabel(
            "O Streamer Sidekick é gratuito e feito com carinho. Se ele te ajuda na sua "
            "live, considere apoiar com o quanto você acha que ele vale — cada "
            "contribuição ajuda a manter o projeto vivo e a trazer novos plugins."
        )
        donate_text.setObjectName("Muted")
        donate_text.setWordWrap(True)
        donate_button = QPushButton("❤  Doar")
        donate_button.setObjectName("PrimaryButton")
        donate_button.setCursor(Qt.CursorShape.PointingHandCursor)
        donate_button.clicked.connect(self._open_livepix)
        donate_layout.addWidget(donate_title)
        donate_layout.addWidget(donate_text)
        donate_layout.addWidget(donate_button, 0, Qt.AlignmentFlag.AlignLeft)

        profile_panel = NeonPanel(accent="#FF4FD8")
        profile_layout = QGridLayout(profile_panel)
        profile_layout.setContentsMargins(22, 20, 22, 20)
        profile_layout.setHorizontalSpacing(24)
        profile_layout.setVerticalSpacing(12)

        avatar = QLabel()
        avatar.setObjectName("AvatarImage")
        avatar.setFixedSize(180, 180)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_path = Path(__file__).resolve().parents[1] / "assets" / "brand" / "gamox_icon.png"
        avatar_pixmap = QPixmap(str(avatar_path))
        if not avatar_pixmap.isNull():
            avatar.setPixmap(
                avatar_pixmap.scaled(
                    166,
                    166,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        about_title = QLabel('Ricardo "Gamox"')
        about_title.setObjectName("SectionTitle")
        about_text = QLabel(
            "Me chamo Ricardo, mas na internet sou conhecido como Gamox. "
            "Sou desenvolvedor júnior, gosto de platinar jogos e compartilho vídeos no meu canal. "
            "Se você curtir esse tipo de conteúdo ou quiser acompanhar meus projetos, se inscreva por lá."
        )
        about_text.setObjectName("Muted")
        about_text.setWordWrap(True)

        channel_button = QPushButton("Abrir canal no YouTube")
        channel_button.setObjectName("PrimaryButton")
        channel_button.setIcon(neon_qicon("about", 20))
        channel_button.setIconSize(QSize(20, 20))
        channel_button.clicked.connect(self._open_youtube_channel)

        text_box = QVBoxLayout()
        text_box.setSpacing(12)
        text_box.addWidget(about_title)
        text_box.addWidget(about_text)
        text_box.addWidget(channel_button, 0, Qt.AlignmentFlag.AlignLeft)
        text_box.addStretch(1)

        profile_layout.addWidget(avatar, 0, 0, Qt.AlignmentFlag.AlignTop)
        profile_layout.addLayout(text_box, 0, 1)
        profile_layout.setColumnStretch(1, 1)

        layout.addWidget(app_panel)
        layout.addWidget(donate_panel)
        layout.addWidget(profile_panel)
        layout.addStretch(1)
        return self._scrollable_page(page)

    def _open_youtube_channel(self) -> None:
        QDesktopServices.openUrl(QUrl("https://www.youtube.com/@Gamoxkun"))

    def _open_livepix(self) -> None:
        QDesktopServices.openUrl(QUrl("https://livepix.gg/gamoxkun"))

    def eventFilter(self, watched, event) -> bool:
        if isinstance(watched, QKeySequenceEdit):
            if event.type() == QEvent.Type.FocusIn:
                self._begin_hotkey_capture(watched)
            elif event.type() in (QEvent.Type.FocusOut, QEvent.Type.Hide):
                self._finish_hotkey_capture(watched)
        return super().eventFilter(watched, event)

    def _begin_hotkey_capture(self, editor: QKeySequenceEdit) -> None:
        if self._hotkey_capture_editor is not editor and self._hotkey_capture_editor is not None:
            self._mark_hotkey_editor(self._hotkey_capture_editor, False)

        self._hotkey_capture_editor = editor
        self._mark_hotkey_editor(editor, True)
        if not self._hotkeys_paused_for_capture:
            self._pause_hotkey_services_for_capture()

        message = "Gravando hotkey... atalhos globais pausados ate concluir."
        self._set_hotkey_capture_message(message, True)
        self.statusBar().showMessage(message)
        QToolTip.showText(
            editor.mapToGlobal(editor.rect().bottomLeft()),
            "Gravando hotkey\nAtalhos globais pausados",
            editor,
            editor.rect(),
            2400,
        )

    def _finish_hotkey_capture(self, editor: QKeySequenceEdit) -> None:
        self._mark_hotkey_editor(editor, False)
        if self._hotkey_capture_editor is editor:
            self._hotkey_capture_editor = None
        QTimer.singleShot(120, self._resume_hotkeys_after_capture_if_idle)

    def _resume_hotkeys_after_capture_if_idle(self) -> None:
        if isinstance(QApplication.focusWidget(), QKeySequenceEdit):
            return

        if self._hotkeys_paused_for_capture:
            self._resume_hotkey_services_after_capture()
        self._set_hotkey_capture_message("Pronto para gravar atalhos.", False)
        self.statusBar().showMessage("Atalhos globais ativos.", 1800)

    def _pause_hotkey_services_for_capture(self) -> None:
        self.hotkeys.stop_global_hotkeys()
        for overlay in self._live_counter_overlays():
            overlay.pause_hotkey()
        self._hotkeys_paused_for_capture = True

    def _resume_hotkey_services_after_capture(self) -> None:
        self.hotkeys.start_global_hotkeys()
        for overlay in self._live_counter_overlays():
            overlay.resume_hotkey()
        self._hotkeys_paused_for_capture = False

    def _mark_hotkey_editor(self, editor: QKeySequenceEdit, recording: bool) -> None:
        editor.setProperty("recording", "true" if recording else "")
        self._repolish(editor)

    def _set_hotkey_capture_message(self, message: str, recording: bool) -> None:
        for label in (self.hotkey_capture_label, self.marker_custom_hotkey_status_label):
            if label is None:
                continue
            label.setText(message)
            label.setProperty("recording", "true" if recording else "")
            self._repolish(label)

    def _repolish(self, widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _info_block(self, title: str, body: str) -> QWidget:
        box = NeonPanel(accent="#37F2FF")
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
        in_plugins_group = page_id in {"marker", "counter"} or page_id in self.plugin_nav_buttons
        if page_id == "plugins" or in_plugins_group:
            self._set_plugins_menu_visible(True)
        if page_id == "marker":
            self._refresh_marker_page()
        if page_id == "counter":
            self._refresh_counter_page()
        if page_id == "hotkeys":
            self._refresh_hotkeys_page()
        if page_id == "diagnostics":
            self._refresh_diagnostics_page()
        if page_id == "help":
            self._refresh_help_page()
        self.pages.setCurrentIndex(self.page_indexes[page_id])
        active_page = "plugins" if in_plugins_group else page_id
        for item, button in self.nav_buttons.items():
            button.setProperty("active", item == active_page)
            button.style().unpolish(button)
            button.style().polish(button)
        for item, button in self.plugin_nav_buttons.items():
            button.setProperty("active", item == page_id)
            button.style().unpolish(button)
            button.style().polish(button)

    def _toggle_plugins_menu(self) -> None:
        is_visible = self.plugin_subnav is not None and self.plugin_subnav.isVisible()
        self._set_plugins_menu_visible(not is_visible)
        if not is_visible:
            self._select_page("plugins")
        elif self.pages.currentIndex() == self.page_indexes.get("plugins"):
            self._select_page("home")

    def _set_plugins_menu_visible(self, visible: bool) -> None:
        if self.plugin_subnav is not None:
            self.plugin_subnav.setVisible(visible)

    def _refresh_hotkeys_page(self) -> None:
        if self.hotkeys_grid is None:
            return

        while self.hotkeys_grid.count():
            item = self.hotkeys_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        headers = ["Módulo", "Ação", "Atalho", "Ativo", ""]
        for column, header in enumerate(headers):
            label = QLabel(header)
            label.setObjectName("SectionTitle")
            self.hotkeys_grid.addWidget(label, 0, column)

        self.hotkeys_grid.setColumnStretch(0, 0)
        self.hotkeys_grid.setColumnStretch(1, 1)
        self.hotkeys_grid.setColumnStretch(2, 0)
        self.hotkeys_grid.setColumnStretch(3, 0)
        self.hotkeys_grid.setColumnStretch(4, 0)

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

            self.hotkeys_grid.addWidget(module_label, row, 0)
            self.hotkeys_grid.addWidget(action_label, row, 1)
            self.hotkeys_grid.addWidget(sequence_edit, row, 2)
            self.hotkeys_grid.addWidget(enabled, row, 3, alignment=Qt.AlignmentFlag.AlignCenter)
            self.hotkeys_grid.addWidget(save, row, 4)

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
        QMessageBox.information(self, "Diagnóstico", "Relatório copiado.")

    def _diagnostics_report_text(self) -> str:
        lines = ["Streamer Sidekick - Diagnóstico"]
        for item in self._last_diagnostics:
            lines.append(f"{item.status.upper()} | {item.title} | {item.detail}")
        return "\n".join(lines)

    def _save_hotkey(self, key: str, editor: QKeySequenceEdit, checkbox: QCheckBox) -> None:
        sequence = editor.keySequence().toString(QKeySequence.SequenceFormat.NativeText)
        conflict = self.hotkeys.set_binding(key, sequence, checkbox.isChecked())
        if conflict:
            QMessageBox.warning(self, "Conflito de atalho", f"Esse atalho já está em uso por: {conflict}")
            editor.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
            self._begin_hotkey_capture(editor)
            return
        self._resume_hotkey_services_after_capture()
        self._hotkey_capture_editor = None
        self._mark_hotkey_editor(editor, False)
        self._set_hotkey_capture_message("Atalho salvo. Atalhos globais ativos.", False)
        self._refresh_marker_custom_hotkeys_list()
        self._refresh_hotkeys_page()
        QMessageBox.information(self, "Atalho salvo", "Atalho atualizado com sucesso.")

    def _create_tray(self) -> None:
        tray_icon = QIcon(str(APP_ICON_PATH)) if APP_ICON_PATH.exists() else self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray = QSystemTrayIcon(tray_icon, self)
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
        self._register_marker_custom_hotkeys()
        self.hotkeys.start_global_hotkeys()

    def _register_marker_custom_hotkeys(self) -> None:
        current_keys = {item["key"] for item in self.marker_service.custom_hotkeys()}
        for key in list(self._marker_custom_callback_keys - current_keys):
            self.hotkeys.unregister_callback(key)
            self._marker_custom_callback_keys.discard(key)

        for key in current_keys:
            self.hotkeys.register_callback(key, lambda item_key=key: self._save_marker_custom_hotkey(item_key))
            self._marker_custom_callback_keys.add(key)

    def _save_marker_custom_hotkey(self, key: str) -> None:
        item = self.marker_service.custom_hotkey_for_key(key)
        if item is None:
            return

        target = self.marker_service.save_marker(item["message"])
        if self.marker_last_label is not None:
            self.marker_last_label.setText(f"Última marcação salva em: {target.name}")
        self._refresh_marker_page()

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

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow_home_modules()

    def _reflow_home_modules(self, force: bool = False) -> None:
        if self.home_modules_layout is None:
            return
        columns = 1 if self.width() < 1120 else 2
        if not force and columns == self._home_module_columns:
            return
        while self.home_modules_layout.count():
            self.home_modules_layout.takeAt(0)
        cards: list[QWidget] = list(self.home_module_cards)
        if self.add_plugin_card is not None:
            cards.append(self.add_plugin_card)
        for index, card in enumerate(cards):
            self.home_modules_layout.addWidget(card, index // columns, index % columns)
        for column in range(2):
            self.home_modules_layout.setColumnStretch(column, 1 if column < columns else 0)
        self._home_module_columns = columns

    # ---- Plugins / marketplace -----------------------------------------

    def _open_marketplace(self) -> None:
        dialog = PluginMarketplaceDialog(self.plugin_manager, self)
        dialog.plugin_installed.connect(self._on_plugin_installed)
        dialog.plugin_removed.connect(self._on_plugin_removed)
        dialog.exec()

    def _on_plugin_installed(self, plugin: object) -> None:
        if not isinstance(plugin, InstalledPlugin):
            return
        if plugin.id in self._plugin_page_ids:
            # Atualizacao de um plugin ja carregado: recarrega no lugar, sem
            # precisar reiniciar o app.
            self._reload_plugin(plugin)
            self._refresh_add_plugin_badge(0)
            QMessageBox.information(
                self,
                "Plugin atualizado",
                f"{plugin.name} foi atualizado para a v{plugin.version} e recarregado.",
            )
            return
        self._integrate_new_plugin(plugin)

    def _integrate_new_plugin(self, plugin: InstalledPlugin) -> None:
        if not self._add_plugin_page(plugin):
            QMessageBox.warning(
                self,
                "Plugin",
                f"{plugin.name} foi baixado, mas não pôde ser carregado:\n"
                f"{plugin.error or 'erro desconhecido'}",
            )
            return
        self._append_plugin_card(plugin)
        self._add_plugin_subnav_button(plugin)
        self._reflow_home_modules(force=True)
        self._refresh_help_page()
        QMessageBox.information(
            self,
            "Plugin instalado",
            f"{plugin.name} foi instalado e já está disponível no hub.",
        )

    def _on_plugin_removed(self, plugin_id: str) -> None:
        """Tira card, pagina e subnav de um plugin removido (sem reiniciar)."""
        # Se a pagina do plugin esta em foco, volta para o inicio.
        if self.pages.currentIndex() == self.page_indexes.get(plugin_id):
            self._select_page("home")

        for index, card in enumerate(list(self.home_module_cards)):
            if getattr(card.module, "module_id", None) == plugin_id:
                self.home_module_cards.pop(index)
                card.deleteLater()
                break

        # O container fica no stack, mas e esvaziado e sai da navegacao (remover
        # do QStackedWidget embaralharia os indices das outras paginas).
        container = self._plugin_page_containers.pop(plugin_id, None)
        if container is not None:
            layout = container.layout()
            while layout is not None and layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        self._plugin_page_ids.discard(plugin_id)
        self.page_indexes.pop(plugin_id, None)

        button = self.plugin_nav_buttons.pop(plugin_id, None)
        if button is not None:
            button.deleteLater()

        self._reflow_home_modules(force=True)
        self._refresh_help_page()

    def _check_plugin_updates_async(self) -> None:
        if not self.plugin_manager.installed():
            return
        worker = _CatalogWorker(self.plugin_manager)
        worker.loaded.connect(self._on_updates_checked)
        self._plugin_update_worker = worker
        worker.start()

    def _on_updates_checked(self, entries: list) -> None:
        updates = self.plugin_manager.updates_available(entries)
        self._refresh_add_plugin_badge(len(updates))

    def _refresh_add_plugin_badge(self, count: int) -> None:
        if self.add_plugin_card is not None:
            self.add_plugin_card.set_update_badge(count)

    # ---- Auto-update do app --------------------------------------------

    def _check_app_update_async(self, auto: bool = False) -> None:
        if self._app_update_worker is not None and self._app_update_worker.isRunning():
            return
        if not auto and self.app_update_status_label is not None:
            self.app_update_status_label.setText("Verificando atualizações...")
        worker = AppUpdateCheckWorker()
        worker.result.connect(lambda release, is_auto=auto: self._on_app_update_result(release, is_auto))
        self._app_update_worker = worker
        worker.start()

    def _on_app_update_result(self, release: object, auto: bool) -> None:
        if release is None:
            if not auto and self.app_update_status_label is not None:
                self.app_update_status_label.setText(
                    f"Você está na versão mais recente (v{app_update.current_version()})."
                )
            return
        if self.app_update_status_label is not None:
            self.app_update_status_label.setText(
                f"Atualização disponível: v{getattr(release, 'version', '?')}"
            )
        # No boot (auto) só abre sozinho no portable congelado, uma vez.
        if auto and (not app_update.is_frozen() or self._app_update_shown):
            return
        self._app_update_shown = True
        AppUpdateDialog(release, on_quit=self._quit_from_tray, parent=self).exec()

    # ---- Ajuda ----------------------------------------------------------

    _BUILTIN_HELP = [
        (
            "Marcador",
            "#37F2FF",
            "Registra eventos da sua live com data/hora em um arquivo de texto por jogo.\n\n"
            "• \"Marcar agora\" ou a hotkey salvam uma anotação no arquivo ativo.\n"
            "• \"Novo jogo\" cria/troca o arquivo ativo (um txt por jogo/sessão).\n"
            "• Você pode criar mensagens pré-setadas com hotkey própria.\n"
            "• Ótimo para marcar melhores momentos e cortar depois pelo horário.",
        ),
        (
            "Contador",
            "#FF4FD8",
            "Overlays de contador transparentes, prontos para o OBS.\n\n"
            "• Crie presets com título, prefixo, limite, fonte e ícone.\n"
            "• Cada contador pode ter uma hotkey que incrementa (e opcionalmente\n"
            "  salva uma marcação no Marcador).\n"
            "• Abra os overlays e capture as janelas no OBS; resete ou feche pelo hub\n"
            "  ou pelas hotkeys globais.",
        ),
        (
            "Atalhos (Hotkeys)",
            "#B9FF43",
            "Atalhos globais funcionam mesmo com o jogo em foco.\n\n"
            "• Configure cada ação na tela \"Atalhos\"; conflitos são detectados.\n"
            "• No Windows use o pacote keyboard; no macOS, o pynput (exige permissão\n"
            "  de Acessibilidade).",
        ),
    ]

    def _help_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 22, 0)
        layout.setSpacing(16)

        title = QLabel("Ajuda")
        title.setObjectName("PageTitle")
        intro = QLabel(
            "O que cada ferramenta faz. Ao instalar um plugin, a ajuda dele aparece "
            "aqui automaticamente."
        )
        intro.setObjectName("Muted")
        intro.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(intro)

        container = QWidget()
        self.help_layout = QVBoxLayout(container)
        self.help_layout.setContentsMargins(0, 0, 0, 0)
        self.help_layout.setSpacing(16)
        layout.addWidget(container)
        layout.addStretch(1)

        self._refresh_help_page()
        return self._scrollable_page(page)

    def _help_panel(self, title: str, body: str, accent: str, icon_path: str = "") -> QWidget:
        panel = NeonPanel(accent=accent)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 16, 18, 16)
        panel_layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(10)
        if icon_path and Path(icon_path).exists():
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                icon_label = QLabel()
                icon_label.setFixedSize(28, 28)
                icon_label.setPixmap(
                    pixmap.scaled(
                        28, 28, Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                header.addWidget(icon_label, 0)
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        header.addWidget(title_label, 1)
        panel_layout.addLayout(header)

        body_label = QLabel(body)
        body_label.setObjectName("Muted")
        body_label.setWordWrap(True)
        panel_layout.addWidget(body_label)
        return panel

    def _refresh_help_page(self) -> None:
        if self.help_layout is None:
            return
        while self.help_layout.count():
            item = self.help_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for title, accent, body in self._BUILTIN_HELP:
            self.help_layout.addWidget(self._help_panel(title, body, accent))

        plugins = self.plugin_manager.installed()
        if plugins:
            divider = QLabel("Plugins instalados")
            divider.setObjectName("SectionTitle")
            self.help_layout.addWidget(divider)
        for plugin in plugins:
            info = plugin.module_info
            name = (getattr(info, "title", "") or plugin.name)
            body = plugin.help or (
                getattr(info, "subtitle", "") or "Este plugin não forneceu texto de ajuda."
            )
            self.help_layout.addWidget(
                self._help_panel(name, body, plugin.accent, icon_path=plugin.icon_path or "")
            )

    def _refresh_marker_page(self) -> None:
        if self.marker_active_label is None or self.marker_folder_label is None:
            return

        active_name = self.marker_service.active_file().name
        marker_count = self.marker_service.marker_count()
        self.marker_active_label.setText(f"Arquivo ativo: {active_name}  |  {marker_count} marcações")
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
                self.marker_recent_list.addItem("Nenhuma marcação salva neste arquivo.")

        self._refresh_marker_custom_hotkeys_list()

        if self.marker_files_list is None:
            return
        self.marker_files_list.clear()
        current = self.marker_service.active_file().name
        for path in self.marker_service.files():
            label = f"{path.name}    | ativo" if path.name == current else path.name
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, path.name)
            if path.name == current:
                item.setForeground(QColor("#B9FF43"))
                item.setToolTip("Arquivo ativo")
            self.marker_files_list.addItem(item)
            if path.name == current:
                self.marker_files_list.setCurrentItem(item)

    def _choose_marker_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta de marcações", str(self.marker_service.folder()))
        if not folder:
            return
        self.config.set("marker.folder", folder)
        self._refresh_marker_page()

    def _open_marker_folder(self) -> None:
        self._open_path(self.marker_service.folder(), "pasta de marcações")

    def _open_active_marker_file(self) -> None:
        path = self.marker_service.active_file()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, "Marcador", f"Não foi possível preparar o arquivo ativo: {exc}")
            return
        self._open_path(path, "arquivo ativo")

    def _open_path(self, path: Path, label: str) -> None:
        try:
            open_path(path)
        except (AttributeError, OSError) as exc:
            QMessageBox.warning(self, "Marcador", f"Não foi possível abrir {label}: {exc}")

    def _save_marker_from_page(self) -> None:
        if self.marker_event_input is None:
            return
        text = self.marker_event_input.text().strip()
        if not text:
            return
        target = self.marker_service.save_marker(text)
        self.marker_event_input.clear()
        if self.marker_last_label is not None:
            self.marker_last_label.setText(f"Última marcação salva em: {target.name}")
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

    def _refresh_marker_custom_hotkeys_list(self) -> None:
        if self.marker_custom_hotkeys_list is None:
            return

        selected_key = None
        selected = self.marker_custom_hotkeys_list.selectedItems()
        if selected:
            selected_key = selected[0].data(Qt.ItemDataRole.UserRole)

        self.marker_custom_hotkeys_list.clear()
        custom_keys = {item["key"] for item in self.marker_service.custom_hotkeys()}
        bindings = [binding for binding in self.hotkeys.all_bindings() if binding["key"] in custom_keys]

        if not bindings:
            empty = QListWidgetItem("Nenhuma hotkey de mensagem criada.")
            empty.setFlags(empty.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.marker_custom_hotkeys_list.addItem(empty)
            return

        for binding in bindings:
            item = QListWidgetItem(
                f"{binding['sequence']}  |  {str(binding['label']).removeprefix('Mensagem: ')}"
            )
            item.setData(Qt.ItemDataRole.UserRole, binding["key"])
            self.marker_custom_hotkeys_list.addItem(item)
            if binding["key"] == selected_key:
                self.marker_custom_hotkeys_list.setCurrentItem(item)

    def _add_marker_custom_hotkey(self) -> None:
        if self.marker_custom_hotkey_message_input is None or self.marker_custom_hotkey_sequence_input is None:
            return

        message = self.marker_custom_hotkey_message_input.text().strip()
        sequence = self.marker_custom_hotkey_sequence_input.keySequence().toString(QKeySequence.SequenceFormat.NativeText).strip()
        if not message:
            QMessageBox.warning(self, "Hotkey do marcador", "Digite a mensagem que sera salva no txt.")
            self.marker_custom_hotkey_message_input.setFocus()
            return
        if not sequence:
            QMessageBox.warning(self, "Hotkey do marcador", "Escolha uma hotkey para essa mensagem.")
            self.marker_custom_hotkey_sequence_input.setFocus()
            return

        conflict = self.hotkeys.find_conflict("", sequence)
        if conflict:
            QMessageBox.warning(self, "Conflito de atalho", f"Esse atalho ja esta em uso por: {conflict}")
            self.marker_custom_hotkey_sequence_input.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
            self._begin_hotkey_capture(self.marker_custom_hotkey_sequence_input)
            return

        item = self.marker_service.add_custom_hotkey(message, sequence)
        self._register_marker_custom_hotkeys()
        self._resume_hotkey_services_after_capture()
        self._hotkey_capture_editor = None
        self._mark_hotkey_editor(self.marker_custom_hotkey_sequence_input, False)
        self._set_hotkey_capture_message("Hotkey criada. Atalhos globais ativos.", False)
        self.marker_custom_hotkey_message_input.clear()
        self.marker_custom_hotkey_sequence_input.setKeySequence(QKeySequence())
        self._refresh_marker_custom_hotkeys_list()
        self._refresh_hotkeys_page()
        QMessageBox.information(self, "Hotkey do marcador", f"Hotkey criada: {sequence} -> {item['message']}")

    def _remove_selected_marker_custom_hotkey(self) -> None:
        if self.marker_custom_hotkeys_list is None:
            return
        selected = self.marker_custom_hotkeys_list.selectedItems()
        if not selected:
            QMessageBox.information(self, "Hotkey do marcador", "Selecione uma hotkey para remover.")
            return

        key = selected[0].data(Qt.ItemDataRole.UserRole)
        if not key:
            return

        if self.marker_service.remove_custom_hotkey(str(key)):
            self.hotkeys.unregister_callback(str(key))
            self._marker_custom_callback_keys.discard(str(key))
            self._register_marker_custom_hotkeys()
            self.hotkeys.start_global_hotkeys()
            self._refresh_marker_custom_hotkeys_list()
            self._refresh_hotkeys_page()

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
            self.marker_last_label.setText(f"Última marcação salva em: {file_name}")
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
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta de marcações", self.setting_marker_folder.text())
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
            QMessageBox.warning(self, "Backup", f"Não foi possível exportar o backup: {exc}")
            return

        QMessageBox.information(
            self,
            "Backup",
            f"Backup salvo em:\n{path}\n\nMarcações: {summary.marker_files}\nArquivos do contador: {summary.counter_files}",
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
            "Restaurar esse backup agora? Configurações e arquivos com o mesmo nome podem ser sobrescritos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._close_counter_overlays()
        try:
            summary = self.backup_service.restore_backup(Path(source))
        except (BackupError, OSError, ValueError) as exc:
            QMessageBox.warning(self, "Backup", f"Não foi possível restaurar o backup: {exc}")
            return

        self._register_marker_custom_hotkeys()
        self.hotkeys.start_global_hotkeys()
        self._sync_settings_inputs()
        self._refresh_marker_page()
        self._refresh_hotkeys_page()
        self._refresh_counter_page()
        QMessageBox.information(
            self,
            "Backup",
            f"Backup restaurado.\n\nMarcações: {summary.marker_files}\nArquivos do contador: {summary.counter_files}",
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
        QMessageBox.information(self, "Configurações", "Configurações salvas.")

    def _open_selected_counter_preset(self) -> None:
        preset_path = self._selected_counter_preset_path()
        if preset_path is None:
            return
        try:
            configs = self.counter_service.load_preset(preset_path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Preset inválido", f"Não foi possível abrir o preset: {exc}")
            return

        if not configs:
            QMessageBox.warning(self, "Preset vazio", "Esse arquivo não tem contadores válidos.")
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
            QMessageBox.warning(self, "Preset inválido", f"Não foi possível editar o preset: {exc}")
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
            QMessageBox.warning(self, "Preset inválido", f"Não foi possível duplicar o preset: {exc}")
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
            QMessageBox.warning(self, "Marcador", f"Não foi possível criar o txt: {exc}")
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
                QMessageBox.warning(self, "Marcador", f"Não foi possível preparar {marker_file}: {exc}")
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
            self.marker_last_label.setText(f"Última marcação salva em: {file_name}")
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
