import sys

from PySide6.QtWidgets import QApplication

from streamer_sidekick.core.config import ConfigStore
from streamer_sidekick.core.hotkeys import HotkeyManager
from streamer_sidekick.core.modules import ModuleRegistry
from streamer_sidekick.modules.counter.service import CounterService
from streamer_sidekick.modules.marker.service import MarkerService
from streamer_sidekick.ui.hub_window import HubWindow
from streamer_sidekick.ui.theme import apply_theme


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Streamer Sidekick")
    app.setOrganizationName("Streamer Sidekick")
    app.setStyle("Fusion")
    apply_theme(app)

    config = ConfigStore()
    hotkeys = HotkeyManager(config)
    marker = MarkerService(config)
    counter = CounterService(config)

    modules = ModuleRegistry()
    modules.register(marker.module_info())
    modules.register(counter.module_info())

    window = HubWindow(
        config=config,
        hotkeys=hotkeys,
        modules=modules,
        marker_service=marker,
        counter_service=counter,
    )
    if config.get("hub.start_minimized", False):
        window.hide()
    else:
        window.show()

    return app.exec()
