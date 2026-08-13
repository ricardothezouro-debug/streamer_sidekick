import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from streamer_sidekick.core.config import ConfigStore
from streamer_sidekick.core.platform_utils import app_icon_path
from streamer_sidekick.core.hotkeys import HotkeyManager
from streamer_sidekick.core.modules import ModuleRegistry
from streamer_sidekick.core.plugins import PluginManager
from streamer_sidekick.modules.counter.service import CounterService
from streamer_sidekick.modules.marker.service import MarkerService
from streamer_sidekick.ui.hub_window import HubWindow
from streamer_sidekick.ui.theme import apply_theme


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Streamer Sidekick")
    app.setOrganizationName("Streamer Sidekick")
    app.setStyle("Fusion")
    icon_path = app_icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    apply_theme(app)

    config = ConfigStore()
    hotkeys = HotkeyManager(config)
    marker = MarkerService(config)
    counter = CounterService(config)

    modules = ModuleRegistry()
    modules.register(marker.module_info())
    modules.register(counter.module_info())

    plugin_manager = PluginManager()
    plugin_manager.load()

    window = HubWindow(
        config=config,
        hotkeys=hotkeys,
        modules=modules,
        marker_service=marker,
        counter_service=counter,
        plugin_manager=plugin_manager,
    )
    if config.get("hub.start_minimized", False):
        window.hide()
    else:
        window.show()

    return app.exec()
