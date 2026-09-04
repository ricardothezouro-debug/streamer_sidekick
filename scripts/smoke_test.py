"""Sobe o hub inteiro sem display e derruba tudo em seguida.

Existe porque os testes de unidade nao pegam a classe de bug que mais dói aqui:
falhas que so acontecem com a aplicacao Qt de pe e as threads de hotkey vivas.
No macOS, por exemplo, um listener do pynput por atalho aborta o processo no
arranque -- sem excecao, sem stack trace, e nenhum teste puro veria isso.

Roda no CI (Windows e macOS) e tambem serve para conferir uma instalacao local:

    QT_QPA_PLATFORM=offscreen PYTHONPATH=src python scripts/smoke_test.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from streamer_sidekick import __version__
from streamer_sidekick.core import hotkey_backend
from streamer_sidekick.core.config import ConfigStore
from streamer_sidekick.core.diagnostics import DiagnosticService
from streamer_sidekick.core.hotkeys import HotkeyManager
from streamer_sidekick.core.modules import ModuleRegistry
from streamer_sidekick.core.paths import app_data_dir
from streamer_sidekick.core.plugins import PluginManager
from streamer_sidekick.modules.counter.overlay import CounterOverlay
from streamer_sidekick.modules.counter.service import CounterService
from streamer_sidekick.modules.marker.service import MarkerService
from streamer_sidekick.ui.hub_window import HubWindow
from streamer_sidekick.ui.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    apply_theme(app)

    print(f"versao      : {__version__}")
    print(f"plataforma  : {sys.platform}")
    print(f"dados do app: {app_data_dir()}")
    print(f"hotkeys     : {hotkey_backend.backend_name()} "
          f"(disponivel: {hotkey_backend.is_available()})")

    config = ConfigStore()
    hotkeys = HotkeyManager(config)
    marker = MarkerService(config)
    counter = CounterService(config)

    modules = ModuleRegistry()
    modules.register(marker.module_info())
    modules.register(counter.module_info())

    plugins = PluginManager()
    plugins.load()

    window = HubWindow(
        config=config,
        hotkeys=hotkeys,
        modules=modules,
        marker_service=marker,
        counter_service=counter,
        plugin_manager=plugins,
    )
    window.show()
    print(f"atalhos     : {hotkeys.registered_sequences()}")

    # Overlays registram os proprios atalhos: e o cenario que derrubava o macOS.
    state_file = Path(tempfile.mkdtemp()) / "state.json"
    overlays = [
        CounterOverlay({"hotkey": f"Ctrl+Alt+{i}", "prefixo": "N: "}, state_file, i, marker)
        for i in (1, 2, 3)
    ]
    for overlay in overlays:
        overlay.show()
        overlay.increment()

    for item in DiagnosticService(config, hotkeys, marker, counter).run():
        print(f"  [{item.status}] {item.title}: {item.detail}")

    def finish() -> None:
        for overlay in overlays:
            overlay.close()
        hotkeys.stop_global_hotkeys()
        # O app real sai com os._exit(); aqui saimos pelo caminho normal do Qt,
        # entao esperamos as threads de rede para nao destruir um QThread vivo.
        for attr in ("_releases_worker", "_app_update_worker", "_plugin_update_worker"):
            worker = getattr(window, attr, None)
            if worker is not None and worker.isRunning():
                worker.wait(5000)
        window.close()
        app.quit()

    QTimer.singleShot(1500, finish)
    app.exec()
    print("smoke test OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
