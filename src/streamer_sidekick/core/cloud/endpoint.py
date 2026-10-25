"""Onde fica o projeto do modo nuvem.

A anon key é pública por desenho: viaja em toda requisição e não dá acesso a
nada sozinha. Quem protege os dados é o RLS do banco (supabase/schema.sql).
Testes e scripts trocam pelas variáveis SSK_SUPABASE_URL e SSK_SUPABASE_ANON_KEY.
"""
from __future__ import annotations

import os

SUPABASE_URL = "https://flhzgxtaknatctdlnvvg.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZsaHpneHRha25hdGN0ZGxudnZnIiwicm9s"
    "ZSI6ImFub24iLCJpYXQiOjE3ODk5MjY2NzQsImV4cCI6MjEwNTUwMjY3NH0.__vHBYdyEQKJPMcTOa9KW1a2JoTaMXHbMBptSkWnuVI"
)


def url() -> str:
    return (os.environ.get("SSK_SUPABASE_URL") or SUPABASE_URL).rstrip("/")


def anon_key() -> str:
    return os.environ.get("SSK_SUPABASE_ANON_KEY") or SUPABASE_ANON_KEY
