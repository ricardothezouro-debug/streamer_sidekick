"""Supabase falso, em memória, para os testes do modo nuvem.

Substitui a função de transporte do cliente: nada de socket. Imita o que a
prova real (scripts/cloud_probe.py) mostrou no projeto de verdade:

- login por PKCE: o código do Google só troca pela sessão com o verificador certo;
- renovação com rotação: o refresh token usado morre na hora;
- perfis com RLS: cada um só lê o próprio; ninguém se promove a admin (403).

Controles para os testes: ``criar_usuario``, ``desativar``, ``revogar``,
``fora_do_ar`` e ``lento``.
"""
from __future__ import annotations

import base64
import hashlib
import itertools
import secrets
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Optional


class Lento(TimeoutError):
    """O que o transporte de verdade levanta quando o tempo acaba."""


@dataclass
class Usuario:
    id: str
    email: str
    admin: bool = False
    ativo: bool = True
    refresh_tokens: set[str] = field(default_factory=set)


class SupabaseFalso:
    URL = "https://falso.supabase.co"
    ANON = "anon-falsa"

    def __init__(self) -> None:
        self.usuarios: dict[str, Usuario] = {}
        self._codigos: dict[str, tuple[str, str]] = {}  # código -> (desafio, id do usuário)
        self._acessos: dict[str, str] = {}               # access token -> id do usuário
        self._seq = itertools.count(1)
        self.fora_do_ar = False
        self.lento = False
        self.chamadas: list[tuple[str, str]] = []
        self.arquivos: dict[tuple[str, str], dict[str, Any]] = {}  # (user_id, path) -> linha de files
        self._relogio = itertools.count(1)
        self.ultimo_timeout: Optional[float] = None

    # ------------------------------------------------------------ controles
    def criar_usuario(self, email: str, admin: bool = False) -> Usuario:
        usuario = Usuario(id=f"u{next(self._seq)}", email=email, admin=admin)
        self.usuarios[usuario.id] = usuario
        return usuario

    def _por_email(self, email: str) -> Usuario:
        return next(u for u in self.usuarios.values() if u.email == email)

    def desativar(self, email: str) -> None:
        self._por_email(email).ativo = False

    def revogar(self, email: str) -> None:
        self._por_email(email).refresh_tokens.clear()

    def autorizar(self, url_de_login: str, email: str) -> str:
        """Faz o papel do Google + Supabase: a pessoa entrou, devolve o código."""
        partes = urllib.parse.urlparse(url_de_login)
        query = dict(urllib.parse.parse_qsl(partes.query))
        assert partes.path == "/auth/v1/authorize", partes.path
        assert query["provider"] == "google" and query["code_challenge_method"] == "s256"
        assert query["redirect_to"].startswith("http://127.0.0.1:")
        usuario = next((u for u in self.usuarios.values() if u.email == email), None) or self.criar_usuario(email)
        codigo = secrets.token_hex(8)
        self._codigos[codigo] = (query["code_challenge"], usuario.id)
        return codigo

    # ------------------------------------------------------------ transporte
    def __call__(self, metodo: str, url: str, cabecalhos: dict[str, str], corpo: Any = None,
                 timeout: float = 30.0) -> tuple[int, Any]:
        self.ultimo_timeout = timeout
        if self.fora_do_ar:
            raise ConnectionError("projeto pausado")
        if self.lento:
            raise Lento("tempo esgotado")
        if cabecalhos.get("apikey") != self.ANON:
            return 401, {"message": "Invalid API key"}
        partes = urllib.parse.urlparse(url)
        query = dict(urllib.parse.parse_qsl(partes.query))
        self.chamadas.append((metodo, partes.path))

        if metodo == "POST" and partes.path == "/auth/v1/token":
            return self._token(query.get("grant_type"), corpo or {})
        usuario = self._autenticado(cabecalhos)
        if partes.path == "/auth/v1/user" and metodo == "GET":
            return (200, {"id": usuario.id, "email": usuario.email}) if usuario else (401, {"msg": "sem sessão"})
        if partes.path == "/auth/v1/logout" and metodo == "POST":
            if usuario:
                usuario.refresh_tokens.clear()
            return 204, None
        if partes.path == "/rest/v1/profiles":
            return self._profiles(metodo, query, corpo, usuario)
        if partes.path == "/rest/v1/files":
            return self._files(metodo, query, corpo, usuario, cabecalhos.get("Prefer", ""))
        return 404, {"message": f"rota desconhecida {metodo} {partes.path}"}

    def _token(self, grant: Optional[str], corpo: dict[str, Any]) -> tuple[int, Any]:
        if grant == "pkce":
            codigo = self._codigos.pop(corpo.get("auth_code", ""), None)
            if codigo is None:
                return 400, {"error": "invalid_grant", "error_description": "código inválido"}
            desafio, uid = codigo
            if _desafio(corpo.get("code_verifier", "")) != desafio:
                return 400, {"error": "invalid_grant", "error_description": "verificador não confere"}
            return 200, self._emitir(self.usuarios[uid])
        if grant == "refresh_token":
            token = corpo.get("refresh_token", "")
            dono = next((u for u in self.usuarios.values() if token in u.refresh_tokens), None)
            if dono is None:
                return 400, {"error": "invalid_grant", "error_description": "Invalid Refresh Token"}
            dono.refresh_tokens.discard(token)  # rotação: o usado morre
            return 200, self._emitir(dono)
        return 400, {"error": "unsupported_grant_type"}

    def _emitir(self, usuario: Usuario) -> dict[str, Any]:
        acesso, refresh = secrets.token_hex(8), secrets.token_hex(8)
        self._acessos[acesso] = usuario.id
        usuario.refresh_tokens.add(refresh)
        return {"access_token": acesso, "refresh_token": refresh, "expires_in": 3600, "token_type": "bearer"}

    def _autenticado(self, cabecalhos: dict[str, str]) -> Optional[Usuario]:
        valor = cabecalhos.get("Authorization", "")
        if not valor.startswith("Bearer "):
            return None
        uid = self._acessos.get(valor.removeprefix("Bearer "))
        return self.usuarios.get(uid) if uid else None

    def _profiles(self, metodo: str, query: dict[str, str], corpo: Any,
                  usuario: Optional[Usuario]) -> tuple[int, Any]:
        if usuario is None:
            return 401, {"code": "42501", "message": "permission denied for table profiles"}
        if metodo == "GET":
            visiveis = [u for u in self.usuarios.values() if usuario.admin or u.id == usuario.id]
            alvo = query.get("id", "")
            if alvo.startswith("eq."):
                visiveis = [u for u in visiveis if u.id == alvo[3:]]
            return 200, [{"id": u.id, "email": u.email, "is_admin": u.admin, "active": u.ativo,
                          "ads_enabled": True} for u in visiveis]
        if metodo == "PATCH":
            if set(corpo or {}) - {"display_name", "last_seen_at"}:
                return 403, {"code": "42501", "message": "permission denied for table profiles"}
            return 204, None
        return 405, {"message": "método não permitido"}


    # ------------------------------------------------------------ files
    def arquivo(self, email: str, caminho: str) -> Optional[dict[str, Any]]:
        """Para os testes: a linha de ``files`` de alguém, como está no banco."""
        return self.arquivos.get((self._por_email(email).id, caminho))

    def _files(self, metodo: str, query: dict[str, str], corpo: Any,
               usuario: Optional[Usuario], prefer: str = "") -> tuple[int, Any]:
        if usuario is None:
            return 401, {"code": "42501", "message": "permission denied for table files"}
        if not usuario.ativo:  # RLS: user_id = auth.uid() and is_active()
            return (200, []) if metodo == "GET" else (403, {"code": "42501", "message": "conta desativada"})
        if metodo == "GET":
            linhas = [linha for (uid, _), linha in self.arquivos.items() if uid == usuario.id]
            filtro = query.get("path", "")
            if filtro.startswith("eq."):
                linhas = [linha for linha in linhas if linha["path"] == filtro[3:]]
            colunas = [c for c in query.get("select", "*").split(",") if c]
            return 200, [linha if colunas == ["*"] else {c: linha.get(c) for c in colunas} for linha in linhas]
        if metodo == "POST":
            if query.get("on_conflict") != "user_id,path":
                return 400, {"message": "o app sempre faz upsert por (user_id, path)"}
            for linha in corpo if isinstance(corpo, list) else [corpo]:
                # Como o PostgREST: sem "resolution=merge-duplicates" é INSERT puro,
                # e o mesmo caminho de novo dá erro de duplicado.
                if (usuario.id, linha.get("path")) in self.arquivos and "resolution=merge-duplicates" not in prefer:
                    return 409, {"code": "23505", "message": "duplicate key value violates unique constraint"}
                status, erro = self._gravar(usuario, linha)
                if status != 201:
                    return status, erro
            return 201, None
        return 405, {"message": "método não permitido"}

    def _gravar(self, usuario: Usuario, linha: dict[str, Any]) -> tuple[int, Any]:
        if linha.get("user_id") != usuario.id:
            return 403, {"code": "42501", "message": "new row violates row-level security policy"}
        caminho = linha["path"]
        for (uid, outro), _ in self.arquivos.items():
            if uid == usuario.id and outro != caminho and outro.lower() == caminho.lower():
                return 409, {"code": "23505", "message": "duplicate key value violates unique constraint"}
        self.arquivos[(usuario.id, caminho)] = {
            "path": caminho,
            "content_b64": linha.get("content_b64", ""),
            "sha256": linha.get("sha256", ""),
            "size": linha.get("size", 0),
            "deleted": bool(linha.get("deleted", False)),
            "updated_at": f"2026-10-25T12:00:{next(self._relogio):02d}+00:00",  # hora do servidor
        }
        return 201, None


def _desafio(verificador: str) -> str:
    resumo = hashlib.sha256(verificador.encode()).digest()
    return base64.urlsafe_b64encode(resumo).rstrip(b"=").decode()
