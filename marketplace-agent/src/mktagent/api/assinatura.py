"""Assinatura HMAC-SHA256 das APIs (Shopee e TikTok Shop).

Cada marketplace assina uma string diferente; as funcoes abaixo isolam isso
para o cliente HTTP e para os testes de vetor.
"""

from __future__ import annotations

import hashlib
import hmac
import time


def timestamp_ms() -> int:
    return int(time.time() * 1000)


def timestamp_s() -> int:
    return int(time.time())


def assinar_shopee(
    partner_key: str,
    partner_id: str | int,
    path: str,
    timestamp: int,
    access_token: str | None = None,
    shop_id: str | int | None = None,
) -> str:
    """Assinatura da Shopee Open Platform v2.

    base_string = partner_id + path + timestamp
    (+ access_token + shop_id nos endpoints de loja)
    sign = HMAC-SHA256(partner_key, base_string) em hex.
    """
    base = f"{partner_id}{path}{timestamp}"
    if access_token is not None and shop_id is not None:
        base = f"{partner_id}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        partner_key.encode("utf-8"), base.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def assinar_tiktok(
    app_secret: str,
    path: str,
    parametros: dict[str, str] | None = None,
    corpo: str = "",
) -> str:
    """Assinatura do TikTok Shop Open API.

    A string assinada e: path + parametros de query ordenados por chave
    (concatenados como chave+valor, sem 'sign' e sem 'access_token') +
    corpo (JSON cru) + app_secret. HMAC-SHA256 com app_secret, em hex.
    """
    parametros = parametros or {}
    ordenados = "".join(
        f"{chave}{valor}"
        for chave, valor in sorted(parametros.items())
        if chave not in {"sign", "access_token"}
    )
    base = f"{path}{ordenados}{corpo}{app_secret}"
    return hmac.new(
        app_secret.encode("utf-8"), base.encode("utf-8"), hashlib.sha256
    ).hexdigest()
