#!/usr/bin/env python3
"""Diagnostico rapido da integracao Shopee (nao imprime segredos).

Uso: python3 scripts/checar_shopee.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from mktagent.api import shopee  # noqa: E402
from mktagent.config import Config  # noqa: E402


def main() -> int:
    config = Config.carregar()
    s = config.shopee
    chave = s.app_secret or ""
    print("== Shopee: configuracao ==")
    print("configurada:", s.configurada)
    print("partner_id:", s.app_id or "(vazio)")
    print(
        "partner_key:",
        (chave[:6] + "..." + chave[-4:]) if chave else "(vazia)",
        f"({len(chave)} chars)",
    )
    print("ambiente:", s.ambiente, "| regiao:", s.regiao)
    print("redirect:", s.redirect_url or "(vazio)")
    print("api:", shopee.url_base(config))
    print("auth:", shopee.url_auth(config))
    tokens = config.dados / "shopee_tokens.json"
    print("token local:", tokens, "| existe:", tokens.exists())

    if not s.configurada:
        print("\nFALTAM SHOPEE_PARTNER_ID/SHOPEE_PARTNER_KEY no .env")
        return 1

    print("\n== Teste de assinatura (endpoint publico) ==")
    try:
        resposta = shopee.requisicao(
            config,
            "GET",
            "/api/v2/public/get_shops_by_partner",
            params={"page_size": 10, "page_no": 0},
            timeout=25,
        )
        print("OK — partner/key aceitos")
        print(json.dumps(resposta, ensure_ascii=False)[:800])
        return 0
    except Exception as erro:  # noqa: BLE001
        print("FALHOU:", str(erro)[:800])
        print(
            "\nSe a mensagem for 'error_sign' (Wrong sign), a Partner Key nao "
            "confere com o Partner ID de teste. Copie a chave novamente no "
            "Console (olho ao lado da chave) e atualize SHOPEE_PARTNER_KEY no .env."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
