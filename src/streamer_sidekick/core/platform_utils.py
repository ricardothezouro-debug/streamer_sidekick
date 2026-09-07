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


def request_accessibility() -> Optional[bool]:
    """Pede a permissao de Acessibilidade ao macOS e devolve se ja esta valendo.

    Diferente de mandar o usuario nos Ajustes do Sistema, isto faz o macOS
    cadastrar A COPIA QUE ESTA RODANDO. Importa porque o ``.app`` e assinado
    apenas ad-hoc: cada build tem uma assinatura diferente, entao uma entrada
    antiga na lista (de outro build, ou de uma copia que foi movida) fica
    marcada mas nao vale para o processo atual -- o usuario ve a chave ligada e
    mesmo assim nada funciona. O prompt resolve isso porque cria a entrada certa.

    Devolve None quando a pergunta nao se aplica (outro SO) ou nao pode ser feita.
    """
    if sys.platform != "darwin":
        return None
    try:
        from ApplicationServices import (  # type: ignore
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )
    except ImportError:
        return None
    try:
        return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}))
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


def open_input_monitoring_settings() -> None:
    """Abre o painel de Monitoramento de Entrada (so no macOS).

    O ``pynput`` cria um event tap do tipo "listen only", que o macOS moderno
    classifica como Monitoramento de Entrada. Em algumas maquinas o app aparece
    nessa lista e nao na de Acessibilidade, entao vale poder abrir as duas.
    """
    if sys.platform != "darwin":
        return
    subprocess.run(
        ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"],
        check=False,
    )


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

    try:
        view = objc.objc_object(c_void_p=win_id)
        window = view.window()
        if window is None:
            return False
        # canJoinAllSpaces (1<<0) | fullScreenAuxiliary (1<<8)
        window.setCollectionBehavior_(window.collectionBehavior() | (1 << 0) | (1 << 8))
        # NSStatusWindowLevel: acima das janelas comuns, abaixo de alertas do SO.
        window.setLevel_(25)
        return True
    except Exception:
        return False
