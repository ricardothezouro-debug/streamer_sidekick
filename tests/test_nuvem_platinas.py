"""Platinas na nuvem (ticket 13; ADR 0003; decisões Q37, Q38 e Q39)."""
import json
from datetime import date

import pytest

from supabase_falso import SupabaseFalso
from test_nuvem_sincronizar_marcador import EMAIL, PC

DREDGE = "platinas/dredge/progress.json"


class PCComPlatinas(PC):
    def guardar(self, guia, progresso, nome="progress.json"):
        pasta = self.dados / "platinas" / guia
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / nome).write_text(json.dumps(progresso), encoding="utf-8")

    def progresso(self, guia="dredge"):
        arquivo = self.dados / "platinas" / guia / "progress.json"
        return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else None


@pytest.fixture
def falso():
    return SupabaseFalso()


def _dois_pcs(tmp_path, falso, inicial):
    pc, mac = PCComPlatinas(tmp_path, falso, "pc"), PCComPlatinas(tmp_path, falso, "mac")
    pc.guardar("dredge", inicial)
    pc.sincronizar()
    mac.sincronizar()
    return pc, mac


# ------------------------------------------------------------ fusão pura
def test_fusao_o_que_um_lado_marcou_entra_e_o_que_desmarcou_sai():
    from streamer_sidekick.core.cloud.merge import fundir_progresso

    def fundir(base, local, nuvem):
        resultado = fundir_progresso(None if base is None else json.dumps(base).encode(),
                                     json.dumps(local).encode(), json.dumps(nuvem).encode())
        return None if resultado is None else json.loads(resultado)

    assert fundir(["a", "b"], ["a", "b", "c"], ["b", "a", "d"]) == ["a", "b", "c", "d"], "ordem do PC, depois a nuvem"
    assert fundir(["a", "b"], ["b"], ["a", "b", "d"]) == ["b", "d"], "desmarcado aqui sai"
    assert fundir(["a", "b"], ["a", "b", "c"], ["a"]) == ["a", "c"], "desmarcado lá sai"
    assert fundir(None, ["a"], ["b"]) == ["a", "b"], "sem base: junta tudo"
    assert fundir([1, 2], [1, 2, 3], [2]) == [2, 3], "ids numéricos"
    assert fundir({"done": ["a"], "aba": 1}, {"done": ["a", "b"], "aba": 2}, {"done": ["a", "c"], "aba": 3}) == \
        {"done": ["a", "b", "c"], "aba": 3}, "com done: os outros campos seguem a nuvem"
    assert fundir(["a"], ["a", "b"], {"done": ["a"]}) is None, "formatos diferentes: a nuvem vence (Q39)"
    assert fundir(None, {"marcados": ["a"]}, {"marcados": ["b"]}) is None, "formato desconhecido"


# ------------------------------------------------------------ dois PCs
def test_marcar_num_pc_e_outra_coisa_no_outro_fica_com_as_duas(tmp_path, falso):
    pc, mac = _dois_pcs(tmp_path, falso, ["peixe-1"])
    pc.guardar("dredge", ["peixe-1", "peixe-2"])
    mac.guardar("dredge", ["peixe-1", "santuario-1"])
    pc.sincronizar()

    assert mac.sincronizar().juntou == [DREDGE]
    pc.sincronizar()

    assert mac.progresso() == pc.progresso() == ["peixe-1", "santuario-1", "peixe-2"]


def test_desmarcar_num_pc_tira_do_outro_e_nao_volta(tmp_path, falso):
    pc, mac = _dois_pcs(tmp_path, falso, ["peixe-1", "peixe-2"])
    pc.guardar("dredge", ["peixe-1"])  # desmarcou por engano no PC
    mac.guardar("dredge", ["peixe-1", "peixe-2", "doca-1"])  # e marcou outra coisa no Mac
    pc.sincronizar()

    mac.sincronizar()
    pc.sincronizar()
    mac.sincronizar()
    pc.sincronizar()

    assert pc.progresso() == mac.progresso() == ["peixe-1", "doca-1"]


def test_formato_com_done_preserva_os_outros_campos_pela_regra_geral(tmp_path, falso):
    pc, mac = _dois_pcs(tmp_path, falso, {"done": ["q1"], "filtro": "todos"})
    pc.guardar("dredge", {"done": ["q1", "q2"], "filtro": "pc"})
    mac.guardar("dredge", {"done": ["q1", "q3"], "filtro": "mac"})
    pc.sincronizar()

    mac.sincronizar()

    assert mac.progresso() == {"done": ["q1", "q3", "q2"], "filtro": "pc"}


def test_formato_desconhecido_a_nuvem_vence_com_backup(tmp_path, falso):
    pc, mac = _dois_pcs(tmp_path, falso, {"marcados": ["a"]})
    pc.guardar("dredge", {"marcados": ["a", "b"]})
    mac.guardar("dredge", {"marcados": ["a", "c"]})
    pc.sincronizar()

    relatorio = mac.sincronizar()

    assert relatorio.baixou == [DREDGE] and mac.progresso() == {"marcados": ["a", "b"]}
    backup = mac.dados / "cloud" / "backup" / date.today().isoformat() / "platinas" / "dredge" / "progress.json"
    assert json.loads(backup.read_text(encoding="utf-8")) == {"marcados": ["a", "c"]}


def test_primeira_sincronizacao_com_os_dois_lados_diferentes_junta(tmp_path, falso):
    pc, mac = PCComPlatinas(tmp_path, falso, "pc"), PCComPlatinas(tmp_path, falso, "mac")
    pc.guardar("dredge", ["peixe-1"])
    mac.guardar("dredge", ["peixe-2"])
    pc.sincronizar()

    assert mac.sincronizar().juntou == [DREDGE]
    assert mac.progresso() == ["peixe-2", "peixe-1"]


def test_guia_novo_desce_inteiro_e_so_o_progresso_sobe(tmp_path, falso):
    pc, mac = PCComPlatinas(tmp_path, falso, "pc"), PCComPlatinas(tmp_path, falso, "mac")
    pc.guardar("dredge", ["peixe-1"])
    pc.guardar("dredge", {"x": 10, "y": 20}, nome="ui.json")  # posição do balão: é da tela deste PC
    (pc.dados / "platinas" / "dredge" / "cache").mkdir()
    (pc.dados / "platinas" / "dredge" / "cache" / "peixe-1.png").write_bytes(b"\x89PNG")
    pc.guardar("wolong", ["bandeira-1"])

    assert sorted(pc.sincronizar().subiu) == [DREDGE, "platinas/wolong/progress.json"]
    assert mac.sincronizar().baixou == [DREDGE, "platinas/wolong/progress.json"]
    assert mac.progresso("wolong") == ["bandeira-1"]
    assert sorted(caminho for (_, caminho) in falso.arquivos if caminho.startswith("platinas/")) == \
        [DREDGE, "platinas/wolong/progress.json"]
    assert falso.arquivo(EMAIL, "platinas/dredge/ui.json") is None


def test_base_que_nao_bate_com_o_hash_e_tratada_como_primeira_vez(tmp_path, falso):
    pc, mac = _dois_pcs(tmp_path, falso, ["peixe-1", "peixe-2"])
    copia = mac.dados / "cloud" / "base" / "platinas" / "dredge" / "progress.json"
    assert json.loads(copia.read_text(encoding="utf-8")) == ["peixe-1", "peixe-2"], "a cópia da base existe"
    copia.write_text("[]", encoding="utf-8")  # estragada
    pc.guardar("dredge", ["peixe-1"])
    mac.guardar("dredge", ["peixe-1", "peixe-2", "doca-1"])
    pc.sincronizar()

    mac.sincronizar()

    assert mac.progresso() == ["peixe-1", "peixe-2", "doca-1"], "sem base confiável, nada se perde"


def test_caminho_com_ponto_ponto_vindo_da_nuvem_nunca_grava_fora_da_pasta(tmp_path, falso):
    import base64
    import hashlib

    pc = PCComPlatinas(tmp_path, falso, "pc")
    usuario = falso._por_email(EMAIL).id
    conteudo = b'["x"]'
    for caminho in ("platinas/../../fora/progress.json", r"platinas/dredge\..\progress.json"):
        falso.arquivos[(usuario, caminho)] = {
            "user_id": usuario, "path": caminho, "content_b64": base64.b64encode(conteudo).decode(),
            "sha256": hashlib.sha256(conteudo).hexdigest(), "size": len(conteudo), "deleted": False}

    assert pc.sincronizar().baixou == []
    assert not (tmp_path / "fora").exists() and not (pc.dados / "fora").exists()


def test_simular_nao_muda_o_progresso_nem_a_base(tmp_path, falso):
    pc, mac = _dois_pcs(tmp_path, falso, ["peixe-1"])
    pc.guardar("dredge", ["peixe-1", "peixe-2"])
    mac.guardar("dredge", ["peixe-1", "doca-1"])
    pc.sincronizar()
    base = (mac.dados / "cloud" / "base.json").read_bytes()

    assert mac.sincronizar(simular=True).juntou == [DREDGE]
    assert mac.progresso() == ["peixe-1", "doca-1"] and (mac.dados / "cloud" / "base.json").read_bytes() == base
