"""Sincronização (GLOSSARY.md; docs/adr/0001): compara cada arquivo com a base.

Para cada caminho lógico:
- mudou só no PC: sobe;
- mudou só na nuvem: baixa;
- mudou nos dois: conflito, resolvido pela regra do tipo de arquivo.

Hoje: os .txt do Marcador (``marcador/``, união de linhas) e o Contador
(``contador/presets/`` e ``contador/icones/``, a nuvem vence com backup). Os
próximos tickets acrescentam preferências e Platinas.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import urllib.parse
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from streamer_sidekick.core.cloud.account import Acesso, Conta
from streamer_sidekick.core.cloud.merge import unir_linhas

MARCADOR = "marcador/"
PRESETS = "contador/presets/"
ICONES = "contador/icones/"
#: Repete o arquivo ativo do config; é configuração da máquina, nunca sobe.
_NUNCA_SOBEM = frozenset({"ultimo_jogo.txt"})
#: Arquivos pela metade (gravação atômica do app e da sincronização).
_TEMPORARIOS = (".sincronizando", ".copiando")


@dataclass
class Relatorio:
    conta: Conta
    subiu: list[str] = field(default_factory=list)
    baixou: list[str] = field(default_factory=list)
    juntou: list[str] = field(default_factory=list)
    excluiu: list[str] = field(default_factory=list)
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

    def excluir(self, caminho: str) -> None:
        """Marca o arquivo como apagado. A linha fica, para os outros PCs saberem."""
        self._gravar_linha({"user_id": self._acesso.usuario, "path": caminho, "content_b64": "",
                            "sha256": "", "size": 0, "deleted": True}, caminho)

    def subir(self, caminho: str, conteudo: bytes) -> None:
        linha = {
            "user_id": self._acesso.usuario,
            "path": caminho,
            "content_b64": base64.b64encode(conteudo).decode("ascii"),
            "sha256": _hash(conteudo),
            "size": len(conteudo),  # tamanho e hash do conteúdo real, não do base64
            "deleted": False,
        }
        self._gravar_linha(linha, caminho)

    def _gravar_linha(self, linha: dict[str, Any], caminho: str) -> None:
        # Sem este Prefer o PostgREST faz INSERT puro e a segunda gravação do
        # mesmo caminho dá erro de duplicado.
        status, erro = self._chamar("POST", "/rest/v1/files?on_conflict=user_id,path",
                                    acesso=self._acesso.token, corpo=linha,
                                    extra={"Prefer": "resolution=merge-duplicates,return=minimal"})
        if status not in (200, 201, 204):
            raise OSError(f"não deu para subir {caminho} (HTTP {status}): {erro}")


def sincronizar(dados: Path, remotos: ArquivosRemotos, conta: Conta, simular: bool,
                hoje: Optional[date] = None, presets_abertos: Iterable[str] = ()) -> Relatorio:
    """``presets_abertos``: presets com o overlay aberto neste PC. O valor deles
    (``<nome>_state.json``) não é baixado nem apagado pela nuvem; só sobe, se
    mudou aqui (decisão Q34)."""
    dados = Path(dados)
    hoje = hoje or date.today()
    relatorio = Relatorio(conta=conta, simulado=simular)
    backup = _Backup(dados / "cloud" / "backup", hoje)
    if not simular:
        backup.limpar_antigos()
    base = _Base(dados / "cloud" / "base.json")
    # Exclusões vêm junto do índice: "deleted" é a marca de que alguém apagou.
    indice = remotos.indice()
    abertos = {f"{PRESETS}{nome}_state.json".lower() for nome in presets_abertos}

    for area in _areas(dados):
        locais = _locais(area)
        nuvem = {linha["path"].lower(): linha for linha in indice
                 if linha.get("path", "").lower().startswith(area.prefixo)}
        for chave in sorted(set(locais) | set(nuvem) | base.chaves(area.prefixo)):
            _sincronizar_um(chave, area, locais.get(chave), nuvem.get(chave), base, backup, remotos,
                            relatorio, simular, aberto=chave in abertos)

    if not simular:
        base.salvar()
    return relatorio


def _sincronizar_um(chave: str, area: "_Area", local: Optional[_Local], remoto: Optional[dict[str, Any]],
                    base: "_Base", backup: "_Backup", remotos: ArquivosRemotos, relatorio: Relatorio,
                    simular: bool, aberto: bool) -> None:
    anterior = base.get(chave)
    vivo = remoto is not None and not remoto.get("deleted")
    caminho = remoto["path"] if remoto else (local.caminho if local else chave)  # reaproveita a caixa da nuvem

    def subir() -> None:
        relatorio.subiu.append(caminho)
        if not simular:
            remotos.subir(caminho, local.conteudo)
            base.set(chave, local.sha256)

    def baixar() -> None:
        relatorio.baixou.append(caminho)
        if not simular:
            conteudo = remotos.baixar(caminho)
            if local:
                backup.guardar(caminho, local.conteudo)
            _gravar(local.arquivo if local else area.pasta / caminho[len(area.prefixo):], conteudo)
            base.set(chave, _hash(conteudo))

    if aberto:
        # Overlay aberto: o PC vence, mas só quando mudou aqui. Se só a nuvem
        # mudou, fica como está até o overlay fechar.
        if local and vivo and local.sha256 == remoto["sha256"]:
            base.set(chave, local.sha256)
        elif local and anterior != local.sha256:
            subir()
        return

    if local and vivo:
        if local.sha256 == remoto["sha256"]:
            base.set(chave, local.sha256)
        elif anterior == local.sha256:  # só a nuvem mudou desde a base
            baixar()
        elif anterior == remoto["sha256"]:  # só o PC mudou desde a base
            subir()
        elif area.juntar is None:  # mudou nos dois: a nuvem vence, a versão do PC vai para o backup
            baixar()
        else:  # mudou nos dois (ou primeira sincronização com os dois lados diferentes)
            relatorio.juntou.append(caminho)
            if not simular:
                junto = area.juntar(local.conteudo, remotos.baixar(caminho))
                backup.guardar(caminho, local.conteudo)
                _gravar(local.arquivo, junto)
                remotos.subir(caminho, junto)
                base.set(chave, _hash(junto))
    elif local:
        if remoto is not None and anterior == local.sha256:
            # Apagado em outro PC e intocado aqui desde a base: sai, mas para o backup.
            relatorio.excluiu.append(caminho)
            if not simular:
                backup.guardar(caminho, local.conteudo)
                local.arquivo.unlink()
                base.remover(chave)
        else:
            # Nunca esteve na nuvem, ou foi editado aqui depois de apagado lá
            # (a exclusão perde para a edição, Q28). Ausência nunca é exclusão.
            subir()
    elif vivo:
        if anterior is not None and anterior == remoto["sha256"]:
            # Apagado aqui e intocado na nuvem desde a base: a exclusão sobe.
            relatorio.excluiu.append(caminho)
            if not simular:
                remotos.excluir(caminho)
                base.remover(chave)
        else:
            baixar()  # novo na nuvem, ou editado lá depois de apagado aqui (Q28)
    elif not simular:
        base.remover(chave)  # sumiu dos dois lados: nada a fazer


# ------------------------------------------------------------------ apoio
@dataclass(frozen=True)
class _Area:
    """Um pedaço do app que sincroniza: o prefixo na nuvem, a pasta no PC,
    quais arquivos entram e a regra de conflito."""

    prefixo: str
    pasta: Path
    padrao: str
    ignorados: frozenset[str]
    #: Junta as duas versões; ``None``: a nuvem vence, com backup.
    juntar: Optional[Callable[[bytes, bytes], bytes]]


def _areas(dados: Path) -> list[_Area]:
    config = _config(dados)
    return [
        _Area(MARCADOR, _pasta(config, "marker", "folder", dados / "markers"), "*.txt", _NUNCA_SOBEM, _unir),
        # config.json na pasta de presets é de versões antigas do Contador, não é preset.
        _Area(PRESETS, _pasta(config, "counter", "presets_folder", dados / "counter_presets"), "*.json",
              frozenset({"config.json"}), None),
        _Area(ICONES, dados / "counter_icons", "*", frozenset(), None),
    ]


def _config(dados: Path) -> dict[str, Any]:
    try:
        config = json.loads((dados / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return config if isinstance(config, dict) else {}


def _pasta(config: dict[str, Any], secao: str, chave: str, padrao: Path) -> Path:
    valores = config.get(secao)
    configurada = valores.get(chave) if isinstance(valores, dict) else ""
    return Path(configurada) if configurada else padrao


def _unir(local: bytes, da_nuvem: bytes) -> bytes:
    return unir_linhas(local.decode("utf-8", "replace"), da_nuvem.decode("utf-8", "replace")).encode("utf-8")


def _locais(area: _Area) -> dict[str, _Local]:
    locais: dict[str, _Local] = {}
    if not area.pasta.is_dir():
        return locais
    for arquivo in sorted(area.pasta.glob(area.padrao)):
        nome = arquivo.name.lower()
        if nome in area.ignorados or nome.endswith(_TEMPORARIOS) or not arquivo.is_file():
            continue
        conteudo = arquivo.read_bytes()
        caminho = area.prefixo + arquivo.name
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

    def remover(self, chave: str) -> None:
        self._hashes.pop(chave, None)

    def chaves(self, prefixo: str) -> set[str]:
        return {chave for chave in self._hashes if chave.startswith(prefixo)}

    def salvar(self) -> None:
        self._arquivo.parent.mkdir(parents=True, exist_ok=True)
        _gravar(self._arquivo, json.dumps(self._hashes, indent=1, sort_keys=True).encode("utf-8"))


class _Backup:
    """Backup da nuvem (GLOSSARY.md): a versão do PC de tudo que a sincronização
    sobrescreve ou tira do lugar, em ``cloud/backup/<AAAA-MM-DD>/<caminho lógico>``.
    Pastas com mais de 30 dias são apagadas ao sincronizar (decisão Q21)."""

    DIAS = 30

    def __init__(self, pasta: Path, hoje: date) -> None:
        self._pasta = pasta
        self._hoje = hoje

    def guardar(self, caminho_logico: str, conteudo: bytes) -> Path:
        destino = self._pasta / self._hoje.isoformat() / caminho_logico
        if destino.exists():  # segunda cópia no mesmo dia: ganha a hora no nome
            hora = datetime.now().strftime("%H%M%S")
            nome, extensao = destino.stem, destino.suffix
            destino = destino.with_name(f"{nome}-{hora}{extensao}")
            extra = 2
            while destino.exists():
                destino = destino.with_name(f"{nome}-{hora}-{extra}{extensao}")
                extra += 1
        _gravar(destino, conteudo)
        return destino

    def limpar_antigos(self) -> None:
        if not self._pasta.is_dir():
            return
        for pasta in self._pasta.iterdir():
            try:
                dia = date.fromisoformat(pasta.name)
            except ValueError:
                continue  # não é pasta de backup do app: não mexe
            if pasta.is_dir() and (self._hoje - dia).days > self.DIAS:
                shutil.rmtree(pasta, ignore_errors=True)
