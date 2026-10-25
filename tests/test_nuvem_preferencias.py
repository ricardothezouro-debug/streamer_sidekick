"""Preferências e atalhos por sistema na nuvem (ticket 11; ADR 0004; decisões Q35 e Q36)."""
import base64
import json
from datetime import date

import pytest

from supabase_falso import SupabaseFalso
from test_nuvem_sincronizar_marcador import EMAIL, PC

GERAL = "preferencias/geral.json"


class PCComPreferencias(PC):
    """Um PC com o app aberto: a sincronização usa o mesmo ConfigStore do app."""

    def __init__(self, raiz, falso, nome, sistema="windows"):
        from streamer_sidekick.core.config import ConfigStore

        self.config = ConfigStore(path=raiz / nome / "config.json")
        super().__init__(raiz, falso, nome, config=self.config, sistema=sistema)

    def sincronizar(self, **opcoes):
        return self.nuvem.sincronizar(**opcoes)  # com as preferências no relatório

    def mensagens(self):
        from streamer_sidekick.modules.marker.service import MarkerService

        return MarkerService(self.config).custom_hotkeys()


@pytest.fixture
def falso():
    return SupabaseFalso()


def _na_nuvem(falso, caminho):
    linha = falso.arquivo(EMAIL, caminho)
    return json.loads(base64.b64decode(linha["content_b64"])) if linha else None


def test_so_as_preferencias_da_lista_sobem(tmp_path, falso):
    pc = PCComPreferencias(tmp_path, falso, "pc")
    pc.config.set("hub.favorites", ["marker", "clipit"])
    pc.config.set("hub.wallpaper", "aurora")
    pc.config.set("hub.start_minimized", True)
    pc.config.set("hub.close_to_tray", False)
    pc.config.set("marker.active_file", "dredge.txt")
    pc.config.set("marker.custom_hotkeys", [{"key": "marker.custom.a1", "message": "boss", "sequence": "Ctrl+1"}])
    pc.config.set_in("hotkeys", "marker.custom.a1", {"sequence": "Ctrl+2", "enabled": True})
    # Configuração da máquina e coisas de plugin: nada disso sobe.
    pc.config.set("marker.folder", "D:/Lives/Marcacoes")
    pc.config.set("counter.presets_folder", "D:/Lives/Presets")
    pc.config.set("counter.last_preset", "D:/Lives/Presets/dredge.json")
    pc.config.set("hub.run_at_startup", True)
    pc.config.set("hub.onboarded", True)
    pc.config.set("app.last_version", "0.9.2")
    pc.config.set("plugins.clipit", {"pasta": "D:/Clips"})
    pc.config.set_in("hotkeys", "clipit.salvar", {"sequence": "F9", "enabled": True})

    assert sorted(pc.sincronizar().subiu) == ["preferencias/atalhos-windows.json", GERAL]

    assert _na_nuvem(falso, GERAL) == {
        "hub.favorites": ["marker", "clipit"],
        "hub.wallpaper": "aurora",
        "hub.start_minimized": True,
        "hub.close_to_tray": False,
        "marker.active_file": "dredge.txt",
        "marker.custom_hotkeys": [{"key": "marker.custom.a1", "message": "boss"}],  # sem a sequência
    }
    atalhos = _na_nuvem(falso, "preferencias/atalhos-windows.json")
    assert set(atalhos["hotkeys"]) == {"hub.show", "marker.open_event", "marker.new_game", "counter.reset_all",
                                       "counter.close_overlays", "marker.custom.a1"}, "atalho de plugin não sobe"
    assert atalhos["mensagens"] == {"marker.custom.a1": "Ctrl+1"}
    assert sorted(caminho for (_, caminho) in falso.arquivos) == ["preferencias/atalhos-windows.json", GERAL]


def test_atalho_do_mac_nao_muda_o_windows_e_o_segundo_windows_herda(tmp_path, falso):
    win = PCComPreferencias(tmp_path, falso, "win")
    mac = PCComPreferencias(tmp_path, falso, "mac", sistema="macos")
    win.config.set_in("hotkeys", "hub.show", {"sequence": "Ctrl+Alt+J", "enabled": True})
    win.sincronizar()
    mac.sincronizar()
    mac.config.set_in("hotkeys", "hub.show", {"sequence": "Meta+Alt+H", "enabled": True})
    mac.config.set("hub.favorites", ["counter"])  # preferência comum: vale nos dois
    mac.sincronizar()

    win.sincronizar()

    assert win.config.get("hotkeys")["hub.show"]["sequence"] == "Ctrl+Alt+J"
    assert win.config.get("hub.favorites") == ["counter"]
    assert mac.config.get("hotkeys")["hub.show"]["sequence"] == "Meta+Alt+H"

    outro_win = PCComPreferencias(tmp_path, falso, "win2")
    outro_win.sincronizar()
    assert outro_win.config.get("hotkeys")["hub.show"]["sequence"] == "Ctrl+Alt+J"
    assert outro_win.config.get("hub.favorites") == ["counter"]


def test_mensagem_criada_no_mac_chega_no_windows_sem_atalho_e_continua_la(tmp_path, falso):
    win = PCComPreferencias(tmp_path, falso, "win")
    mac = PCComPreferencias(tmp_path, falso, "mac", sistema="macos")
    win.sincronizar()
    mac.sincronizar()
    mac.config.set("marker.custom_hotkeys", [{"key": "marker.custom.b2", "message": "boss", "sequence": "Meta+1"}])
    mac.sincronizar()

    win.sincronizar()

    assert win.mensagens() == [{"key": "marker.custom.b2", "message": "boss", "sequence": ""}]
    win.config.set_in("hotkeys", "marker.custom.b2", {"sequence": "Ctrl+1", "enabled": True})  # escolhido em Atalhos
    win.sincronizar()
    mac.sincronizar()
    assert mac.mensagens() == [{"key": "marker.custom.b2", "message": "boss", "sequence": "Meta+1"}]
    assert "marker.custom.b2" not in (mac.config.get("hotkeys") or {}), "o atalho do Windows não vai para o Mac"


def test_mensagem_apagada_num_pc_sai_do_outro(tmp_path, falso):
    win = PCComPreferencias(tmp_path, falso, "win")
    win.config.set("marker.custom_hotkeys", [{"key": "marker.custom.c3", "message": "boss", "sequence": "Ctrl+1"}])
    win.sincronizar()
    mac = PCComPreferencias(tmp_path, falso, "mac", sistema="macos")
    mac.sincronizar()
    assert [item["key"] for item in mac.mensagens()] == ["marker.custom.c3"]

    win.config.set("marker.custom_hotkeys", [])
    win.sincronizar()
    mac.sincronizar()

    assert mac.mensagens() == []


def test_preferencia_baixada_nao_e_desfeita_pelo_proximo_salvamento_do_app(tmp_path, falso):
    win = PCComPreferencias(tmp_path, falso, "win")
    mac = PCComPreferencias(tmp_path, falso, "mac", sistema="macos")
    win.sincronizar()
    mac.sincronizar()
    mac.config.set("hub.favorites", ["counter", "marker"])
    mac.sincronizar()

    win.sincronizar()
    win.config.set("hub.start_minimized", True)  # o app aberto grava outra coisa depois

    no_disco = json.loads((win.dados / "config.json").read_text(encoding="utf-8"))
    assert no_disco["hub"]["favorites"] == ["counter", "marker"] and no_disco["hub"]["start_minimized"] is True


def test_conflito_em_preferencias_a_nuvem_vence_e_o_do_pc_vai_para_o_backup(tmp_path, falso):
    win = PCComPreferencias(tmp_path, falso, "win")
    mac = PCComPreferencias(tmp_path, falso, "mac", sistema="macos")
    win.sincronizar()
    mac.sincronizar()
    win.config.set("hub.favorites", ["marker"])
    mac.config.set("hub.favorites", ["counter"])
    mac.sincronizar()  # o Mac chega primeiro

    relatorio = win.sincronizar()

    assert GERAL in relatorio.baixou and win.config.get("hub.favorites") == ["counter"]
    backup = win.dados / "cloud" / "backup" / date.today().isoformat() / "preferencias" / "geral.json"
    assert json.loads(backup.read_text(encoding="utf-8"))["hub.favorites"] == ["marker"]


def test_sem_mudanca_nada_sobe_de_novo(tmp_path, falso):
    win = PCComPreferencias(tmp_path, falso, "win")
    win.sincronizar()

    relatorio = win.sincronizar()

    assert (relatorio.subiu, relatorio.baixou, relatorio.excluiu) == ([], [], [])


def test_o_config_grava_de_forma_atomica(tmp_path):
    from streamer_sidekick.core.config import ConfigStore

    config = ConfigStore(path=tmp_path / "config.json")
    config.set("hub.favorites", ["marker"])
    antes = (tmp_path / "config.json").read_bytes()

    with pytest.raises(TypeError):
        config.set("hub.wallpaper", object())  # quebra no meio da gravação

    assert (tmp_path / "config.json").read_bytes() == antes, "o arquivo antigo fica inteiro"
    assert [p.name for p in tmp_path.iterdir()] == ["config.json"], "sem temporário largado"


def test_o_sistema_vem_do_proprio_computador(monkeypatch):
    from streamer_sidekick.core.cloud import preferences

    for plataforma, esperado in (("win32", "windows"), ("darwin", "macos"), ("linux", "linux")):
        monkeypatch.setattr(preferences.sys, "platform", plataforma)
        assert preferences.sistema_atual() == esperado


def test_mensagem_sem_atalho_aparece_na_lista_do_marcador_e_nao_e_registrada(tmp_path, monkeypatch):
    from test_favoritos import _fechar, _janela

    janela, config = _janela(tmp_path, monkeypatch, [])
    try:
        config.set("marker.custom_hotkeys", [{"key": "marker.custom.d4", "message": "boss", "sequence": ""}])
        janela._refresh_marker_custom_hotkeys_list()

        textos = [janela.marker_custom_hotkeys_list.item(i).text()
                  for i in range(janela.marker_custom_hotkeys_list.count())]
        assert textos == ["Sem atalho neste sistema  |  boss"]
        assert all(sequencia for sequencia, _ in janela.hotkeys._registered), "nada registrado sem sequência"
    finally:
        _fechar(janela)
