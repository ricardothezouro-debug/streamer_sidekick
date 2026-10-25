"""Regras dos favoritos do Início, separadas da tela.

A lista salva (preferência ``hub.favorites``) nunca perde um favorito só porque
o plugin não está instalado neste PC: com o modo nuvem, ela é a mesma em todos
os PCs, e podar aqui apagaria o favorito nos outros. A tela só esconde.
"""
from __future__ import annotations

from collections.abc import Collection, Iterable

MAX_FAVORITES = 4


def visible_favorites(stored: Iterable[str], available: Collection[str], limit: int = MAX_FAVORITES) -> list[str]:
    """Os favoritos que aparecem: os instalados aqui, na ordem salva, até ``limit``."""
    return [fid for fid in stored if fid in available][:limit]


def favorites_to_save(selected: Iterable[str], stored: Iterable[str], available: Collection[str]) -> list[str]:
    """O que gravar ao salvar a janela: o que foi marcado e, depois, os favoritos
    que não estão instalados neste PC (e por isso nem apareceram na janela)."""
    marcados = list(dict.fromkeys(selected))
    guardados = [fid for fid in stored if fid not in available and fid not in marcados]
    return marcados + guardados
