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

# Flag do CreateProcess (Windows): roda o updater sem janela de console.
# O processo filho sobrevive ao fim do app (sem job object que o mate junto).
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
    progress: Optional[Callable[[str, Optional[float]], None]] = None,
) -> None:
    """Baixa a versão nova e dispara o updater. Lança RuntimeError se não aplicável.

    ``progress(message, fraction)``: fraction em 0..1 durante o download, ou None
    (indeterminado) nas demais fases.

    Depois desta chamada retornar, quem chama DEVE encerrar o app imediatamente
    para liberar os arquivos (o updater espera o processo sair antes de copiar).
    """
    def report(message: str, fraction: Optional[float] = None) -> None:
        if progress is not None:
            progress(message, fraction)

    if not is_frozen():
        raise RuntimeError(
            "Auto-update só funciona no app empacotado (portable). Em desenvolvimento, use git pull."
        )
    if sys.platform != "win32":
        raise RuntimeError("Auto-update automático está disponível apenas no Windows por enquanto.")

    report("Baixando a nova versão...", 0.0)
    payload = _download(
        release.zip_url,
        on_progress=lambda read, total: report(
            _download_message(read, total),
            (read / total) if total else None,
        ),
    )

    report("Preparando arquivos...")
    staging = Path(tempfile.mkdtemp(prefix="ssk_update_"))
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        archive.extractall(staging)
    new_root = _single_top_dir(staging)

    target = install_dir()
    ps_path = _write_updater_ps1(new_root, target, staging, os.getpid(), release.version)

    report("Reiniciando para concluir a atualização...")
    subprocess.Popen(
        [
            "powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
            "-ExecutionPolicy", "Bypass", "-File", str(ps_path),
        ],
        creationflags=_CREATE_NO_WINDOW,
        close_fds=True,
    )


def _download(url: str, on_progress: Optional[Callable[[int, int], None]] = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    parts: list[bytes] = []
    with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT) as response:
        total = int(response.headers.get("Content-Length") or 0)
        read = 0
        while True:
            chunk = response.read(65536)
            if not chunk:
                break
            parts.append(chunk)
            read += len(chunk)
            if on_progress is not None:
                on_progress(read, total)
    return b"".join(parts)


def _download_message(read: int, total: int) -> str:
    mb = read / (1024 * 1024)
    if total:
        return f"Baixando… {mb:.0f} MB de {total / (1024 * 1024):.0f} MB"
    return f"Baixando… {mb:.0f} MB"


def _single_top_dir(extracted: Path) -> Path:
    dirs = [item for item in extracted.iterdir() if item.is_dir()]
    files = [item for item in extracted.iterdir() if item.is_file()]
    # Zip portable tem uma unica pasta raiz (ex.: StreamerSidekick-0.4.0-portable).
    if len(dirs) == 1 and not files:
        return dirs[0]
    return extracted


def _ps_quote(value: str) -> str:
    """Aspa simples de PowerShell (literal), escapando aspas internas."""
    return "'" + str(value).replace("'", "''") + "'"


def build_updater_script(
    new_root: Path, target: Path, staging: Path, pid: int, new_version: str = ""
) -> str:
    """Conteúdo do updater em PowerShell. Separado para poder ser testado.

    Usa ``Wait-Process`` (espera o app sair de forma confiável, sem depender de
    ``tasklist``/``timeout`` que falham num processo sem console), ``robocopy``
    para trocar os arquivos e ``Start-Process`` para reabrir. Ao final limpa o
    diretório temporário e a si mesmo.

    Se ``new_version`` for informado e a pasta de instalação ainda tiver o nome
    padrão (``StreamerSidekick-<versão>-portable``), ela é renomeada para refletir
    a nova versão — e o app reabre a partir do novo caminho. Pastas com nome
    customizado pelo usuário são preservadas.
    """
    new_root_q = _ps_quote(str(new_root))
    target_q = _ps_quote(str(target))
    staging_q = _ps_quote(str(staging))
    version = str(new_version).strip()

    lines = [
        "$ErrorActionPreference = 'SilentlyContinue'",
        f"Wait-Process -Id {int(pid)} -Timeout 120",
        "Start-Sleep -Seconds 1",
        f"$null = robocopy {new_root_q} {target_q} /E /IS /IT /R:3 /W:2 /NFL /NDL /NJH /NJS",
        f"$finalTarget = {target_q}",
    ]
    if version:
        lines += [
            f"$leaf = Split-Path -Leaf {target_q}",
            f"$parent = Split-Path -Parent {target_q}",
            "if ($leaf -match '^StreamerSidekick-.*-portable$') {",
            f"  $newName = 'StreamerSidekick-{version}-portable'",
            "  if ($leaf -ne $newName) {",
            "    $candidate = Join-Path $parent $newName",
            "    if (-not (Test-Path -LiteralPath $candidate)) {",
            f"      Rename-Item -LiteralPath {target_q} -NewName $newName",
            "      if (Test-Path -LiteralPath $candidate) { $finalTarget = $candidate }",
            "    }",
            "  }",
            "}",
        ]
    lines += [
        f"Start-Process -FilePath (Join-Path $finalTarget '{EXE_NAME}')",
        "Start-Sleep -Seconds 1",
        f"Remove-Item -LiteralPath {staging_q} -Recurse -Force",
        "Remove-Item -LiteralPath $PSCommandPath -Force",
    ]
    return "\r\n".join(lines) + "\r\n"


def _write_updater_ps1(
    new_root: Path, target: Path, staging: Path, pid: int, new_version: str = ""
) -> Path:
    # O .ps1 fica FORA de staging para poder apagar staging e a si mesmo.
    # utf-8-sig (BOM) para o Windows PowerShell 5.1 ler o arquivo corretamente.
    fd, path = tempfile.mkstemp(prefix="ssk_apply_", suffix=".ps1")
    os.close(fd)
    ps_path = Path(path)
    ps_path.write_text(
        build_updater_script(new_root, target, staging, pid, new_version), encoding="utf-8-sig"
    )
    return ps_path
