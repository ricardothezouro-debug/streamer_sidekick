"""Regras de conflito da sincronização (GLOSSARY.md: Conflito).

``unir_linhas`` é a regra dos .txt do Marcador: junta os dois lados sem
duplicar, mantendo a ordem do arquivo do PC (decisão Q20 da fase 1).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

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
