#!/usr/bin/env python3
"""Conecta a loja Shopee via OAuth (sandbox por padrao) e salva o token.

Fluxo:
1. Le as credenciais do .env (Partner ID/Key, redirect).
2. Sobe um servidor local no caminho /shopee/callback (porta 8765).
3. Mostra a URL de autorizacao; voce entra com a loja de teste e autoriza.
4. Recebe o code, troca por access_token/refresh_token e salva em
   dados/shopee_tokens.json (permissao 600).
5. Chama shop/get_shop_info para confirmar que o token funciona.

Uso:
    python3 scripts/conectar_shopee.py              # sobe o callback e espera
    python3 scripts/conectar_shopee.py --somente-link
    python3 scripts/conectar_shopee.py --porta 8765 --timeout 300
"""

from __future__ import annotations

import argparse
import html
import json
import os
import secrets
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from mktagent.api import shopee  # noqa: E402
from mktagent.config import Config  # noqa: E402

ESTADO: dict[str, object] = {"codigo": None, "shop_id": None, "erro": None, "recebido": False}


def _salvar_token(config: Config, shop_id: str, dados: dict) -> Path:
    caminho = config.dados / "shopee_tokens.json"
    existentes: dict = {}
    if caminho.exists():
        try:
            existentes = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existentes = {}
    expire_in = int(dados.get("expire_in") or 0)
    existentes[str(shop_id)] = {
        "shop_id": str(shop_id),
        "ambiente": config.shopee.ambiente,
        "access_token": dados.get("access_token"),
        "refresh_token": dados.get("refresh_token"),
        "obtido_em": int(time.time()),
        "expira_em": int(time.time()) + expire_in if expire_in else None,
        "expire_in": expire_in,
    }
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(existentes, indent=2), encoding="utf-8")
    os.chmod(caminho, 0o600)
    return caminho


class Handler(BaseHTTPRequestHandler):
    def _responder(self, titulo: str, mensagem: str, status: int = 200) -> None:
        corpo = (
            "<!doctype html><html lang='pt-BR'><meta charset='utf-8'>"
            "<title>Shopee</title><body style='font-family:system-ui;padding:40px;"
            "max-width:640px;margin:auto'><h1>" + html.escape(titulo) + "</h1>"
            "<p>" + html.escape(mensagem) + "</p></body></html>"
        )
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(corpo.encode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        partes = urllib.parse.urlparse(self.path)
        if partes.path.rstrip("/") not in ("/shopee/callback", "/callback", ""):
            self._responder("Shopee", "Caminho nao encontrado.", 404)
            return
        query = urllib.parse.parse_qs(partes.query)
        codigo = (query.get("code") or [None])[0]
        shop_id = (query.get("shop_id") or [None])[0]
        estado = (query.get("state") or [None])[0]
        if not codigo:
            # Sondagens de saude/validacao de dominio nao devem derrubar o servidor.
            # So encerra se a Shopee devolver um erro explicito de autorizacao.
            if query.get("error") or query.get("error_description"):
                ESTADO["erro"] = "autorizacao recusada: " + str(
                    query.get("error") or query.get("error_description")
                )
                ESTADO["recebido"] = True
                self._responder("Autorizacao recusada", "A Shopee devolveu um erro.")
            else:
                self._responder(
                    "Aguardando autorizacao",
                    "Callback sem code; o conector continua esperando a autorizacao.",
                    400,
                )
            return
        if ESTADO.get("state") and estado and estado != ESTADO["state"]:
            ESTADO["erro"] = "state invalido"
            ESTADO["recebido"] = True
            self._responder("Falha de seguranca", "O state do callback nao confere.", 400)
            return
        ESTADO["codigo"] = codigo
        ESTADO["shop_id"] = shop_id
        ESTADO["recebido"] = True
        self._responder(
            "Autorizacao recebida",
            "Pode voltar para o terminal: estou trocando o code pelo token.",
        )

    def log_message(self, formato: str, *args) -> None:  # silencia log HTTP
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Conecta a Shopee via OAuth")
    parser.add_argument("--porta", type=int, default=8765)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--somente-link", action="store_true")
    parser.add_argument("--nao-abrir", action="store_true")
    args = parser.parse_args()

    config = Config.carregar()
    s = config.shopee
    if not s.configurada:
        print("Configure SHOPEE_PARTNER_ID e SHOPEE_PARTNER_KEY no .env.")
        return 1
    if not s.redirect_url:
        print("Configure SHOPEE_REDIRECT_URL no .env.")
        return 1

    estado = secrets.token_urlsafe(16)
    ESTADO["state"] = estado
    link = shopee.link_autorizacao(config, state=estado)
    print("== Shopee OAuth ==")
    print("ambiente:", s.ambiente, "| redirect:", s.redirect_url)
    print("\nAbra esta URL e autorize com a loja de teste:\n")
    print(link)
    print("\nO Console precisa ter o dominio do redirect igual ao do .env (sem porta).")
    if args.somente_link:
        return 0

    servidor = ThreadingHTTPServer(("127.0.0.1", args.porta), Handler)
    servidor.timeout = 1
    print(f"\nAguardando callback em http://127.0.0.1:{args.porta}/shopee/callback ...")
    if not args.nao_abrir:
        try:
            import webbrowser

            webbrowser.open(link)
        except Exception:
            pass

    limite = time.time() + args.timeout
    try:
        while not ESTADO["recebido"] and time.time() < limite:
            servidor.handle_request()
    finally:
        servidor.server_close()

    if not ESTADO["recebido"]:
        print("Timeout: nenhum callback recebido.")
        return 1
    if ESTADO["erro"]:
        print("Falha:", ESTADO["erro"])
        return 1
    codigo = str(ESTADO["codigo"])
    shop_id = ESTADO["shop_id"]
    if not shop_id:
        print("Callback sem shop_id. Use a autorizacao de seller (shop), nao main account.")
        return 1

    print("\nCode recebido; trocando por token...")
    try:
        token = shopee.trocar_code(config, codigo, shop_id)
    except Exception as erro:  # noqa: BLE001
        print("Erro ao trocar code:", str(erro)[:800])
        return 1
    caminho = _salvar_token(config, str(shop_id), token)
    print("Token salvo em", caminho, "(permissao 600)")
    print("access_token:", (str(token.get("access_token") or "")[:8] + "...") or "(vazio)")
    print("expire_in:", token.get("expire_in"))

    try:
        info = shopee.requisicao(
            config,
            "GET",
            "/api/v2/shop/get_shop_info",
            access_token=token.get("access_token"),
            shop_id=shop_id,
            timeout=25,
        )
        print("\nLoja conectada:")
        print(json.dumps(info, ensure_ascii=False)[:1200])
    except Exception as erro:  # noqa: BLE001
        print("\nToken salvo, mas get_shop_info falhou:", str(erro)[:800])
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
