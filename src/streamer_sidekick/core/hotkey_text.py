"""Conversao entre o ``QKeySequence`` do Qt e a notacao de atalho do app.

Existe por causa de uma troca que o Qt faz no macOS: la o ``Qt.ControlModifier``
representa a tecla **Command** e o ``Qt.MetaModifier`` representa a tecla
**Control** -- o inverso do nome. Isso e proposital no Qt (deixa um ``Ctrl+C``
escrito uma vez virar ``Cmd+C`` no Mac), mas atalho global nao e atalho de menu:
aqui a gente precisa da tecla FISICA que o usuario apertou.

Sem tratar isso, tres coisas quebravam no macOS:

* ``Ctrl+Alt+M`` aparecia na tela como ``⌥⌘M`` (Option+Command) e disparava com
  Control+Option -- o que a tela dizia nao era o que funcionava;
* gravar um atalho salvava ``toString(NativeText)``, ou seja a string ``"⌥⌘M"``
  com os simbolos dentro, que nenhum backend consegue interpretar. Trocar
  qualquer atalho no Mac o quebrava para sempre;
* por consequencia, o que era gravado nunca coincidia com o que disparava.

A notacao do app e sempre a mesma nos tres sistemas -- ``Ctrl``, ``Alt``,
``Shift``, ``Cmd`` -- e sempre significa a tecla fisica de mesmo nome.
"""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence

_ON_MACOS = sys.platform == "darwin"

# Como cada modificador aparece para o usuario.
_SIMBOLOS_MACOS = {"ctrl": "⌃", "alt": "⌥", "shift": "⇧", "cmd": "⌘"}
_NOMES = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "cmd": "Cmd"}

# Ordem canonica, para o mesmo atalho nunca ser escrito de duas formas.
_ORDEM = ("ctrl", "alt", "shift", "cmd")


def from_key_sequence(sequence: QKeySequence) -> str:
    """Le o que o usuario apertou e devolve a notacao do app.

    Desfaz a troca do Qt no macOS, para que a tecla gravada seja a que ele
    realmente pressionou.
    """
    if sequence.isEmpty():
        return ""

    combo = sequence[0]
    tecla = combo.key()
    mods = combo.keyboardModifiers()

    presentes: list[str] = []
    if _ON_MACOS:
        # No Mac o Qt inverte: ControlModifier == tecla Command,
        # MetaModifier == tecla Control.
        if mods & Qt.KeyboardModifier.MetaModifier:
            presentes.append("ctrl")
        if mods & Qt.KeyboardModifier.ControlModifier:
            presentes.append("cmd")
    else:
        if mods & Qt.KeyboardModifier.ControlModifier:
            presentes.append("ctrl")
        if mods & Qt.KeyboardModifier.MetaModifier:
            presentes.append("cmd")
    if mods & Qt.KeyboardModifier.AltModifier:
        presentes.append("alt")
    if mods & Qt.KeyboardModifier.ShiftModifier:
        presentes.append("shift")

    nome_tecla = QKeySequence(tecla).toString(QKeySequence.SequenceFormat.PortableText)
    if not nome_tecla:
        return ""

    ordenados = [m for m in _ORDEM if m in presentes]
    return "+".join([_NOMES[m] for m in ordenados] + [nome_tecla])


def to_key_sequence(texto: str) -> QKeySequence:
    """Notacao do app -> ``QKeySequence``, para preencher o campo da tela.

    No macOS troca de volta, senao o Qt entenderia o nosso ``Ctrl`` como Command.
    """
    if not texto:
        return QKeySequence()

    partes = [p.strip() for p in str(texto).split("+") if p.strip()]
    if not partes:
        return QKeySequence()

    tecla = partes[-1]
    mods = {p.lower() for p in partes[:-1]}

    traduzidos: list[str] = []
    for mod in mods:
        if mod in ("ctrl", "control"):
            traduzidos.append("Meta" if _ON_MACOS else "Ctrl")
        elif mod in ("cmd", "command", "meta", "super", "win"):
            traduzidos.append("Ctrl" if _ON_MACOS else "Meta")
        elif mod in ("alt", "option", "opt"):
            traduzidos.append("Alt")
        elif mod == "shift":
            traduzidos.append("Shift")

    return QKeySequence("+".join(traduzidos + [tecla]))


def to_display(texto: str) -> str:
    """Como mostrar o atalho para o usuario.

    No macOS usa os simbolos das teclas fisicas certas (``⌃⌥M``), e nao o que o
    Qt renderizaria por conta propria.
    """
    if not texto:
        return ""
    partes = [p.strip() for p in str(texto).split("+") if p.strip()]
    if not partes:
        return ""

    tecla = partes[-1]
    mods = {p.lower() for p in partes[:-1]}
    normalizados: list[str] = []
    for mod in mods:
        if mod in ("ctrl", "control"):
            normalizados.append("ctrl")
        elif mod in ("cmd", "command", "meta", "super", "win"):
            normalizados.append("cmd")
        elif mod in ("alt", "option", "opt"):
            normalizados.append("alt")
        elif mod == "shift":
            normalizados.append("shift")

    ordenados = [m for m in _ORDEM if m in normalizados]
    if _ON_MACOS:
        return "".join(_SIMBOLOS_MACOS[m] for m in ordenados) + tecla.upper()
    return "+".join([_NOMES[m] for m in ordenados] + [tecla])
