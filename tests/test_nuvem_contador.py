"""Contador na nuvem (ticket 12; decisão Q34): presets, valores e ícones em dois PCs."""
import json
from datetime import date

import pytest

from supabase_falso import SupabaseFalso
from test_nuvem_sincronizar_marcador import EMAIL, PC

PRESET = [{"titulo": "Mortes", "hotkey": "ctrl+1", "icone": "caveira-5f7539d3.png", "icon_size": 40}]
ICONE = b"\x89PNG\r\n\x1a\n caveira"


class PCComContador(PC):
    def __init__(self, raiz, falso, nome, presets=None):
        super().__init__(raiz, falso, nome)
        self.presets = presets or self.dados / "counter_presets"
        if presets is not None:
            (self.dados / "config.json").write_text(
                json.dumps({"counter": {"presets_folder": str(presets)}}), encoding="utf-8")
        self.presets.mkdir(parents=True, exist_ok=True)
        self.icones = self.dados / "counter_icons"

    def salvar_preset(self, nome, contadores=PRESET):
        (self.presets / f"{nome}.json").write_text(json.dumps(contadores), encoding="utf-8")

    def salvar_valor(self, nome, valor):
        (self.presets / f"{nome}_state.json").write_text(json.dumps({"Mortes_0": valor}), encoding="utf-8")

    def salvar_icone(self, nome=PRESET[0]["icone"], conteudo=ICONE):
        self.icones.mkdir(parents=True, exist_ok=True)
        (self.icones / nome).write_bytes(conteudo)

    def preset(self, nome):
        arquivo = self.presets / f"{nome}.json"
        return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else None

    def valor(self, nome):
        arquivo = self.presets / f"{nome}_state.json"
        return json.loads(arquivo.read_text(encoding="utf-8"))["Mortes_0"] if arquivo.exists() else None


@pytest.fixture
def falso():
    return SupabaseFalso()


def _dois_pcs_com_o_dredge(tmp_path, falso):
    pc, mac = PCComContador(tmp_path, falso, "pc"), PCComContador(tmp_path, falso, "mac")
    pc.salvar_preset("dredge")
    pc.salvar_valor("dredge", 3)
    pc.salvar_icone()
    pc.sincronizar()
    mac.sincronizar()
    return pc, mac


def test_preset_valor_e_icone_criados_num_pc_aparecem_no_outro(tmp_path, falso):
    pc = PCComContador(tmp_path, falso, "pc")
    mac = PCComContador(tmp_path, falso, "mac", presets=tmp_path / "presets-do-mac")  # pasta escolhida na tela
    pc.salvar_preset("dredge")
    pc.salvar_valor("dredge", 3)
    pc.salvar_icone()
    (pc.presets / "config.json").write_text("{}", encoding="utf-8")  # não é preset: fica no PC

    esperado = ["contador/icones/caveira-5f7539d3.png", "contador/presets/dredge.json",
                "contador/presets/dredge_state.json"]
    assert sorted(pc.sincronizar().subiu) == esperado
    assert sorted(mac.sincronizar().baixou) == esperado
    assert mac.preset("dredge") == PRESET and mac.valor("dredge") == 3
    assert (mac.icones / "caveira-5f7539d3.png").read_bytes() == ICONE
    assert not (mac.presets / "config.json").exists()


def test_overlay_aberto_nao_tem_o_valor_substituido_pela_nuvem(tmp_path, falso):
    pc, mac = _dois_pcs_com_o_dredge(tmp_path, falso)
    pc.salvar_valor("dredge", 10)  # ajustado no outro PC
    pc.sincronizar()

    relatorio = mac.sincronizar(presets_abertos=["dredge"])

    assert "contador/presets/dredge_state.json" not in relatorio.baixou and mac.valor("dredge") == 3
    assert mac.sincronizar().baixou == ["contador/presets/dredge_state.json"], "fechou o overlay: baixa"
    assert mac.valor("dredge") == 10


def test_overlay_aberto_que_contou_vence_o_conflito(tmp_path, falso):
    pc, mac = _dois_pcs_com_o_dredge(tmp_path, falso)
    pc.salvar_valor("dredge", 10)
    pc.sincronizar()
    mac.salvar_valor("dredge", 4)  # o overlay do Mac contou uma morte

    assert mac.sincronizar(presets_abertos=["dredge"]).subiu == ["contador/presets/dredge_state.json"]
    assert mac.valor("dredge") == 4
    pc.sincronizar()
    assert pc.valor("dredge") == 4


def test_overlay_aberto_nao_e_apagado_pela_nuvem(tmp_path, falso):
    pc, mac = _dois_pcs_com_o_dredge(tmp_path, falso)
    (pc.presets / "dredge_state.json").unlink()
    pc.sincronizar()

    relatorio = mac.sincronizar(presets_abertos=["dredge"])

    assert "contador/presets/dredge_state.json" not in relatorio.excluiu and mac.valor("dredge") == 3


def test_renomear_preset_nao_faz_o_nome_antigo_voltar(tmp_path, falso):
    pc, mac = _dois_pcs_com_o_dredge(tmp_path, falso)
    for antigo in ("dredge.json", "dredge_state.json"):  # o que a janela faz ao renomear
        (pc.presets / antigo).unlink()
    pc.salvar_preset("dredge 2")
    pc.salvar_valor("dredge 2", 3)

    relatorio = pc.sincronizar()
    assert sorted(relatorio.excluiu) == ["contador/presets/dredge.json", "contador/presets/dredge_state.json"]
    assert sorted(relatorio.subiu) == ["contador/presets/dredge 2.json", "contador/presets/dredge 2_state.json"]

    mac.sincronizar()
    assert mac.preset("dredge") is None and mac.preset("dredge 2") == PRESET and mac.valor("dredge 2") == 3
    pc.sincronizar()
    mac.sincronizar()
    assert pc.preset("dredge") is None and mac.preset("dredge") is None, "o nome antigo não volta"


def test_conflito_em_preset_a_nuvem_vence_e_o_do_pc_vai_para_o_backup(tmp_path, falso):
    pc, mac = _dois_pcs_com_o_dredge(tmp_path, falso)
    do_pc = [dict(PRESET[0], titulo="Mortes no PC")]
    do_mac = [dict(PRESET[0], titulo="Mortes no Mac")]
    pc.salvar_preset("dredge", do_pc)
    mac.salvar_preset("dredge", do_mac)
    pc.sincronizar()  # o PC chega primeiro na nuvem

    relatorio = mac.sincronizar()

    assert relatorio.baixou == ["contador/presets/dredge.json"] and relatorio.juntou == []
    assert mac.preset("dredge") == do_pc
    backup = mac.dados / "cloud" / "backup" / date.today().isoformat() / "contador" / "presets" / "dredge.json"
    assert json.loads(backup.read_text(encoding="utf-8")) == do_mac


def test_o_marcador_continua_sincronizando_junto(tmp_path, falso):
    pc, mac = _dois_pcs_com_o_dredge(tmp_path, falso)
    pc.escrever("dredge.txt", "[2026-10-25 10:30:00] boss derrotado\n")

    assert pc.sincronizar().subiu == ["marcador/dredge.txt"]
    assert mac.sincronizar().baixou == ["marcador/dredge.txt"]
    assert falso.arquivo(EMAIL, "contador/presets/dredge.json")["deleted"] is False
