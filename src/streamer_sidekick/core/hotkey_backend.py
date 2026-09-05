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
    unregister(handle) -> None

IMPORTANTE (macOS): o ``pynput`` traduz teclas com o HIToolbox
(``TISGetInputSourceProperty``), e essa API **exige a fila principal**. Chamada
de qualquer outra thread ela dispara ``dispatch_assert_queue`` e o macOS mata o
processo na hora -- SIGTRAP, sem excecao Python, sem chance de tratar. O pynput
chama exatamente isso de dentro da thread do listener, entao qualquer listener
criado pode derrubar o app.

Nao da para escolher em que thread o pynput roda, entao fazemos o inverso:
``_refresh_keycode_snapshot()`` calcula o layout do teclado AQUI, na thread
principal, e troca o ``keycode_context`` do pynput por um que devolve esse valor
ja pronto. A thread do listener deixa de tocar no HIToolbox.

O snapshot e refeito a cada reconstrucao (sempre na thread principal), entao
trocar de layout de teclado continua sendo percebido.

Alem disso, fora do Windows este modulo mantem UM UNICO listener para o processo
inteiro: registrar ou remover um atalho reescreve o mapa de combos e reconstroi
esse listener (parando o anterior e esperando ele morrer antes de subir o novo).
Quem chama nao precisa saber disso -- a API continua sendo por atalho.

``sequence`` usa a notacao do app, por exemplo ``"Ctrl+Alt+H"`` ou
``"Ctrl+Alt+Shift+C"``. Os callbacks disparam em uma thread de fundo; quem
chama e responsavel por voltar para a thread da GUI (o app ja faz isso via
sinais do Qt).
"""
from __future__ import annotations

import contextlib
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

# Layout do teclado lido na thread principal (ver a nota no topo).
_keycode_snapshot: Any = None
_original_keycode_context: Any = None
_keycode_patch_failed = False


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
    """Registra um atalho global e devolve um handle opaco (ou lanca excecao).

    No Windows cada atalho vira um hook proprio do ``keyboard``, exatamente como
    antes. Fora dele o atalho entra no mapa do listener unico, que e reconstruido.
    """
    if _ON_WINDOWS:
        if _keyboard is None:
            raise RuntimeError("Pacote keyboard nao esta disponivel")
        return _keyboard.add_hotkey(sequence, callback, suppress=False)

    if _pynput_keyboard is None:
        raise RuntimeError("Pacote pynput nao esta disponivel")

    with _lock:
        token = next(_tokens)
        _entries[token] = (_to_pynput(sequence), callback)
        try:
            _rebuild()
        except Exception:
            # Nao deixa um combo problematico derrubar os que ja funcionavam.
            _entries.pop(token, None)
            _rebuild()
            raise
        return token


def unregister(handle: Any) -> None:
    """Remove atalhos previamente registrados. Tolerante a handles invalidos."""
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

    with _lock:
        _entries.pop(handle, None)
        _rebuild()


def keycode_snapshot_ok() -> bool:
    """O layout do teclado foi lido com sucesso na thread principal?

    Se voltar False, criar um listener pode derrubar o processo -- o
    Diagnostico usa isto para avisar em vez de deixar o app morrer sozinho.
    """
    if _ON_WINDOWS:
        return True
    return _keycode_snapshot is not None


def _refresh_keycode_snapshot() -> None:
    """Le o layout do teclado na thread principal e fixa o resultado no pynput.

    Precisa rodar na thread principal: e justamente a exigencia do HIToolbox que
    causava o crash. Fora dela, nao faz nada -- o snapshot anterior continua
    valendo.
    """
    global _keycode_snapshot, _original_keycode_context, _keycode_patch_failed

    if _ON_WINDOWS or _pynput_keyboard is None or _keycode_patch_failed:
        return
    if threading.current_thread() is not threading.main_thread():
        return

    try:
        from pynput._util import darwin as _util_darwin
        from pynput.keyboard import _darwin as _kb_darwin
    except ImportError:
        _keycode_patch_failed = True
        return

    if _original_keycode_context is None:
        candidato = _util_darwin.keycode_context
        # Nunca adotar o nosso proprio substituto como "original": ele devolve o
        # snapshot, entao usa-lo para RECALCULAR o snapshot criaria um ciclo que
        # cacharia o valor vazio para sempre.
        if getattr(candidato, "_ssk_snapshot", False):
            return
        _original_keycode_context = candidato

    try:
        with _original_keycode_context() as context:
            _keycode_snapshot = context
    except Exception:
        _keycode_patch_failed = True
        return

    @contextlib.contextmanager
    def _snapshot_context():
        yield _keycode_snapshot

    _snapshot_context._ssk_snapshot = True

    # O keyboard/_darwin.py importa o nome direto, entao trocar so no _util nao
    # bastaria -- precisa ser nos dois lugares.
    _util_darwin.keycode_context = _snapshot_context
    _kb_darwin.keycode_context = _snapshot_context


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
    # Antes de subir a thread do listener: garante que o layout ja foi lido aqui,
    # na thread principal, senao o pynput vai ler la e o processo morre.
    _refresh_keycode_snapshot()
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
