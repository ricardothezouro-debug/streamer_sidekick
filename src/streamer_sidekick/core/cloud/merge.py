"""Regras de conflito da sincronização (GLOSSARY.md: Conflito).

``unir_linhas`` é a regra dos .txt do Marcador: junta os dois lados sem
duplicar, mantendo a ordem do arquivo do PC (decisão Q20 da fase 1).

``fundir_progresso`` é a regra do progresso das platinas (ADR 0003): fusão em
três vias contra a base.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

_DATA_E_HORA = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")


@dataclass
class _Bloco:
    """Uma linha com [data hora] e as linhas sem data logo abaixo dela."""

    cabeca: str
    quando: str
    grudadas: list[str] = field(default_factory=list)


def _blocos(texto: str) -> tuple[list[str], list[_Bloco]]:
    cabecalho: list[str] = []  # linhas antes da primeira data e hora
    blocos: list[_Bloco] = []
    for linha in texto.splitlines():
        achou = _DATA_E_HORA.match(linha)
        if achou:
            blocos.append(_Bloco(linha, achou.group(1)))
        elif blocos:
            blocos[-1].grudadas.append(linha)
        else:
            cabecalho.append(linha)
    return cabecalho, blocos


def _juntar(base: list[str], extra: list[str]) -> list[str]:
    """``base`` na ordem dela, mais as linhas de ``extra`` que faltam (sem repetir)."""
    vistas = set(base)
    return base + [linha for linha in extra if not (linha in vistas or vistas.add(linha))]


def unir_linhas(pc: str, nuvem: str) -> str:
    """União de linhas por data e hora.

    - A ordem do arquivo do PC é mantida.
    - Bloco que só existe na nuvem entra no lugar da data e hora dele (depois
      do último bloco com data e hora menor ou igual).
    - A mesma linha com data e hora dos dois lados aparece uma vez; as linhas
      grudadas nela (anotações escritas à mão) se juntam.
    - O cabeçalho (antes da primeira data e hora) também se junta.
    """
    cabecalho_pc, blocos = _blocos(pc)
    cabecalho_nuvem, blocos_nuvem = _blocos(nuvem)
    por_cabeca = {bloco.cabeca: bloco for bloco in blocos}

    for bloco in blocos_nuvem:
        existente = por_cabeca.get(bloco.cabeca)
        if existente is not None:
            existente.grudadas = _juntar(existente.grudadas, bloco.grudadas)
            continue
        posicao = 0
        for indice, atual in enumerate(blocos):
            if atual.quando <= bloco.quando:
                posicao = indice + 1
        novo = _Bloco(bloco.cabeca, bloco.quando, list(bloco.grudadas))
        blocos.insert(posicao, novo)
        por_cabeca[novo.cabeca] = novo

    linhas = _juntar(cabecalho_pc, cabecalho_nuvem)
    for bloco in blocos:
        linhas.append(bloco.cabeca)
        linhas.extend(bloco.grudadas)
    return "".join(linha + "\n" for linha in linhas)


def fundir_progresso(base: Optional[bytes], pc: bytes, nuvem: bytes) -> Optional[bytes]:
    """O que um lado marcou desde a base entra; o que um lado desmarcou sai.

    Aceita a lista de ids marcados e o objeto com essa lista em ``done`` (os
    outros campos seguem a nuvem). Formato desconhecido, ou diferente entre os
    dois lados, devolve ``None``: aí vale "a nuvem vence" (Q39). Sem base (ou
    base em outro formato), junta tudo: nada se perde.

    A ordem é a do PC, e o que só a nuvem marcou vai no fim, na ordem dela (Q38).
    """
    do_pc, da_nuvem = _ler_json(pc), _ler_json(nuvem)
    marcados_pc, marcados_nuvem = _marcados(do_pc), _marcados(da_nuvem)
    if marcados_pc is None or marcados_nuvem is None or type(do_pc) is not type(da_nuvem):
        return None
    anterior = _ler_json(base) if base is not None else None
    marcados_base = _marcados(anterior) if type(anterior) is type(do_pc) else None

    no_pc = {_id(item) for item in marcados_pc}
    na_nuvem = {_id(item) for item in marcados_nuvem}
    desmarcados = {_id(item) for item in marcados_base or []
                   if _id(item) not in no_pc or _id(item) not in na_nuvem}
    resultado: list[Any] = []
    vistos: set[str] = set()
    for item in marcados_pc + marcados_nuvem:
        chave = _id(item)
        if chave not in desmarcados and chave not in vistos:
            vistos.add(chave)
            resultado.append(item)

    if isinstance(da_nuvem, dict):
        junto: Any = dict(da_nuvem, done=resultado)
    else:
        junto = resultado
    return json.dumps(junto, ensure_ascii=False).encode("utf-8")


_INVALIDO = object()


def _ler_json(conteudo: bytes) -> Any:
    try:
        return json.loads(conteudo.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return _INVALIDO


def _marcados(documento: Any) -> Optional[list[Any]]:
    if isinstance(documento, list):
        return documento
    if isinstance(documento, dict) and isinstance(documento.get("done"), list):
        return documento["done"]
    return None


def _id(item: Any) -> str:
    # Compara como veio no JSON: "3" e 3 são ids diferentes.
    return json.dumps(item, sort_keys=True)
