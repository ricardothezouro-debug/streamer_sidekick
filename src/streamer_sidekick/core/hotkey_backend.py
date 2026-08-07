"""Backend de hotkeys globais multiplataforma.

No Windows usamos o pacote ``keyboard`` (funciona sem privilegios de
administrador para hotkeys nao supressivas). No macOS/Linux usamos ``pynput``,
que roda em espaco de usuario -- no macOS o app precisa receber permissao de
Acessibilidade (Ajustes do Sistema > Privacidade e Seguranca > Acessibilidade)
para que os atalhos globais funcionem.

Ambos os backends expoem a mesma API minima:

    is_available() -> bool
    backend_name() -> str
    register(sequence, callback) -> handle
    unregister(handle) -> None

``sequence`` usa a notacao do app, por exemplo ``"Ctrl+Alt+H"`` ou
``"Ctrl+Alt+Shift+C"``. Os callbacks disparam em uma thread de fundo; quem
chama e responsavel por voltar para a thread da GUI (o app ja faz isso via
sinais do Qt).
"""
from __future__ import annotations

import sys
from typing import Any, Callable

_ON_WINDOWS = sys.platform == "win32"

_keyboard: Any = None
_pynput_keyboard: Any = None

if _ON_WINDOWS:
    try:  # pragma: no cover - depende da plataforma
        import keyboard as _keyboard  # type: ignore
    except ImportError:
        _keyboard = None
else:
    try:  # pragma: no cover - depende da plataforma
        from pynput import keyboard as _pynput_keyboard  # type: ignore
    except ImportError:
        _pynput_keyboard = None


def backend_name() -> str:
    """Nome do backend ativo para exibicao em diagnosticos."""
    return "keyboard" if _ON_WINDOWS else "pynput"


def is_available() -> bool:
    """True se a biblioteca de hotkeys do SO atual esta instalada."""
    if _ON_WINDOWS:
        return _keyboard is not None
    return _pynput_keyboard is not None


def register(sequence: str, callback: Callable[[], None]) -> Any:
    """Registra um atalho global e devolve um handle opaco (ou lanca excecao)."""
    if _ON_WINDOWS:
        if _keyboard is None:
            raise RuntimeError("Pacote keyboard nao esta disponivel")
        return _keyboard.add_hotkey(sequence, callback, suppress=False)

    if _pynput_keyboard is None:
        raise RuntimeError("Pacote pynput nao esta disponivel")
    combo = _to_pynput(sequence)
    listener = _pynput_keyboard.GlobalHotKeys({combo: callback})
    listener.start()
    return listener


def unregister(handle: Any) -> None:
    """Remove um atalho previamente registrado. Tolerante a handles invalidos."""
    if handle is None:
        return
    if _ON_WINDOWS:
        if _keyboard is None:
            return
        try:
            _keyboard.remove_hotkey(handle)
        except (KeyError, ValueError):
            pass
        return
    # pynput: o handle e um listener em sua propria thread.
    try:
        handle.stop()
    except Exception:
        pass


# --- Conversao de notacao "Ctrl+Alt+H" -> formato do pynput "<ctrl>+<alt>+h" ---

_MODIFIERS = {
    "ctrl": "<ctrl>",
    "control": "<ctrl>",
    "alt": "<alt>",
    "option": "<alt>",
    "opt": "<alt>",
    "altgr": "<alt_gr>",
    "shift": "<shift>",
    "cmd": "<cmd>",
    "command": "<cmd>",
    "win": "<cmd>",
    "super": "<cmd>",
    "meta": "<cmd>",
}

_SPECIAL_KEYS = {
    "space": "<space>",
    "enter": "<enter>",
    "return": "<enter>",
    "tab": "<tab>",
    "esc": "<esc>",
    "escape": "<esc>",
    "up": "<up>",
    "down": "<down>",
    "left": "<left>",
    "right": "<right>",
    "home": "<home>",
    "end": "<end>",
    "delete": "<delete>",
    "del": "<delete>",
    "backspace": "<backspace>",
    "insert": "<insert>",
    "pageup": "<page_up>",
    "pagedown": "<page_down>",
    "capslock": "<caps_lock>",
}


def _to_pynput(sequence: str) -> str:
    """Traduz a notacao do app para o formato aceito por ``GlobalHotKeys``."""
    parts = [part.strip().lower() for part in sequence.split("+") if part.strip()]
    tokens: list[str] = []
    for part in parts:
        if part in _MODIFIERS:
            tokens.append(_MODIFIERS[part])
        elif part in _SPECIAL_KEYS:
            tokens.append(_SPECIAL_KEYS[part])
        elif len(part) == 1:
            tokens.append(part)
        elif part.startswith("f") and part[1:].isdigit():
            tokens.append(f"<{part}>")
        else:
            # Ultimo recurso: entrega o nome literal e deixa o pynput decidir.
            tokens.append(f"<{part}>")
    return "+".join(tokens)
