"""Iniciar o Streamer Sidekick junto com o Windows.

Usa a chave ``HKCU\\...\\Run`` do registro (não precisa de admin). Só tem efeito
no app empacotado (portable) do Windows; em outros SOs / em desenvolvimento é
no-op, para não registrar o ``python.exe`` por engano.
"""
from __future__ import annotations

import sys
from pathlib import Path

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "StreamerSidekick"


def supported() -> bool:
    """True só no portable congelado do Windows (onde faz sentido registrar)."""
    return sys.platform == "win32" and bool(getattr(sys, "frozen", False))


def _exe_path() -> str:
    return str(Path(sys.executable).resolve())


def is_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, _VALUE_NAME)
            return bool(value)
    except (FileNotFoundError, OSError):
        return False


def set_enabled(enabled: bool) -> None:
    """Liga/desliga o início automático, apontando para o exe atual.

    Reescreve o caminho a cada chamada (o portable pode mudar de pasta). Só age
    no portable congelado do Windows.
    """
    if not supported():
        return
    import winreg

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            if enabled:
                winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, f'"{_exe_path()}"')
            else:
                try:
                    winreg.DeleteValue(key, _VALUE_NAME)
                except FileNotFoundError:
                    pass
    except OSError:
        pass
