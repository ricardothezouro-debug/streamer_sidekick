"""Login pelo navegador: abre a página do Google e espera a volta em 127.0.0.1.

É o ``receber_codigo`` de verdade de ``Nuvem.entrar``. Não tem teste
automático (abre porta e navegador); é conferido à mão pelo
``scripts/cloud_sync.py entrar``. A mesma lógica passou na prova real
(``scripts/cloud_probe.py``) no Windows e no macOS.
"""
from __future__ import annotations

import http.server
import time
import urllib.parse
import webbrowser
from typing import Callable

from streamer_sidekick.core.cloud.account import ErroDeLogin

#: As portas que estão na lista de retorno permitido do Supabase. Mudou aqui, muda lá.
PORTAS = (53682, 53683, 53684)
HOST = "127.0.0.1"  # nunca "localhost": o navegador pode resolver para ::1

# Página que o navegador mostra na volta. As cores são os tokens "canvas" e "ink"
# do Sidekick OS escritos à mão: ui/tokens.py importa o Qt, e o motor da nuvem
# não pode depender dele (docs/adr e decisão da fase 1).
_PAGINA = (
    "<html><head><meta charset='utf-8'><title>Streamer Sidekick</title></head>"
    "<body style='background:#120A24;color:#F4F0FF;font-family:sans-serif;"
    "display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
    "<h2>{}</h2></body></html>"
)


def receber_pelo_navegador(montar_url: Callable[[str], str], prazo: float = 300.0) -> str:
    """Abre o login no navegador e devolve o código que voltou para o app."""
    resultado: dict[str, str] = {}

    class Retorno(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (nome exigido pelo http.server)
            partes = urllib.parse.urlparse(self.path)
            if partes.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            query = urllib.parse.parse_qs(partes.query)
            resultado["codigo"] = query.get("code", [""])[0]
            resultado["erro"] = query.get("error_description", query.get("error", [""]))[0]
            texto = ("Pronto, pode fechar esta aba e voltar ao Streamer Sidekick."
                     if resultado["codigo"] else "O login não terminou. Volte ao Streamer Sidekick e tente de novo.")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(_PAGINA.format(texto).encode("utf-8"))

        def log_message(self, *_args):  # sem barulho no terminal
            pass

    servidor = _escutar(Retorno)
    try:
        retorno = f"http://{HOST}:{servidor.server_address[1]}/callback"
        webbrowser.open(montar_url(retorno))
        limite = time.monotonic() + prazo
        servidor.timeout = 1.0
        while not resultado and time.monotonic() < limite:
            servidor.handle_request()
    finally:
        servidor.server_close()
    if not resultado:
        raise ErroDeLogin("o login não voltou a tempo; tente de novo")
    if not resultado.get("codigo"):
        raise ErroDeLogin(resultado.get("erro") or "o login foi cancelado")
    return resultado["codigo"]


def _escutar(tratador: type) -> http.server.HTTPServer:
    for porta in PORTAS:
        try:
            return http.server.HTTPServer((HOST, porta), tratador)
        except OSError:
            continue
    raise ErroDeLogin(f"as portas {', '.join(map(str, PORTAS))} estão ocupadas; feche o outro app que usa elas")
