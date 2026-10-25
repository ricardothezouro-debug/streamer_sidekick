"""Barramento de eventos do hub (GLOSSARY.md: Evento).

Uma parte do app, ou um plugin, publica um evento quando algo acontece; quem
quiser reagir assina pelo nome. Python puro, sem Qt.

    cancelar = events.subscribe("marker.saved", ao_marcar)
    events.publish("marker.saved", {"file": "dredge.txt", "text": "boss derrotado", "when": "2026-10-25T15:44:04"})
    cancelar()
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable

Listener = Callable[[dict[str, Any]], None]

_listeners: dict[str, list[Listener]] = {}
_lock = threading.Lock()  # a interface assina numa thread; os atalhos globais publicam de outra
_log = logging.getLogger(__name__)


def subscribe(name: str, listener: Listener) -> Callable[[], None]:
    """Assina o evento ``name``. Devolve a função que cancela a assinatura."""
    with _lock:
        _listeners.setdefault(name, []).append(listener)

    def cancel() -> None:
        with _lock:
            current = _listeners.get(name, [])
            if listener in current:  # cancelar de novo não faz nada
                current.remove(listener)

    return cancel


def publish(name: str, data: dict[str, Any]) -> None:
    """Entrega ``data`` a quem assinou ``name``, na ordem das assinaturas."""
    with _lock:
        listeners = list(_listeners.get(name, []))
    for listener in listeners:
        try:
            listener(data)
        except Exception:  # um plugin com defeito não derruba quem publicou nem os outros ouvintes
            _log.exception("Ouvinte do evento %s falhou", name)
