"""Acesso HTTPS que nao depende do estado de certificados da maquina.

Por que isto existe: o Python do python.org no macOS nao usa o Keychain -- ele
procura um ``cert.pem`` que so aparece depois de rodar
"Install Certificates.command". Sem ele, TODA chamada HTTPS do app morre com
``CERTIFICATE_VERIFY_FAILED``: o marketplace nao carrega o catalogo (e cai no
embutido, mostrando uma lista velha sem avisar), o feed de novidades fica vazio
e instalar plugin quebra. O mesmo vale para o ``.app`` empacotado, que nem tem a
pasta do framework.

A correcao NAO e trocar a loja do sistema pelo ``certifi``: no Windows a loja e
justamente o que faz um proxy corporativo com raiz propria funcionar, e trocar
ela quebraria quem depende disso. Entao usamos o contexto padrao e so
completamos com as raizes do ``certifi`` quando o padrao vem vazio -- o que
acontece no macOS e em nenhum Windows saudavel.
"""
from __future__ import annotations

import ssl
import urllib.request
from functools import lru_cache
from typing import Any, Optional


def _certifi_cafile() -> Optional[str]:
    try:
        import certifi
    except ImportError:
        return None
    try:
        return certifi.where()
    except Exception:
        return None


def _has_roots(context: ssl.SSLContext) -> bool:
    """O contexto carregou alguma CA? Na duvida, assume que sim e nao mexe."""
    try:
        return int(context.cert_store_stats().get("x509_ca", 0)) > 0
    except Exception:
        return True


@lru_cache(maxsize=1)
def ssl_context() -> ssl.SSLContext:
    """Contexto TLS do app: o padrao do sistema, com certifi so como remendo."""
    context = ssl.create_default_context()
    if _has_roots(context):
        return context

    cafile = _certifi_cafile()
    if cafile is not None:
        try:
            context.load_verify_locations(cafile=cafile)
        except OSError:
            pass
    return context


def used_certifi_fallback() -> bool:
    """True quando a loja do sistema estava vazia e o certifi entrou no lugar.

    Serve para o Diagnostico explicar por que a rede funciona (ou nao).
    """
    return not _has_roots(ssl.create_default_context())


def urlopen(request: Any, timeout: float) -> Any:
    """``urllib.request.urlopen`` com o contexto TLS do app."""
    return urllib.request.urlopen(request, timeout=timeout, context=ssl_context())
