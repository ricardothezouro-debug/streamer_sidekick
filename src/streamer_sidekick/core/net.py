"""Acesso HTTPS com raizes de certificado proprias.

Por que isto existe: o Python do python.org no macOS nao usa o Keychain do
sistema -- ele procura um ``cert.pem`` que so aparece depois de rodar
"Install Certificates.command". Sem ele, TODA chamada HTTPS do app morre com
``CERTIFICATE_VERIFY_FAILED``: o marketplace nao carrega o catalogo, o feed de
novidades fica vazio e instalar plugin quebra. O mesmo vale para o ``.app``
empacotado, que nem tem a pasta do framework.

A solucao e nao depender do estado da maquina: usamos o pacote ``certifi``
(as raizes da Mozilla) quando ele estiver presente, e so caimos no contexto
padrao do sistema se ele faltar -- que e o caso normal no Windows, onde o
Python usa a loja de certificados do proprio SO.
"""
from __future__ import annotations

import ssl
import urllib.request
from functools import lru_cache
from typing import Any, Optional


@lru_cache(maxsize=1)
def ssl_context() -> Optional[ssl.SSLContext]:
    """Contexto TLS com as raizes do ``certifi``, ou None para usar o padrao."""
    try:
        import certifi
    except ImportError:
        return None
    try:
        return ssl.create_default_context(cafile=certifi.where())
    except OSError:
        return None


def urlopen(request: Any, timeout: float) -> Any:
    """``urllib.request.urlopen`` com o contexto TLS do app."""
    context = ssl_context()
    if context is None:
        return urllib.request.urlopen(request, timeout=timeout)
    return urllib.request.urlopen(request, timeout=timeout, context=context)
