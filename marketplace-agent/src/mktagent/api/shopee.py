"""Cliente da Shopee Open Platform v2.

Fase 2: a estrutura de auth/assinatura esta pronta, mas a sincronizacao
automatica ainda NAO foi validada contra o sandbox. Nada aqui roda sozinho.

Documentacao oficial consultada em 2026-10-25 (ver docs/PESQUISA_APIS.md).
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from ..config import Config
from .assinatura import assinar_shopee

HOSTS = {
    "producao": {
        "global": "https://partner.shopeemobile.com",
        "br": "https://openplatform.shopee.com.br",
        "cn": "https://openplatform.shopee.cn",
    },
    "sandbox": {
        # O host de sandbox .com.br nao resolve em DNS publico (NXDOMAIN).
        # O sandbox e global em Singapura; usamos o mesmo host para BR.
        "global": "https://openplatform.sandbox.test-stable.shopee.sg",
        "br": "https://openplatform.sandbox.test-stable.shopee.sg",
        "cn": "https://openplatform.sandbox.test-stable.shopee.cn",
    },
}

AUTH_HOSTS = {
    "producao": {
        "global": "https://open.shopee.com",
        "br": "https://open.shopee.com.br",
        "cn": "https://open.shopee.cn",
    },
    "sandbox": {
        "global": "https://open.sandbox.test-stable.shopee.com",
        # o host .com.br tambem nao resolve; o auth sandbox e global
        "br": "https://open.sandbox.test-stable.shopee.com",
        "cn": "https://open.sandbox.test-stable.shopee.cn",
    },
}

ENDPOINTS = {
    "listar_pedidos": "/api/v2/order/get_order_list",
    "detalhe_pedido": "/api/v2/order/get_order_detail",
    "escrow_pedido": "/api/v2/payment/get_escrow_detail",
    "receitas": "/api/v2/payment/get_income_detail",
    "info_loja": "/api/v2/shop/get_shop_info",
}

JANELA_MAXIMA_PEDIDOS_DIAS = 15
JANELA_MAXIMA_RECEITAS_DIAS = 14
MAX_SNS_DETALHE = 50


def _ambiente(config: Config) -> str:
    return "sandbox" if config.shopee.ambiente.startswith("sandbox") else "producao"


def url_base(config: Config) -> str:
    regiao = config.shopee.regiao or "br"
    return HOSTS[_ambiente(config)].get(regiao, HOSTS[_ambiente(config)]["global"])


def url_auth(config: Config) -> str:
    regiao = config.shopee.regiao or "br"
    return AUTH_HOSTS[_ambiente(config)].get(regiao, AUTH_HOSTS[_ambiente(config)]["global"])


def link_autorizacao(config: Config, state: str = "") -> str:
    """Link que o vendedor abre para autorizar a app (auth_type=seller)."""
    if not config.shopee.app_id:
        raise ValueError("SHOPEE_PARTNER_ID nao configurado no .env")
    parametros = {
        "partner_id": config.shopee.app_id,
        "auth_type": "seller",
        "redirect_uri": config.shopee.redirect_url,
        "response_type": "code",
        "state": state,
    }
    parametros = {chave: valor for chave, valor in parametros.items() if valor not in ("", None)}
    return f"{url_auth(config)}/auth?" + urllib.parse.urlencode(parametros)


def _parametros_assinados(
    config: Config,
    caminho: str,
    access_token: str | None = None,
    shop_id: str | int | None = None,
    timestamp: int | None = None,
) -> dict[str, str]:
    timestamp = timestamp or int(time.time())
    parametros = {
        "partner_id": str(config.shopee.app_id),
        "timestamp": str(timestamp),
        "sign": assinar_shopee(
            config.shopee.app_secret,
            config.shopee.app_id,
            caminho,
            timestamp,
            access_token=access_token,
            shop_id=shop_id,
        ),
    }
    if access_token and shop_id:
        parametros["access_token"] = access_token
        parametros["shop_id"] = str(shop_id)
    return parametros


def requisicao(
    config: Config,
    metodo: str,
    caminho: str,
    params: dict | None = None,
    body: dict | None = None,
    access_token: str | None = None,
    shop_id: str | int | None = None,
    timeout: int = 30,
) -> dict:
    """Chama a API ja assinada e valida o campo ``error`` (HTTP 200 com erro)."""
    if not config.shopee.configurada:
        raise ValueError(
            "Shopee nao configurada: preencha SHOPEE_PARTNER_ID e SHOPEE_PARTNER_KEY no .env."
        )
    parametros = _parametros_assinados(config, caminho, access_token, shop_id)
    parametros.update({chave: str(valor) for chave, valor in (params or {}).items()})
    url = url_base(config) + caminho + "?" + urllib.parse.urlencode(parametros)
    dados = None
    cabecalhos = {"Content-Type": "application/json"}
    if body is not None:
        dados = json.dumps(body).encode("utf-8")
    requisicao_http = urllib.request.Request(
        url, data=dados, headers=cabecalhos, method=metodo.upper()
    )
    try:
        with urllib.request.urlopen(requisicao_http, timeout=timeout) as resposta:
            texto = resposta.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as erro:
        raise RuntimeError(
            f"HTTP {erro.code} da Shopee: {erro.read().decode('utf-8', errors='replace')[:500]}"
        ) from erro
    except urllib.error.URLError as erro:
        raise RuntimeError(f"nao consegui falar com a Shopee: {erro.reason}") from erro
    try:
        resposta = json.loads(texto)
    except json.JSONDecodeError as erro:
        raise RuntimeError(f"resposta nao-JSON da Shopee: {texto[:300]}") from erro
    if resposta.get("error"):
        raise RuntimeError(f"erro da Shopee: {resposta.get('error')} ({resposta.get('message')})")
    return resposta


def trocar_code(config: Config, code: str, shop_id: str | int) -> dict:
    """Troca o ``code`` do callback por access_token/refresh_token."""
    caminho = "/api/v2/auth/token/get"
    resposta = requisicao(
        config,
        "POST",
        caminho,
        body={"code": code, "shop_id": int(shop_id), "partner_id": int(config.shopee.app_id)},
    )
    return resposta


def renovar_token(config: Config, refresh_token: str, shop_id: str | int) -> dict:
    """Renova o access_token (validade 4h)."""
    return requisicao(
        config,
        "POST",
        "/api/v2/auth/access_token/get",
        body={
            "refresh_token": refresh_token,
            "shop_id": int(shop_id),
            "partner_id": int(config.shopee.app_id),
        },
    )


__all__ = [
    "ENDPOINTS",
    "JANELA_MAXIMA_PEDIDOS_DIAS",
    "JANELA_MAXIMA_RECEITAS_DIAS",
    "MAX_SNS_DETALHE",
    "link_autorizacao",
    "renovar_token",
    "requisicao",
    "trocar_code",
    "url_auth",
    "url_base",
]
