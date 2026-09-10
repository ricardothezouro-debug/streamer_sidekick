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


def float_above_fullscreen(widget: object) -> bool:
    """Faz a janela aparecer por cima de um app em tela cheia (so no macOS).

    Por padrao o macOS trata cada app em tela cheia como um Space proprio, e uma
    janela de outro app simplesmente nao e desenhada la. Para o Streamer
    Sidekick isso derruba o caso de uso principal: marcar um evento com o jogo
    em tela cheia. O atalho dispara, a janela abre -- mas no Space errado, entao
    parece que nao aconteceu nada.

    A correcao e declarar a janela como auxiliar de tela cheia e presente em
    todos os Spaces, mais um nivel acima das janelas comuns.

    Devolve False quando nao se aplica ou os bindings nao estao disponiveis.
    """
    if sys.platform != "darwin":
        return False

    # So existe NSWindow sob a plataforma Cocoa. Em "offscreen" (testes, CI) o
    # winId() nao aponta para um NSView, e entregar esse ponteiro ao objc faz o
    # processo morrer com SIGSEGV -- foi assim que o smoke test quebrou.
    try:
        from PySide6.QtGui import QGuiApplication

        if QGuiApplication.platformName() != "cocoa":
            return False
    except Exception:
        return False

    try:
        import objc  # type: ignore
    except ImportError:
        return False

    try:
        win_id = int(widget.winId())  # type: ignore[attr-defined]
    except Exception:
        return False
    if not win_id:
        return False

    _CAN_JOIN_ALL_SPACES = 1 << 0
    _MOVE_TO_ACTIVE_SPACE = 1 << 1
    _FULLSCREEN_AUXILIARY = 1 << 8
    _POPUP_MENU_LEVEL = 101

    try:
        view = objc.objc_object(c_void_p=win_id)
        window = view.window()
        if window is None:
            return False

        # MoveToActiveSpace tem que ser LIMPO, nao apenas sobreposto: o macOS
        # recusa a combinacao com CanJoinAllSpaces e lanca
        # NSInternalInconsistencyException. O Qt marca essa bit em janelas com
        # pai, entao somar sem limpar fazia a configuracao inteira falhar --
        # e era exatamente a janela do marcador que tinha o problema.
        comportamento = window.collectionBehavior()
        comportamento &= ~_MOVE_TO_ACTIVE_SPACE
        comportamento |= _CAN_JOIN_ALL_SPACES | _FULLSCREEN_AUXILIARY
        window.setCollectionBehavior_(comportamento)

        # Um app em tela cheia cobre os niveis baixos; 25 nao bastava. Por
        # ultimo, porque algumas chamadas do AppKit rebaixam o nivel.
        window.setLevel_(_POPUP_MENU_LEVEL)
        return True
    except Exception as exc:
        # Nao engolir: foi um except silencioso aqui que escondeu a excecao
        # acima por uma versao inteira, com a janela simplesmente nao aparecendo.
        print(f"[streamer_sidekick] float_above_fullscreen falhou: {exc}")
        return False
