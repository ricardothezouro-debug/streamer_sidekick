"""Atalhos globais do macOS pela API nativa (``RegisterEventHotKey``).

Por que nao usamos o ``pynput`` aqui: ele monta um event tap e chama o HIToolbox
de dentro da thread do listener. Essa API exige a fila principal -- fora dela o
macOS dispara ``dispatch_assert_queue`` e mata o processo com SIGTRAP, sem
excecao Python. Sao pelo menos dois pontos de chamada (a leitura do layout e o
``NSEvent.eventWithCGEvent_`` a cada tecla), entao remendar um de cada vez nao
fecha o problema: o listener inteiro roda no lugar errado.

``RegisterEventHotKey`` e a API que o proprio macOS oferece para atalho global:

* o callback chega **na thread principal**, pelo loop de eventos que o Qt ja roda;
* **nao exige** permissao de Acessibilidade nem de Monitoramento de Entrada,
  porque o app nao le o teclado -- ele so pede ao sistema para ser avisado de uma
  combinacao especifica;
* o sistema recusa o registro quando a combinacao ja pertence a outro app, o que
  nos deixa avisar o usuario em vez de falhar em silencio.

O preco e nao dar para capturar qualquer tecla exotica: so o que tem virtual
keycode conhecido (ver ``_KEYCODES``). Para atalhos de app isso cobre o caso.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import itertools
from typing import Any, Callable, Optional

# --- constantes do Carbon ---------------------------------------------------
_kEventClassKeyboard = 0x6B657962  # 'keyb'
_kEventHotKeyPressed = 5
_kEventParamDirectObject = 0x2D2D2D2D  # '----'
_typeEventHotKeyID = 0x686B6964  # 'hkid'
_SIGNATURE = 0x53534B48  # 'SSKH'

_cmdKey = 0x0100
_shiftKey = 0x0200
_optionKey = 0x0800
_controlKey = 0x1000

# Erro devolvido quando a combinacao ja e de outro app.
_eventHotKeyExistsErr = -9878

_MODIFIERS = {
    "ctrl": _controlKey,
    "control": _controlKey,
    "alt": _optionKey,
    "option": _optionKey,
    "opt": _optionKey,
    "shift": _shiftKey,
    "cmd": _cmdKey,
    "command": _cmdKey,
    "meta": _cmdKey,
    "super": _cmdKey,
    "win": _cmdKey,
}

# Virtual keycodes do layout ANSI. Sao posicoes fisicas, nao letras impressas:
# o mesmo codigo vale em qualquer layout, que e o que queremos num atalho.
_KEYCODES = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8,
    "v": 9, "b": 11, "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17,
    "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23, "=": 24, "9": 25,
    "7": 26, "-": 27, "8": 28, "0": 29, "]": 30, "o": 31, "u": 32, "[": 33,
    "i": 34, "p": 35, "l": 37, "j": 38, "'": 39, "k": 40, ";": 41,
    "\\": 42, ",": 43, "/": 44, "n": 45, "m": 46, ".": 47, "`": 50,
    "enter": 36, "return": 36, "tab": 48, "space": 49, "backspace": 51,
    "delete": 51, "escape": 53, "esc": 53,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97, "f7": 98,
    "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111,
    "f13": 105, "f14": 107, "f15": 113, "f16": 106, "f17": 64, "f18": 79,
    "f19": 80, "f20": 90,
    "home": 115, "end": 119, "pageup": 116, "pagedown": 121,
    "left": 123, "right": 124, "down": 125, "up": 126,
    "del": 117,  # forward delete
}


class _EventTypeSpec(ctypes.Structure):
    _fields_ = [("eventClass", ctypes.c_uint32), ("eventKind", ctypes.c_uint32)]


class _EventHotKeyID(ctypes.Structure):
    _fields_ = [("signature", ctypes.c_uint32), ("id", ctypes.c_uint32)]


_HANDLER_PROC = ctypes.CFUNCTYPE(
    ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
)


def _load_carbon() -> Optional[ctypes.CDLL]:
    caminho = ctypes.util.find_library("Carbon")
    if not caminho:
        return None
    try:
        lib = ctypes.cdll.LoadLibrary(caminho)
    except OSError:
        return None

    lib.GetApplicationEventTarget.restype = ctypes.c_void_p
    lib.RegisterEventHotKey.argtypes = [
        ctypes.c_uint32, ctypes.c_uint32, _EventHotKeyID,
        ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p),
    ]
    lib.RegisterEventHotKey.restype = ctypes.c_int32
    lib.UnregisterEventHotKey.argtypes = [ctypes.c_void_p]
    lib.UnregisterEventHotKey.restype = ctypes.c_int32
    lib.InstallEventHandler.argtypes = [
        ctypes.c_void_p, _HANDLER_PROC, ctypes.c_uint32,
        ctypes.POINTER(_EventTypeSpec), ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    lib.InstallEventHandler.restype = ctypes.c_int32
    lib.GetEventParameter.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32), ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p,
    ]
    lib.GetEventParameter.restype = ctypes.c_int32
    return lib


_carbon = _load_carbon()

_ids = itertools.count(1)
_callbacks: dict[int, Callable[[], None]] = {}
_refs: dict[int, ctypes.c_void_p] = {}
# O ctypes nao segura referencia ao callback nem ao handler: sem estes nomes o
# coletor de lixo os levaria e o macOS chamaria memoria liberada.
_handler_proc: Any = None
_handler_ref: Any = None


def is_available() -> bool:
    return _carbon is not None


def backend_name() -> str:
    return "carbon"


# Simbolos que o Qt escreve no macOS. Versoes antigas do app gravaram o atalho
# ja renderizado ("⌃⌥2") em vez da notacao, entao precisamos aceitar isso na
# leitura -- senao o atalho de quem ja tinha um preset salvo nunca registra.
_SIMBOLOS = {"⌃": "ctrl", "⌥": "alt", "⇧": "shift", "⌘": "cmd"}

# Teclas que fazem sentido sozinhas, sem modificador: sao dedicadas e nao
# atrapalham a digitacao. Uma letra sozinha seria capturada no sistema inteiro.
_SOZINHAS_OK = {f"f{n}" for n in range(1, 21)}


def normalize(sequence: str) -> str:
    """Converte um atalho escrito com simbolos de volta para a notacao do app.

    ``"⌃⌥2"`` vira ``"Ctrl+Alt+2"``. Quem ja esta na notacao passa intacto.
    """
    texto = str(sequence or "").strip()
    if not texto or not any(simbolo in texto for simbolo in _SIMBOLOS):
        return texto

    partes: list[str] = []
    resto = ""
    for char in texto:
        if char in _SIMBOLOS:
            partes.append(_SIMBOLOS[char].capitalize())
        elif char != "+":
            resto += char
    resto = resto.strip()
    if not resto:
        return texto
    return "+".join(partes + [resto])


def parse(sequence: str) -> tuple[int, int]:
    """Traduz ``"Ctrl+Alt+M"`` em ``(keycode, mascara de modificadores)``.

    Levanta ``ValueError`` quando a combinacao nao e representavel -- e o que o
    ``validate()`` usa para recusar antes de tentar registrar.
    """
    partes = [p.strip().lower() for p in normalize(sequence).split("+") if p.strip()]
    if not partes:
        raise ValueError("Atalho vazio")

    mascara = 0
    tecla: Optional[str] = None
    for parte in partes:
        if parte in _MODIFIERS:
            mascara |= _MODIFIERS[parte]
        elif tecla is None:
            tecla = parte
        else:
            raise ValueError(f"Atalho com mais de uma tecla: {sequence}")

    if tecla is None:
        raise ValueError(f"Atalho sem tecla principal: {sequence}")
    if tecla not in _KEYCODES:
        raise ValueError(f"Tecla nao suportada no macOS: {tecla}")
    if not mascara and tecla not in _SOZINHAS_OK:
        # Uma letra sozinha seria capturada no sistema inteiro e quebraria a
        # digitacao. As teclas de funcao sao dedicadas, entao passam -- e o
        # Windows sempre aceitou "F2" solto, entao recusar aqui seria criar uma
        # diferenca entre os dois sistemas.
        raise ValueError(
            "Atalho global precisa de um modificador (ou uma tecla de funcao)"
        )

    return _KEYCODES[tecla], mascara


def validate(sequence: str) -> None:
    parse(sequence)


def _ao_disparar(_call_ref, event, _user_data) -> int:
    """Chamado pelo macOS NA THREAD PRINCIPAL quando um atalho e apertado."""
    if _carbon is None:
        return 0
    hk = _EventHotKeyID()
    tamanho = ctypes.c_uint32()
    status = _carbon.GetEventParameter(
        event, _kEventParamDirectObject, _typeEventHotKeyID,
        None, ctypes.sizeof(hk), ctypes.byref(tamanho), ctypes.byref(hk),
    )
    if status != 0:
        return 0
    callback = _callbacks.get(int(hk.id))
    if callback is not None:
        try:
            callback()
        except Exception:
            # Nunca deixar uma excecao subir para o Carbon.
            pass
    return 0


def _garantir_handler() -> None:
    global _handler_proc, _handler_ref
    if _handler_ref is not None or _carbon is None:
        return
    _handler_proc = _HANDLER_PROC(_ao_disparar)
    spec = _EventTypeSpec(_kEventClassKeyboard, _kEventHotKeyPressed)
    ref = ctypes.c_void_p()
    status = _carbon.InstallEventHandler(
        _carbon.GetApplicationEventTarget(), _handler_proc, 1,
        ctypes.byref(spec), None, ctypes.byref(ref),
    )
    if status != 0:
        _handler_proc = None
        raise RuntimeError(f"Nao foi possivel instalar o handler de atalhos ({status})")
    _handler_ref = ref


def register(sequence: str, callback: Callable[[], None]) -> Any:
    """Registra um atalho global e devolve um handle opaco."""
    if _carbon is None:
        raise RuntimeError("Carbon nao esta disponivel")

    keycode, mascara = parse(sequence)
    _garantir_handler()

    hotkey_id = next(_ids)
    ref = ctypes.c_void_p()
    status = _carbon.RegisterEventHotKey(
        keycode, mascara, _EventHotKeyID(_SIGNATURE, hotkey_id),
        _carbon.GetApplicationEventTarget(), 0, ctypes.byref(ref),
    )
    if status != 0:
        if status == _eventHotKeyExistsErr:
            raise RuntimeError("Este atalho ja esta em uso por outro aplicativo")
        raise RuntimeError(f"O sistema recusou o atalho ({status})")

    _callbacks[hotkey_id] = callback
    _refs[hotkey_id] = ref
    return hotkey_id


def unregister(handle: Any) -> None:
    """Remove um atalho. Tolerante a handles invalidos."""
    if handle is None or _carbon is None:
        return
    hotkey_id = int(handle)
    ref = _refs.pop(hotkey_id, None)
    _callbacks.pop(hotkey_id, None)
    if ref is not None:
        try:
            _carbon.UnregisterEventHotKey(ref)
        except Exception:
            pass
