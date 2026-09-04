"""Backend de hotkeys globais multiplataforma.

No Windows usamos o pacote ``keyboard`` (funciona sem privilegios de
administrador para hotkeys nao supressivas). No macOS/Linux usamos ``pynput``,
que roda em espaco de usuario -- no macOS o app precisa receber permissao de
Acessibilidade (Ajustes do Sistema > Privacidade e Seguranca > Acessibilidade)
para que os atalhos globais funcionem.

Ambos os backends expoem a mesma API minima:

    is_available() -> bool
    backend_name() -> str
    validate(sequence) -> None          # levanta excecao se a notacao for invalida
    register(sequence, callback) -> handle
    register_batch({sequence: callback}) -> handle
    unregister(handle) -> None

IMPORTANTE (macOS): o ``pynput`` traduz teclas via Carbon (``TISCopy...``), que
NAO e seguro para chamadas concorrentes. Subir tres ou mais listeners ao mesmo
tempo aborta o processo inteiro -- SIGABRT, sem excecao Python, sem chance de
tratar. Como o app registra cinco atalhos no hub e mais um por overlay de
contador, isso derrubava o Streamer Sidekick no arranque.

Por isso, fora do Windows este modulo mantem UM UNICO listener para o processo
inteiro: registrar ou remover um atalho reescreve o mapa de combos e reconstroi
esse listener (parando o anterior e esperando ele morrer antes de subir o novo).
Quem chama nao precisa saber disso -- a API continua sendo por atalho.

``sequence`` usa a notacao do app, por exemplo ``"Ctrl+Alt+H"`` ou
``"Ctrl+Alt+Shift+C"``. Os callbacks disparam em uma thread de fundo; quem
chama e responsavel por voltar para a thread da GUI (o app ja faz isso via
sinais do Qt).
"""
from __future__ import annotations

import itertools
import sys
import threading
from typing import Any, Callable

_ON_WINDOWS = sys.platform == "win32"

# Quanto esperamos o listener antigo morrer antes de subir o proximo.
_STOP_TIMEOUT = 2.0

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


# Estado do listener unico (so usado fora do Windows).
_lock = threading.RLock()
_tokens = itertools.count(1)
_entries: dict[int, tuple[str, Callable[[], None]]] = {}
_listener: Any = None


def backend_name() -> str:
    """Nome do backend ativo para exibicao em diagnosticos."""
    return "keyboard" if _ON_WINDOWS else "pynput"


def is_available() -> bool:
    """True se a biblioteca de hotkeys do SO atual esta instalada."""
    if _ON_WINDOWS:
        return _keyboard is not None
    return _pynput_keyboard is not None


def validate(sequence: str) -> None:
    """Levanta excecao se o backend atual nao entender a notacao informada."""
    if _ON_WINDOWS:
        if _keyboard is None:
            raise RuntimeError("Pacote keyboard nao esta disponivel")
        _keyboard.parse_hotkey(sequence)
        return
    if _pynput_keyboard is None:
        raise RuntimeError("Pacote pynput nao esta disponivel")
    _pynput_keyboard.HotKey.parse(_to_pynput(sequence))


def register(sequence: str, callback: Callable[[], None]) -> Any:
    """Registra um atalho global e devolve um handle opaco (ou lanca excecao)."""
    return register_batch({sequence: callback})


def register_batch(items: dict[str, Callable[[], None]]) -> Any:
    """Registra varios atalhos de uma vez, com uma unica reconstrucao."""
    if not items:
        return None

    if _ON_WINDOWS:
        if _keyboard is None:
            raise RuntimeError("Pacote keyboard nao esta disponivel")
        return [
            _keyboard.add_hotkey(sequence, callback, suppress=False)
            for sequence, callback in items.items()
        ]

    if _pynput_keyboard is None:
        raise RuntimeError("Pacote pynput nao esta disponivel")

    with _lock:
        added: list[int] = []
        for sequence, callback in items.items():
            token = next(_tokens)
            _entries[token] = (_to_pynput(sequence), callback)
            added.append(token)
        try:
            _rebuild()
        except Exception:
            # Nao deixa um combo invalido derrubar os atalhos que ja funcionavam.
            for token in added:
                _entries.pop(token, None)
            _rebuild()
            raise
        return added


def unregister(handle: Any) -> None:
    """Remove atalhos previamente registrados. Tolerante a handles invalidos."""
    if handle is None:
        return

    if _ON_WINDOWS:
        if _keyboard is None:
            return
        for hook in handle if isinstance(handle, list) else [handle]:
            try:
                _keyboard.remove_hotkey(hook)
            except (KeyError, ValueError):
                pass
        return

    with _lock:
        for token in handle if isinstance(handle, list) else [handle]:
            _entries.pop(token, None)
        _rebuild()


def _rebuild() -> None:
    """Derruba o listener atual e sobe outro com o mapa de combos vigente.

    Chamado sempre com ``_lock`` seguro, para que nunca existam dois listeners
    vivos ao mesmo tempo (ver a nota sobre o Carbon no topo do modulo).
    """
    global _listener

    if _listener is not None:
        try:
            _listener.stop()
        except Exception:
            pass
        try:
            _listener.join(_STOP_TIMEOUT)
        except Exception:
            pass
        _listener = None

    if not _entries:
        return

    # Dois contadores podem usar o mesmo atalho; como o mapa do pynput e um
    # dicionario, agrupamos os callbacks para que todos disparem.
    grouped: dict[str, list[Callable[[], None]]] = {}
    for combo, callback in _entries.values():
        grouped.setdefault(combo, []).append(callback)

    mapping = {combo: _fan_out(callbacks) for combo, callbacks in grouped.items()}
    listener = _pynput_keyboard.GlobalHotKeys(mapping)
    listener.start()
    _listener = listener


def _fan_out(callbacks: list[Callable[[], None]]) -> Callable[[], None]:
    """Um callback que dispara todos os inscritos no mesmo combo."""
    def run() -> None:
        for callback in callbacks:
            try:
                callback()
            except Exception:
                pass

    return run


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
