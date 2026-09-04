"""Utilitarios dependentes de sistema operacional."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


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


def accessibility_trusted() -> Optional[bool]:
    """No macOS: o app tem permissao de Acessibilidade? Fora dele, None.

    Sem essa permissao o macOS entrega ZERO eventos de teclado ao processo. Os
    atalhos globais sao registrados com sucesso e simplesmente nunca disparam --
    e nada no app denuncia o motivo. Por isso o Diagnostico pergunta ao sistema.

    Devolve None quando a pergunta nao se aplica (outro SO) ou nao pode ser
    feita (bindings do pyobjc ausentes).
    """
    if sys.platform != "darwin":
        return None
    try:
        from ApplicationServices import AXIsProcessTrusted  # type: ignore
    except ImportError:
        return None
    try:
        return bool(AXIsProcessTrusted())
    except Exception:
        return None


def open_accessibility_settings() -> None:
    """Abre o painel de Acessibilidade dos Ajustes do Sistema (so no macOS)."""
    if sys.platform != "darwin":
        return
    subprocess.run(
        ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"],
        check=False,
    )
