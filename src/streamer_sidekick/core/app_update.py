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

No macOS o desenho é o mesmo, trocando o portable por um ``.app``: o updater é
um shell script que espera o processo sair, substitui o bundle inteiro com
``ditto`` e reabre com ``open``. Uma ressalva que não existe no Windows — como o
``.app`` não é assinado com Developer ID, o macOS trata cada build como um app
diferente e **revoga a permissão de Acessibilidade**; depois de atualizar é
preciso reativá-la. O app avisa isso antes de aplicar.

Só funciona no build congelado (``sys.frozen``). Em desenvolvimento a checagem
funciona, mas aplicar levanta ``RuntimeError`` (a mensagem orienta a usar ``git
pull``). Os dados do usuário ficam fora da pasta do app e não são tocados: a
troca acontece só na instalação.
"""
from __future__ import annotations

import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from streamer_sidekick import __version__ as CURRENT_VERSION
from streamer_sidekick.core import net
from streamer_sidekick.core.plugins import version_tuple

APP_MANIFEST_URL = (
    "https://raw.githubusercontent.com/ricardothezouro-debug/streamer_sidekick/main/app_release.json"
)
RELEASES_API_URL = (
    "https://api.github.com/repos/ricardothezouro-debug/streamer_sidekick/releases"
)
_HTTP_TIMEOUT = 30
_USER_AGENT = "StreamerSidekick-AppUpdater"
EXE_NAME = "StreamerSidekick.exe"

# Flag do CreateProcess (Windows): roda o updater sem janela de console.
# O processo filho sobrevive ao fim do app (sem job object que o mate junto).
_CREATE_NO_WINDOW = 0x08000000


# Chave da plataforma dentro de "platforms" no manifesto.
PLATFORM_KEYS = {"win32": "windows", "darwin": "macos"}


def platform_key() -> str:
    return PLATFORM_KEYS.get(sys.platform, "linux")


@dataclass(frozen=True)
class AppRelease:
    version: str
    zip_url: str
    notes: str = ""


@dataclass(frozen=True)
class ReleaseNote:
    """Uma release publicada no GitHub, para o feed de 'Últimas atualizações'."""

    version: str
    title: str
    notes: str = ""
    url: str = ""
    date: str = ""  # AAAA-MM-DD


def parse_releases(payload: Any, limit: int = 5) -> list[ReleaseNote]:
    """Converte o JSON da API de releases do GitHub em ``ReleaseNote`` (puro/testável)."""
    result: list[ReleaseNote] = []
    if not isinstance(payload, list):
        return result
    for item in payload:
        if not isinstance(item, dict) or item.get("draft"):
            continue
        tag = str(item.get("tag_name") or "").strip()
        version = tag[1:] if tag.lower().startswith("v") else tag
        title = str(item.get("name") or tag).strip()
        result.append(
            ReleaseNote(
                version=version,
                title=title or tag,
                notes=str(item.get("body") or "").strip(),
                url=str(item.get("html_url") or ""),
                date=str(item.get("published_at") or "")[:10],
            )
        )
        if len(result) >= limit:
            break
    return result


def fetch_recent_releases(limit: int = 5) -> list[ReleaseNote]:
    """Busca as últimas releases publicadas no GitHub (para o feed do Início)."""
    url = f"{RELEASES_API_URL}?per_page={int(limit)}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    with net.urlopen(request, timeout=_HTTP_TIMEOUT) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return parse_releases(payload, limit=limit)


def current_version() -> str:
    return CURRENT_VERSION


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def can_self_update() -> bool:
    """Auto-update completo no build congelado do Windows e do macOS."""
    return is_frozen() and sys.platform in ("win32", "darwin")


def macos_permissions_reset_on_update() -> bool:
    """True quando aplicar o update vai custar a permissão de Acessibilidade.

    O macOS amarra a permissão à assinatura do app. Como os builds são só
    ad-hoc (sem Developer ID), cada versão nova conta como outro app e o
    usuário precisa reativar a Acessibilidade. Vale a pena avisar antes.
    """
    return sys.platform == "darwin"


def install_dir() -> Path:
    """O que a atualização substitui.

    No Windows é a pasta do executável (o portable inteiro). No macOS é o bundle
    ``.app``, três níveis acima do executável em ``Contents/MacOS/``.
    """
    if is_frozen():
        exe = Path(sys.executable).resolve()
        if sys.platform == "darwin":
            for parent in exe.parents:
                if parent.suffix == ".app":
                    return parent
        return exe.parent
    # Em dev não se aplica; devolve a raiz do repo por completude.
    return Path(__file__).resolve().parents[3]


def release_from_manifest(data: Any, key: Optional[str] = None) -> Optional[AppRelease]:
    """Extrai a release da plataforma pedida. Puro, para poder ser testado.

    O manifesto tem os campos soltos na raiz (Windows) e, opcionalmente, uma
    seção ``platforms`` por sistema. Os campos soltos continuam existindo de
    propósito: clientes já instalados leem só eles, e mudar isso os deixaria
    sem update para sempre. A seção da plataforma, quando existe, tem
    precedência; ``notes`` e ``version`` caem para a raiz quando não repetidos.
    """
    if not isinstance(data, dict):
        return None
    key = key or platform_key()

    root_version = str(data.get("version") or "").strip()
    root_notes = str(data.get("notes") or "").strip()

    platforms = data.get("platforms")
    entry = platforms.get(key) if isinstance(platforms, dict) else None

    if isinstance(entry, dict):
        version = str(entry.get("version") or root_version).strip()
        zip_url = str(entry.get("zip_url") or "").strip()
        notes = str(entry.get("notes") or root_notes).strip()
    elif key == "windows":
        # Sem seção de plataforma, a raiz é o manifesto do Windows.
        version, zip_url, notes = root_version, str(data.get("zip_url") or "").strip(), root_notes
    else:
        # Nada anunciado para este sistema: melhor não oferecer nada.
        return None

    if not version or not zip_url:
        return None
    return AppRelease(version=version, zip_url=zip_url, notes=notes)


def check_for_update() -> Optional[AppRelease]:
    """Devolve um AppRelease se houver versão mais nova; senão None."""
    release = release_from_manifest(_fetch_manifest())
    if release is None:
        return None
    if version_tuple(release.version) > version_tuple(CURRENT_VERSION):
        return release
    return None


def _fetch_manifest() -> Optional[dict[str, Any]]:
    try:
        request = urllib.request.Request(APP_MANIFEST_URL, headers={"User-Agent": _USER_AGENT})
        with net.urlopen(request, timeout=_HTTP_TIMEOUT) as response:
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
            "Auto-update só funciona no app empacotado. Em desenvolvimento, use git pull."
        )
    if not can_self_update():
        raise RuntimeError(
            f"Auto-update automático ainda não está disponível em {sys.platform}."
        )

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
    _extract_payload(payload, staging)
    new_root = _single_top_dir(staging)

    target = install_dir()

    if sys.platform == "darwin":
        script = _write_updater_sh(new_root, target, staging, os.getpid())
        report("Reiniciando para concluir a atualização...")
        # start_new_session: o updater precisa sobreviver à morte deste processo.
        subprocess.Popen(["/bin/sh", str(script)], close_fds=True, start_new_session=True)
        return

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


def _extract_payload(payload: bytes, destination: Path) -> None:
    """Extrai o zip baixado em ``destination``.

    No macOS delegamos ao ``ditto``: um ``.app`` do PyInstaller e cheio de
    symlinks (``Contents/Resources/AppKit -> ../Frameworks/AppKit``) e de bits
    de execucao, e o ``zipfile`` do Python nao restaura nem um nem outro -- ele
    gravaria cada symlink como um arquivo comum contendo o caminho de destino,
    produzindo um bundle quebrado que so falharia DEPOIS de o updater ja ter
    apagado o app antigo. O ``ditto`` vem no sistema, nao e dependencia nova.
    """
    if sys.platform == "darwin":
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(payload)
            archive_path = Path(tmp.name)
        try:
            result = subprocess.run(
                ["ditto", "-x", "-k", str(archive_path), str(destination)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Falha ao extrair a atualizacao: {result.stderr.strip() or result.returncode}"
                )
        finally:
            archive_path.unlink(missing_ok=True)
        return

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        archive.extractall(destination)


def build_updater_sh(new_root: Path, target: Path, staging: Path, pid: int) -> str:
    """Conteudo do updater do macOS. Separado para poder ser testado.

    Espera o app sair (o ``kill -0`` e so uma checagem de existencia), troca o
    bundle com ``ditto`` -- que preserva symlinks e metadados do ``.app``, coisa
    que ``cp -R`` faz mal -- reabre e se autolimpa.

    A troca e feita em duas etapas, com um bundle temporario ao lado do destino:
    o ``.app`` antigo so e removido depois que o novo ja esta no disco, entao uma
    falha no meio do caminho nao deixa o usuario sem app nenhum.
    """
    lines = [
        "#!/bin/sh",
        "# Updater do Streamer Sidekick (macOS). Gerado pelo app; se autoapaga.",
        "PID=" + str(int(pid)),
        "TARGET=" + shlex.quote(str(target)),
        "NEW=" + shlex.quote(str(new_root)),
        "STAGING=" + shlex.quote(str(staging)),
        'NEXT="$TARGET.new"',
        "",
        "# Espera o app fechar (ate 120s) para nao trocar arquivos em uso.",
        "i=0",
        'while kill -0 "$PID" 2>/dev/null && [ "$i" -lt 120 ]; do',
        "  sleep 1",
        "  i=$((i + 1))",
        "done",
        "sleep 1",
        "",
        "# Copia primeiro, remove depois: se o ditto falhar, o app antigo continua la.",
        'rm -rf "$NEXT"',
        'if ! ditto "$NEW" "$NEXT"; then',
        '  rm -rf "$NEXT"',
        '  open "$TARGET"',
        '  rm -rf "$STAGING"',
        '  rm -f "$0"',
        "  exit 1",
        "fi",
        'rm -rf "$TARGET"',
        'mv "$NEXT" "$TARGET"',
        "",
        "# Zip baixado por navegador vem em quarentena e o macOS recusa abrir.",
        "# O nosso download nao marca, mas isso cobre quem baixou o zip na mao.",
        'xattr -dr com.apple.quarantine "$TARGET" 2>/dev/null',
        'open "$TARGET"',
        'rm -rf "$STAGING"',
        'rm -f "$0"',
    ]
    return "\n".join(lines) + "\n"


def _write_updater_sh(new_root: Path, target: Path, staging: Path, pid: int) -> Path:
    # Fica FORA de staging para poder apagar staging e a si mesmo.
    fd, path = tempfile.mkstemp(prefix="ssk_apply_", suffix=".sh")
    os.close(fd)
    sh_path = Path(path)
    sh_path.write_text(build_updater_sh(new_root, target, staging, pid), encoding="utf-8")
    sh_path.chmod(0o755)
    return sh_path


def _download(url: str, on_progress: Optional[Callable[[int, int], None]] = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    parts: list[bytes] = []
    with net.urlopen(request, timeout=_HTTP_TIMEOUT) as response:
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
