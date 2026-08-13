"""Auto-atualização do próprio Streamer Sidekick (build portable do Windows).

Fluxo:
  1. ``check_for_update()`` busca um manifesto remoto (``app_release.json``) e,
     se a versão anunciada for maior que a instalada, devolve um ``AppRelease``.
  2. ``download_and_apply()`` baixa o zip da versão nova, extrai num diretório
     temporário e dispara um pequeno *updater* (.bat) DESTACADO que:
       - espera o processo atual encerrar,
       - copia os arquivos novos por cima da pasta de instalação,
       - reabre o app,
       - se autolimpa.
     Logo após disparar o updater, o app precisa encerrar (quem chama faz isso).

Só funciona no build congelado (``sys.frozen``) e, por ora, no Windows. Em
desenvolvimento a checagem funciona, mas aplicar levanta ``RuntimeError`` (a
mensagem orienta a usar ``git pull``). Os dados do usuário ficam em ``%APPDATA%``
e não são tocados: a troca acontece só na pasta do executável.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from streamer_sidekick import __version__ as CURRENT_VERSION
from streamer_sidekick.core.plugins import version_tuple

APP_MANIFEST_URL = (
    "https://raw.githubusercontent.com/ricardothezouro-debug/streamer_sidekick/main/app_release.json"
)
_HTTP_TIMEOUT = 30
_USER_AGENT = "StreamerSidekick-AppUpdater"
EXE_NAME = "StreamerSidekick.exe"

# Flags do CreateProcess (Windows) para o updater sobreviver ao fim do app.
_DETACHED_PROCESS = 0x00000008
_CREATE_NO_WINDOW = 0x08000000


@dataclass(frozen=True)
class AppRelease:
    version: str
    zip_url: str
    notes: str = ""


def current_version() -> str:
    return CURRENT_VERSION


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def can_self_update() -> bool:
    """Auto-update completo só no portable congelado do Windows."""
    return is_frozen() and sys.platform == "win32"


def install_dir() -> Path:
    """Pasta que contém o executável (onde a troca de arquivos acontece)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    # Em dev não se aplica; devolve a raiz do repo por completude.
    return Path(__file__).resolve().parents[3]


def check_for_update() -> Optional[AppRelease]:
    """Devolve um AppRelease se houver versão mais nova; senão None."""
    data = _fetch_manifest()
    if not data:
        return None
    version = str(data.get("version") or "").strip()
    zip_url = str(data.get("zip_url") or "").strip()
    notes = str(data.get("notes") or "").strip()
    if not version or not zip_url:
        return None
    if version_tuple(version) > version_tuple(CURRENT_VERSION):
        return AppRelease(version=version, zip_url=zip_url, notes=notes)
    return None


def _fetch_manifest() -> Optional[dict[str, Any]]:
    try:
        request = urllib.request.Request(APP_MANIFEST_URL, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def download_and_apply(
    release: AppRelease,
    progress: Optional[Callable[[str], None]] = None,
) -> None:
    """Baixa a versão nova e dispara o updater. Lança RuntimeError se não aplicável.

    Depois desta chamada retornar, quem chama DEVE encerrar o app imediatamente
    para liberar os arquivos (o updater espera o processo sair antes de copiar).
    """
    def report(message: str) -> None:
        if progress is not None:
            progress(message)

    if not is_frozen():
        raise RuntimeError(
            "Auto-update só funciona no app empacotado (portable). Em desenvolvimento, use git pull."
        )
    if sys.platform != "win32":
        raise RuntimeError("Auto-update automático está disponível apenas no Windows por enquanto.")

    report("Baixando a nova versão...")
    payload = _download(release.zip_url)

    report("Preparando arquivos...")
    staging = Path(tempfile.mkdtemp(prefix="ssk_update_"))
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        archive.extractall(staging)
    new_root = _single_top_dir(staging)

    target = install_dir()
    bat_path = _write_updater_bat(new_root, target, staging, os.getpid())

    report("Reiniciando para concluir a atualização...")
    subprocess.Popen(
        ["cmd", "/c", str(bat_path)],
        creationflags=_DETACHED_PROCESS | _CREATE_NO_WINDOW,
        close_fds=True,
    )


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT) as response:
        return response.read()


def _single_top_dir(extracted: Path) -> Path:
    dirs = [item for item in extracted.iterdir() if item.is_dir()]
    files = [item for item in extracted.iterdir() if item.is_file()]
    # Zip portable tem uma unica pasta raiz (ex.: StreamerSidekick-0.4.0-portable).
    if len(dirs) == 1 and not files:
        return dirs[0]
    return extracted


def build_updater_script(new_root: Path, target: Path, staging: Path, pid: int) -> str:
    """Conteúdo do .bat que troca os arquivos. Separado para poder ser testado."""
    return (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        ":wait\r\n"
        f'tasklist /FI "PID eq {pid}" 2>nul | find "{pid}" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        "  timeout /t 1 /nobreak >nul\r\n"
        "  goto wait\r\n"
        ")\r\n"
        f'robocopy "{new_root}" "{target}" /E /IS /IT /R:3 /W:2 /NFL /NDL /NJH /NJS >nul\r\n'
        f'start "" "{target}\\{EXE_NAME}"\r\n'
        "timeout /t 1 /nobreak >nul\r\n"
        f'rmdir /S /Q "{staging}"\r\n'
        '(goto) 2>nul & del "%~f0"\r\n'
    )


def _write_updater_bat(new_root: Path, target: Path, staging: Path, pid: int) -> Path:
    # O .bat fica FORA de staging para poder apagar staging e a si mesmo.
    fd, path = tempfile.mkstemp(prefix="ssk_apply_", suffix=".bat")
    os.close(fd)
    bat_path = Path(path)
    bat_path.write_text(build_updater_script(new_root, target, staging, pid), encoding="utf-8")
    return bat_path
