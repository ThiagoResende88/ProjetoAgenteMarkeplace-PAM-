#!/usr/bin/env python3
"""Mostra o status da conexao Shopee salva em dados/shopee_tokens.json."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from mktagent.api import shopee  # noqa: E402
from mktagent.config import Config  # noqa: E402


def main() -> int:
    config = Config.carregar()
    caminho = config.dados / "shopee_tokens.json"
    if not caminho.exists():
        print("Nenhum token salvo. Rode scripts/conectar_shopee.py primeiro.")
        return 1
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    for shop_id, token in dados.items():
        acesso = token.get("access_token") or ""
        expira = token.get("expira_em")
        print(f"shop_id {shop_id} | ambiente {token.get('ambiente')} | token {acesso[:8]}... | expira em {expira}")
        if expira and int(expira) < time.time() + 300 and token.get("refresh_token"):
            print("token vencendo; renovando...")
            try:
                novo = shopee.renovar_token(config, token["refresh_token"], shop_id)
                token.update(
                    access_token=novo.get("access_token"),
                    refresh_token=novo.get("refresh_token", token.get("refresh_token")),
                    expire_in=int(novo.get("expire_in") or 0),
                    obtido_em=int(time.time()),
                    expira_em=int(time.time()) + int(novo.get("expire_in") or 0),
                )
                caminho.write_text(json.dumps(dados, indent=2), encoding="utf-8")
                acesso = token["access_token"]
                print("token renovado")
            except Exception as erro:  # noqa: BLE001
                print("falha ao renovar:", str(erro)[:300])
        try:
            info = shopee.requisicao(config, "GET", "/api/v2/shop/get_shop_info",
                                     access_token=acesso, shop_id=shop_id, timeout=25)
            print("loja:", info.get("shop_name"), "| regiao:", info.get("region"), "| status:", info.get("status"))
        except Exception as erro:  # noqa: BLE001
            print("shop_info falhou:", str(erro)[:300]); continue
        agora = int(time.time())
        try:
            pedidos = shopee.requisicao(
                config, "GET", "/api/v2/order/get_order_list",
                params={"time_range_field": "create_time", "time_from": agora - 15 * 86400,
                        "time_to": agora, "page_size": 20, "page_no": 1},
                access_token=acesso, shop_id=shop_id, timeout=25,
            )
            lista = (pedidos.get("response") or {}).get("order_list") or []
            print("pedidos (15 dias):", len(lista))
        except Exception as erro:  # noqa: BLE001
            print("order_list falhou:", str(erro)[:300])
        try:
            itens = shopee.requisicao(
                config, "GET", "/api/v2/product/get_item_list",
                params={"offset": 0, "page_size": 20, "item_status": "NORMAL"},
                access_token=acesso, shop_id=shop_id, timeout=25,
            )
            print("produtos:", ((itens.get("response") or {}).get("total_count")))
        except Exception as erro:  # noqa: BLE001
            print("item_list falhou:", str(erro)[:300])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
