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
