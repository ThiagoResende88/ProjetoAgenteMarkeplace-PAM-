"""Cliente do TikTok Shop Partner Center (Open API).

Fase 2: estrutura de auth/assinatura pronta, sincronizacao NAO validada em sandbox.
Documentacao oficial consultada em 2026-10-25 (ver docs/PESQUISA_APIS.md).
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from ..config import Config
from .assinatura import assinar_tiktok

DOMINIOS = {
    "row": {
        "autorizacao": "https://services.tiktokshop.com/open/authorize",
        "token": "https://auth.tiktok-shops.com",
        "api": "https://open-api.tiktokglobalshop.com",
    },
    "us": {
        "autorizacao": "https://services.us.tiktokshop.com/open/authorize",
        "token": "https://auth.tiktok-shops.com",
        "api": "https://open-api.tiktokglobalshop.com",
    },
}

ENDPOINTS = {
    "buscar_pedidos": "/order/202309/orders/search",
    "detalhe_pedidos": "/order/202507/orders",
    "statements": "/finance/202309/statements",
    "transacoes_pedido": "/finance/202501/orders/{order_id}/statement_transactions",
    "nao_liquidados": "/finance/202507/orders/unsettled",
}

MAX_IDS_DETALHE = 50
PAGE_SIZE_MAX = 100


def _dominios(config: Config) -> dict[str, str]:
    return DOMINIOS.get(config.tiktok.regiao or "row", DOMINIOS["row"])


def link_autorizacao(config: Config, state: str = "") -> str:
    if not config.tiktok.service_id:
        raise ValueError("TIKTOK_SERVICE_ID nao configurado no .env")
    parametros = {"service_id": config.tiktok.service_id, "state": state}
    parametros = {chave: valor for chave, valor in parametros.items() if valor}
    return _dominios(config)["autorizacao"] + "?" + urllib.parse.urlencode(parametros)


def _token(config: Config, caminho: str, parametros: dict[str, str]) -> dict:
    if not config.tiktok.configurada:
        raise ValueError(
            "TikTok Shop nao configurado: preencha TIKTOK_APP_KEY e TIKTOK_APP_SECRET no .env."
        )
    consulta = {"app_key": config.tiktok.app_id, "app_secret": config.tiktok.app_secret, **parametros}
    url = _dominios(config)["token"] + caminho + "?" + urllib.parse.urlencode(consulta)
    requisicao_http = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(requisicao_http, timeout=30) as resposta:
            texto = resposta.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as erro:
        raise RuntimeError(
            f"HTTP {erro.code} do TikTok: {erro.read().decode('utf-8', errors='replace')[:500]}"
        ) from erro
    except urllib.error.URLError as erro:
        raise RuntimeError(f"nao consegui falar com o TikTok: {erro.reason}") from erro
    dados = json.loads(texto)
    if dados.get("code") not in (0, "0", None):
        raise RuntimeError(f"erro do TikTok: {dados.get('code')} {dados.get('message')}")
    return dados


def trocar_code(config: Config, auth_code: str) -> dict:
    """Troca o auth_code do callback por token (grant_type=authorized_code)."""
    return _token(
        config,
        "/api/v2/token/get",
        {"auth_code": auth_code, "grant_type": "authorized_code"},
    )


def renovar_token(config: Config, refresh_token: str) -> dict:
    return _token(
        config, "/api/v2/token/refresh", {"refresh_token": refresh_token, "grant_type": "refresh_token"}
    )


def requisicao(
    config: Config,
    metodo: str,
    caminho: str,
    parametros: dict | None = None,
    corpo: dict | None = None,
    access_token: str | None = None,
    timeout: int = 30,
) -> dict:
    """Chama a OpenAPI assinada e valida ``code == 0``.

    ``parametros`` entram na query e na assinatura. ``corpo`` vira JSON exato
    usado tanto no corpo quanto no calculo do sign.
    """
    if not config.tiktok.configurada:
        raise ValueError(
            "TikTok Shop nao configurado: preencha TIKTOK_APP_KEY e TIKTOK_APP_SECRET no .env."
        )
    if not access_token:
        raise ValueError("access_token obrigatorio para chamar a OpenAPI do TikTok")

    parametros = {chave: str(valor) for chave, valor in (parametros or {}).items()}
    parametros["app_key"] = config.tiktok.app_id
    parametros["timestamp"] = str(int(time.time()))
    corpo_texto = json.dumps(corpo) if corpo is not None else ""
    parametros["sign"] = assinar_tiktok(
        config.tiktok.app_secret, caminho, parametros, corpo_texto
    )
    url = (
        _dominios(config)["api"]
        + caminho
        + "?"
        + urllib.parse.urlencode(parametros, quote_via=urllib.parse.quote)
    )
    cabecalhos = {
        "Content-Type": "application/json",
        "x-tts-access-token": access_token,
    }
    requisicao_http = urllib.request.Request(
        url,
        data=corpo_texto.encode("utf-8") if corpo is not None else None,
        headers=cabecalhos,
        method=metodo.upper(),
    )
    try:
        with urllib.request.urlopen(requisicao_http, timeout=timeout) as resposta:
            texto = resposta.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as erro:
        raise RuntimeError(
            f"HTTP {erro.code} do TikTok: {erro.read().decode('utf-8', errors='replace')[:500]}"
        ) from erro
    except urllib.error.URLError as erro:
        raise RuntimeError(f"nao consegui falar com o TikTok: {erro.reason}") from erro
    dados = json.loads(texto)
    if dados.get("code") not in (0, "0", None):
        raise RuntimeError(f"erro do TikTok: {dados.get('code')} {dados.get('message')}")
    return dados


__all__ = [
    "ENDPOINTS",
    "MAX_IDS_DETALHE",
    "PAGE_SIZE_MAX",
    "link_autorizacao",
    "renovar_token",
    "requisicao",
    "trocar_code",
]
