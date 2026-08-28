# Como criar um Guia de Platina (para o Streamer Sidekick)

Um **guia de platina** é um plugin (categoria `platina`) que aparece na aba
**Platinas** do Streamer Sidekick: uma checklist de troféus por jogo, com
progresso salvo, dicas e imagens.

> **Uso com IA:** entregue **este arquivo + o `PLUGIN_STANDARD.md`** para uma IA,
> junto da lista de troféus do jogo. Ela gera o repositório completo. Você não
> precisa clonar nada — o repo template `platina-template` é só uma referência.

## O que muda por jogo (só 2 coisas)

1. **O nome da pasta do pacote**: `src/platina_<jogo>/` (ex.: `platina_elden_ring`).
   Use um nome **único** por guia — dois guias com o mesmo nome de pacote colidem.
2. **O arquivo `guide_data.py`**: nome do jogo + lista de troféus.

Os outros arquivos (`module.py`, `page.py`, `storage.py`, `image_loader.py`,
`__main__.py`, `__init__.py`) são **genéricos** — use-os **verbatim**. Eles usam
imports **relativos**, então funcionam sob qualquer nome de pacote sem edição.

## Estrutura do repositório

```
platina-<jogo>/                     (repositório no GitHub)
  src/
    platina_<jogo>/
      __init__.py
      module.py          (genérico)
      page.py            (genérico)
      storage.py         (genérico)
      image_loader.py    (genérico)
      __main__.py        (genérico)
      guide_data.py      <- EDITE ISTO
  requirements.txt
  README.md
  .gitignore
```

---

## `guide_data.py` — o único arquivo a editar

```python
# Identificador único do guia (kebab-case). Vira o id do plugin e a pasta de
# progresso. Ex.: "elden-ring".
GUIDE_ID = "elden-ring"

GAME_NAME = "Elden Ring"
GAME_SUBTITLE = "Guia de platina: marque os troféus e acompanhe seu progresso."
ACCENT = "#B9FF43"  # cor de destaque do card (hex)

# Cada troféu:
#   id    (str, estável, NÃO repita)
#   name  (str)
#   tier  ("bronze" | "prata" | "ouro" | "platina")
#   tip   (str, como conseguir)
#   image (str, opcional) — URL de imagem (mapa, print de guia). Baixada e
#         cacheada; prefira CDNs estáveis para hotlink (ex.: Steam).
TROPHIES = [
    {"id": "t01", "name": "Erdtree...", "tier": "bronze", "tip": "Como fazer..."},
    {"id": "t02", "name": "Grande Runa", "tier": "prata", "tip": "...",
     "image": "https://exemplo.com/mapa.jpg"},
    {"id": "plat", "name": "Elden Lord", "tier": "platina",
     "tip": "Conquiste todos os outros troféus."},
]
```

---

## Arquivos genéricos (copie EXATAMENTE, não altere)

### `src/platina_<jogo>/__init__.py`
```python
__version__ = "1.0.0"
```

### `src/platina_<jogo>/module.py`
```python
"""Adaptador de plugin do Streamer Sidekick (categoria: platina)."""
from dataclasses import dataclass

from . import guide_data

MODULE_ID = guide_data.GUIDE_ID


@dataclass(frozen=True)
class ModuleInfo:
    module_id: str
    title: str
    subtitle: str
    status: str
    accent: str


def module_info():
    from .storage import load_progress

    done = len(load_progress())
    total = len(guide_data.TROPHIES)
    data = dict(
        module_id=guide_data.GUIDE_ID,
        title=guide_data.GAME_NAME,
        subtitle=guide_data.GAME_SUBTITLE,
        status=f"{done}/{total} troféus",
        accent=guide_data.ACCENT,
    )
    try:
        from streamer_sidekick.core.modules import ModuleInfo as SidekickModuleInfo

        return SidekickModuleInfo(**data)
    except Exception:
        return ModuleInfo(**data)


def help_text() -> str:
    return (
        "Marque cada troféu conforme conquista — o progresso fica salvo "
        "automaticamente. Use a busca para achar um troféu rápido."
    )


def build_page(config=None):
    from .page import GuidePage

    return GuidePage()
```

### `src/platina_<jogo>/storage.py`
```python
"""Persistência do progresso (fora da pasta do plugin, sobrevive a updates)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import guide_data


def _data_dir() -> Path:
    base = os.getenv("APPDATA")
    root = Path(base) / "StreamerSidekick" if base else Path.home() / ".streamer_sidekick"
    path = root / "platinas" / guide_data.GUIDE_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_progress() -> set[str]:
    file = _data_dir() / "progress.json"
    try:
        return set(json.loads(file.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return set()


def save_progress(done: set[str]) -> None:
    file = _data_dir() / "progress.json"
    try:
        file.write_text(json.dumps(sorted(done)), encoding="utf-8")
    except OSError:
        pass
```

### `src/platina_<jogo>/image_loader.py`
```python
"""Carrega imagens por URL com cache em disco."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Callable
from urllib import request

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QPixmap

from . import guide_data


def _cache_dir() -> Path:
    base = os.getenv("APPDATA")
    root = Path(base) / "StreamerSidekick" if base else Path.home() / ".streamer_sidekick"
    path = root / "platinas" / guide_data.GUIDE_ID / "img_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_path(url: str) -> Path:
    ext = ".img"
    clean = url.lower().split("?")[0]
    for candidate in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if clean.endswith(candidate):
            ext = candidate
            break
    return _cache_dir() / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ext)


class _DownloadWorker(QThread):
    done = Signal(str)

    def __init__(self, url: str, dest: Path) -> None:
        super().__init__()
        self._url = url
        self._dest = dest

    def run(self) -> None:
        try:
            req = request.Request(self._url, headers={"User-Agent": "Mozilla/5.0"})
            with request.urlopen(req, timeout=20) as response:
                data = response.read()
            self._dest.write_bytes(data)
            self.done.emit(str(self._dest))
        except Exception:
            self.done.emit("")


class ImageLoader(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._workers: list[_DownloadWorker] = []

    def load(self, url: str, on_ready: Callable[[QPixmap], None]) -> QPixmap | None:
        cache = _cache_path(url)
        if cache.exists():
            pixmap = QPixmap(str(cache))
            if not pixmap.isNull():
                return pixmap
        worker = _DownloadWorker(url, cache)

        def _finish(path: str) -> None:
            if worker in self._workers:
                self._workers.remove(worker)
            if path:
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    on_ready(pixmap)

        worker.done.connect(_finish)
        self._workers.append(worker)
        worker.start()
        return None
```

### `src/platina_<jogo>/page.py`
```python
"""Página do guia: checklist, progresso, busca e imagens."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QProgressBar, QScrollArea, QVBoxLayout, QWidget,
)

from . import guide_data
from .image_loader import ImageLoader
from .storage import load_progress, save_progress

_IMG_MAX_W = 620
_IMG_MAX_H = 420
_TIER_COLORS = {"bronze": "#C77B3B", "prata": "#B8C0CC", "ouro": "#E7C64A", "platina": "#7FE7FF"}
_PROGRESS_QSS = (
    "QProgressBar{background:#0B111A;border:1px solid #273140;border-radius:9px;"
    "min-height:18px;text-align:center;color:#F3F6FF;font-weight:600}"
    "QProgressBar::chunk{border-radius:8px;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
    "stop:0 #37F2FF,stop:0.5 #B9FF43,stop:1 #FF4FD8)}"
)


class _TrophyRow(QFrame):
    def __init__(self, trophy, checked, on_toggle, image_loader=None, parent=None):
        super().__init__(parent)
        self.trophy = trophy
        self.setObjectName("NeonPanel")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)
        self.check = QCheckBox()
        self.check.setChecked(checked)
        self.check.toggled.connect(lambda done: on_toggle(trophy["id"], done))
        text = QVBoxLayout()
        text.setSpacing(2)
        name = QLabel(trophy["name"]); name.setObjectName("SectionTitle")
        tip = QLabel(trophy.get("tip", "")); tip.setObjectName("Muted"); tip.setWordWrap(True)
        text.addWidget(name); text.addWidget(tip)
        image_url = str(trophy.get("image") or "").strip()
        if image_url and image_loader is not None:
            self._image_label = QLabel("Carregando imagem…"); self._image_label.setObjectName("Muted")
            text.addWidget(self._image_label)
            pixmap = image_loader.load(image_url, self._set_image)
            if pixmap is not None:
                self._set_image(pixmap)
        tier = QLabel(str(trophy.get("tier", "")).upper())
        tier.setStyleSheet(f"color:{_TIER_COLORS.get(trophy.get('tier', ''), '#A8B0BC')};font-weight:700;font-size:11px;")
        layout.addWidget(self.check, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text, 1)
        layout.addWidget(tier, 0, Qt.AlignmentFlag.AlignTop)

    def _set_image(self, pixmap):
        self._image_label.setText("")
        self._image_label.setPixmap(pixmap.scaled(
            _IMG_MAX_W, _IMG_MAX_H, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))


class GuidePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._done = load_progress()
        self._rows = []
        self._image_loader = ImageLoader(self)
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 22, 0); outer.setSpacing(14)
        title = QLabel(guide_data.GAME_NAME); title.setObjectName("PageTitle")
        subtitle = QLabel(guide_data.GAME_SUBTITLE); subtitle.setObjectName("Muted"); subtitle.setWordWrap(True)
        outer.addWidget(title); outer.addWidget(subtitle)
        self.progress = QProgressBar(); self.progress.setStyleSheet(_PROGRESS_QSS)
        self.progress.setRange(0, max(1, len(guide_data.TROPHIES)))
        self.progress_label = QLabel(""); self.progress_label.setObjectName("StatusPill")
        prow = QHBoxLayout(); prow.addWidget(self.progress, 1); prow.addWidget(self.progress_label, 0)
        outer.addLayout(prow)
        self.search = QLineEdit(); self.search.setPlaceholderText("Filtrar troféu…")
        self.search.textChanged.connect(self._apply_filter)
        outer.addWidget(self.search)
        container = QWidget(); self.list_layout = QVBoxLayout(container)
        self.list_layout.setContentsMargins(0, 0, 0, 0); self.list_layout.setSpacing(10)
        for trophy in guide_data.TROPHIES:
            row = _TrophyRow(trophy, trophy["id"] in self._done, self._on_toggle, image_loader=self._image_loader)
            self._rows.append(row); self.list_layout.addWidget(row)
        self.list_layout.addStretch(1)
        scroll = QScrollArea(); scroll.setObjectName("PageScroll"); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(container); outer.addWidget(scroll, 1)
        self._update_progress()

    def _on_toggle(self, trophy_id, done):
        if done: self._done.add(trophy_id)
        else: self._done.discard(trophy_id)
        save_progress(self._done); self._update_progress()

    def _update_progress(self):
        total = len(guide_data.TROPHIES)
        done = sum(1 for t in guide_data.TROPHIES if t["id"] in self._done)
        self.progress.setValue(done); self.progress_label.setText(f"{done}/{total}")

    def _apply_filter(self):
        query = self.search.text().strip().lower()
        for row in self._rows:
            t = row.trophy
            row.setVisible(query in f"{t['name']} {t.get('tip', '')}".lower())
```

### `src/platina_<jogo>/__main__.py`
```python
"""Rodar standalone: python -m platina_<jogo>"""
import sys

from PySide6.QtWidgets import QApplication

from . import guide_data
from .page import GuidePage

_THEME = """
QWidget{background:#0A0B12;color:#F3F6FF;font-family:'Segoe UI';font-size:14px}
QLabel#PageTitle{font-size:30px;font-weight:700}
QLabel#SectionTitle{font-size:16px;font-weight:700}
QLabel#Muted{color:#A8B0BC}
QLabel#StatusPill{background:#0A0B12;border:1px solid #273140;border-radius:8px;padding:6px 10px;color:#C7D0DD;font-weight:600}
QFrame#NeonPanel{background:#0D121B;border:1px solid #273140;border-radius:10px}
QLineEdit{background:#0B111A;border:1px solid #273140;border-radius:8px;padding:8px 10px;color:#F3F6FF}
QCheckBox::indicator{width:18px;height:18px;border-radius:5px;border:1px solid #596373;background:#0B111A}
QCheckBox::indicator:checked{background:#14383F;border-color:#37F2FF}
QScrollArea{border:0}
"""


def run() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(_THEME)
    page = GuidePage()
    page.setWindowTitle(f"{guide_data.GAME_NAME} — Guia de Platina")
    page.resize(720, 760)
    page.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
```

### `requirements.txt`
```
PySide6>=6.6
```

### `.gitignore`
```
__pycache__/
*.py[cod]
.venv/
build/
dist/
```

---

## Publicar o guia

1. Crie um repositório no GitHub (ex.: `platina-elden-ring`) e envie os arquivos.
2. Teste standalone: `set PYTHONPATH=src && python -m platina_<jogo>`.
3. Adicione uma entrada no `platinas.json` do Streamer Sidekick:

```json
{
  "id": "elden-ring",
  "name": "Elden Ring",
  "description": "Guia de platina do Elden Ring.",
  "repo": "seu-usuario/platina-elden-ring",
  "ref": "main",
  "version": "1.0.0",
  "src_subdir": "src",
  "module": "platina_elden_ring.module",
  "min_sidekick_version": "0.6.0"
}
```

Pronto — o guia aparece na aba **Platinas** para instalar.

---

## Prompt pronto para a IA

> Você recebeu `PLUGIN_STANDARD.md` e `GUIA_DE_PLATINA.md`. Crie um guia de
> platina para o jogo **<JOGO>** seguindo exatamente esse padrão:
> - Use o nome de pacote `platina_<slug_do_jogo>`.
> - Copie os arquivos genéricos verbatim.
> - Preencha o `guide_data.py` com estes troféus: **<cole a lista de troféus,
>   com id/nome/tier/dica e, quando útil, uma URL de imagem>**.
> - Gere também `requirements.txt`, `.gitignore`, `README.md` e a entrada do
>   `platinas.json`.
