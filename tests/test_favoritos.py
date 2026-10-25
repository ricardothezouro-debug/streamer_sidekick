"""Favoritos não são podados no disco (ticket 05, decisão Q30)."""


def test_aparecem_so_os_instalados_na_ordem_salva_e_no_maximo_4():
    from streamer_sidekick.ui.favorites import visible_favorites

    salvos = ["marker", "clipit", "counter", "launcher", "subtitler", "dredge"]
    instalados = {"marker", "counter", "launcher", "subtitler", "dredge"}  # sem o ClipIt neste PC

    assert visible_favorites(salvos, instalados) == ["marker", "counter", "launcher", "subtitler"]
    assert visible_favorites(salvos, instalados | {"clipit"}) == ["marker", "clipit", "counter", "launcher"], \
        "reinstalar o ClipIt traz o favorito de volta, no lugar dele"


def test_salvar_a_janela_mantem_os_que_nao_estao_instalados_aqui():
    from streamer_sidekick.ui.favorites import favorites_to_save

    salvos = ["marker", "clipit"]
    instalados = {"marker", "counter"}  # o ClipIt não está neste PC: não aparece na janela

    assert favorites_to_save(["counter", "marker"], salvos, instalados) == ["counter", "marker", "clipit"]
    assert favorites_to_save([], salvos, instalados) == ["clipit"], "desmarcar tudo aqui não apaga o de outro PC"


def _janela(tmp_path, monkeypatch, favoritos):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QSystemTrayIcon

    import streamer_sidekick.core.hotkey_backend as hk
    import streamer_sidekick.ui.hub_window as hub

    monkeypatch.setattr(hk, "register", lambda *a, **k: None)  # nada de atalho global no PC
    monkeypatch.setattr(hk, "is_available", lambda: False)

    class BandejaMuda(QSystemTrayIcon):
        def show(self):
            pass

        def setVisible(self, _visivel):
            pass

    monkeypatch.setattr(hub, "QSystemTrayIcon", BandejaMuda)
    # Sem rede no teste: novidades, atualização do app e dos plugins, e as
    # janelas de boas-vindas/atualização que abrem logo depois.
    for metodo in ("_load_releases_async", "_check_app_update_async", "_check_plugin_updates_async",
                   "_run_startup_dialogs"):
        monkeypatch.setattr(hub.HubWindow, metodo, lambda *a, **k: None)
    app = QApplication.instance() or QApplication([])
    from streamer_sidekick.core.config import ConfigStore
    from streamer_sidekick.core.hotkeys import HotkeyManager
    from streamer_sidekick.core.modules import ModuleRegistry
    from streamer_sidekick.core.plugins import PluginManager
    from streamer_sidekick.modules.counter.service import CounterService
    from streamer_sidekick.modules.marker.service import MarkerService

    config = ConfigStore(path=tmp_path / "config.json")
    config.set("hub.onboarded", True)
    config.set("hub.favorites", favoritos)
    marcador, contador = MarkerService(config), CounterService(config)
    modulos = ModuleRegistry()
    modulos.register(marcador.module_info())
    modulos.register(contador.module_info())
    janela = hub.HubWindow(config=config, hotkeys=HotkeyManager(config), modules=modulos,
                           marker_service=marcador, counter_service=contador, plugin_manager=PluginManager())
    janela.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    janela.show()
    app.processEvents()
    return janela, config


def _fechar(janela):
    """Fecha só a janela. O close() normal, sem bandeja visível, agenda a saída
    do app (hard_exit), e ela mataria o pytest no próximo teste que rodar eventos."""
    janela._quitting = True
    janela.close()
    janela.deleteLater()


def test_inicio_nao_poda_os_favoritos_salvos_e_conta_so_os_visiveis(tmp_path, monkeypatch):
    janela, config = _janela(tmp_path, monkeypatch, ["marker", "clipit", "counter"])  # sem o ClipIt aqui
    try:
        janela._reflow_favorites()

        assert config.get("hub.favorites") == ["marker", "clipit", "counter"], "o ClipIt continua salvo"
        assert [c.module.module_id for c in janela.home_favorite_cards] == ["marker", "counter"]
        assert janela.home_favorites_panel._meta == "2/4"
    finally:
        _fechar(janela)
