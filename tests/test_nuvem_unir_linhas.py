"""Regra de conflito dos .txt do Marcador: união de linhas (ticket 09, decisão Q20)."""


def _unir(pc, nuvem):
    from streamer_sidekick.core.cloud.merge import unir_linhas

    return unir_linhas(pc, nuvem)


def test_linha_que_so_existe_na_nuvem_entra_no_lugar_da_data_e_hora():
    pc = ("[2026-10-25 10:00:00] começou a live\n"
          "[2026-10-25 10:30:00] boss derrotado\n")
    nuvem = ("[2026-10-25 10:00:00] começou a live\n"
             "[2026-10-25 10:15:00] achei o peixe aberrante\n")

    assert _unir(pc, nuvem) == ("[2026-10-25 10:00:00] começou a live\n"
                                "[2026-10-25 10:15:00] achei o peixe aberrante\n"
                                "[2026-10-25 10:30:00] boss derrotado\n")


def test_anotacao_escrita_a_mao_vem_grudada_na_linha_de_cima():
    pc = "[2026-10-25 10:30:00] boss derrotado\n"
    nuvem = ("[2026-10-25 10:10:00] morri pro peixe\n"
             "   cortar esse trecho, ficou engraçado\n"
             "[2026-10-25 10:30:00] boss derrotado\n")

    assert _unir(pc, nuvem) == ("[2026-10-25 10:10:00] morri pro peixe\n"
                                "   cortar esse trecho, ficou engraçado\n"
                                "[2026-10-25 10:30:00] boss derrotado\n")


def test_mesma_linha_nos_dois_lados_aparece_uma_vez_com_as_anotacoes_dos_dois():
    pc = "[2026-10-25 10:30:00] boss derrotado\nnota do PC\n"
    nuvem = "[2026-10-25 10:30:00] boss derrotado\nnota do Mac\n"

    assert _unir(pc, nuvem) == "[2026-10-25 10:30:00] boss derrotado\nnota do PC\nnota do Mac\n"


def test_cabecalho_antes_da_primeira_data_se_junta_sem_repetir():
    pc = "Live de DREDGE\n[2026-10-25 10:00:00] começou\n"
    nuvem = "Live de DREDGE\nparte 2\n[2026-10-25 10:00:00] começou\n"

    assert _unir(pc, nuvem) == "Live de DREDGE\nparte 2\n[2026-10-25 10:00:00] começou\n"


def test_arquivos_iguais_continuam_iguais_e_um_lado_vazio_fica_com_o_outro():
    texto = "[2026-10-25 10:00:00] começou\n[2026-10-25 10:30:00] boss derrotado — https://clips.twitch.tv/AbcXyz\n"

    assert _unir(texto, texto) == texto
    assert _unir("", texto) == texto
    assert _unir(texto, "") == texto
