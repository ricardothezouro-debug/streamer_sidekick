"""A conta do modo nuvem neste PC: entrar, ver quem está logado, sair."""
from __future__ import annotations

import base64
import hashlib
import secrets
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from streamer_sidekick.core.cloud import endpoint, transport
from streamer_sidekick.core.cloud.session import SessionStore

CONECTADA = "conectada"
PRECISA_ENTRAR = "precisa_entrar"
DESATIVADA = "desativada"
INDISPONIVEL = "indisponivel"

#: Recebe a função que monta a URL de login (dado o endereço de retorno) e
#: devolve o código que o Supabase mandou de volta. O de verdade abre o
#: navegador e escuta em 127.0.0.1 (core/cloud/login.py); nos testes é o falso.
ReceberCodigo = Callable[[Callable[[str], str]], str]


@dataclass(frozen=True)
class Conta:
    estado: str
    email: str = ""
    admin: bool = False
    motivo: str = ""


class ErroDeLogin(Exception):
    """O login não terminou: código recusado, janela fechada, tempo esgotado."""


class _Indisponivel(Exception):
    """Sem rede, projeto pausado ou tempo esgotado: nada muda, tenta de novo depois."""


class Nuvem:
    def __init__(self, dados: Path, transporte: Optional[Callable[..., Any]] = None,
                 url: Optional[str] = None, chave: Optional[str] = None, timeout: float = 10.0) -> None:
        self._sessao = SessionStore(Path(dados) / "cloud")
        self._transporte = transporte or transport.http
        self._url = (url or endpoint.url()).rstrip("/")
        self._chave = chave or endpoint.anon_key()
        self._timeout = timeout

    # ------------------------------------------------------------ público
    def entrar(self, receber_codigo: ReceberCodigo) -> Conta:
        verificador = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
        desafio = base64.urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest()).rstrip(b"=").decode()

        def montar_url(retorno: str) -> str:
            return f"{self._url}/auth/v1/authorize?" + urllib.parse.urlencode({
                "provider": "google",
                "redirect_to": retorno,
                "code_challenge": desafio,
                "code_challenge_method": "s256",
            })

        codigo = receber_codigo(montar_url)
        try:
            status, dados = self._chamar("POST", "/auth/v1/token?grant_type=pkce",
                                         corpo={"auth_code": codigo, "code_verifier": verificador})
            if status != 200 or not isinstance(dados, dict) or "refresh_token" not in dados:
                raise ErroDeLogin(_motivo(dados) or f"HTTP {status}")
            self._sessao.save(dados["refresh_token"])
            return self._perfil(dados["access_token"])
        except _Indisponivel as erro:
            raise ErroDeLogin(f"nuvem indisponível: {erro}") from erro

    def conta(self) -> Conta:
        refresh = self._sessao.load()
        if refresh is None:
            return Conta(PRECISA_ENTRAR)
        try:
            return self._renovar(refresh)
        except _Indisponivel as erro:
            return Conta(INDISPONIVEL, motivo=str(erro))

    def sair(self) -> None:
        """Encerra a sessão: no servidor, quando dá; neste PC, sempre."""
        refresh = self._sessao.load()
        try:
            if refresh:
                status, dados = self._chamar("POST", "/auth/v1/token?grant_type=refresh_token",
                                             corpo={"refresh_token": refresh})
                if status == 200 and isinstance(dados, dict) and dados.get("access_token"):
                    self._chamar("POST", "/auth/v1/logout", acesso=dados["access_token"])
        except _Indisponivel:
            pass  # sem rede: a sessão expira sozinha no servidor
        finally:
            self._sessao.clear()

    # ------------------------------------------------------------ interno
    def _renovar(self, refresh: str) -> Conta:
        status, dados = self._chamar("POST", "/auth/v1/token?grant_type=refresh_token",
                                     corpo={"refresh_token": refresh})
        if status in (400, 401):  # token revogado, expirado ou reusado: não volta a valer
            self._sessao.clear()
            return Conta(PRECISA_ENTRAR, motivo=_motivo(dados))
        if status != 200 or not isinstance(dados, dict) or "refresh_token" not in dados:
            return Conta(INDISPONIVEL, motivo=_motivo(dados) or f"HTTP {status}")
        self._sessao.save(dados["refresh_token"])  # rotação: o token usado já morreu
        return self._perfil(dados["access_token"])

    def _perfil(self, acesso: str) -> Conta:
        status, usuario = self._chamar("GET", "/auth/v1/user", acesso=acesso)
        if status != 200 or not isinstance(usuario, dict):
            return Conta(PRECISA_ENTRAR, motivo=_motivo(usuario))
        filtro = urllib.parse.urlencode({"id": f"eq.{usuario['id']}", "select": "email,is_admin,active"})
        status, perfis = self._chamar("GET", f"/rest/v1/profiles?{filtro}", acesso=acesso)
        perfil = perfis[0] if status == 200 and isinstance(perfis, list) and perfis else None
        if perfil is None:
            return Conta(PRECISA_ENTRAR, motivo="perfil não encontrado")
        if perfil.get("active") is False:
            # Desativada pelo admin: a nuvem desliga neste PC. Só a sessão sai;
            # marcações, presets e progresso ficam como estão.
            self._sessao.clear()
            return Conta(DESATIVADA, email=perfil.get("email", ""))
        return Conta(CONECTADA, email=perfil.get("email") or usuario.get("email", ""),
                     admin=bool(perfil.get("is_admin")))

    def _chamar(self, metodo: str, caminho: str, acesso: str = "", corpo: Any = None) -> tuple[int, Any]:
        cabecalhos = {"apikey": self._chave}
        if acesso:
            cabecalhos["Authorization"] = f"Bearer {acesso}"
        try:
            return self._transporte(metodo, self._url + caminho, cabecalhos, corpo, self._timeout)
        except OSError as erro:  # sem rede, DNS, recusa, tempo esgotado (TimeoutError é OSError)
            raise _Indisponivel(str(erro) or type(erro).__name__) from erro


def _motivo(dados: Any) -> str:
    if isinstance(dados, dict):
        return str(dados.get("error_description") or dados.get("msg") or dados.get("message") or "")
    return ""
