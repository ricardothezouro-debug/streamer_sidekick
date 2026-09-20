"""Monta o e-mail de feedback -- sem Qt, para ser testável.

O botão da aba Sobre abre o Gmail já com destinatário, assunto e corpo
preenchidos. O corpo leva junto o contexto que o usuário nunca sabe informar
e que a gente sempre precisa: versão, sistema e plugins instalados. É o que
transforma "não funciona" em algo que dá para agir.

Dois destinos:

* ``gmail_url``: a tela de escrever do Gmail, no navegador. Se a pessoa está
  logada, cai direto no e-mail pronto. É o caminho principal.
* ``mailto_url``: o cliente de e-mail padrão do sistema, para quem não usa
  Gmail. Secundário, porque em muita máquina nunca houve cliente configurado.
"""
from __future__ import annotations

import platform
import sys
import urllib.parse
from typing import Iterable, Sequence

DESTINATARIO = "streamersidekick@gmail.com"
ASSUNTO_PADRAO = "Feedback do Streamer Sidekick"

#: Navegadores aceitam mais, mas acima disto alguns cortam em silêncio e o
#: e-mail chega pela metade -- pior do que chegar curto.
LIMITE_URL = 2000


def sistema() -> str:
    if sys.platform == "win32":
        return f"Windows {platform.release()}"
    if sys.platform == "darwin":
        return f"macOS {platform.mac_ver()[0] or platform.release()}"
    return f"{platform.system()} {platform.release()}"


def contexto(versao: str, plugins: Iterable[tuple[str, str]] = ()) -> str:
    """As linhas que vão ao fim do corpo. ``plugins`` são pares (nome, versão)."""
    lista = ", ".join(f"{nome} {ver}" for nome, ver in plugins) or "nenhum"
    return (
        "—\n"
        f"Versão: {versao} · {sistema()}\n"
        f"Plugins: {lista}"
    )


def corpo(mensagem: str, versao: str, plugins: Sequence[tuple[str, str]] = ()) -> str:
    texto = (mensagem or "").strip()
    return f"{texto}\n\n{contexto(versao, plugins)}\n" if texto else f"{contexto(versao, plugins)}\n"


def _cortar(texto: str, maximo: int) -> str:
    """Garante que a URL final caiba. Corta a mensagem, nunca o contexto."""
    return texto if len(texto) <= maximo else texto[: max(0, maximo - 1)] + "…"


def _montar_gmail(assunto: str, texto: str, versao: str,
                  plugins: Sequence[tuple[str, str]]) -> str:
    return "https://mail.google.com/mail/?view=cm&fs=1&" + urllib.parse.urlencode(
        {"to": DESTINATARIO, "su": assunto, "body": corpo(texto, versao, plugins)},
        quote_via=urllib.parse.quote,
    )


def gmail_url(assunto: str, mensagem: str, versao: str,
              plugins: Sequence[tuple[str, str]] = ()) -> str:
    assunto = (assunto or "").strip() or ASSUNTO_PADRAO
    texto = (mensagem or "").strip()
    url = _montar_gmail(assunto, texto, versao, plugins)
    # Um caractere acentuado vira 6 no encode ("ç" -> "%C3%A7"), entao estimar
    # a expansao erra. Corta a mensagem ate a URL caber; o contexto fica.
    while len(url) > LIMITE_URL and texto:
        excesso = len(url) - LIMITE_URL
        texto = _cortar(texto, max(0, len(texto) - max(1, excesso // 6)))
        url = _montar_gmail(assunto, texto, versao, plugins)
    return url


def mailto_url(assunto: str, mensagem: str, versao: str,
               plugins: Sequence[tuple[str, str]] = ()) -> str:
    assunto = (assunto or "").strip() or ASSUNTO_PADRAO
    texto = _cortar((mensagem or "").strip(), 600)
    campos = urllib.parse.urlencode(
        {"subject": assunto, "body": corpo(texto, versao, plugins)},
        quote_via=urllib.parse.quote,
    )
    return f"mailto:{DESTINATARIO}?{campos}"
