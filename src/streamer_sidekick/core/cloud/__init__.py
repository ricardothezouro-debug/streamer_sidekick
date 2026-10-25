"""Modo nuvem (GLOSSARY.md): conta, sessão e, nos próximos tickets, sincronização.

Python puro, sem Qt: quem roda isto em segundo plano e mostra na tela é a
interface (fase 2). Decisões em docs/adr/0001 a 0005.
"""
from streamer_sidekick.core.cloud.account import (
    CONECTADA,
    DESATIVADA,
    INDISPONIVEL,
    PRECISA_ENTRAR,
    Conta,
    ErroDeLogin,
    Nuvem,
)

__all__ = ["CONECTADA", "DESATIVADA", "INDISPONIVEL", "PRECISA_ENTRAR", "Conta", "ErroDeLogin", "Nuvem"]
