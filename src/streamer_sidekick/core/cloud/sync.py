"""Sincronização (GLOSSARY.md; docs/adr/0001): compara cada arquivo com a base.

Para cada caminho lógico:
- mudou só no PC: sobe;
- mudou só na nuvem: baixa;
- mudou nos dois: conflito, resolvido pela regra do tipo de arquivo.

Ticket 09: só os .txt do Marcador (``marcador/<arquivo>.txt``). Os próximos
tickets acrescentam exclusões, preferências, Contador e Platinas.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from streamer_sidekick.core.cloud.account import Acesso, Conta
from streamer_sidekick.core.cloud.merge import unir_linhas

MARCADOR = "marcador/"
#: Repete o arquivo ativo do config; é configuração da máquina, nunca sobe.
_NUNCA_SOBEM = {"ultimo_jogo.txt"}


@dataclass
class Relatorio:
    conta: Conta
    subiu: list[str] = field(default_factory=list)
    baixou: list[str] = field(default_factory=list)
    juntou: list[str] = field(default_factory=list)
    simulado: bool = False


@dataclass
class _Local:
    caminho: str  # lógico, com a caixa do nome no PC
    arquivo: Path
    conteudo: bytes
    sha256: str


class ArquivosRemotos:
    """A tabela ``files`` da pessoa, pela API do Supabase (RLS: só os dela)."""

    def __init__(self, chamar: Callable[..., tuple[int, Any]], acesso: Acesso) -> None:
        self._chamar = chamar
        self._acesso = acesso

    def indice(self) -> list[dict[str, Any]]:
        status, linhas = self._chamar("GET", "/rest/v1/files?select=path,sha256,size,deleted",
                                      acesso=self._acesso.token)
        if status != 200 or not isinstance(linhas, list):
            raise OSError(f"não deu para ler os arquivos da nuvem (HTTP {status})")
        return linhas

    def baixar(self, caminho: str) -> bytes:
        filtro = urllib.parse.urlencode({"select": "path,content_b64", "path": f"eq.{caminho}"})
        status, linhas = self._chamar("GET", f"/rest/v1/files?{filtro}", acesso=self._acesso.token)
        if status != 200 or not isinstance(linhas, list) or not linhas:
            raise OSError(f"não deu para baixar {caminho} (HTTP {status})")
        return base64.b64decode(linhas[0]["content_b64"])

    def subir(self, caminho: str, conteudo: bytes) -> None:
        linha = {
            "user_id": self._acesso.usuario,
            "path": caminho,
            "content_b64": base64.b64encode(conteudo).decode("ascii"),
            "sha256": _hash(conteudo),
            "size": len(conteudo),  # tamanho e hash do conteúdo real, não do base64
            "deleted": False,
        }
        # Sem este Prefer o PostgREST faz INSERT puro e a segunda gravação do
        # mesmo caminho dá erro de duplicado.
        status, erro = self._chamar("POST", "/rest/v1/files?on_conflict=user_id,path",
                                    acesso=self._acesso.token, corpo=linha,
                                    extra={"Prefer": "resolution=merge-duplicates,return=minimal"})
        if status not in (200, 201, 204):
            raise OSError(f"não deu para subir {caminho} (HTTP {status}): {erro}")


def sincronizar(dados: Path, remotos: ArquivosRemotos, conta: Conta, simular: bool) -> Relatorio:
    relatorio = Relatorio(conta=conta, simulado=simular)
    base = _Base(Path(dados) / "cloud" / "base.json")
    pasta = _pasta_do_marcador(Path(dados))
    locais = _locais(pasta)
    nuvem = {linha["path"].lower(): linha for linha in remotos.indice()
             if linha.get("path", "").lower().startswith(MARCADOR) and not linha.get("deleted")}

    for chave in sorted(set(locais) | set(nuvem)):
        local, remoto, anterior = locais.get(chave), nuvem.get(chave), base.get(chave)
        caminho_na_nuvem = remoto["path"] if remoto else local.caminho  # reaproveita a caixa da nuvem

        if local and remoto and local.sha256 == remoto["sha256"]:
            base.set(chave, local.sha256)
        elif local and not remoto:
            relatorio.subiu.append(caminho_na_nuvem)
            if not simular:
                remotos.subir(caminho_na_nuvem, local.conteudo)
                base.set(chave, local.sha256)
        elif remoto and not local:
            relatorio.baixou.append(caminho_na_nuvem)
            if not simular:
                conteudo = remotos.baixar(caminho_na_nuvem)
                _gravar(pasta / caminho_na_nuvem[len(MARCADOR):], conteudo)
                base.set(chave, _hash(conteudo))
        elif anterior == local.sha256:  # só a nuvem mudou desde a base
            relatorio.baixou.append(caminho_na_nuvem)
            if not simular:
                conteudo = remotos.baixar(caminho_na_nuvem)
                _gravar(local.arquivo, conteudo)
                base.set(chave, _hash(conteudo))
        elif anterior == remoto["sha256"]:  # só o PC mudou desde a base
            relatorio.subiu.append(caminho_na_nuvem)
            if not simular:
                remotos.subir(caminho_na_nuvem, local.conteudo)
                base.set(chave, local.sha256)
        else:  # mudou nos dois (ou primeira sincronização com os dois lados diferentes)
            relatorio.juntou.append(caminho_na_nuvem)
            if not simular:
                da_nuvem = remotos.baixar(caminho_na_nuvem)
                junto = unir_linhas(local.conteudo.decode("utf-8", "replace"),
                                    da_nuvem.decode("utf-8", "replace")).encode("utf-8")
                _gravar(local.arquivo, junto)
                remotos.subir(caminho_na_nuvem, junto)
                base.set(chave, _hash(junto))

    if not simular:
        base.salvar()
    return relatorio


# ------------------------------------------------------------------ apoio
def _pasta_do_marcador(dados: Path) -> Path:
    try:
        config = json.loads((dados / "config.json").read_text(encoding="utf-8"))
        configurada = (config.get("marker") or {}).get("folder") or ""
    except (OSError, ValueError, AttributeError):
        configurada = ""
    return Path(configurada) if configurada else dados / "markers"


def _locais(pasta: Path) -> dict[str, _Local]:
    locais: dict[str, _Local] = {}
    if not pasta.is_dir():
        return locais
    for arquivo in sorted(pasta.glob("*.txt")):
        if arquivo.name.lower() in _NUNCA_SOBEM or not arquivo.is_file():
            continue
        conteudo = arquivo.read_bytes()
        caminho = MARCADOR + arquivo.name
        locais[caminho.lower()] = _Local(caminho, arquivo, conteudo, _hash(conteudo))
    return locais


def _hash(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def _gravar(arquivo: Path, conteudo: bytes) -> None:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    temporario = arquivo.with_name(arquivo.name + ".sincronizando")
    temporario.write_bytes(conteudo)
    os.replace(temporario, arquivo)


class _Base:
    """O hash de cada arquivo ao fim da última sincronização, só neste PC."""

    def __init__(self, arquivo: Path) -> None:
        self._arquivo = arquivo
        try:
            self._hashes: dict[str, str] = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self._hashes = {}

    def get(self, chave: str) -> Optional[str]:
        return self._hashes.get(chave)

    def set(self, chave: str, sha256: str) -> None:
        self._hashes[chave] = sha256

    def salvar(self) -> None:
        self._arquivo.parent.mkdir(parents=True, exist_ok=True)
        _gravar(self._arquivo, json.dumps(self._hashes, indent=1, sort_keys=True).encode("utf-8"))
