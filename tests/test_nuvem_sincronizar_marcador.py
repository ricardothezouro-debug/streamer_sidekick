"""Sincronizar o Marcador de ponta a ponta (ticket 09): dois PCs, uma conta, o Supabase falso."""
import pytest

from supabase_falso import SupabaseFalso

EMAIL = "gamox@exemplo.com"


class PC:
    """Uma pasta de dados do app, como num computador, logada na conta."""

    def __init__(self, raiz, falso, nome):
        from streamer_sidekick.core.cloud import Nuvem

        self.dados = raiz / nome
        self.marcacoes = self.dados / "markers"
        self.marcacoes.mkdir(parents=True)
        self.nuvem = Nuvem(self.dados, transporte=falso, url=falso.URL, chave=falso.ANON)
        self.nuvem.entrar(lambda montar_url: falso.autorizar(montar_url("http://127.0.0.1:53682/callback"), EMAIL))

    def escrever(self, nome, texto):
        (self.marcacoes / nome).write_text(texto, encoding="utf-8")

    def ler(self, nome):
        arquivo = self.marcacoes / nome
        return arquivo.read_text(encoding="utf-8") if arquivo.exists() else None

    def sincronizar(self, **opcoes):
        return self.nuvem.sincronizar(**opcoes)


@pytest.fixture
def falso():
    return SupabaseFalso()


def test_marcacao_feita_num_pc_aparece_no_outro(tmp_path, falso):
    pc, mac = PC(tmp_path, falso, "pc"), PC(tmp_path, falso, "mac")
    pc.escrever("dredge.txt", "[2026-10-25 10:30:00] boss derrotado\n")

    assert pc.sincronizar().subiu == ["marcador/dredge.txt"]
    assert mac.sincronizar().baixou == ["marcador/dredge.txt"]
    assert mac.ler("dredge.txt") == "[2026-10-25 10:30:00] boss derrotado\n"


def _dois_pcs_sincronizados(tmp_path, falso, texto="[2026-10-25 10:00:00] começou\n"):
    pc, mac = PC(tmp_path, falso, "pc"), PC(tmp_path, falso, "mac")
    pc.escrever("dredge.txt", texto)
    pc.sincronizar()
    mac.sincronizar()
    return pc, mac


def test_so_um_lado_mudou_vai_para_o_outro_sem_juntar(tmp_path, falso):
    pc, mac = _dois_pcs_sincronizados(tmp_path, falso)
    mac.escrever("dredge.txt", "[2026-10-25 10:00:00] começou\n[2026-10-25 11:00:00] platinei\n")

    relatorio_mac = mac.sincronizar()
    relatorio_pc = pc.sincronizar()

    assert (relatorio_mac.subiu, relatorio_mac.juntou) == (["marcador/dredge.txt"], [])
    assert (relatorio_pc.baixou, relatorio_pc.juntou) == (["marcador/dredge.txt"], [])
    assert pc.ler("dredge.txt") == mac.ler("dredge.txt")


def test_os_dois_mudaram_junta_as_linhas_e_os_dois_ficam_iguais(tmp_path, falso):
    pc, mac = _dois_pcs_sincronizados(tmp_path, falso)
    pc.escrever("dredge.txt", "[2026-10-25 10:00:00] começou\n[2026-10-25 10:20:00] morri\n")
    mac.escrever("dredge.txt", "[2026-10-25 10:00:00] começou\n[2026-10-25 10:10:00] achei o peixe\n")

    assert pc.sincronizar().subiu == ["marcador/dredge.txt"]
    assert mac.sincronizar().juntou == ["marcador/dredge.txt"]
    pc.sincronizar()

    esperado = ("[2026-10-25 10:00:00] começou\n[2026-10-25 10:10:00] achei o peixe\n"
                "[2026-10-25 10:20:00] morri\n")
    assert mac.ler("dredge.txt") == esperado and pc.ler("dredge.txt") == esperado


def test_primeira_sincronizacao_com_os_dois_lados_diferentes_junta(tmp_path, falso):
    pc, mac = PC(tmp_path, falso, "pc"), PC(tmp_path, falso, "mac")
    pc.escrever("dredge.txt", "[2026-10-25 10:20:00] morri\n")
    mac.escrever("dredge.txt", "[2026-10-25 10:10:00] achei o peixe\n")

    pc.sincronizar()
    assert mac.sincronizar().juntou == ["marcador/dredge.txt"]
    assert mac.ler("dredge.txt") == "[2026-10-25 10:10:00] achei o peixe\n[2026-10-25 10:20:00] morri\n"


def test_nome_com_maiuscula_diferente_vira_um_arquivo_so(tmp_path, falso):
    pc, mac = PC(tmp_path, falso, "pc"), PC(tmp_path, falso, "mac")
    pc.escrever("kh1.txt", "[2026-10-25 10:00:00] começou\n")
    pc.sincronizar()
    mac.escrever("Kh1.txt", "[2026-10-25 10:30:00] boss\n")

    relatorio = mac.sincronizar()

    assert relatorio.juntou == ["marcador/kh1.txt"], "usa o nome que já está na nuvem"
    assert falso.arquivo(EMAIL, "marcador/Kh1.txt") is None
    assert mac.ler("Kh1.txt") == "[2026-10-25 10:00:00] começou\n[2026-10-25 10:30:00] boss\n"


def test_ultimo_jogo_nunca_sobe_e_a_linha_do_clipit_sobe(tmp_path, falso):
    pc, mac = _dois_pcs_sincronizados(tmp_path, falso)
    pc.escrever("ultimo_jogo.txt", "dredge")
    with (pc.marcacoes / "dredge.txt").open("a", encoding="utf-8") as arquivo:  # o ClipIt escreve por fora do hub
        arquivo.write("[2026-10-25 10:40:00] boss — https://clips.twitch.tv/AbcXyz\n")

    assert pc.sincronizar().subiu == ["marcador/dredge.txt"]
    assert falso.arquivo(EMAIL, "marcador/ultimo_jogo.txt") is None
    mac.sincronizar()
    assert "clips.twitch.tv/AbcXyz" in mac.ler("dredge.txt")


def test_simular_nao_muda_nada(tmp_path, falso):
    pc, mac = _dois_pcs_sincronizados(tmp_path, falso)
    pc.escrever("dredge.txt", "[2026-10-25 10:00:00] começou\n[2026-10-25 10:20:00] morri\n")
    pc.escrever("wolong.txt", "[2026-10-25 12:00:00] novo jogo\n")
    base_antes = (pc.dados / "cloud" / "base.json").read_text(encoding="utf-8")
    nuvem_antes = dict(falso.arquivos)

    relatorio = pc.sincronizar(simular=True)

    assert relatorio.simulado and relatorio.subiu == ["marcador/dredge.txt", "marcador/wolong.txt"]
    assert falso.arquivos == nuvem_antes
    assert (pc.dados / "cloud" / "base.json").read_text(encoding="utf-8") == base_antes


def test_sem_conta_conectada_nada_muda(tmp_path, falso):
    from streamer_sidekick.core.cloud import INDISPONIVEL, PRECISA_ENTRAR

    pc = PC(tmp_path, falso, "pc")
    pc.escrever("dredge.txt", "[2026-10-25 10:00:00] começou\n")
    falso.fora_do_ar = True
    assert pc.sincronizar().conta.estado == INDISPONIVEL
    falso.fora_do_ar = False
    pc.nuvem.sair()
    relatorio = pc.sincronizar()
    assert relatorio.conta.estado == PRECISA_ENTRAR and not relatorio.subiu
    assert falso.arquivos == {}


def test_pasta_do_marcador_escolhida_fora_da_pasta_do_app(tmp_path, falso):
    import json

    pc = PC(tmp_path, falso, "pc")
    pasta = tmp_path / "Documentos" / "marcacoes"
    pasta.mkdir(parents=True)
    (pasta / "dredge.txt").write_text("[2026-10-25 10:00:00] começou\n", encoding="utf-8")
    (pc.dados / "config.json").write_text(json.dumps({"marker": {"folder": str(pasta)}}), encoding="utf-8")

    assert pc.sincronizar().subiu == ["marcador/dredge.txt"]


def test_servidor_recusando_no_meio_vira_indisponivel_e_a_proxima_vez_completa(tmp_path, falso, monkeypatch):
    from streamer_sidekick.core.cloud import INDISPONIVEL

    pc = PC(tmp_path, falso, "pc")
    pc.escrever("dredge.txt", "[2026-10-25 10:00:00] começou\n")
    monkeypatch.setattr(falso, "_gravar", lambda *_args: (500, {"message": "erro interno"}))

    assert pc.sincronizar().conta.estado == INDISPONIVEL
    monkeypatch.undo()
    assert pc.sincronizar().subiu == ["marcador/dredge.txt"], "nada ficou marcado como sincronizado"
