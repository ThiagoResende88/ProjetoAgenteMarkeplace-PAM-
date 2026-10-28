#!/usr/bin/env python3
"""Gera a planilha padronizada de custos (Mocozim / 3D Print Franca).

Fontes:
- aba "Custos" da planilha Google (peso/tempo por lote, embalagem, preços de kits)
- export Shopee "Order.all" (preços praticados e taxas observadas)
- export TikTok reconstruído (preços praticados)
- custos legados do contexto (Cubo, Chaveiro, Vape - descontinuados)

Saídas em saidas/custos/:
- Custos_Mocozim_3DPrintFranca_2026-10.xlsx (6 abas)
- custos_itens.csv
- custos_para_importar.csv (para o mktagent)
- resumo_custos.md
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

from mktagent.dinheiro import parse_valor  # noqa: E402
from mktagent.ingestao.leitor import ler_tabela  # noqa: E402
from xlsx_mini import escrever_xlsx  # noqa: E402

SAIDA = RAIZ / "saidas" / "custos"
SHOPEE_EXPORT = Path(
    "/home/thiago_dev/.dsh/attachments/v1/files/99/"
    "994e7865c7ffebc53f802d353c393af31f0ff5e3a072c71fb528da9547955137/"
    "Order.all.20260901_20261001.xlsx"
)
TIKTOK_CSV = RAIZ / "dados" / "tiktok_orders_reconstruido.csv"

FILAMENTO_KG = 64.00  # media das compras em promocao (faixa 59-69)
TIKTOK_COMISSAO = 0.10
TIKTOK_SFP = 0.06
TIKTOK_FIXO = 4.00
SEDA_UN = 1.00
EMBALAGEM_UN = 0.50
MAQUINA_HORA = 0.55          # estimativa: energia + depreciação + manutenção
SHOPEE_COMISSAO = 0.18
SHOPEE_SERVICO_PCT = 0.02
SHOPEE_FIXO = 4.00
ENERGIA_KWH = 0.95
IMPRESSORA_PRECO = 2500.00
IMPRESSORA_VIDA_H = 7200
MANUTENCAO_H = 0.0625


def brl(valor) -> str:
    if valor is None:
        return ""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def item(
    sku: str,
    nome: str,
    linha: str,
    status: str,
    *,
    lote_un: float | None = None,
    peso_lote_g: float | None = None,
    horas_lote: float | None = None,
    custo_legado: float | None = None,
    preco_direto: float | None = None,
    preco_consig: float | None = None,
    preco_shopee: float | None = None,
    preco_tiktok: float | None = None,
    unidades: int = 1,
    custo_extra: float | None = None,
    pendente: bool = False,
    obs: str = "",
) -> dict:
    registro = {
        "sku": sku,
        "nome": nome,
        "linha": linha,
        "status": status,
        "lote_un": lote_un,
        "peso_lote_g": peso_lote_g,
        "horas_lote": horas_lote,
        "custo_legado": custo_legado,
        "preco_direto": preco_direto,
        "preco_consig": preco_consig,
        "preco_shopee": preco_shopee,
        "preco_tiktok": preco_tiktok,
        "unidades": unidades,
        "custo_extra": custo_extra,
        "pendente": pendente,
        "obs": obs,
    }
    return registro


def calcular(registro: dict) -> dict:
    r = dict(registro)
    peso_un = horas_un = custo_fil = maquina_un = None
    if r["peso_lote_g"] and r["lote_un"]:
        peso_un = r["peso_lote_g"] / r["lote_un"]
        custo_fil = peso_un / 1000 * FILAMENTO_KG
    if r["horas_lote"] and r["lote_un"]:
        horas_un = r["horas_lote"] / r["lote_un"]
        maquina_un = horas_un * MAQUINA_HORA

    if r["custo_legado"] is not None:
        custo_direto = r["custo_legado"] * r["unidades"]
    elif custo_fil is not None:
        custo_direto = (custo_fil + EMBALAGEM_UN) * r["unidades"]
    else:
        custo_direto = None
    if custo_direto is not None and r["custo_extra"]:
        custo_direto += r["custo_extra"]
    if custo_direto is not None and r["pendente"]:
        custo_direto = None

    machine = maquina_un * r["unidades"] if maquina_un is not None else None
    custo_total = (
        custo_direto + machine if custo_direto is not None and machine is not None else custo_direto
    )

    def margens(preco_shopee: float | None, preco_tiktok: float | None) -> dict:
        vazio = {
            "comissao": None, "servico": None, "lucro_direto": None,
            "margem_direta": None, "lucro_total": None, "margem_total": None,
            "tt_comissao": None, "tt_sfp": None, "tt_fixo": None,
            "tt_lucro_direto": None, "tt_margem_direta": None,
            "tt_lucro_total": None, "tt_margem_total": None,
        }
        if custo_direto is None:
            return vazio
        base = custo_total if custo_total is not None else custo_direto

        if preco_shopee is not None:
            comissao = SHOPEE_COMISSAO * preco_shopee
            servico = SHOPEE_FIXO + SHOPEE_SERVICO_PCT * preco_shopee
            lucro_direto = preco_shopee - comissao - servico - custo_direto
            lucro_total = preco_shopee - comissao - servico - base
            vazio.update({
                "comissao": comissao, "servico": servico,
                "lucro_direto": lucro_direto,
                "margem_direta": lucro_direto / preco_shopee,
                "lucro_total": lucro_total,
                "margem_total": lucro_total / preco_shopee,
            })

        if preco_tiktok is not None:
            tt_comissao = TIKTOK_COMISSAO * preco_tiktok
            tt_sfp = TIKTOK_SFP * preco_tiktok
            tt_fixo = TIKTOK_FIXO  # uma taxa por item vendido (o kit é 1 item)
            tt_lucro_direto = preco_tiktok - tt_comissao - tt_sfp - tt_fixo - custo_direto
            tt_lucro_total = preco_tiktok - tt_comissao - tt_sfp - tt_fixo - base
            vazio.update({
                "tt_comissao": tt_comissao, "tt_sfp": tt_sfp, "tt_fixo": tt_fixo,
                "tt_lucro_direto": tt_lucro_direto,
                "tt_margem_direta": tt_lucro_direto / preco_tiktok,
                "tt_lucro_total": tt_lucro_total,
                "tt_margem_total": tt_lucro_total / preco_tiktok,
            })
        return vazio

    r.update(
        {
            "peso_un": peso_un,
            "horas_un": horas_un,
            "custo_fil": custo_fil,
            "maquina_un": maquina_un,
            "custo_direto": custo_direto,
            "custo_total": custo_total,
            **margens(r["preco_shopee"], r["preco_tiktok"]),
        }
    )
    return r


def linhas_custos(itens: list[dict]) -> tuple[list[list], dict[int, str]]:
    cabecalho = [
        "SKU", "Produto", "Linha", "Status",
        "Un/lote", "Peso lote (g)", "Tempo lote (h)", "Peso/un (g)", "Tempo/un (h)",
        "Filamento (R$/kg)", "Custo filamento/un", "Embalagem/un", "Custo direto/un",
        "Máquina (R$/h)", "Custo máquina/un", "Custo total/un",
        "Preço direto", "Preço consignação", "Preço Shopee", "Preço TikTok",
        "Comissão Shopee (18%)", "Serviço Shopee (R$4 + 2%)",
        "Lucro Shopee (direto)", "Margem Shopee (direto)",
        "Lucro Shopee (c/ máquina)", "Margem Shopee (c/ máquina)",
        "Comissão TikTok (10%)", "SFP TikTok (6%)", "Fixo TikTok (R$4/un)",
        "Lucro TikTok (direto)", "Margem TikTok (direto)",
        "Lucro TikTok (c/ máquina)", "Margem TikTok (c/ máquina)",
        "Observações",
    ]
    linhas = [cabecalho]
    for r in itens:
        c = calcular(r)
        linhas.append(
            [
                c["sku"], c["nome"], c["linha"], c["status"],
                c["lote_un"] or (c["unidades"] if c["unidades"] > 1 else ""),
                c["peso_lote_g"] or "",
                round(c["horas_lote"], 2) if c["horas_lote"] else "",
                round(c["peso_un"], 2) if c["peso_un"] else "",
                round(c["horas_un"], 3) if c["horas_un"] else "",
                FILAMENTO_KG if c["peso_un"] else "",
                round(c["custo_fil"], 2) if c["custo_fil"] else "",
                EMBALAGEM_UN if c["custo_direto"] is not None else "",
                round(c["custo_direto"], 2) if c["custo_direto"] is not None else "a confirmar",
                MAQUINA_HORA if c["horas_un"] else "",
                round(c["maquina_un"], 2) if c["maquina_un"] is not None else "",
                round(c["custo_total"], 2) if c["custo_total"] is not None else "a confirmar",
                c["preco_direto"], c["preco_consig"], c["preco_shopee"], c["preco_tiktok"],
                round(c["comissao"], 2) if c["comissao"] is not None else "",
                round(c["servico"], 2) if c["servico"] is not None else "",
                round(c["lucro_direto"], 2) if c["lucro_direto"] is not None else "",
                c["margem_direta"],
                round(c["lucro_total"], 2) if c["lucro_total"] is not None else "",
                c["margem_total"],
                round(c["tt_comissao"], 2) if c["tt_comissao"] is not None else "",
                round(c["tt_sfp"], 2) if c["tt_sfp"] is not None else "",
                round(c["tt_fixo"], 2) if c["tt_fixo"] is not None else "",
                round(c["tt_lucro_direto"], 2) if c["tt_lucro_direto"] is not None else "",
                c["tt_margem_direta"],
                round(c["tt_lucro_total"], 2) if c["tt_lucro_total"] is not None else "",
                c["tt_margem_total"],
                c["obs"],
            ]
        )
    formatos = {
        4: "inteiro", 5: "numero", 6: "numero", 7: "numero", 8: "numero",
        9: "moeda", 10: "moeda", 11: "moeda", 12: "moeda", 13: "moeda",
        14: "moeda", 15: "moeda", 16: "moeda", 17: "moeda", 18: "moeda",
        19: "moeda", 20: "moeda", 21: "moeda", 22: "moeda", 23: "pct",
        24: "moeda", 25: "pct", 26: "moeda", 27: "moeda", 28: "moeda",
        29: "moeda", 30: "pct", 31: "moeda", 32: "pct",
    }
    return linhas, formatos


def vendas_shopee() -> tuple[list[list], dict]:
    linhas = [["SKU", "Produto", "Qtd", "Receita (subtotal)", "Comissão", "Serviço",
               "Custo direto", "Margem Shopee", "Margem %", "Pedidos"]]
    if not SHOPEE_EXPORT.exists():
        return linhas, {"aviso": "export Shopee não encontrado"}
    tabela = ler_tabela(SHOPEE_EXPORT)
    agregado: dict[str, dict] = {}

    def custo_unitario(sku: str) -> float | None:
        s = sku.lower()
        if "tubo hermetico" in s or "tubete" in s:
            return (66 / 8 / 1000 * FILAMENTO_KG) + EMBALAGEM_UN
        if "banquinho" in s and "seda" not in s:
            return (15 / 3 / 1000 * FILAMENTO_KG) + EMBALAGEM_UN
        return None

    def f(x):
        valor = parse_valor(x)
        return float(valor) if valor is not None else 0.0

    for l in tabela.linhas:
        if l.get("Status do pedido") != "Concluído":
            continue
        devolucao = (l.get("Status da Devolução / Reembolso") or "").lower()
        if "aprovad" in devolucao:
            continue
        sku = l.get("Número de referência SKU") or "SEM-SKU"
        receita = f(l.get("Subtotal do produto"))
        comissao = f(l.get("Taxa de comissão líquida"))
        servico = f(l.get("Taxa de serviço líquida"))
        qtd = int(f(l.get("Quantidade") or 0))
        reg = agregado.setdefault(
            sku,
            {"nome": l.get("Nome do Produto") or "", "qtd": 0, "receita": 0.0,
             "comissao": 0.0, "servico": 0.0, "pedidos": 0},
        )
        reg["qtd"] += qtd
        reg["receita"] += receita
        reg["comissao"] += comissao
        reg["servico"] += servico
        reg["pedidos"] += 1

    total = {"receita": 0.0, "comissao": 0.0, "servico": 0.0, "custo": 0.0}
    for sku, reg in sorted(agregado.items(), key=lambda kv: -kv[1]["receita"]):
        custo_un = custo_unitario(sku)
        custo = custo_un * reg["qtd"] if custo_un is not None else None
        margem = reg["receita"] - reg["comissao"] - reg["servico"] - (custo or 0)
        margem_pct = margem / reg["receita"] if reg["receita"] else None
        total["receita"] += reg["receita"]
        total["comissao"] += reg["comissao"]
        total["servico"] += reg["servico"]
        total["custo"] += custo or 0
        linhas.append([
            sku, reg["nome"][:80], reg["qtd"], round(reg["receita"], 2),
            round(reg["comissao"], 2), round(reg["servico"], 2),
            round(custo, 2) if custo is not None else "a confirmar",
            round(margem, 2), margem_pct, reg["pedidos"],
        ])
    margem_total = total["receita"] - total["comissao"] - total["servico"] - total["custo"]
    linhas.append([
        "TOTAL", "", "", round(total["receita"], 2), round(total["comissao"], 2),
        round(total["servico"], 2), round(total["custo"], 2), round(margem_total, 2),
        margem_total / total["receita"] if total["receita"] else None, "",
    ])
    formatos = {2: "inteiro", 3: "moeda", 4: "moeda", 5: "moeda", 6: "moeda",
                7: "moeda", 8: "pct", 9: "inteiro"}
    return linhas, {"formatos": formatos, **total}


def vendas_tiktok() -> tuple[list[list], dict]:
    linhas = [["SKU", "Produto", "Pedidos", "Qtd", "Receita (subtotal)",
               "Comissão (10%)", "SFP (6%)", "Fixo (R$ 4/un)", "Custo direto",
               "Margem estimada", "Margem %", "Observação"]]
    if not TIKTOK_CSV.exists():
        return linhas, {"aviso": "CSV TikTok reconstruído não encontrado"}

    def custo_unitario(sku: str) -> float | None:
        s = sku.lower()
        tubete = (8.25 / 1000 * FILAMENTO_KG) + EMBALAGEM_UN
        bico = (10 / 1000 * FILAMENTO_KG) + EMBALAGEM_UN
        banquinho = (5 / 1000 * FILAMENTO_KG) + EMBALAGEM_UN
        if "tubo hermetico" in s or "tubete" in s:
            if "banquinho" in s:
                return 2 * tubete + banquinho + SEDA_UN
            return tubete
        if "aplicador" in s or "bico" in s or "kit" in s and "un" in s:
            return bico
        if "banquinho" in s and "seda" in s:
            return banquinho + SEDA_UN
        if "kit completo" in s:
            return tubete + (53 / 4 / 1000 * FILAMENTO_KG + EMBALAGEM_UN) + SEDA_UN
        if "porta esqueiro" in s and "kit" in s:
            return (9 / 1000 * FILAMENTO_KG + EMBALAGEM_UN) + tubete
        if "porta esqueiro" in s:
            return 9 / 1000 * FILAMENTO_KG + EMBALAGEM_UN
        return None

    agregado: dict[str, dict] = {}
    status: dict[str, int] = {}
    total = {"receita": 0.0, "comissao": 0.0, "sfp": 0.0, "fixo": 0.0, "custo": 0.0}
    with TIKTOK_CSV.open(encoding="utf-8-sig") as fh:
        for linha in csv.DictReader(fh, delimiter=";"):
            status[linha["status"]] = status.get(linha["status"], 0) + 1
            if "cancel" in linha["status"].lower():
                continue
            sku = linha["sku"] or "SEM-SKU"
            qtd = int(linha["quantidade"] or 1)
            receita = float(linha["itens_total"].replace(".", "").replace(",", "."))
            reg = agregado.setdefault(
                sku, {"nome": linha["produto"], "pedidos": 0, "qtd": 0, "receita": 0.0}
            )
            reg["pedidos"] += 1
            reg["qtd"] += qtd
            reg["receita"] += receita

    for sku, reg in sorted(agregado.items(), key=lambda kv: -kv[1]["receita"]):
        comissao = TIKTOK_COMISSAO * reg["receita"]
        sfp = TIKTOK_SFP * reg["receita"]
        fixo = TIKTOK_FIXO * reg["qtd"]
        custo_un = custo_unitario(sku)
        custo = custo_un * reg["qtd"] if custo_un is not None else None
        margem = reg["receita"] - comissao - sfp - fixo - (custo or 0)
        margem_pct = margem / reg["receita"] if reg["receita"] else None
        total["receita"] += reg["receita"]
        total["comissao"] += comissao
        total["sfp"] += sfp
        total["fixo"] += fixo
        total["custo"] += custo or 0
        linhas.append([
            sku, reg["nome"][:70], reg["pedidos"], reg["qtd"], round(reg["receita"], 2),
            round(comissao, 2), round(sfp, 2), round(fixo, 2),
            round(custo, 2) if custo is not None else "a confirmar",
            round(margem, 2), margem_pct,
            "estimativa pela tela de liquidação (10% + 6% + R$ 4/item)" if custo is not None
            else "sem custo cadastrado para o SKU",
        ])
    margem_total = (total["receita"] - total["comissao"] - total["sfp"]
                    - total["fixo"] - total["custo"])
    linhas.append(["TOTAL", "", sum(r["pedidos"] for r in agregado.values()),
                   sum(r["qtd"] for r in agregado.values()), round(total["receita"], 2),
                   round(total["comissao"], 2), round(total["sfp"], 2),
                   round(total["fixo"], 2), round(total["custo"], 2),
                   round(margem_total, 2),
                   margem_total / total["receita"] if total["receita"] else None, ""])
    formatos = {2: "inteiro", 3: "inteiro", 4: "moeda", 5: "moeda", 6: "moeda",
                7: "moeda", 8: "moeda", 9: "moeda", 10: "pct"}
    return linhas, {"formatos": formatos, "status": status, "receita": total["receita"]}


def tarifas_tiktok() -> list[list]:
    return [
        ["Item", "Valor no exemplo (R$)", "Regra / observação"],
        ["Subtotal do item (antes do desconto)", 49.90, "preço cheio do anúncio"],
        ["Desconto financiado pelo vendedor", -34.00, "promoção do vendedor"],
        ["Vendas líquidas estimadas", 15.90, "subtotal - desconto do vendedor"],
        ["Custo do frete", -6.02, "coberto pelo TikTok Shop no exemplo"],
        ["Frete coberto pelo TikTok Shop", 6.02, "vendedor não paga"],
        ["Comissão da plataforma (10%)", -1.59, "10% das vendas líquidas"],
        ["SFP - taxa de serviço (6%)", -0.95, "6% das vendas líquidas"],
        ["Taxa por item vendido", -4.00, "R$ 4,00 por item"],
        ["Total de taxas estimadas", -6.54, "10% + 6% + R$ 4,00"],
        ["Valor total a ser liquidado", 9.36, "vendas líquidas - taxas"],
        ["", "", ""],
        ["Pedido de referência", "586752000250119957", "print de 27/10/2026 (SKU: 1 tubo hermetico rosa)"],
        ["Regra usada na planilha", "16% + R$ 4,00 por item", "frete zero quando coberto pela plataforma"],
    ]


def capacidade() -> list[list]:
    linhas = [["Item", "Un/lote", "Tempo lote (h)", "Un/h", "Un/dia (8h)",
               "Un/semana (8h x 6d)", "Un/dia (12h)", "Un/semana (12h x 6d)",
               "Un/semana (24h x 7d)", "Observação"]]
    dados = [
        ("Tubete", 8, 6 + 55 / 60, "prioridade Mocozim"),
        ("Porta Bic Hello Kit", 4, 3 + 40 / 60, "lote de 4 peças"),
        ("Banquinho (par)", 3, 50 / 60, "lote de 3 pares"),
        ("Porta Bic Espiral", 1, 1 + 10 / 60, "peça única"),
        ("Bico PU EasyPU", 4, 3 + 10 / 60, "lote de 4 peças / 40 g"),
    ]
    for nome, lote, horas, obs in dados:
        un_h = lote / horas
        linhas.append([
            nome, lote, round(horas, 2), round(un_h, 2),
            round(un_h * 8, 1), round(un_h * 8 * 6, 0),
            round(un_h * 12, 1), round(un_h * 12 * 6, 0),
            round(un_h * 24 * 7, 0), obs,
        ])
    linhas.append([])
    linhas.append(["Premissa: 1 impressora, com prioridade para Mocozim; 3D Print Franca usa a mesma máquina."])
    linhas.append(["Capacidade real depende de horas ligadas/dia, falhas e acabamento; use as colunas como cenário."])
    linhas.append(["Tubete: 1,16 un/h -> ~9 un/dia em 8h; ~55 un/semana em 8h x 6 dias; ~194 un/semana em 24h x 7 dias."])
    return linhas


def premissas() -> list[list]:
    return [
        ["Premissa", "Valor", "Fonte / observação"],
        ["Filamento PETG", "R$ 64,00/kg (faixa 59-69)", "compras em promoção no TikTok; usar 64 como média"],
        ["Embalagem", "R$ 0,50/un", "aba Custos da planilha Google"],
        ["Máquina (estimativa)", "R$ 0,55/h", f"energia {ENERGIA_KWH:.2f}/kWh + depreciação + manutenção"],
        ["Energia", f"R$ {ENERGIA_KWH:.2f}/kWh", "premissa; ajustar pela conta de luz"],
        ["Impressora", f"R$ {IMPRESSORA_PRECO:,.2f} / {IMPRESSORA_VIDA_H} h", "premissa de vida útil (3 anos x 2.400 h/ano)"],
        ["Manutenção", f"R$ {MANUTENCAO_H:.4f}/h", "bicos, mesa, lubrificante (~R$ 150/ano)"],
        ["Comissão Shopee", "18%", "observado no export Shopee de set/26"],
        ["Serviço Shopee", "R$ 4,00 + 2% por item", "observado no export Shopee de set/26"],
        ["Frete Shopee", "não incluído", "export mistura subsídio da plataforma e vendedor; conciliar extrato"],
        ["Comissão TikTok", "10%", "tela de liquidação de 27/10/2026"],
        ["SFP TikTok", "6%", "tela de liquidação de 27/10/2026"],
        ["Taxa por item TikTok", "R$ 4,00", "tela de liquidação de 27/10/2026"],
        ["Frete TikTok", "R$ 0,00", "no exemplo o frete foi coberto pelo TikTok Shop; conferir caso a caso"],
        ["Seda", "R$ 1,00/livreto", "pacote em promoção; usar como custo extra do banquinho com seda"],
        ["Mão de obra", "não incluída", "adicionar na coluna de custo extra se houver"],
        ["Acabamento do tubete", "não há", "sai da máquina pronto (informado em 27/10/2026)"],
        ["Máquina no custo por peça", "opcional", "pode ir para despesa mensal em vez do custo unitário"],
        ["Bico PU EasyPU", "4 peças / 40 g / 3h10", "10 g e 47,5 min por unidade (informado em 27/10/2026)"],
    ]


def custos_fixos() -> list[list]:
    maquina_mes = 176 * MAQUINA_HORA
    return [
        ["Item", "Valor mensal (R$)", "Observação"],
        ["Máquina (176 h/mês x R$ 0,55)", round(maquina_mes, 2), "cenário 8 h/dia x 22 dias; ajustar às horas reais"],
        ["UpSeller", 149.00, "plano Inicial, quando assinar"],
        ["Licenciamento digital (3x)", 33.00, "lançamento no Set/Out26"],
        ["Shopee Ads", 0.00, "variável; lançar o valor real do mês"],
        ["Impostos", None, "a definir (MEI/DAS/Simples)"],
        ["Embalagem", None, "variável: R$ 0,50/un"],
        ["Total parcial (sem Ads/impostos)", round(149 + 33 + maquina_mes, 2), "referência de custo fixo mensal"],
    ]


def skus_marketplace() -> list[list]:
    return [
        ["SKU no canal", "Canal", "Produto no canal", "SKU canônico", "Custo usado", "Preço médio", "Observação"],
        ["1 tubo hermetico preto", "Shopee/TikTok", "Tubete Mocozim", "TUBETE-PRETO", 1.24, 15.90, "cores"],
        ["1 tubo hermetico rosa", "Shopee/TikTok", "Tubete Mocozim", "TUBETE-ROSA", 1.24, 15.90, "cores"],
        ["1 tubo hermetico cinza", "Shopee/TikTok", "Tubete Mocozim", "TUBETE-CINZA", 1.24, 15.90, "cores"],
        ["TUBETE PRETO", "Shopee", "Tubete Mocozim", "TUBETE-PRETO", 1.24, 15.89, ""],
        ["TUBETE ROSA", "Shopee", "Tubete Mocozim", "TUBETE-ROSA", 1.24, 15.89, ""],
        ["TUBETE CINZA", "Shopee", "Tubete Mocozim", "TUBETE-CINZA", 1.24, 15.90, ""],
        ["banquinho com seda", "Shopee/TikTok", "Banquinho com seda", "BANQUINHO-SEDA", 1.82, 10.90, "seda R$ 1,00"],
        ["banquinho com seda+2 tub preto", "Shopee/TikTok", "Combo banquinho + 2 tubetes", "COMBO-2TUB-BANQUINHO", 3.88, 35.90, "2 tubetes + banquinho + seda"],
        ["banquinho com seda+2 tub cinza", "TikTok", "Combo banquinho + 2 tubetes", "COMBO-2TUB-BANQUINHO", 3.88, 35.90, "2 tubetes + banquinho + seda"],
        ["kit só porta esqueiro + tubete", "TikTok", "Combo porta esqueiro + tubete", "COMBO-PORTA-BIC-TUBETE", 2.10, 29.90, ""],
        ["1 porta esqueiro", "TikTok", "Porta Bic Espiral", "PORTA-BIC-ESPIRAL", 1.08, 17.90, ""],
        ["Aplicador de PU 1 UN", "Shopee/TikTok", "Bico EasyPU 1 un", "BICO-PU-1UN", 1.14, 19.90, ""],
        ["Aplicador de PU 2 UN", "Shopee", "Bico EasyPU 2 un", "BICO-PU-KIT2", 2.28, 34.90, ""],
        ["Aplicador de PU 3 UN", "Shopee", "Bico EasyPU 3 un", "BICO-PU-KIT3", 3.42, 49.90, ""],
        ["KIT 2 UN", "Shopee", "Kit 2 bicos EasyPU", "BICO-PU-KIT2", 2.28, 34.90, ""],
        ["KIT 3 UN", "Shopee", "Kit 3 bicos EasyPU", "BICO-PU-KIT3", 3.42, 49.90, ""],
        ["1 UN", "Shopee", "Bico EasyPU 1 un", "BICO-PU-1UN", 1.14, 19.90, ""],
        ["kit completo", "TikTok", "Kit Organizador Feminino", "KIT-FEMININO", 3.38, 33.13, "estimativa"],
        ["auto:kit_2_unidades_aplicador_de_pu...", "Shopee", "Bico EasyPU 2 un", "BICO-PU-KIT2", None, 34.90, "SKU vazio no export"],
        ["auto:kit_organizador_3d_feminino...", "TikTok", "Kit Organizador Feminino", "KIT-FEMININO", None, 15.90, "SKU vazio no export"],
    ]


def main() -> int:
    itens = [
        item("TUBETE", "Tubete Mocozim PETG (unidade)", "Mocozim", "Ativo",
             lote_un=8, peso_lote_g=66, horas_lote=6 + 55 / 60,
             preco_direto=15.00, preco_consig=11.00, preco_shopee=15.90, preco_tiktok=15.90,
             obs="Cores: rosa/preto/cinza; sem acabamento; máquina pode ir para despesa mensal"),
        item("KIT-TUBETE-2", "Kit 2 tubetes Mocozim", "Mocozim", "Ativo",
             lote_un=2, peso_lote_g=2 * 8.25, horas_lote=2 * (6 + 55 / 60) / 8,
             unidades=2, preco_shopee=29.90, obs="2 tubetes + embalagem do kit"),
        item("KIT-TUBETE-3", "Kit 3 tubetes Mocozim", "Mocozim", "Ativo",
             lote_un=3, peso_lote_g=3 * 8.25, horas_lote=3 * (6 + 55 / 60) / 8,
             unidades=3, preco_shopee=39.90, obs="3 tubetes + embalagem do kit"),
        item("KIT-TUBETE-10", "Kit 10 tubetes Mocozim", "Mocozim", "Ativo",
             lote_un=10, peso_lote_g=10 * 8.25, horas_lote=10 * (6 + 55 / 60) / 8,
             unidades=10, preco_shopee=95.00, obs="10 tubetes + embalagem do kit"),
        item("BANQUINHO", "Banquinho (par)", "Mocozim", "Ativo",
             lote_un=3, peso_lote_g=15, horas_lote=50 / 60,
             preco_shopee=10.90, obs="lote de 3 pares; sem seda"),
        item("BANQUINHO-SEDA", "Banquinho com seda", "Mocozim", "Ativo",
             lote_un=3, peso_lote_g=15, horas_lote=50 / 60,
             custo_extra=SEDA_UN, preco_shopee=10.90, preco_tiktok=10.90,
             obs="seda ~R$ 1,00 o livreto (pacote em promoção)"),
        item("COMBO-TUBO-BANQUINHO", "Combo tubete + banquinho (+ seda)", "Mocozim", "Ativo",
             lote_un=2, peso_lote_g=8.25 + 5, horas_lote=(6 + 55 / 60) / 8 + 50 / 60 / 3,
             unidades=2, preco_shopee=31.80, obs="custo = tubete + banquinho; seda a confirmar"),
        item("COMBO-2TUB-BANQUINHO", "Combo 2 tubetes + banquinho (+ seda)", "Mocozim", "Ativo",
             lote_un=3, peso_lote_g=2 * 8.25 + 5, horas_lote=2 * (6 + 55 / 60) / 8 + 50 / 60 / 3,
             unidades=3, preco_shopee=35.90, obs="custo = 2 tubetes + banquinho; seda a confirmar"),
        item("PORTA-BIC-ESPIRAL", "Porta Bic Espiral (unidade)", "Mocozim", "Ativo",
             lote_un=1, peso_lote_g=9, horas_lote=1 + 10 / 60,
             obs="vendido só no kit com tubete (R$ 29,90); ainda sem venda e fora da Shopee"),
        item("COMBO-PORTA-BIC-TUBETE", "Combo porta esqueiro + tubete", "Mocozim", "Ativo",
             lote_un=2, peso_lote_g=9 + 8.25, horas_lote=(1 + 10 / 60) + (6 + 55 / 60) / 8,
             unidades=2, preco_tiktok=29.90,
             obs="kit porta esqueiro + tubete a R$ 29,90; ainda sem vendas"),
        item("PORTA-BIC-FEMININO", "Porta Bic (modelo feminino)", "Mocozim", "Ativo",
             lote_un=4, peso_lote_g=53, horas_lote=3 + 40 / 60,
             obs="⚠️ modelo inspirado em personagem de terceiro: anunciar só sem marca e, de preferência, redesenhar"),
        item("BICO-PU-1UN", "Bico Aplicador PU EasyPU (1 un)", "EasyPU", "Ativo",
             lote_un=4, peso_lote_g=40, horas_lote=3 + 10 / 60,
             preco_shopee=19.90, preco_tiktok=19.90,
             obs="4 peças / 40 g / 3h10; por unidade 10 g / 47,5 min"),
        item("BICO-PU-KIT2", "Kit 2 bicos PU EasyPU", "EasyPU", "Ativo",
             lote_un=4, peso_lote_g=40, horas_lote=3 + 10 / 60, unidades=2,
             preco_shopee=34.90, preco_tiktok=34.90, obs="2 x custo unitário do bico"),
        item("BICO-PU-KIT3", "Kit 3 bicos PU EasyPU", "EasyPU", "Ativo",
             lote_un=4, peso_lote_g=40, horas_lote=3 + 10 / 60, unidades=3,
             preco_shopee=49.90, preco_tiktok=49.90, obs="3 x custo unitário do bico"),
        item("KIT-FEMININO", "Kit Organizador Feminino 3D (TikTok)", "Mocozim", "Ativo",
             lote_un=2, peso_lote_g=8.25 + 53 / 4, horas_lote=(6 + 55 / 60) / 8 + (3 + 40 / 60) / 4,
             unidades=2, custo_extra=SEDA_UN, preco_tiktok=31.80,
             obs="estimativa: tubete + porta feminino + seda; revisar composição e risco de marca"),
        item("CUBO-INFINITO", "Cubo Infinito PETG (legado)", "3D Print Franca", "Descontinuado",
             custo_legado=5.00, preco_direto=15.00, obs="pedido pontual/descontinuado"),
        item("CHV-CORINTHIANS", "Chaveiro Corinthians (legado)", "3D Print Franca", "Descontinuado",
             custo_legado=8.00, preco_direto=15.00, obs="marca de terceiro; pedido único"),
        item("VAPE-V8", "Vape V8 PETG (legado)", "3D Print Franca", "Descontinuado",
             custo_legado=10.00, preco_direto=40.00, obs="restrição em marketplace; descontinuado"),
    ]

    linhas, formatos = linhas_custos(itens)
    v_shopee, meta_shopee = vendas_shopee()
    v_tiktok, meta_tiktok = vendas_tiktok()

    SAIDA.mkdir(parents=True, exist_ok=True)
    caminho_xlsx = SAIDA / "Custos_Mocozim_3DPrintFranca_2026-10.xlsx"
    escrever_xlsx(
        caminho_xlsx,
        [
            {"nome": "Custos_Itens", "linhas": linhas, "formatos": formatos,
             "larguras": [17, 38, 15, 13, 8, 11, 11, 10, 10, 12, 13, 11, 12, 10, 12, 12,
                          11, 13, 12, 11, 12, 14, 12, 12, 12, 12,
                          12, 11, 13, 12, 12, 12, 12, 45]},
            {"nome": "Premissas", "linhas": premissas(), "larguras": [26, 28, 70]},
            {"nome": "Custos_Fixos", "linhas": custos_fixos(), "formatos": {1: "moeda"},
             "larguras": [34, 16, 60]},
            {"nome": "Capacidade", "linhas": capacidade(),
             "formatos": {1: "numero", 2: "numero", 3: "numero", 4: "numero", 5: "numero",
                          6: "numero", 7: "numero", 8: "numero"},
             "larguras": [24, 9, 12, 9, 12, 16, 12, 16, 16, 45]},
            {"nome": "Vendas_Shopee_Set26", "linhas": v_shopee,
             "formatos": {2: "inteiro", 3: "moeda", 4: "moeda", 5: "moeda", 6: "moeda",
                          7: "moeda", 8: "pct", 9: "inteiro"},
             "larguras": [24, 58, 7, 14, 12, 12, 13, 14, 10, 9]},
            {"nome": "Vendas_TikTok_Out26", "linhas": v_tiktok,
             "formatos": {2: "inteiro", 3: "inteiro", 4: "moeda", 5: "moeda", 6: "moeda",
                          7: "moeda", 8: "moeda", 9: "moeda", 10: "pct"},
             "larguras": [22, 52, 7, 6, 14, 11, 10, 11, 12, 13, 9, 44]},
            {"nome": "Tarifas_TikTok", "linhas": tarifas_tiktok(),
             "formatos": {1: "moeda"}, "larguras": [38, 22, 60]},
            {"nome": "SKUs_Marketplace", "linhas": skus_marketplace(),
             "formatos": {4: "moeda", 5: "moeda"},
             "larguras": [34, 13, 32, 22, 12, 12, 28]},
        ],
        titulo="Custos Mocozim / 3D Print Franca",
    )

    # CSV principal + CSV de importação
    with (SAIDA / "custos_itens.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        escritor = csv.writer(fh, delimiter=";")
        escritor.writerows(linhas)

    categorias = {"Mocozim": "mocozim", "EasyPU": "easypu",
                  "3D Print Franca": "3dprintfranca"}
    with (SAIDA / "custos_para_importar.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        escritor = csv.writer(fh, delimiter=";")
        escritor.writerow(["sku", "produto", "custo_unitario", "preco_venda", "categoria"])
        for r in itens:
            c = calcular(r)
            custo = c["custo_direto"]
            preco = r["preco_shopee"] or r["preco_tiktok"] or r["preco_direto"]
            if custo is None and preco is None:
                continue
            escritor.writerow([
                r["sku"], r["nome"],
                f"{custo:.2f}".replace(".", ",") if custo is not None else "",
                f"{preco:.2f}".replace(".", ",") if preco is not None else "",
                categorias.get(r["linha"], "outros"),
            ])
            # variacoes de cor do tubete compartilham o mesmo custo
            if r["sku"] == "TUBETE":
                for variacao, nome_cor in (
                    ("TUBETE-ROSA", "Tubete Mocozim PETG Rosa"),
                    ("TUBETE-PRETO", "Tubete Mocozim PETG Preto"),
                    ("TUBETE-CINZA", "Tubete Mocozim PETG Cinza"),
                ):
                    escritor.writerow([
                        variacao, nome_cor,
                        f"{custo:.2f}".replace(".", ",") if custo is not None else "",
                        "15,90", "mocozim",
                    ])

    # SKUs de marketplace para importar (custo conhecido quando houver)
    with (SAIDA / "skus_marketplace.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        escritor = csv.writer(fh, delimiter=";")
        escritor.writerow(["sku", "produto", "custo_unitario", "preco_venda", "categoria"])
        for linha in skus_marketplace()[1:]:
            sku_canal, _, produto, _canonico, custo, preco, _obs = linha[:7]
            if sku_canal.startswith("auto:"):
                continue
            escritor.writerow([
                sku_canal, produto,
                f"{custo:.2f}".replace(".", ",") if custo is not None else "",
                f"{preco:.2f}".replace(".", ",") if preco is not None else "",
                "mocozim" if "tub" in produto.lower() or "banquinho" in produto.lower() else "easypu",
            ])

    # markdown resumo
    md = ["# Custos padronizados — Mocozim / 3D Print Franca (out/2026)", ""]
    md.append(f"Planilha: `{caminho_xlsx.relative_to(RAIZ)}`")
    md.append("")
    md.append("## Premissas")
    for linha in premissas()[1:]:
        md.append(f"- **{linha[0]}**: {linha[1]} — {linha[2]}")
    md.append("")
    md.append("## Custos por item")
    md.append("| SKU | Item | Custo direto | Custo c/ máquina | Preço Shopee | Margem Shopee | Margem TikTok |")
    md.append("|---|---|---:|---:|---:|---:|---:|")
    for r in itens:
        c = calcular(r)
        custo = brl(c["custo_direto"]) if c["custo_direto"] is not None else "a confirmar"
        total = brl(c["custo_total"]) if c["custo_total"] is not None else "a confirmar"
        preco = brl(r["preco_shopee"] or r["preco_tiktok"]) if (r["preco_shopee"] or r["preco_tiktok"]) else "-"
        margem = f"{c['margem_direta']*100:.1f}%" if c["margem_direta"] is not None else "-"
        margem_tt = f"{c['tt_margem_direta']*100:.1f}%" if c["tt_margem_direta"] is not None else "-"
        md.append(f"| {r['sku']} | {r['nome']} | {custo} | {total} | {preco} | {margem} | {margem_tt} |")
    md.append("")
    md.append("## Capacidade de produção (1 máquina)")
    md.append("| Item | Un/lote | Tempo lote | Un/h | Un/dia 8h | Un/semana 8h x 6 | Un/dia 12h | Un/semana 12h x 6 | Un/semana 24h x 7 |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for linha in capacidade()[1:6]:
        md.append("| " + " | ".join(str(x) for x in linha[:9]) + " |")
    md.append("")
    md.append("## Vendas Shopee set/26 (pedidos concluídos)")
    for linha in v_shopee[1:]:
        if linha[0] == "TOTAL":
            md.append(f"- **Total**: receita {brl(linha[3])}, comissão {brl(linha[4])}, "
                      f"serviço {brl(linha[5])}, margem {brl(linha[7])}")
    md.append("")
    md.append("## Pendências")
    md.append("- Peso/tempo de impressão do **bico PU EasyPU** (1/2/3 un) para calcular custo.")
    md.append("- Custo da **seda** (banquinho com seda) e composição do **kit feminino**.")
    md.append("- Preço de venda de **Porta Bic Espiral** e **Porta Bic Hello Kit** (este exige licença da marca).")
    md.append("- Confirmar preço pago do filamento (R$/kg) e horas ligadas/dia da máquina.")
    md.append("- Taxas do TikTok: export não traz comissão; conciliar no Seller Center.")
    path_md = SAIDA / "resumo_custos.md"
    path_md.write_text("\n".join(md), encoding="utf-8")

    print(f"XLSX: {caminho_xlsx}")
    print(f"CSV: {SAIDA / 'custos_itens.csv'}")
    print(f"CSV import: {SAIDA / 'custos_para_importar.csv'}")
    print(f"MD: {path_md}")
    print(f"Shopee: receita R$ {meta_shopee.get('receita', 0):.2f} | "
          f"comissão R$ {meta_shopee.get('comissao', 0):.2f} | "
          f"serviço R$ {meta_shopee.get('servico', 0):.2f}")
    print(f"TikTok: receita R$ {meta_tiktok.get('receita', 0):.2f} | status {meta_tiktok.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
