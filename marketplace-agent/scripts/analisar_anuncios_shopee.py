#!/usr/bin/env python3
"""Analisa os anuncios Shopee (API) e gera planilha + relatorio de otimizacao."""

from __future__ import annotations

import collections
import json
import re
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))
from xlsx_mini import escrever_xlsx  # noqa: E402

RAW = RAIZ / "saidas" / "shopee_api" / "dados_brutos.json"
SAIDA = RAIZ / "saidas" / "analises"
DB = RAIZ / "dados" / "mkt.db"
MARCAS_RISCO = ("veipar", "sealbrand", "hello kitty", "hello kit", "sanrio", "corinthians", "kitty")


def custos() -> dict[str, float]:
    conn = sqlite3.connect(DB)
    mapa = {}
    for sku, custo in conn.execute("SELECT sku, custo_unitario_centavos FROM produtos WHERE custo_unitario_centavos IS NOT NULL"):
        mapa[str(sku).strip().lower()] = custo / 100.0
    conn.close()
    return mapa


def custo_por_titulo(titulo: str) -> float | None:
    t = titulo.lower()
    if "kit 10 unidades" in t: return 11.40
    if "kit 5 unidades" in t: return 5.70
    if "kit 3 unidades" in t: return 3.42
    if "kit 2 unidades" in t: return 2.28
    return None


def preco_por_titulo(titulo: str) -> float | None:
    t = titulo.lower()
    if "kit 10 unidades" in t: return 149.90
    if "kit 5 unidades" in t: return 79.90
    if "kit 3 unidades" in t: return 49.90
    if "kit 2 unidades" in t: return 34.90
    if "porta incenso" in t: return 24.90
    if "pote herm" in t: return 19.99
    if "chaveiro" in t: return 19.90
    return None


def marca_de(nome: str) -> str:
    """Mocozim = headshop; 3DPrintFranca = demais linhas (EasyPU, rosario etc.)."""
    t = (nome or "").lower()
    headshop = ("tubo", "tubete", "banquinho", "seda", "porta bic", "porta esqueiro", "isqueiro")
    return "Mocozim" if any(x in t for x in headshop) else "3DPrintFranca"


def sugerir_titulo(nome: str, modelos: list) -> str:
    t = (nome or "").lower()
    marca = marca_de(nome)
    if "kit 10 unidades" in t: return f"Kit 10 Aplicadores de PU Easy Vedação 3D em PETG — {marca}"
    if "kit 5 unidades" in t: return f"Kit 5 Aplicadores de PU Easy Vedação 3D em PETG — {marca}"
    if "kit 3 unidades" in t: return f"Kit 3 Aplicadores de PU Easy Vedação 3D em PETG — {marca}"
    if "kit 2 unidades" in t: return f"Kit 2 Aplicadores de PU Easy Vedação 3D em PETG — {marca}"
    if "aplicador" in t or "easy" in t:
        if len(modelos) > 1: return f"Aplicador de PU Easy Vedação 3D em PETG — 1, 2 ou 3 Unidades | {marca}"
        return f"Aplicador de PU Easy Vedação 3D em PETG — {marca}"
    if "tubo herm" in t or "tubete" in t: return "Tubete Hermético 3D em PETG 14 cm — Tampa Rosqueada | Mocozim"
    if "pote" in t: return f"Pote Hermético 3D em PETG com Design Geométrico — {marca}"
    if "porta incenso" in t: return f"Porta Incenso 3D Mandala Flor — Suporte Decorativo em PETG | {marca}"
    if "chaveiro" in t: return f"Chaveiro Terço 3D Rosário de Bolso Católico — {marca}"
    limpo = re.sub(r"(?i)(veipar|sealbrand|hello kit(ty)?|sanrio|corinthians)", "", nome or "")
    limpo = re.sub(r"\s+", " ", limpo).strip(" -|")
    return (limpo[:90] + f" — 3D PETG {marca}")[:120]


def problemas(titulo: str, preco, estoque, vendas, custo, margem, imagens):
    p = []
    low = titulo.lower()
    for marca in MARCAS_RISCO:
        if marca in low:
            p.append(f"marca de terceiro: {marca}")
            break
    if len(titulo) > 120: p.append("título com mais de 120 caracteres")
    if len(titulo) < 60: p.append("título curto")
    if not any(x in low for x in ("3d", "petg", "mocozim")): p.append("sem 3D/PETG/marca no título")
    if vendas == 0: p.append("sem vendas no período")
    if estoque is not None and estoque < 5: p.append("estoque baixo")
    if margem is not None and margem < 0.30: p.append("margem abaixo de 30%")
    return "; ".join(p)


def main() -> int:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    mapa_custos = custos()
    # vendas e taxas por item
    vendas = collections.defaultdict(lambda: {"qtd": 0, "receita": 0.0, "taxas": 0.0, "custo": 0.0, "pedidos": 0, "nome": ""})
    pedidos_validos = 0
    for ped in raw["pedidos"]:
        det = ped.get("detalhe") or {}
        esc = ped.get("escrow") or {}
        if str(det.get("order_status") or "").upper() in ("CANCELLED", "UNPAID", "IN_CANCEL"):
            continue
        pedidos_validos += 1
        itens = det.get("item_list") or []
        total_itens = sum(int(i.get("model_quantity_purchased") or 1) * float(i.get("model_discounted_price") or 0) for i in itens)
        taxas_pedido = float(esc.get("commission_fee") or 0) + float(esc.get("service_fee") or 0)
        for it in itens:
            iid = int(it.get("item_id") or 0)
            q = int(it.get("model_quantity_purchased") or 1)
            valor = q * float(it.get("model_discounted_price") or 0)
            reg = vendas[iid]
            reg["qtd"] += q
            reg["receita"] += valor
            reg["pedidos"] += 1
            reg["nome"] = it.get("item_name") or reg["nome"]
            reg["taxas"] += taxas_pedido * (valor / total_itens if total_itens else 0)
            sku = str(it.get("model_sku") or it.get("item_sku") or "").strip().lower()
            if sku in mapa_custos:
                reg["custo"] += q * mapa_custos[sku]

    linhas_ativos = [["Item ID", "Título", "Status", "Preço", "Estoque", "Un. vendidas", "Receita",
                      "Taxas alocadas", "Custo", "Contribuição", "Margem", "Imagens", "Problemas", "Prioridade", "Título sugerido", "Recomendação"]]
    ativos = []
    for prod in raw["produtos"]:
        iid = int(prod["item_id"])
        modelos = prod.get("modelos") or []
        precos = []
        estoque = 0
        for m in modelos:
            pi = (m.get("price_info") or [{}])[0]
            if pi.get("current_price") is not None: precos.append(float(pi["current_price"]))
            estoque += int((((m.get("stock_info_v2") or {}).get("summary_info") or {}).get("total_available_stock") or 0))
        tem_modelos = bool(modelos)
        preco = min(precos) if precos else preco_por_titulo(prod.get("item_name") or "")
        vendas_item = vendas.get(iid, {"qtd": 0, "receita": 0.0, "taxas": 0.0})
        # custo total das unidades vendidas, ponderado pelo SKU/modelo de cada item
        custo = vendas_item.get("custo") or 0.0
        if custo == 0:
            unitario = custo_por_titulo(prod.get("item_name") or "")
            custo = (unitario or 0) * vendas_item["qtd"]
            if unitario is None:
                custo = None
        taxas = vendas_item["taxas"]
        contrib = vendas_item["receita"] - taxas - (custo if custo is not None else 0)
        margem = contrib / vendas_item["receita"] if vendas_item["receita"] else None
        imagens = len((prod.get("image") or {}).get("image_url_list") or [])
        texto = (prod.get("item_name") or "") + " " + (prod.get("description") or "")
        probs = problemas(texto, preco, estoque, vendas_item["qtd"], custo, margem, imagens)
        recs = []
        sugestao = sugerir_titulo(prod.get("item_name") or "", modelos)
        prioridade = "P1"
        if "marca de terceiro" in probs or (margem is not None and margem < 0.30): prioridade = "P0"
        elif vendas_item["qtd"] == 0: prioridade = "P1"
        else: prioridade = "P2"
        if "marca de terceiro" in probs: recs.append("remover marca de terceiro do título/descrição")
        if "sem 3D" in probs: recs.append("incluir 3D/PETG/Mocozim no título e nos atributos")
        if vendas_item["qtd"] == 0: recs.append("revisar título, imagem principal e preço; testar kit")
        if estoque is not None and estoque < 5: recs.append("repor estoque")
        if margem is not None and margem < 0.30: recs.append("reprecificar ou aumentar kit")
        if not recs: recs.append("manter e testar variação de título/imagem")
        ativos.append({"iid": iid, "titulo": prod.get("item_name") or "", "status": prod.get("item_status"),
                       "preco": preco, "estoque": estoque, "qtd": vendas_item["qtd"], "receita": vendas_item["receita"],
                       "taxas": taxas, "custo": custo, "contrib": contrib, "margem": margem, "imagens": imagens,
                       "problemas": probs, "prioridade": prioridade, "sugestao": sugestao,
                       "recomendacao": "; ".join(recs)})
        estoque_cell = estoque if tem_modelos else None
        linhas_ativos.append([iid, prod.get("item_name"), len(prod.get("item_name") or ""), prod.get("item_status"),
                              round(preco,2) if preco else "",
                              estoque_cell, vendas_item["qtd"], round(vendas_item["receita"],2), round(taxas,2),
                              round(custo,2) if custo is not None else "",
                              round(contrib,2), margem, imagens, probs, prioridade, sugestao, "; ".join(recs)])

    ids_atuais = {int(p["item_id"]) for p in raw["produtos"]}
    linhas_hist = [["Item ID", "Produto", "Un. vendidas", "Receita", "Taxas alocadas", "Situação"]]
    for iid, reg in sorted(vendas.items(), key=lambda kv: -kv[1]["receita"]):
        if iid in ids_atuais: continue
        linhas_hist.append([iid, reg["nome"], reg["qtd"], round(reg["receita"],2), round(reg["taxas"],2), "anúncio antigo/fora da lista atual"])

    total_receita = sum(v["receita"] for v in vendas.values())
    total_qtd = sum(v["qtd"] for v in vendas.values())
    total_taxas = sum(v["taxas"] for v in vendas.values())
    total_custo = sum(v.get("custo", 0.0) for v in vendas.values())
    contrib_total = total_receita - total_taxas - total_custo
    try:
        conn = sqlite3.connect(DB)
        ads = (conn.execute("SELECT COALESCE(SUM(valor_centavos),0) FROM contas_financeiras WHERE categoria='marketing'").fetchone()[0] or 0) / 100.0
        conn.close()
    except Exception:
        ads = 0.0
    top = sorted(vendas.items(), key=lambda kv: -kv[1]["receita"])[:5]
    resumo = [["Métrica", "Valor"]]
    resumo += [
        ["Pedidos no histórico", len(raw["pedidos"])],
        ["Pedidos válidos (sem cancelados/unpaid)", pedidos_validos],
        ["Unidades vendidas", total_qtd],
        ["Receita dos itens", round(total_receita, 2)],
        ["Anúncios ativos", len(raw["produtos"])],
        ["Anúncios ativos com venda", sum(1 for a in ativos if a["qtd"] > 0)],
        ["Anúncios ativos sem venda", sum(1 for a in ativos if a["qtd"] == 0)],
        ["Taxas Shopee (período)", round(total_taxas, 2)],
        ["CMV estimado", round(total_custo, 2)],
        ["Contribuição antes de Ads", round(contrib_total, 2)],
        ["Ads pagos (set+out)", round(ads, 2)],
        ["Contribuição após Ads", round(contrib_total - ads, 2)],
        ["Item com maior receita", top[0][1]["nome"] if top else ""],
        ["Receita do top item", round(top[0][1]["receita"],2) if top else 0],
    ]
    for iid, reg in top:
        resumo.append([f"Top: {reg['nome'][:45]}", f"R$ {reg['receita']:.2f} · {reg['qtd']} un"])

    SAIDA.mkdir(parents=True, exist_ok=True)
    xlsx = SAIDA / "Shopee_Analise_Anuncios_2026-10-29.xlsx"
    escrever_xlsx(xlsx, [
        {"nome": "Resumo", "linhas": resumo, "formatos": {1: "moeda"}},
        {"nome": "Anuncios_Ativos", "linhas": linhas_ativos,
         "formatos": {2: "inteiro", 4: "moeda", 5: "inteiro", 6: "inteiro", 7: "moeda", 8: "moeda",
                      9: "moeda", 10: "moeda", 11: "pct", 12: "inteiro"}},
        {"nome": "Historico_Vendas", "linhas": linhas_hist,
         "formatos": {2: "inteiro", 3: "moeda", 4: "moeda"}},
    ], titulo="Shopee — análise de anúncios")

    md = ["# Análise de anúncios Shopee — 3D Print Franca", "", f"Planilha: `{xlsx.relative_to(RAIZ)}`", ""]
    md.append("## Resumo")
    md.append(f"- Pedidos no histórico: **{len(raw['pedidos'])}**")
    md.append(f"- Unidades: **{total_qtd}** | receita dos itens: **R$ {total_receita:.2f}**")
    md.append(f"- Anúncios ativos: **{len(raw['produtos'])}** | com venda: {sum(1 for a in ativos if a['qtd']>0)} | sem venda: {sum(1 for a in ativos if a['qtd']==0)}")
    md.append(f"- Taxas Shopee: **R$ {total_taxas:.2f}** | CMV estimado: **R$ {total_custo:.2f}**")
    md.append(f"- Contribuição antes de Ads: **R$ {contrib_total:.2f}** | Ads pagos: **R$ {ads:.2f}** | após Ads: **R$ {contrib_total-ads:.2f}**")
    md.append("")
    md.append("## Top vendas")
    for iid, reg in top:
        md.append(f"- `{iid}` {reg['nome'][:70]} — {reg['qtd']} un, R$ {reg['receita']:.2f}")
    md.append("")
    md.append("## Anúncios ativos")
    md.append("| Item | Título | Preço | Vendas | Receita | Margem | Problemas |")
    md.append("|---|---|---:|---:|---:|---:|---|")
    for a in sorted(ativos, key=lambda x: -x["receita"]):
        margem = f"{a['margem']*100:.1f}%" if a["margem"] is not None else "—"
        md.append(f"| {a['iid']} | {a['titulo'][:55]} | {a['preco'] or '—'} | {a['qtd']} | R$ {a['receita']:.2f} | {margem} | {a['problemas'] or '—'} |")
    md.append("")
    md.append("## Recomendações por anúncio")
    for a in sorted(ativos, key=lambda x: x["receita"]):
        md.append(f"### {a['iid']} — {a['titulo'][:80]}")
        md.append(f"- Vendas: {a['qtd']} un | receita R$ {a['receita']:.2f} | margem {f'{a['margem']*100:.1f}%' if a['margem'] is not None else '—'} | prioridade {a['prioridade']}")
        md.append(f"- Problemas: {a['problemas'] or 'nenhum'}")
        md.append(f"- Marca: **{marca_de(a['titulo'])}** | Título sugerido: **{a['sugestao']}**")
        md.append(f"- Ação: {a['recomendacao']}")
    md.append("")
    md.append("## Fora da lista atual (histórico)")
    for linha in linhas_hist[1:]:
        md.append(f"- `{linha[0]}` {linha[1][:70]} — {linha[2]} un, R$ {linha[3]:.2f}")
    (SAIDA / "analise_anuncios_shopee.md").write_text("\n".join(md), encoding="utf-8")
    print("XLSX:", xlsx)
    print("MD:", SAIDA / "analise_anuncios_shopee.md")
    print("ativos:", len(ativos), "| top:", top[0][1]["nome"][:60] if top else "-")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
