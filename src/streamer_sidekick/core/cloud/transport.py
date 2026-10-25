"""Transporte HTTP do modo nuvem.

Toda chamada da nuvem passa por uma função com esta forma:

    transporte(metodo, url, cabecalhos, corpo, timeout) -> (status, dados)

Nos testes ela é trocada pelo Supabase falso (tests/supabase_falso.py); aqui
está a de verdade, sobre o ``net.urlopen`` do app (certificados no macOS,
proxy corporativo no Windows). Falha de rede ou tempo esgotado levantam
exceção; resposta de erro do servidor volta como status.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Optional

from streamer_sidekick.core import net


def http(metodo: str, url: str, cabecalhos: dict[str, str], corpo: Optional[Any] = None,
         timeout: float = 30.0) -> tuple[int, Any]:
    dados = None if corpo is None else json.dumps(corpo).encode("utf-8")
    pedido = urllib.request.Request(url, data=dados, method=metodo)
    for nome, valor in cabecalhos.items():
        pedido.add_header(nome, valor)
    if dados is not None:
        pedido.add_header("Content-Type", "application/json")
    try:
        with net.urlopen(pedido, timeout=timeout) as resposta:
            return resposta.status, _json(resposta.read())
    except urllib.error.HTTPError as erro:
        return erro.code, _json(erro.read())


def _json(bruto: bytes) -> Any:
    if not bruto:
        return None
    try:
        return json.loads(bruto.decode("utf-8"))
    except ValueError:
        return bruto.decode("utf-8", "replace")
