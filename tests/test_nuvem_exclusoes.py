"""Exclusões e backup da nuvem (ticket 10; decisões Q14, Q21, Q28 e Q29)."""
from datetime import date

import pytest

from supabase_falso import SupabaseFalso
from test_nuvem_sincronizar_marcador import EMAIL, PC


@pytest.fixture
def falso():
    return SupabaseFalso()


def _backup(pc, caminho_logico):
    return pc.dados / "cloud" / "backup" / date.today().isoformat() / caminho_logico


def _sincronizados(tmp_path, falso):
    pc, mac = PC(tmp_path, falso, "pc"), PC(tmp_path, falso, "mac")
    pc.escrever("dredge.txt", "[2026-10-25 10:00:00] começou\n")
    pc.sincronizar()
    mac.sincronizar()
    return pc, mac


def test_apagar_num_pc_tira_do_outro_e_guarda_no_backup(tmp_path, falso):
    pc, mac = _sincronizados(tmp_path, falso)
    (pc.marcacoes / "dredge.txt").unlink()

    assert pc.sincronizar().excluiu == ["marcador/dredge.txt"]
    assert falso.arquivo(EMAIL, "marcador/dredge.txt")["deleted"] is True

    assert mac.sincronizar().excluiu == ["marcador/dredge.txt"]
    assert mac.ler("dredge.txt") is None
    assert _backup(mac, "marcador/dredge.txt").read_text(encoding="utf-8") == "[2026-10-25 10:00:00] começou\n"
    assert pc.sincronizar().excluiu == [] and mac.sincronizar().excluiu == [], "não volta nem repete"


def test_sumir_da_nuvem_sem_marca_de_exclusao_nao_apaga_nada(tmp_path, falso):
    pc, _mac = _sincronizados(tmp_path, falso)
    falso.arquivos.clear()  # a linha some da tabela (ex.: apagada à mão no painel)

    relatorio = pc.sincronizar()

    assert relatorio.excluiu == [] and relatorio.subiu == ["marcador/dredge.txt"]
    assert pc.ler("dredge.txt") == "[2026-10-25 10:00:00] começou\n"


def test_apagado_aqui_e_editado_la_vale_a_edicao(tmp_path, falso):
    pc, mac = _sincronizados(tmp_path, falso)
    (pc.marcacoes / "dredge.txt").unlink()
    mac.escrever("dredge.txt", "[2026-10-25 10:00:00] começou\n[2026-10-25 11:00:00] platinei\n")
    mac.sincronizar()  # a edição chega na nuvem antes

    relatorio = pc.sincronizar()

    assert relatorio.baixou == ["marcador/dredge.txt"] and relatorio.excluiu == []
    assert "platinei" in pc.ler("dredge.txt")


def test_apagado_la_primeiro_e_editado_aqui_depois_vale_a_edicao(tmp_path, falso):
    pc, mac = _sincronizados(tmp_path, falso)
    (pc.marcacoes / "dredge.txt").unlink()
    pc.sincronizar()  # a exclusão chega na nuvem antes
    mac.escrever("dredge.txt", "[2026-10-25 10:00:00] começou\n[2026-10-25 11:00:00] platinei\n")

    assert mac.sincronizar().subiu == ["marcador/dredge.txt"], "a edição desfaz a exclusão"
    assert falso.arquivo(EMAIL, "marcador/dredge.txt")["deleted"] is False
    assert pc.sincronizar().baixou == ["marcador/dredge.txt"]
    assert "platinei" in pc.ler("dredge.txt")


def test_toda_substituicao_guarda_a_versao_do_pc_e_a_segunda_ganha_a_hora(tmp_path, falso):
    pc, mac = _sincronizados(tmp_path, falso)
    mac.escrever("dredge.txt", "[2026-10-25 10:00:00] começou\n[2026-10-25 11:00:00] platinei\n")
    mac.sincronizar()
    assert pc.sincronizar().baixou == ["marcador/dredge.txt"]  # 1ª substituição: download por cima
    assert _backup(pc, "marcador/dredge.txt").read_text(encoding="utf-8") == "[2026-10-25 10:00:00] começou\n"

    pc.escrever("dredge.txt", pc.ler("dredge.txt") + "[2026-10-25 11:10:00] nota do pc\n")
    mac.escrever("dredge.txt", mac.ler("dredge.txt") + "[2026-10-25 11:20:00] nota do mac\n")
    mac.sincronizar()
    assert pc.sincronizar().juntou == ["marcador/dredge.txt"]  # 2ª substituição: junção

    copias = {p.name for p in _backup(pc, "marcador/dredge.txt").parent.iterdir()}
    segunda = copias - {"dredge.txt"}
    assert "dredge.txt" in copias and len(segunda) == 1, copias
    assert next(iter(segunda)).startswith("dredge-"), "a segunda cópia do dia ganha a hora no nome"


def test_backups_com_mais_de_30_dias_somem_e_os_recentes_ficam(tmp_path, falso):
    from datetime import timedelta

    pc, _mac = _sincronizados(tmp_path, falso)
    raiz = pc.dados / "cloud" / "backup"
    velho = raiz / (date.today() - timedelta(days=31)).isoformat()
    recente = raiz / (date.today() - timedelta(days=29)).isoformat()
    outra = raiz / "minhas-coisas"  # pasta que não é do app: nunca é apagada
    for pasta in (velho, recente, outra):
        pasta.mkdir(parents=True)
        (pasta / "x.txt").write_text("x", encoding="utf-8")

    pc.sincronizar(simular=True)
    assert velho.exists(), "simular não apaga nada"
    pc.sincronizar()
    assert not velho.exists() and recente.exists() and outra.exists()


def test_simular_mostra_a_exclusao_sem_fazer(tmp_path, falso):
    pc, mac = _sincronizados(tmp_path, falso)
    (pc.marcacoes / "dredge.txt").unlink()
    pc.sincronizar()

    relatorio = mac.sincronizar(simular=True)

    assert relatorio.excluiu == ["marcador/dredge.txt"]
    assert mac.ler("dredge.txt") is not None and not (mac.dados / "cloud" / "backup").exists()
