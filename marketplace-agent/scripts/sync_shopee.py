#!/usr/bin/env python3
"""Sincroniza pedidos/produtos da Shopee (API oficial) para a base e planilhas.

- Usa o token de producao salvo por scripts/conectar_shopee.py.
- Renova o access_token automaticamente com o refresh_token quando necessario.
- Varre o historico em janelas de 14 dias (limite da API de pedidos).
- Busca detalhe de cada pedido e o escrow (comissao/servico/repasse).
- Gera CSV canonico para o importador, planilha XLSX e dados brutos JSON.

Uso:
    python3 scripts/sync_shopee.py
    python3 scripts/sync_shopee.py --desde 2026-01-01
    python3 scripts/sync_shopee.py --sem-escrow --limite 50
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

from mktagent.api import shopee  # noqa: E402
from mktagent.config import Config  # noqa: E402
from xlsx_mini import escrever_xlsx  # noqa: E402

FORMATO_DATA = "%Y-%m-%d"
INTERVALO_DIAS = 14
TAMANHO_PAGINA = 50
PAUSA = 0.15


def _tokens(config: Config) -> tuple[str, str, dict]:
    caminho = config.dados / "shopee_tokens.json"
    if not caminho.exists():
        raise SystemExit("Nenhum token salvo. Rode scripts/conectar_shopee.py.")
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    candidatos = {
        k: v for k, v in dados.items()
        if v.get("ambiente") == config.shopee.ambiente and v.get("access_token")
    }
    if not candidatos:
        raise SystemExit(f"Nenhum token para o ambiente ativo ({config.shopee.ambiente}).")
    shop_id, token = sorted(candidatos.items(), key=lambda kv: kv[1].get("obtido_em", 0))[-1]
    expira = int(token.get("expira_em") or 0)
    if expira and expira < time.time() + 300 and token.get("refresh_token"):
        print("access_token vencendo; renovando...")
        novo = shopee.renovar_token(config, token["refresh_token"], shop_id)
        token.update(
            access_token=novo.get("access_token"),
            refresh_token=novo.get("refresh_token", token.get("refresh_token")),
            expire_in=int(novo.get("expire_in") or 0),
            obtido_em=int(time.time()),
            expira_em=int(time.time()) + int(novo.get("expire_in") or 0),
        )
        dados[shop_id] = token
        caminho.write_text(json.dumps(dados, indent=2), encoding="utf-8")
        print("token renovado")
    return shop_id, token["access_token"], token


def _api(config, shop_id, token, caminho, params=None, tentativas=3):
    for n in range(tentativas):
        try:
            return shopee.requisicao(
                config, "GET", caminho, params=params,
                access_token=token, shop_id=shop_id, timeout=30,
            )
        except Exception as erro:  # noqa: BLE001
            texto = str(erro)
            if ("HTTP 429" in texto or "error_limit" in texto) and n < tentativas - 1:
                print("rate limit; esperando 5s...")
                time.sleep(5)
                continue
            raise
    raise RuntimeError("falhou")


def _iso(ts) -> str:
    try:
        return dt.datetime.fromtimestamp(int(ts), tz=dt.timezone.utc).astimezone().strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return ""


def _status_pt(status: str) -> str:
    s = (status or "").upper()
    if s in ("UNPAID", "PENDING", "TO_PAY"):
        return "Pendente"
    if s in ("CANCELLED", "IN_CANCEL", "CANCEL"):
        return "Cancelado"
    if s in ("TO_RETURN", "RETURN", "REFUND"):
        return "Devolvido"
    return "Aprovado"


def _pedidos(config, shop_id, token, desde: dt.date, ate: dt.date, sem_escrow: bool, limite: int | None):
    pedidos: dict[str, dict] = {}
    cursor = desde
    janela = dt.timedelta(days=INTERVALO_DIAS)
    while cursor <= ate:
        fim = min(cursor + janela - dt.timedelta(days=1), ate)
        t0 = int(dt.datetime.combine(cursor, dt.time.min, tzinfo=dt.timezone.utc).timestamp())
        t1 = int(dt.datetime.combine(fim, dt.time.max, tzinfo=dt.timezone.utc).timestamp())
        pagina = 1
        while True:
            r = _api(config, shop_id, token, "/api/v2/order/get_order_list", {
                "time_range_field": "create_time", "time_from": t0, "time_to": t1,
                "page_size": TAMANHO_PAGINA, "page_no": pagina,
            })
            resp = r.get("response") or {}
            for o in resp.get("order_list") or []:
                pedidos[o["order_sn"]] = {"order_sn": o["order_sn"]}
            if not resp.get("more") or pagina > 100:
                break
            pagina += 1
            time.sleep(PAUSA)
        print(f"  {cursor} a {fim}: total acumulado {len(pedidos)} pedidos")
        if limite and len(pedidos) >= limite:
            break
        cursor = fim + dt.timedelta(days=1)

    sns = list(pedidos)[: limite or None]
    if not sns:
        return []
    detalhes: dict[str, dict] = {}
    for i in range(0, len(sns), 50):
        lote = sns[i:i + 50]
        r = _api(config, shop_id, token, "/api/v2/order/get_order_detail", {
            "order_sn_list": ",".join(lote),
            "response_optional_fields": "order_status,total_amount,create_time,currency,item_list,shipping_carrier",
        })
        for o in (r.get("response") or {}).get("order_list") or []:
            detalhes[o["order_sn"]] = o
        print(f"  detalhes: {len(detalhes)}/{len(sns)}")
        time.sleep(PAUSA)

    for idx, sn in enumerate(sns, start=1):
        detalhe = detalhes.get(sn)
        if not detalhe:
            continue
        renda = {}
        if not sem_escrow:
            try:
                e = _api(config, shop_id, token, "/api/v2/payment/get_escrow_detail", {"order_sn": sn})
                renda = (e.get("response") or {}).get("order_income") or {}
            except Exception as erro:  # noqa: BLE001
                print(f"  escrow {sn} falhou: {str(erro)[:120]}")
            time.sleep(PAUSA)
        pedidos[sn] = {"detalhe": detalhe, "escrow": renda}
        if idx % 25 == 0:
            print(f"  escrow: {idx}/{len(sns)}")
    return [pedidos[sn] for sn in sns if "detalhe" in pedidos[sn]]


def _produtos(config, shop_id, token):
    itens: dict[int, dict] = {}
    for status in ("NORMAL", "UNLIST"):
        pagina = 0
        while True:
            r = _api(config, shop_id, token, "/api/v2/product/get_item_list", {
                "offset": pagina * 100, "page_size": 100, "item_status": status,
            })
            resp = r.get("response") or {}
            for it in resp.get("item") or []:
                itens[int(it["item_id"])] = {"item_id": it["item_id"], "status": it.get("item_status")}
            if not resp.get("has_next_page"):
                break
            pagina += 1
            time.sleep(PAUSA)
    ids = list(itens)
    if not ids:
        return []
    for i in range(0, len(ids), 50):
        lote = ids[i:i + 50]
        r = _api(config, shop_id, token, "/api/v2/product/get_item_base_info", {
            "item_id_list": ",".join(str(x) for x in lote),
        })
        for it in (r.get("response") or {}).get("item_list") or []:
            itens[int(it["item_id"])].update(it)
        time.sleep(PAUSA)
    for idx, item_id in enumerate(ids, start=1):
        try:
            r = _api(config, shop_id, token, "/api/v2/product/get_model_list", {"item_id": item_id})
            itens[item_id]["modelos"] = (r.get("response") or {}).get("model") or []
        except Exception as erro:  # noqa: BLE001
            itens[item_id]["modelos"] = []
            print(f"  modelos {item_id} falhou: {str(erro)[:100]}")
        time.sleep(PAUSA)
    return [itens[x] for x in ids]


def _escrever_csvs(saida: Path, pedidos, produtos):
    os_pedidos = []
    os_itens = []
    for p in pedidos:
        det = p.get("detalhe") or {}
        esc = p.get("escrow") or {}
        sn = det.get("order_sn") or ""
        status = _status_pt(det.get("order_status"))
        data = _iso(det.get("create_time"))
        itens = det.get("item_list") or []
        total = 0.0
        for it in itens:
            qtd = int(it.get("model_quantity_purchased") or 1)
            preco = float(it.get("model_discounted_price") or 0)
            total += preco * qtd
            os_itens.append({
                "order_sn": sn, "data": data, "status_original": det.get("order_status"),
                "item_id": it.get("item_id"), "item_name": it.get("item_name"),
                "sku": it.get("model_sku") or it.get("item_sku") or str(it.get("item_id")),
                "model_name": it.get("model_name"), "quantidade": qtd,
                "preco_unitario": preco, "total": preco * qtd,
            })
        os_pedidos.append({
            "order_sn": sn, "data": data, "status": status,
            "status_original": det.get("order_status"),
            "itens": len(itens), "receita": total,
            "comissao": float(esc.get("commission_fee") or 0),
            "servico": float(esc.get("service_fee") or 0),
            "cupom": float(esc.get("seller_voucher") or esc.get("seller_discount") or 0),
            "repasse": float(esc.get("escrow_amount") or esc.get("escrow_amount_after_adjustment") or 0),
            "buyer": det.get("buyer_username") or "",
        })
    with (saida / "pedidos_api.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(os_pedidos[0]) if os_pedidos else ["order_sn"], delimiter=";")
        w.writeheader(); w.writerows(os_pedidos)
    with (saida / "itens_api.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(os_itens[0]) if os_itens else ["order_sn"], delimiter=";")
        w.writeheader(); w.writerows(os_itens)

    # CSV canonico para o importador do agente
    with (saida / "pedidos_para_importar.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["pedido", "status", "data_pedido", "sku", "produto", "quantidade",
                    "preco_unitario", "itens_total", "comissao", "taxa_servico", "cupom",
                    "repasse", "cliente", "desconto", "frete_cobrado", "frete_pago"])
        for p in pedidos:
            det = p["detalhe"]; esc = p.get("escrow") or {}
            sn = det["order_sn"]; data = _iso(det.get("create_time")); status = _status_pt(det.get("order_status"))
            itens = det.get("item_list") or []
            comissao = esc.get("commission_fee") or 0
            servico = esc.get("service_fee") or 0
            cupom = esc.get("seller_voucher") or 0
            repasse = esc.get("escrow_amount") or 0
            for it in itens:
                qtd = int(it.get("model_quantity_purchased") or 1)
                preco = float(it.get("model_discounted_price") or 0)
                sku = it.get("model_sku") or it.get("item_sku") or str(it.get("item_id"))
                w.writerow([sn, status, data, sku, it.get("item_name") or "", qtd,
                            f"{preco:.2f}".replace(".", ","), f"{preco*qtd:.2f}".replace(".", ","),
                            f"{comissao:.2f}".replace(".", ","), f"{servico:.2f}".replace(".", ","),
                            f"{cupom:.2f}".replace(".", ","), f"{repasse:.2f}".replace(".", ","),
                            det.get("buyer_username") or "", "0,00", "0,00", "0,00"])

    # CSV de produtos
    with (saida / "produtos_para_importar.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["sku", "produto", "preco_venda", "estoque", "categoria"])
        vistos = set()
        for prod in produtos:
            item_id = prod.get("item_id")
            modelos = prod.get("modelos") or []
            if modelos:
                for m in modelos:
                    sku = m.get("model_sku") or f"{item_id}"
                    if sku in vistos:
                        continue
                    vistos.add(sku)
                    preco = (m.get("price_info") or [{}])[0].get("current_price")
                    estoque = (((m.get("stock_info_v2") or {}).get("summary_info") or {}).get("total_available_stock"))
                    w.writerow([sku, prod.get("item_name") or f"Item {item_id}",
                                f"{float(preco):.2f}".replace(".", ",") if preco is not None else "",
                                estoque if estoque is not None else "", "shopee"])
            else:
                sku = prod.get("item_sku") or str(item_id)
                if sku in vistos:
                    continue
                vistos.add(sku)
                w.writerow([sku, prod.get("item_name") or f"Item {item_id}", "", "", "shopee"])


def _planilha(saida: Path, pedidos, produtos):
    # agrega vendas por item
    vendas: dict[int, dict] = {}
    for p in pedidos:
        det = p.get("detalhe") or {}
        for it in det.get("item_list") or []:
            iid = int(it.get("item_id") or 0)
            q = int(it.get("model_quantity_purchased") or 1)
            total = q * float(it.get("model_discounted_price") or 0)
            reg = vendas.setdefault(iid, {"qtd": 0, "receita": 0.0})
            reg["qtd"] += q
            reg["receita"] += total

    linhas = [["Order SN", "Data", "Status", "Status original", "Itens", "Receita", "Comissão", "Serviço", "Cupom", "Repasse", "Cliente"]]
    for p in pedidos:
        o = p.get("detalhe") or {}
        e = p.get("escrow") or {}
        linhas.append([
            o.get("order_sn"), _iso(o.get("create_time")), _status_pt(o.get("order_status")),
            o.get("order_status"), len(o.get("item_list") or []),
            float(e.get("cost_of_goods_sold") or 0), float(e.get("commission_fee") or 0),
            float(e.get("service_fee") or 0), float(e.get("seller_voucher") or 0),
            float(e.get("escrow_amount") or 0), o.get("buyer_username") or "",
        ])
    linhas_itens = [["Order SN", "Data", "Status", "Item ID", "Produto", "SKU", "Variação", "Qtd", "Preço unit.", "Total"]]
    for p in pedidos:
        o = p.get("detalhe") or {}
        for it in o.get("item_list") or []:
            q = int(it.get("model_quantity_purchased") or 1)
            preco = float(it.get("model_discounted_price") or 0)
            linhas_itens.append([o.get("order_sn"), _iso(o.get("create_time")), _status_pt(o.get("order_status")),
                                 it.get("item_id"), it.get("item_name"), it.get("model_sku") or it.get("item_sku"),
                                 it.get("model_name"), q, preco, q * preco])
    # produtos + análise
    linhas_prod = [["Item ID", "Título", "Status", "Preço atual", "Estoque", "Un. vendidas", "Receita",
                    "Tam. título", "Imagens", "Problemas / oportunidade"]]
    for prod in produtos:
        iid = int(prod.get("item_id") or 0)
        modelos = prod.get("modelos") or []
        precos = [((m.get("price_info") or [{}])[0].get("current_price")) for m in modelos]
        precos = [float(x) for x in precos if x is not None]
        preco = min(precos) if precos else None
        estoque = sum((((m.get("stock_info_v2") or {}).get("summary_info") or {}).get("total_available_stock") or 0) for m in modelos)
        v = vendas.get(iid, {"qtd": 0, "receita": 0.0})
        nome = prod.get("item_name") or ""
        problemas = []
        if len(nome) < 60: problemas.append("título curto")
        if len(nome) > 120: problemas.append("título longo")
        if not any(t in nome.lower() for t in ("3d", "petg", "mocozim")): problemas.append("sem material/marca")
        if v["qtd"] == 0: problemas.append("sem vendas no período")
        if estoque and estoque < 5: problemas.append("estoque baixo")
        linhas_prod.append([iid, nome, prod.get("item_status"), preco, estoque, v["qtd"], round(v["receita"], 2),
                            len(nome), len((prod.get("image") or {}).get("image_url_list") or []), "; ".join(problemas)])

    caminho = saida / f"Shopee_Pedidos_{dt.date.today().isoformat()}.xlsx"
    escrever_xlsx(caminho, [
        {"nome": "Pedidos", "linhas": linhas,
         "formatos": {5: "moeda", 6: "moeda", 7: "moeda", 8: "moeda", 9: "moeda"}},
        {"nome": "Itens", "linhas": linhas_itens,
         "formatos": {7: "inteiro", 8: "moeda", 9: "moeda"}},
        {"nome": "Produtos", "linhas": linhas_prod,
         "formatos": {3: "moeda", 4: "inteiro", 5: "inteiro", 6: "moeda", 7: "inteiro", 8: "inteiro"}},
    ], titulo="Shopee — pedidos e anúncios")
    return caminho


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--desde", default="2024-01-01")
    parser.add_argument("--ate", default=dt.date.today().isoformat())
    parser.add_argument("--limite", type=int, default=None)
    parser.add_argument("--sem-escrow", action="store_true")
    args = parser.parse_args()

    config = Config.carregar()
    shop_id, token, _ = _tokens(config)
    print(f"loja {shop_id} | ambiente {config.shopee.ambiente}")
    desde = dt.date.fromisoformat(args.desde)
    ate = dt.date.fromisoformat(args.ate)
    saida = config.saidas / "shopee_api"
    saida.mkdir(parents=True, exist_ok=True)

    print("buscando pedidos...")
    pedidos = _pedidos(config, shop_id, token, desde, ate, args.sem_escrow, args.limite)
    print("pedidos com detalhe:", len(pedidos))
    print("buscando produtos...")
    produtos = _produtos(config, shop_id, token)
    (saida / "dados_brutos.json").write_text(
        json.dumps({"pedidos": pedidos, "produtos": produtos}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    _escrever_csvs(saida, pedidos, produtos)
    caminho = _planilha(saida, pedidos, produtos)
    print("planilha:", caminho)
    print("CSV import:", saida / "pedidos_para_importar.csv")
    print("CSV produtos:", saida / "produtos_para_importar.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
