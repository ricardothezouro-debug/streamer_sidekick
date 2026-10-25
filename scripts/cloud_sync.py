"""Testa o motor do modo nuvem de verdade, antes de existir interface.

Usa uma pasta de dados que VOCÊ escolhe (--dados), nunca a do app por padrão:
assim dá para testar com a conta real sem tocar em marcações, presets e
progresso de verdade.

    python scripts/cloud_sync.py --dados C:\\teste-nuvem entrar
    python scripts/cloud_sync.py --dados C:\\teste-nuvem conta
    python scripts/cloud_sync.py --dados C:\\teste-nuvem sair

    python scripts/cloud_sync.py --dados C:\\teste-nuvem sincronizar --simular
    python scripts/cloud_sync.py --dados C:\\teste-nuvem sincronizar

Hoje sincroniza os .txt do Marcador (a pasta configurada no config.json da pasta
de dados, ou <dados>/markers). Os próximos tickets acrescentam o resto e
"baixar-tudo".
O projeto e a chave pública vêm do app; troque com SSK_SUPABASE_URL e
SSK_SUPABASE_ANON_KEY para apontar para outro projeto.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from streamer_sidekick.core.cloud import CONECTADA, DESATIVADA, INDISPONIVEL, ErroDeLogin, Nuvem  # noqa: E402
from streamer_sidekick.core.cloud.login import receber_pelo_navegador  # noqa: E402
from streamer_sidekick.core.paths import app_data_dir  # noqa: E402


def _descrever(conta) -> str:
    if conta.estado == CONECTADA:
        return f"conectada: {conta.email}" + (" (admin)" if conta.admin else "")
    if conta.estado == DESATIVADA:
        return f"conta desativada pelo admin ({conta.email}); a sessão saiu deste PC, os dados ficaram"
    if conta.estado == INDISPONIVEL:
        return f"nuvem indisponível agora ({conta.motivo}); tente de novo depois"
    return "ninguém conectado; rode o comando entrar" + (f" ({conta.motivo})" if conta.motivo else "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Testa o modo nuvem com uma pasta de dados de teste.")
    parser.add_argument("--dados", required=True, type=Path,
                        help="pasta de dados de teste (fica no lugar da pasta do app)")
    parser.add_argument("--permitir-dados-reais", action="store_true",
                        help="aceita usar a pasta de dados de verdade do app (só se você tiver certeza)")
    parser.add_argument("--simular", action="store_true",
                        help="com sincronizar: mostra o que faria, sem mudar nada")
    parser.add_argument("comando", choices=["entrar", "conta", "sair", "sincronizar"])
    args = parser.parse_args()

    dados = args.dados.expanduser().resolve()
    if dados == app_data_dir().resolve() and not args.permitir_dados_reais:
        print(f"Essa é a pasta de dados de verdade do app ({dados}).\n"
              "Escolha uma pasta de teste, ou passe --permitir-dados-reais se for mesmo isso.")
        return 2
    dados.mkdir(parents=True, exist_ok=True)
    nuvem = Nuvem(dados)
    print(f"pasta de dados: {dados}")

    if args.comando == "entrar":
        print("Abrindo o navegador para entrar com o Google…")
        try:
            conta = nuvem.entrar(receber_pelo_navegador)
        except ErroDeLogin as erro:
            print(f"O login não deu certo: {erro}")
            return 1
        print(_descrever(conta))
        return 0 if conta.estado == CONECTADA else 1
    if args.comando == "conta":
        conta = nuvem.conta()
        print(_descrever(conta))
        return 0 if conta.estado == CONECTADA else 1
    if args.comando == "sincronizar":
        relatorio = nuvem.sincronizar(simular=args.simular)
        print(_descrever(relatorio.conta))
        if relatorio.conta.estado != CONECTADA:
            return 1
        simulado = relatorio.simulado
        for rotulo, caminhos in (("subiria" if simulado else "subiu", relatorio.subiu),
                                 ("baixaria" if simulado else "baixou", relatorio.baixou),
                                 ("juntaria" if simulado else "juntou", relatorio.juntou),
                                 ("excluiria" if simulado else "excluiu", relatorio.excluiu)):
            for caminho in caminhos:
                print(f"  {rotulo}: {caminho}")
        if not (relatorio.subiu or relatorio.baixou or relatorio.juntou or relatorio.excluiu):
            print("  tudo igual: nada a fazer")
        if simulado:
            print("(simulação: nada foi mudado)")
        return 0
    nuvem.sair()
    print("Sessão encerrada neste PC.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
