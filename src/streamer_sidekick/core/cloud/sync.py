"""Sincronização (GLOSSARY.md; docs/adr/0001): compara cada arquivo com a base.

Para cada caminho lógico:
- mudou só no PC: sobe;
- mudou só na nuvem: baixa;
- mudou nos dois: conflito, resolvido pela regra do tipo de arquivo.

Hoje: os .txt do Marcador (``marcador/``, união de linhas), o Contador
(``contador/presets/`` e ``contador/icones/``) e as preferências
(``preferencias/``, montadas do config; veja ``preferences.py``). Nesses dois,
a nuvem vence, com backup. O próximo ticket acrescenta as Platinas.
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

from streamer_sidekick.core.cloud import preferences
from streamer_sidekick.core.cloud.account import Acesso, Conta
from streamer_sidekick.core.cloud.merge import unir_linhas
from streamer_sidekick.core.config import ConfigStore

MARCADOR = "marcador/"
PRESETS = "contador/presets/"
ICONES = "contador/icones/"
GERAL = "preferencias/geral.json"
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
    conteudo: bytes
    sha256: str
    gravar: Callable[[bytes], None]
    #: ``None``: não se apaga (as preferências existem sempre).
    apagar: Optional[Callable[[], None]]


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
                hoje: Optional[date] = None, presets_abertos: Iterable[str] = (),
                config: Optional[ConfigStore] = None, sistema: Optional[str] = None) -> Relatorio:
    """``presets_abertos``: presets com o overlay aberto neste PC. O valor deles
    (``<nome>_state.json``) não é baixado nem apagado pela nuvem; só sobe, se
    mudou aqui (decisão Q34).

    ``config``: o ``ConfigStore`` do app aberto, para as preferências baixadas
    não serem desfeitas pelo próximo ``set()`` dele (ADR 0004). Sem app aberto
    (o script de teste), lê o config.json da pasta de dados."""
    dados = Path(dados)
    config = config if config is not None else ConfigStore(path=dados / "config.json")
    hoje = hoje or date.today()
    relatorio = Relatorio(conta=conta, simulado=simular)
    backup = _Backup(dados / "cloud" / "backup", hoje)
    if not simular:
        backup.limpar_antigos()
    base = _Base(dados / "cloud" / "base.json")
    # Exclusões vêm junto do índice: "deleted" é a marca de que alguém apagou.
    indice = remotos.indice()
    abertos = {f"{PRESETS}{nome}_state.json".lower() for nome in presets_abertos}

    for area in _areas(dados, config, sistema or preferences.sistema_atual()):
        locais = area.ler()  # na hora: as preferências gerais podem ter mudado os atalhos
        nuvem = {linha["path"].lower(): linha for linha in indice if area.inclui(linha.get("path", ""))}
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
                local.gravar(conteudo)
            else:
                _gravar(area.pasta / caminho[len(area.prefixo):], conteudo)
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
                local.gravar(junto)
                remotos.subir(caminho, junto)
                base.set(chave, _hash(junto))
    elif local:
        if remoto is not None and anterior == local.sha256 and local.apagar is not None:
            # Apagado em outro PC e intocado aqui desde a base: sai, mas para o backup.
            relatorio.excluiu.append(caminho)
            if not simular:
                backup.guardar(caminho, local.conteudo)
                local.apagar()
                base.remover(chave)
        else:
            # Nunca esteve na nuvem, ou foi editado aqui depois de apagado lá
            # (a exclusão perde para a edição, Q28). Ausência nunca é exclusão.
            subir()
    elif vivo and area.pasta is not None:
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
    """Um pedaço do app que sincroniza: o prefixo na nuvem, de onde vêm os
    arquivos deste PC e a regra de conflito."""

    prefixo: str
    ler: Callable[[], dict[str, _Local]]
    #: Junta as duas versões; ``None``: a nuvem vence, com backup.
    juntar: Optional[Callable[[bytes, bytes], bytes]]
    #: Onde grava o que só existe na nuvem; ``None``: um arquivo só, que existe sempre.
    pasta: Optional[Path] = None

    def inclui(self, caminho: str) -> bool:
        caminho = caminho.lower()
        return caminho.startswith(self.prefixo) if self.pasta is not None else caminho == self.prefixo


def _areas(dados: Path, config: ConfigStore, sistema: str) -> list[_Area]:
    marcacoes = _pasta(config, "marker.folder", dados / "markers")
    presets = _pasta(config, "counter.presets_folder", dados / "counter_presets")
    icones = dados / "counter_icons"
    return [
        _Area(MARCADOR, lambda: _arquivos(MARCADOR, marcacoes, "*.txt", _NUNCA_SOBEM), _unir, marcacoes),
        # config.json na pasta de presets é de versões antigas do Contador, não é preset.
        _Area(PRESETS, lambda: _arquivos(PRESETS, presets, "*.json", frozenset({"config.json"})), None, presets),
        _Area(ICONES, lambda: _arquivos(ICONES, icones, "*", frozenset()), None, icones),
        _preferencia(GERAL, config, preferences.geral, preferences.aplicar_geral),
        _preferencia(preferences.caminho_dos_atalhos(sistema), config, preferences.atalhos,
                     preferences.aplicar_atalhos),
    ]


def _preferencia(caminho: str, config: ConfigStore, montar: Callable[[ConfigStore], bytes],
                 aplicar: Callable[[ConfigStore, bytes], None]) -> _Area:
    def ler() -> dict[str, _Local]:
        conteudo = montar(config)
        return {caminho: _Local(caminho, conteudo, _hash(conteudo), lambda novo: aplicar(config, novo), None)}

    return _Area(caminho, ler, None)


def _pasta(config: ConfigStore, chave: str, padrao: Path) -> Path:
    configurada = config.get(chave) or ""
    return Path(str(configurada)) if configurada else padrao


def _unir(local: bytes, da_nuvem: bytes) -> bytes:
    return unir_linhas(local.decode("utf-8", "replace"), da_nuvem.decode("utf-8", "replace")).encode("utf-8")


def _arquivos(prefixo: str, pasta: Path, padrao: str, ignorados: frozenset[str]) -> dict[str, _Local]:
    locais: dict[str, _Local] = {}
    if not pasta.is_dir():
        return locais
    for arquivo in sorted(pasta.glob(padrao)):
        nome = arquivo.name.lower()
        if nome in ignorados or nome.endswith(_TEMPORARIOS) or not arquivo.is_file():
            continue
        conteudo = arquivo.read_bytes()
        caminho = prefixo + arquivo.name
        locais[caminho.lower()] = _Local(caminho, conteudo, _hash(conteudo),
                                         lambda novo, alvo=arquivo: _gravar(alvo, novo), arquivo.unlink)
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
