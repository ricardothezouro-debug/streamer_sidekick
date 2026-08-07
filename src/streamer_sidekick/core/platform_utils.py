"""Utilitarios dependentes de sistema operacional."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def open_path(path: Path | str) -> None:
    """Abre um arquivo ou pasta no aplicativo padrao do SO.

    Substitui ``os.startfile`` (que so existe no Windows) por uma versao que
    tambem funciona no macOS (``open``) e no Linux (``xdg-open``).
    """
    target = str(path)
    if sys.platform == "win32":
        os.startfile(target)  # type: ignore[attr-defined]  # noqa: S606 - Windows only
    elif sys.platform == "darwin":
        subprocess.run(["open", target], check=False)
    else:
        subprocess.run(["xdg-open", target], check=False)


def app_icon_path() -> Path:
    """Devolve o melhor arquivo de icone para a plataforma atual.

    No Windows preferimos o ``.ico``; nas demais plataformas o ``.png`` (o Qt
    nao renderiza ``.ico`` com a mesma consistencia fora do Windows).
    """
    brand = Path(__file__).resolve().parents[1] / "assets" / "brand"
    ico = brand / "app_icon.ico"
    png = brand / "app_icon.png"
    if sys.platform == "win32" and ico.exists():
        return ico
    if png.exists():
        return png
    return ico
