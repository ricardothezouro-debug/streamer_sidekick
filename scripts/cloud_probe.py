"""Prova do modo nuvem: login pelo Google e cada endpoint que o app vai usar.

Roda ANTES de existir qualquer codigo de nuvem no app. Se passar aqui, no
Windows e no macOS, a fase de interface pode comecar. Se falhar, o erro diz em
qual passo e o que conferir no painel do Supabase.

Nao grava sessao em lugar nenhum. So imprime.

    PYTHONPATH=src python scripts/cloud_probe.py

Onde ele le a URL do projeto e a anon key (a primeira que existir):
  1. variaveis de ambiente SSK_SUPABASE_URL e SSK_SUPABASE_ANON_KEY
  2. o arquivo <dados do app>/cloud/endpoint.json:
        {"url": "https://xxxx.supabase.co", "anon_key": "eyJ..."}
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import socket
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from streamer_sidekick.core import net  # noqa: E402
from streamer_sidekick.core.paths import app_data_dir  # noqa: E402

#: As portas que ficam na allow-list do Supabase. Mudou aqui, muda la.
PORTAS = (53682, 53683, 53684)
HOST = "127.0.0.1"  # nunca "localhost": o navegador pode resolver para ::1


# ------------------------------------------------------------- endpoint --
def endpoint() -> tuple[str, str]:
    url = os.environ.get("SSK_SUPABASE_URL", "").strip()
    chave = os.environ.get("SSK_SUPABASE_ANON_KEY", "").strip()
    if url and chave:
        return url.rstrip("/"), chave
    arquivo = app_data_dir() / "cloud" / "endpoint.json"
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        return str(dados["url"]).rstrip("/"), str(dados["anon_key"])
    except (OSError, KeyError, json.JSONDecodeError):
        raise SystemExit(
            "Falta a URL e a anon key do projeto.\n"
            f"Crie {arquivo} com {{\"url\": ..., \"anon_key\": ...}}\n"
            "ou exporte SSK_SUPABASE_URL e SSK_SUPABASE_ANON_KEY."
        )


# ------------------------------------------------------------------ http --
def chamar(metodo: str, url: str, chave: str, token: str = "",
           corpo: dict | None = None, extra: dict | None = None):
    cabecalhos = {"apikey": chave, "Content-Type": "application/json"}
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    if extra:
        cabecalhos.update(extra)
    dados = json.dumps(corpo).encode() if corpo is not None else None
    pedido = urllib.request.Request(url, data=dados, method=metodo, headers=cabecalhos)
    try:
        with net.urlopen(pedido, timeout=30) as r:
            texto = r.read().decode("utf-8")
            return r.status, (json.loads(texto) if texto else None)
    except urllib.error.HTTPError as e:
        texto = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(texto)
        except json.JSONDecodeError:
            return e.code, texto[:300]


# ------------------------------------------------------------------ pkce --
def pkce() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


class _Callback(http.server.BaseHTTPRequestHandler):
    codigo: str = ""
    erro: str = ""

    def do_GET(self):  # noqa: N802
        if not self.path.startswith("/callback"):
            self.send_response(404); self.end_headers(); return  # favicon etc.
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _Callback.codigo = q.get("code", [""])[0]
        _Callback.erro = q.get("error_description", q.get("error", [""]))[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            "<html><body style='background:#0A0B12;color:#F3F6FF;font-family:sans-serif;"
            "display:flex;align-items:center;justify-content:center;height:100vh'>"
            "<h2>Pode fechar esta aba e voltar ao Streamer Sidekick.</h2></body></html>"
            .encode("utf-8")
        )

    def log_message(self, *a):  # silencio
        pass


def escutar() -> tuple[http.server.HTTPServer, int]:
    for porta in PORTAS:
        try:
            servidor = http.server.HTTPServer((HOST, porta), _Callback)
            return servidor, porta
        except OSError:
            continue
    raise SystemExit(f"Nenhuma das portas {PORTAS} esta livre em {HOST}.")


# ------------------------------------------------------------------ main --
def main() -> int:
    url, chave = endpoint()
    print(f"projeto     : {url}")
    print(f"plataforma  : {sys.platform}")
    ok = True

    def passo(nome: str, deu: bool, detalhe: str = "") -> None:
        nonlocal ok
        ok = ok and deu
        print(f"  [{'ok' if deu else 'FALHOU'}] {nome}" + (f"  {detalhe}" if detalhe else ""))

    # 1. login
    verifier, challenge = pkce()
    servidor, porta = escutar()
    redirect = f"http://{HOST}:{porta}/callback"
    autorizar = f"{url}/auth/v1/authorize?" + urllib.parse.urlencode({
        "provider": "google",
        "redirect_to": redirect,
        "code_challenge": challenge,
        "code_challenge_method": "s256",
    })
    print(f"\n1. Abrindo o navegador para o login (escutando em {redirect})...")
    webbrowser.open(autorizar)
    servidor.timeout = 300
    while not _Callback.codigo and not _Callback.erro:
        servidor.handle_request()
    servidor.server_close()
    if _Callback.erro:
        passo("callback do login", False, _Callback.erro)
        print("\n  Confira: Redirect URLs no Supabase tem exatamente", redirect)
        return 1
    passo("callback do login", True, f"code recebido em {redirect}")

    # 2. trocar o code pela sessao
    status, dados = chamar("POST", f"{url}/auth/v1/token?grant_type=pkce", chave,
                           corpo={"auth_code": _Callback.codigo, "code_verifier": verifier})
    if status != 200 or not isinstance(dados, dict) or "access_token" not in dados:
        passo("troca do code por sessao", False, f"HTTP {status}: {dados}")
        return 1
    token = dados["access_token"]; refresh = dados.get("refresh_token", "")
    passo("troca do code por sessao", True, f"expira em {dados.get('expires_in')}s")

    # 3. quem sou eu
    status, dados = chamar("GET", f"{url}/auth/v1/user", chave, token)
    email = dados.get("email") if isinstance(dados, dict) else None
    passo("GET /auth/v1/user", status == 200 and bool(email), f"{email}")

    # 4. perfil (criado pelo gatilho)
    status, dados = chamar("GET", f"{url}/rest/v1/profiles?select=id,email,is_admin,active,ads_enabled", chave, token)
    perfil = dados[0] if isinstance(dados, list) and dados else None
    passo("perfil criado pelo gatilho", perfil is not None,
          f"admin={perfil.get('is_admin')} ativo={perfil.get('active')} ads={perfil.get('ads_enabled')}" if perfil else f"HTTP {status}: {dados}")
    if not perfil:
        print("\n  Confira: o schema.sql rodou inteiro? O gatilho on_auth_user_created existe?")
        return 1
    uid = perfil["id"]

    # 5. o proprio usuario NAO consegue se promover
    status, dados = chamar("PATCH", f"{url}/rest/v1/profiles?id=eq.{uid}", chave, token,
                           corpo={"is_admin": True}, extra={"Prefer": "return=minimal"})
    passo("usuario nao consegue virar admin sozinho", status in (401, 403, 400), f"HTTP {status}")

    # 6. upsert de um arquivo
    conteudo = base64.b64encode("[2026-09-20 10:00:00] prova\n".encode()).decode()
    linha = {"user_id": uid, "path": "_probe/teste.txt", "content_b64": conteudo,
             "sha256": hashlib.sha256(conteudo.encode()).hexdigest(), "size": len(conteudo)}
    status, dados = chamar("POST", f"{url}/rest/v1/files?on_conflict=user_id,path", chave, token,
                           corpo=linha, extra={"Prefer": "resolution=merge-duplicates,return=representation"})
    passo("upsert em files", status in (200, 201), f"HTTP {status}" + ("" if status in (200, 201) else f": {dados}"))

    # 7. ler de volta (o indice, sem conteudo)
    status, dados = chamar("GET", f"{url}/rest/v1/files?select=path,sha256,size,updated_at,deleted&order=updated_at.desc&limit=5", chave, token)
    achou = isinstance(dados, list) and any(d.get("path") == "_probe/teste.txt" for d in dados)
    passo("ler o indice", achou, f"{len(dados) if isinstance(dados, list) else dados} linha(s)")

    # 8. limite por arquivo (3 MB deve ser recusado pelo check)
    grande = dict(linha, path="_probe/grande.bin", size=3 * 1024 * 1024)
    status, dados = chamar("POST", f"{url}/rest/v1/files", chave, token, corpo=grande, extra={"Prefer": "return=minimal"})
    passo("arquivo de 3 MB e recusado", status >= 400, f"HTTP {status}")

    # 9. apagar a prova
    status, dados = chamar("DELETE", f"{url}/rest/v1/files?path=like._probe/*", chave, token, extra={"Prefer": "return=minimal"})
    passo("apagar a prova", status in (200, 204), f"HTTP {status}")

    # 10. renovar a sessao
    status, dados = chamar("POST", f"{url}/auth/v1/token?grant_type=refresh_token", chave,
                           corpo={"refresh_token": refresh})
    novo = isinstance(dados, dict) and dados.get("refresh_token")
    passo("renovar a sessao", status == 200 and bool(novo),
          "refresh token novo (o antigo morreu: rotacao ligada)" if novo else f"HTTP {status}: {dados}")

    # 11. funcao de admin (deve recusar quem nao e admin, e listar para quem e)
    token2 = dados.get("access_token", token) if isinstance(dados, dict) else token
    status, dados = chamar("POST", f"{url}/rest/v1/rpc/admin_list_profiles", chave, token2, corpo={})
    if perfil.get("is_admin"):
        passo("admin_list_profiles (voce e admin)", status == 200, f"{len(dados) if isinstance(dados, list) else dados} perfil(is)")
    else:
        passo("admin_list_profiles recusa quem nao e admin", status in (401, 403, 400), f"HTTP {status}")

    print("\nRESULTADO:", "TUDO OK" if ok else "algo falhou; veja acima")
    print("Nada foi gravado neste computador.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
