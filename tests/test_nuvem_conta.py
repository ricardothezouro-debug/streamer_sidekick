"""Modo nuvem: entrar, ver a conta e sair (ticket 08), contra o Supabase falso."""
import pytest


def _transporte_proibido(*_args, **_kwargs):
    raise AssertionError("não devia chamar a rede")


def test_sem_sessao_precisa_entrar_sem_chamar_a_rede(tmp_path):
    from streamer_sidekick.core.cloud import PRECISA_ENTRAR, Nuvem

    nuvem = Nuvem(tmp_path, transporte=_transporte_proibido)

    assert nuvem.conta().estado == PRECISA_ENTRAR


from supabase_falso import SupabaseFalso  # noqa: E402

EMAIL = "gamox@exemplo.com"


def _nuvem(tmp_path, falso):
    from streamer_sidekick.core.cloud import Nuvem

    return Nuvem(tmp_path, transporte=falso, url=falso.URL, chave=falso.ANON)


def _entrar(nuvem, falso, email=EMAIL):
    # Faz o papel do navegador: a pessoa entra no Google e o app recebe o código.
    return nuvem.entrar(lambda montar_url: falso.autorizar(montar_url("http://127.0.0.1:53682/callback"), email))


# ---- o falso é fiel ao Supabase de verdade (os próximos tickets confiam nele) -----


def _sessao_crua(falso, email):
    from supabase_falso import _desafio

    verificador = "v" * 50
    url = (f"{falso.URL}/auth/v1/authorize?provider=google&redirect_to=http://127.0.0.1:53682/callback"
           f"&code_challenge={_desafio(verificador)}&code_challenge_method=s256")
    codigo = falso.autorizar(url, email)
    _, dados = falso("POST", f"{falso.URL}/auth/v1/token?grant_type=pkce", {"apikey": falso.ANON},
                     {"auth_code": codigo, "code_verifier": verificador})
    return {"apikey": falso.ANON, "Authorization": f"Bearer {dados['access_token']}"}


def test_falso_recusa_quem_tenta_virar_admin():
    falso = SupabaseFalso()
    cabecalhos = _sessao_crua(falso, EMAIL)
    status, _ = falso("PATCH", f"{falso.URL}/rest/v1/profiles?id=eq.u1", cabecalhos, {"is_admin": True})
    assert status == 403


def test_falso_so_mostra_o_proprio_perfil():
    falso = SupabaseFalso()
    falso.criar_usuario("outra@exemplo.com")
    cabecalhos = _sessao_crua(falso, EMAIL)
    status, perfis = falso("GET", f"{falso.URL}/rest/v1/profiles?select=email", cabecalhos)
    assert status == 200 and [p["email"] for p in perfis] == [EMAIL]


# ---- entrar, conta e sair -------------------------------------------------------


def test_entrar_conecta_e_a_sessao_sobrevive_a_fechar_e_abrir(tmp_path):
    from streamer_sidekick.core.cloud import CONECTADA

    falso = SupabaseFalso()
    conta = _entrar(_nuvem(tmp_path, falso), falso)
    assert (conta.estado, conta.email, conta.admin) == (CONECTADA, EMAIL, False)

    de_novo = _nuvem(tmp_path, falso).conta()  # outra instância: como fechar e abrir o app
    assert (de_novo.estado, de_novo.email) == (CONECTADA, EMAIL)


def _token_salvo(tmp_path):
    import json

    arquivo = tmp_path / "cloud" / "session.json"
    return json.loads(arquivo.read_text(encoding="utf-8"))["refresh_token"] if arquivo.exists() else None


def test_renovar_troca_o_token_salvo_e_o_antigo_morre(tmp_path):
    from streamer_sidekick.core.cloud import CONECTADA, PRECISA_ENTRAR
    from streamer_sidekick.core.cloud.session import SessionStore

    falso = SupabaseFalso()
    nuvem = _nuvem(tmp_path, falso)
    _entrar(nuvem, falso)
    antigo = _token_salvo(tmp_path)

    assert nuvem.conta().estado == CONECTADA
    assert _token_salvo(tmp_path) not in (None, antigo)

    SessionStore(tmp_path / "cloud").save(antigo)  # alguém reusando o token velho
    assert nuvem.conta().estado == PRECISA_ENTRAR


def test_sessao_revogada_pede_para_entrar_de_novo_e_apaga_a_sessao(tmp_path):
    from streamer_sidekick.core.cloud import PRECISA_ENTRAR

    falso = SupabaseFalso()
    nuvem = _nuvem(tmp_path, falso)
    _entrar(nuvem, falso)
    falso.revogar(EMAIL)

    assert nuvem.conta().estado == PRECISA_ENTRAR
    assert _token_salvo(tmp_path) is None, "a sessão morta não fica no PC"


def test_conta_desativada_desliga_a_nuvem_sem_apagar_os_dados(tmp_path):
    from streamer_sidekick.core.cloud import DESATIVADA

    falso = SupabaseFalso()
    nuvem = _nuvem(tmp_path, falso)
    _entrar(nuvem, falso)
    marcacoes = tmp_path / "markers" / "dredge.txt"
    marcacoes.parent.mkdir()
    marcacoes.write_text("[2026-10-25 10:00:00] boss derrotado\n", encoding="utf-8")
    falso.desativar(EMAIL)

    assert nuvem.conta().estado == DESATIVADA
    assert _token_salvo(tmp_path) is None, "a sessão sai deste PC"
    assert marcacoes.read_text(encoding="utf-8") == "[2026-10-25 10:00:00] boss derrotado\n"


@pytest.mark.parametrize("problema", ["fora_do_ar", "lento"])
def test_nuvem_indisponivel_nao_trava_e_mantem_a_sessao(tmp_path, problema):
    from streamer_sidekick.core.cloud import INDISPONIVEL, Nuvem

    falso = SupabaseFalso()
    _entrar(_nuvem(tmp_path, falso), falso)
    setattr(falso, problema, True)
    nuvem = Nuvem(tmp_path, transporte=falso, url=falso.URL, chave=falso.ANON, timeout=5)

    conta = nuvem.conta()
    assert conta.estado == INDISPONIVEL and conta.motivo
    assert falso.ultimo_timeout == 5, "o tempo limite pedido chega até a chamada"
    assert _token_salvo(tmp_path) is not None, "volta a funcionar quando a nuvem voltar"


def test_sair_apaga_a_sessao_e_avisa_o_servidor(tmp_path):
    from streamer_sidekick.core.cloud import PRECISA_ENTRAR

    falso = SupabaseFalso()
    nuvem = _nuvem(tmp_path, falso)
    _entrar(nuvem, falso)
    nuvem.sair()

    assert nuvem.conta().estado == PRECISA_ENTRAR
    assert ("POST", "/auth/v1/logout") in falso.chamadas
    assert not falso.usuarios["u1"].refresh_tokens, "a sessão também morre no servidor"


def test_sair_funciona_mesmo_com_a_nuvem_fora_do_ar(tmp_path):
    falso = SupabaseFalso()
    nuvem = _nuvem(tmp_path, falso)
    _entrar(nuvem, falso)
    falso.fora_do_ar = True

    nuvem.sair()
    assert _token_salvo(tmp_path) is None


def test_login_recusado_da_erro_claro_e_nao_deixa_sessao(tmp_path):
    from streamer_sidekick.core.cloud import ErroDeLogin

    falso = SupabaseFalso()
    nuvem = _nuvem(tmp_path, falso)
    with pytest.raises(ErroDeLogin):
        nuvem.entrar(lambda montar_url: "codigo-que-nao-existe")
    assert _token_salvo(tmp_path) is None


def test_nuvem_nao_depende_do_qt():
    import subprocess
    import sys
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src"
    codigo = ("import sys; sys.path.insert(0, r'%s'); import streamer_sidekick.core.cloud; "
              "print('PySide6' in sys.modules)" % src)
    saida = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, timeout=60)
    assert saida.returncode == 0, saida.stderr
    assert saida.stdout.strip() == "False"
