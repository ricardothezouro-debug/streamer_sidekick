"""Preferências na nuvem (ADR 0004): dois arquivos montados a partir do config.

- ``preferencias/geral.json``: só as chaves da lista, iguais em todos os PCs,
  e as mensagens rápidas sem a sequência.
- ``preferencias/atalhos-<sistema>.json``: os atalhos do hub e a sequência de
  cada mensagem rápida, separados por sistema (o Mac nunca muda o Windows).

Configuração da máquina (pastas, iniciar com o sistema, onboarding, última
versão) e qualquer coisa de plugin nunca entram. Chave nova só sobe se entrar
em ``GERAL``.

Baixar aplica pelo ``ConfigStore`` do app aberto, nunca trocando o arquivo no
disco: o app regravaria o config inteiro no próximo ``set()``.
"""
from __future__ import annotations

import json
import sys
from typing import Any

from streamer_sidekick.core.config import DEFAULT_CONFIG, ConfigStore

GERAL = ("hub.favorites", "hub.wallpaper", "hub.start_minimized", "hub.close_to_tray", "marker.active_file")
MENSAGENS = "marker.custom_hotkeys"
#: Atalhos do próprio app; atalho com outro id (de plugin) nunca sobe.
_ATALHOS_DO_APP = frozenset(DEFAULT_CONFIG["hotkeys"])
_PREFIXO_DAS_MENSAGENS = "marker.custom."
_AUSENTE = object()


def sistema_atual() -> str:
    """``windows``, ``macos`` ou ``linux`` (decisão Q36)."""
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def caminho_dos_atalhos(sistema: str) -> str:
    return f"preferencias/atalhos-{sistema}.json"


# ------------------------------------------------------------------ montar
def geral(config: ConfigStore) -> bytes:
    documento: dict[str, Any] = {}
    for chave in GERAL:
        valor = config.get(chave, _AUSENTE)
        if valor is not _AUSENTE:
            documento[chave] = valor
    documento[MENSAGENS] = [{"key": item["key"], "message": item["message"]} for item in _mensagens(config)]
    return _json(documento)


def atalhos(config: ConfigStore) -> bytes:
    guardados = config.get("hotkeys", {})
    guardados = guardados if isinstance(guardados, dict) else {}
    return _json({
        "hotkeys": {chave: valor for chave, valor in guardados.items() if _e_do_app(chave)},
        # Mensagem sem atalho neste sistema (veio do outro, Q35) não entra.
        "mensagens": {item["key"]: item["sequence"] for item in _mensagens(config) if item["sequence"]},
    })


# ------------------------------------------------------------------ aplicar
def aplicar_geral(config: ConfigStore, conteudo: bytes) -> None:
    documento = _ler(conteudo)
    for chave in GERAL:
        if chave in documento and config.get(chave, _AUSENTE) != documento[chave]:
            config.set(chave, documento[chave])

    da_nuvem = documento.get(MENSAGENS)
    if not isinstance(da_nuvem, list):
        return
    locais = {item["key"]: item for item in _mensagens(config)}
    novas = []
    for item in da_nuvem:
        if not isinstance(item, dict) or not item.get("key") or not item.get("message"):
            continue
        chave = str(item["key"])
        # A sequência é deste sistema: a de um item novo vem dos atalhos, ou fica vazia (Q35).
        sequencia = locais[chave]["sequence"] if chave in locais else ""
        novas.append({"key": chave, "message": str(item["message"]), "sequence": sequencia})
    if novas != list(locais.values()):
        config.set(MENSAGENS, novas)
    for chave in set(locais) - {item["key"] for item in novas}:
        config.remove_in("hotkeys", chave)  # mensagem apagada no outro PC


def aplicar_atalhos(config: ConfigStore, conteudo: bytes) -> None:
    documento = _ler(conteudo)
    da_nuvem = documento.get("hotkeys")
    if isinstance(da_nuvem, dict):
        guardados = config.get("hotkeys", {})
        guardados = guardados if isinstance(guardados, dict) else {}
        for chave, valor in da_nuvem.items():
            if _e_do_app(chave) and guardados.get(chave) != valor:
                config.set_in("hotkeys", chave, valor)
        for chave in [chave for chave in guardados if _e_do_app(chave) and chave not in da_nuvem]:
            config.remove_in("hotkeys", chave)

    sequencias = documento.get("mensagens")
    if isinstance(sequencias, dict):
        atuais = _mensagens(config)
        novas = [dict(item, sequence=str(sequencias.get(item["key"]) or "")) for item in atuais]
        if novas != atuais:
            config.set(MENSAGENS, novas)


# ------------------------------------------------------------------ apoio
def _mensagens(config: ConfigStore) -> list[dict[str, str]]:
    itens = config.get(MENSAGENS, [])
    linhas: list[dict[str, str]] = []
    for item in itens if isinstance(itens, list) else []:
        if not isinstance(item, dict):
            continue
        chave = str(item.get("key") or "").strip()
        mensagem = str(item.get("message") or "").strip()
        if chave and mensagem:
            linhas.append({"key": chave, "message": mensagem, "sequence": str(item.get("sequence") or "").strip()})
    return linhas


def _e_do_app(chave: str) -> bool:
    return chave in _ATALHOS_DO_APP or chave.startswith(_PREFIXO_DAS_MENSAGENS)


def _json(documento: dict[str, Any]) -> bytes:
    # Ordenado e estável: o mesmo config dá sempre o mesmo hash.
    return (json.dumps(documento, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _ler(conteudo: bytes) -> dict[str, Any]:
    try:
        documento = json.loads(conteudo.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return {}
    return documento if isinstance(documento, dict) else {}
