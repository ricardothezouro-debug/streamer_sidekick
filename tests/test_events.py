"""Barramento de eventos: o que um plugin vê quando assina e quando o hub publica."""


def test_quem_assina_recebe_o_evento_na_ordem_em_que_assinou():
    from streamer_sidekick.core import events

    recebidos = []
    cancelar_a = events.subscribe("teste.ordem", lambda dados: recebidos.append(("a", dados)))
    cancelar_b = events.subscribe("teste.ordem", lambda dados: recebidos.append(("b", dados)))
    try:
        events.publish("teste.ordem", {"valor": 1})
    finally:
        cancelar_a()
        cancelar_b()

    assert recebidos == [("a", {"valor": 1}), ("b", {"valor": 1})]


def test_ouvinte_com_erro_nao_impede_os_outros_e_vai_para_o_log(caplog):
    from streamer_sidekick.core import events

    def quebra(_dados):
        raise RuntimeError("plugin com defeito")

    recebidos = []
    cancelar_a = events.subscribe("teste.erro", quebra)
    cancelar_b = events.subscribe("teste.erro", recebidos.append)
    try:
        with caplog.at_level("ERROR", logger="streamer_sidekick.core.events"):
            events.publish("teste.erro", {"valor": 2})
    finally:
        cancelar_a()
        cancelar_b()

    assert recebidos == [{"valor": 2}], "o segundo ouvinte recebe mesmo com o primeiro quebrando"
    assert "teste.erro" in caplog.text and "plugin com defeito" in caplog.text


def test_evento_chega_na_thread_de_quem_publicou():
    import threading

    from streamer_sidekick.core import events

    threads = []
    cancelar = events.subscribe("teste.thread", lambda _dados: threads.append(threading.get_ident()))
    try:
        publicadora = threading.Thread(target=lambda: events.publish("teste.thread", {}))
        publicadora.start()
        publicadora.join(timeout=5)
    finally:
        cancelar()

    assert threads == [publicadora.ident], "como os atalhos globais: quem assina recebe na thread de fundo"


def test_cancelar_para_a_entrega_e_pode_ser_chamado_de_novo():
    from streamer_sidekick.core import events

    recebidos = []
    cancelar = events.subscribe("teste.cancelar", recebidos.append)
    events.publish("teste.cancelar", {"n": 1})
    cancelar()
    events.publish("teste.cancelar", {"n": 2})
    cancelar()  # o plugin pode cancelar no encerrar() mesmo que já tenha cancelado antes

    assert recebidos == [{"n": 1}]


def test_publicar_sem_ninguem_assinando_nao_quebra():
    from streamer_sidekick.core import events

    events.publish("teste.ninguem", {"n": 1})


def test_barramento_nao_depende_do_qt():
    import subprocess
    import sys
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src"
    codigo = (
        "import sys; sys.path.insert(0, r'%s'); "
        "import streamer_sidekick.core.events; "
        "print('PySide6' in sys.modules)" % src
    )
    saida = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, timeout=60)
    assert saida.returncode == 0, saida.stderr
    assert saida.stdout.strip() == "False", "plugins e o motor da nuvem usam o barramento sem interface"


# ---- o Marcador publica marker.saved ----------------------------------------


def _marcador(tmp_path):
    from streamer_sidekick.core.config import ConfigStore
    from streamer_sidekick.modules.marker.service import MarkerService

    config = ConfigStore(path=tmp_path / "config.json")
    config.set("marker.folder", str(tmp_path / "markers"))
    config.set("marker.active_file", "dredge.txt")
    return MarkerService(config)


def _assinar(nome):
    from streamer_sidekick.core import events

    recebidos = []
    return recebidos, events.subscribe(nome, recebidos.append)


def test_marcar_publica_marker_saved_com_o_que_foi_gravado(tmp_path):
    from datetime import datetime

    marcador = _marcador(tmp_path)
    recebidos, cancelar = _assinar("marker.saved")
    try:
        alvo = marcador.save_marker("  boss derrotado  ")
    finally:
        cancelar()

    linha = alvo.read_text(encoding="utf-8").splitlines()[-1]
    gravado = datetime.strptime(linha[1:20], "%Y-%m-%d %H:%M:%S")
    assert recebidos == [{"file": "dredge.txt", "text": "boss derrotado", "when": gravado.isoformat()}]
    assert linha == f"[{gravado:%Y-%m-%d %H:%M:%S}] boss derrotado"


def test_marcar_em_outro_arquivo_informa_esse_arquivo(tmp_path):
    marcador = _marcador(tmp_path)
    recebidos, cancelar = _assinar("marker.saved")
    try:
        marcador.save_marker("morri", "kh1")  # o contador marca no arquivo dele, não no ativo
    finally:
        cancelar()

    assert [r["file"] for r in recebidos] == ["kh1.txt"]


def test_texto_vazio_nao_grava_nem_publica(tmp_path):
    marcador = _marcador(tmp_path)
    recebidos, cancelar = _assinar("marker.saved")
    try:
        marcador.save_marker("   ")
    finally:
        cancelar()

    assert recebidos == []


# ---- preferências publicam preferences.changed -------------------------------


def test_mudar_preferencia_publica_e_configuracao_da_maquina_nao(tmp_path):
    from streamer_sidekick.core.config import ConfigStore

    config = ConfigStore(path=tmp_path / "config.json")
    recebidos, cancelar = _assinar("preferences.changed")
    try:
        config.set("hub.wallpaper", "noite")                  # preferência
        config.set("marker.folder", str(tmp_path / "pasta"))  # configuração da máquina
        config.set("hub.run_at_startup", True)                # configuração da máquina
        config.set("hub.favorites", ["marker", "clipit"])     # preferência
    finally:
        cancelar()

    assert recebidos == [{"key": "hub.wallpaper"}, {"key": "hub.favorites"}]


def test_gravar_o_mesmo_valor_de_novo_nao_publica(tmp_path):
    from streamer_sidekick.core.config import ConfigStore

    config = ConfigStore(path=tmp_path / "config.json")
    config.set("hub.wallpaper", "noite")
    recebidos, cancelar = _assinar("preferences.changed")
    try:
        config.set("hub.wallpaper", "noite")
    finally:
        cancelar()

    assert recebidos == []


def test_lista_alterada_no_lugar_tambem_publica(tmp_path):
    from streamer_sidekick.core.config import ConfigStore

    config = ConfigStore(path=tmp_path / "config.json")
    config.set("hub.favorites", ["marker"])
    recebidos, cancelar = _assinar("preferences.changed")
    try:
        favoritos = config.get("hub.favorites")
        favoritos.append("clipit")  # a tela mexe na própria lista e grava a mesma lista
        config.set("hub.favorites", favoritos)
    finally:
        cancelar()

    assert recebidos == [{"key": "hub.favorites"}]


def test_trocar_atalho_publica_com_o_id_do_atalho(tmp_path):
    from streamer_sidekick.core.config import ConfigStore
    from streamer_sidekick.core.hotkeys import HotkeyManager

    config = ConfigStore(path=tmp_path / "config.json")
    atalhos = HotkeyManager(config)
    recebidos, cancelar = _assinar("preferences.changed")
    try:
        assert atalhos.set_binding("marker.open_event", "Ctrl+Alt+J") is None
        atalhos.set_enabled("hub.show", False)
    finally:
        cancelar()

    assert recebidos == [{"key": "hotkeys.marker.open_event"}, {"key": "hotkeys.hub.show"}]
    salvo = ConfigStore(path=tmp_path / "config.json").get("hotkeys")
    assert salvo["marker.open_event"] == {"sequence": "Ctrl+Alt+J", "enabled": True}, "o id com ponto continua inteiro"


def test_remover_mensagem_rapida_publica_a_lista_e_o_atalho(tmp_path):
    marcador = _marcador(tmp_path)
    item = marcador.add_custom_hotkey("boss derrotado", "Ctrl+Alt+B")
    marcador.config.set_in("hotkeys", item["key"], {"sequence": "Ctrl+Alt+B", "enabled": True})
    recebidos, cancelar = _assinar("preferences.changed")
    try:
        assert marcador.remove_custom_hotkey(item["key"])
    finally:
        cancelar()

    assert {"key": "marker.custom_hotkeys"} in recebidos
    assert {"key": f"hotkeys.{item['key']}"} in recebidos
    assert item["key"] not in marcador.config.get("hotkeys"), "o atalho some do config"


# ---- o Contador publica counter.preset_saved e counter.changed -----------------


def _contador(tmp_path):
    from streamer_sidekick.core.config import ConfigStore
    from streamer_sidekick.modules.counter.service import CounterService, default_counter_config

    config = ConfigStore(path=tmp_path / "config.json")
    config.set("counter.presets_folder", str(tmp_path / "presets"))
    return CounterService(config), default_counter_config


def test_salvar_preset_publica_com_o_nome_do_preset(tmp_path):
    servico, padrao = _contador(tmp_path)
    recebidos, cancelar = _assinar("counter.preset_saved")
    try:
        caminho = servico.save_preset("Dredge", [padrao(0)])          # criar
        servico.save_preset("Dredge", [padrao(0), padrao(1)], caminho)  # editar o mesmo
        servico.save_preset("Dredge (cópia)", [padrao(0)])            # duplicar
    finally:
        cancelar()

    assert recebidos == [{"preset": "Dredge"}, {"preset": "Dredge"}, {"preset": "Dredge (cópia)"}]


def _overlay(tmp_path, **ajustes):
    from PySide6.QtWidgets import QApplication

    from streamer_sidekick.modules.counter.overlay import CounterOverlay

    QApplication.instance() or QApplication([])
    _servico, padrao = _contador(tmp_path)
    config = padrao(0)
    config.update({"titulo": "Mortes", "hotkey": ""}, **ajustes)  # sem atalho: nada registrado no PC
    return CounterOverlay(config, tmp_path / "presets" / "Dredge_state.json", 0)


def test_incrementar_e_zerar_publicam_o_valor_novo(tmp_path):
    (tmp_path / "presets").mkdir()
    overlay = _overlay(tmp_path)
    recebidos, cancelar = _assinar("counter.changed")
    try:
        overlay.increment()
        overlay.increment()
        overlay.reset()
    finally:
        cancelar()
        overlay.close()

    assert recebidos == [
        {"preset": "Dredge", "counter": "Mortes", "value": 1},
        {"preset": "Dredge", "counter": "Mortes", "value": 2},
        {"preset": "Dredge", "counter": "Mortes", "value": 0},
    ]


def test_contador_no_limite_nao_publica_de_novo(tmp_path):
    (tmp_path / "presets").mkdir()
    overlay = _overlay(tmp_path, infinito=False, limite=1)
    recebidos, cancelar = _assinar("counter.changed")
    try:
        overlay.increment()  # 0 -> 1
        overlay.increment()  # já está no limite: nada muda
    finally:
        cancelar()
        overlay.close()

    assert [r["value"] for r in recebidos] == [1]
