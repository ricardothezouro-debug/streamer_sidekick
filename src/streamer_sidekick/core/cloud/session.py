"""Sessão do modo nuvem neste PC (GLOSSARY.md: Sessão; docs/adr/0002).

Só o refresh token, num arquivo gravado de forma atômica e com permissão só do
usuário. O token gira a cada uso: cada renovação grava o novo.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


class SessionStore:
    def __init__(self, pasta: Path) -> None:
        self._arquivo = Path(pasta) / "session.json"

    def load(self) -> Optional[str]:
        try:
            token = json.loads(self._arquivo.read_text(encoding="utf-8")).get("refresh_token")
        except (OSError, ValueError, AttributeError):
            return None
        return token or None

    def save(self, refresh_token: str) -> None:
        self._arquivo.parent.mkdir(parents=True, exist_ok=True)
        temporario = self._arquivo.with_name(self._arquivo.name + ".tmp")
        temporario.write_text(json.dumps({"refresh_token": refresh_token}), encoding="utf-8")
        try:
            os.chmod(temporario, 0o600)  # no Windows não faz nada; o arquivo já está no perfil do usuário
        except OSError:
            pass
        os.replace(temporario, self._arquivo)  # se faltar energia no meio, o arquivo bom continua lá

    def clear(self) -> None:
        self._arquivo.unlink(missing_ok=True)
