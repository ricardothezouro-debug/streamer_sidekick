"""Ícones do contador numa pasta do app (``<app_data>/counter_icons/``).

O preset guarda só o nome do arquivo, nunca o caminho: assim ele funciona em
qualquer PC (e a nuvem sincroniza a pasta como ``contador/icones/<arquivo>``).

- Até 1 MB a imagem é copiada como está; acima disso vira PNG de 512 px no
  lado maior, sem aumentar imagem pequena (decisão Q33).
- O nome é o original mais um pedaço do hash do conteúdo (``moeda-3f9a1c2b.png``):
  a mesma imagem nunca duplica e dois "icon.png" diferentes não se sobrescrevem
  (decisão Q31).
"""
from __future__ import annotations

import hashlib
import html
import os
from pathlib import Path
from typing import Optional

from streamer_sidekick.core.paths import app_data_dir

MAX_BYTES = 1024 * 1024
MAX_SIDE = 512


class IconError(Exception):
    pass


class CounterIcons:
    def __init__(self, folder: Optional[Path] = None) -> None:
        self.folder = Path(folder) if folder is not None else app_data_dir() / "counter_icons"

    def import_image(self, source: Path) -> str:
        """Copia (ou converte) a imagem para a pasta e devolve o nome do arquivo."""
        source = Path(source)
        try:
            conteudo = source.read_bytes()
        except OSError as exc:
            raise IconError(f"não deu para ler {source.name}") from exc
        resumo = hashlib.sha256(conteudo).hexdigest()[:8]
        if len(conteudo) > MAX_BYTES:
            conteudo, extensao = _png_reduzido(conteudo), ".png"
        else:
            extensao = source.suffix.lower()
        nome = f"{_nome_seguro(source.stem)}-{resumo}{extensao}"
        destino = self.folder / nome
        if not destino.exists():
            self.folder.mkdir(parents=True, exist_ok=True)
            temporario = destino.with_name(destino.name + ".copiando")
            temporario.write_bytes(conteudo)
            os.replace(temporario, destino)
        return nome

    def path_for(self, name: Optional[str]) -> Optional[Path]:
        """O arquivo de um nome guardado no preset, ou ``None`` se não existe aqui."""
        if not name or Path(name).name != name or name in {".", ".."}:
            return None
        caminho = self.folder / name
        return caminho if caminho.is_file() else None


def img_tag(path: Optional[Path], size: int) -> str:
    """O ``<img>`` do rich text do Qt, ou vazio quando o ícone não existe aqui."""
    if path is None:
        return ""
    return f'<img src="{html.escape(path.as_posix(), quote=True)}" height="{size}"> '


def _png_reduzido(conteudo: bytes) -> bytes:
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
    from PySide6.QtGui import QImage

    imagem = QImage.fromData(conteudo)
    if imagem.isNull():
        raise IconError("não deu para usar essa imagem")
    if max(imagem.width(), imagem.height()) > MAX_SIDE:
        imagem = imagem.scaled(MAX_SIDE, MAX_SIDE, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
    saida = QByteArray()
    buffer = QBuffer(saida)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not imagem.save(buffer, "PNG"):
        raise IconError("não deu para converter essa imagem")
    buffer.close()
    return bytes(saida.data())


def _nome_seguro(stem: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid else char for char in stem.strip()).strip(". ")
    return cleaned or "icone"
