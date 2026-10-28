"""Margem por SKU e curva ABC.

As taxas do marketplace sao por pedido; aqui elas sao rateadas entre os itens
proporcionalmente a receita de cada item. Assim a margem por SKU ja desconta
comissao, frete, desconto e cupom — nao apenas o CMV.
"""

from __future__ import annotations

import sqlite3
from decimal import Decimal, ROUND_CEILING

from ..datas import fmt_mes, intervalo_mes, normalizar_mes
from ..dinheiro import fmt_brl, fmt_pct
from .consultas import periodo_dias, rotulo_periodo


def _arredondar_90(valor: Decimal) -> Decimal:
    """Arredonda para cima no proximo preco terminado em ,90."""
    base = valor.quantize(Decimal("1"), rounding=ROUND_CEILING)
    candidato = base - Decimal("0.10")
    if candidato < valor:
        candidato = base + Decimal("0.90")
    return candidato


def _ratear(total: int, peso: int, peso_total: int) -> int:
    if not peso_total:
        return 0
    return int(round(total * (peso / peso_total)))


def margem_por_sku(
    conn: sqlite3.Connection,
    mes: str | None = None,
    dias: int | None = None,
    limite: int | None = None,
    marketplace: str | None = None,
    margem_alvo: Decimal = Decimal("0.20"),
) -> dict:
    if dias:
        inicio_txt, fim_txt = periodo_dias(dias)
        rotulo = f"ultimos {dias} dias ({rotulo_periodo(inicio_txt, fim_txt)})"
        marcador_periodo = "dias"
    else:
        mes = normalizar_mes(mes) or _ultimo_mes(conn)
        inicio, fim = intervalo_mes(mes)
        inicio_txt, fim_txt = inicio.isoformat(), fim.isoformat()
        rotulo = fmt_mes(mes)
        marcador_periodo = "mes"

    sql = (
        "SELECT p.id, p.marketplace, p.pedido_externo, p.itens_total_centavos, "
        "p.desconto_centavos, p.frete_cobrado_centavos, p.frete_pago_centavos, "
        "p.comissao_centavos, p.taxa_servico_centavos, p.cupom_centavos, p.imposto_centavos "
        "FROM pedidos p WHERE p.situacao='aprovado' AND p.data_pedido BETWEEN ? AND ?"
    )
    parametros: list = [inicio_txt, fim_txt]
    if marketplace:
        sql += " AND p.marketplace = ?"
        parametros.append(marketplace)
    pedidos = list(conn.execute(sql, parametros))

    acumulado: dict[str, dict] = {}
    for pedido in pedidos:
        itens = list(
            conn.execute(
                "SELECT sku, nome_produto, quantidade, preco_unitario_centavos, "
                "custo_unitario_centavos FROM itens_pedido WHERE pedido_id = ?",
                (pedido["id"],),
            )
        )
        if not itens:
            continue
        receita_itens = sum(
            i["quantidade"] * i["preco_unitario_centavos"] for i in itens
        )
        receita_liquida_pedido = (
            receita_itens
            - pedido["desconto_centavos"]
            + pedido["frete_cobrado_centavos"]
            - pedido["frete_pago_centavos"]
            - pedido["comissao_centavos"]
            - pedido["taxa_servico_centavos"]
            - pedido["cupom_centavos"]
            - pedido["imposto_centavos"]
        )
        ajustes = receita_itens - receita_liquida_pedido

        for item in itens:
            sku = item["sku"]
            receita_item = item["quantidade"] * item["preco_unitario_centavos"]
            ajuste = _ratear(ajustes, receita_item, receita_itens)
            liquida_item = receita_item - ajuste
            custo_unit = item["custo_unitario_centavos"]
            cmv_item = (custo_unit or 0) * item["quantidade"]

            registro = acumulado.setdefault(
                sku,
                {
                    "sku": sku,
                    "nome": item["nome_produto"],
                    "unidades": 0,
                    "receita_bruta": 0,
                    "receita_liquida": 0,
                    "cmv": 0,
                    "pedidos": set(),
                    "custo_conhecido": True,
                    "soma_custo_unit": 0,
                    "soma_preco_unit": 0,
                    "unidades_custo": 0,
                },
            )
            registro["unidades"] += item["quantidade"]
            registro["receita_bruta"] += receita_item
            registro["receita_liquida"] += liquida_item
            registro["cmv"] += cmv_item
            registro["pedidos"].add(pedido["pedido_externo"])
            registro["soma_preco_unit"] += item["preco_unitario_centavos"] * item["quantidade"]
            if custo_unit is None:
                registro["custo_conhecido"] = False
            else:
                registro["soma_custo_unit"] += custo_unit * item["quantidade"]
                registro["unidades_custo"] += item["quantidade"]
            if not registro["nome"] and item["nome_produto"]:
                registro["nome"] = item["nome_produto"]

    linhas = []
    for registro in acumulado.values():
        unidades = max(1, registro["unidades"])
        margem = registro["receita_liquida"] - registro["cmv"]
        bruta = registro["receita_bruta"]
        taxa_pct = (bruta - registro["receita_liquida"]) / bruta if bruta else 0.0
        custo_medio = (
            registro["soma_custo_unit"] / registro["unidades_custo"]
            if registro["unidades_custo"]
            else None
        )
        preco_medio = registro["soma_preco_unit"] / unidades
        sugerido = None
        if custo_medio:
            denominador = Decimal("1") - Decimal(str(taxa_pct)) - margem_alvo
            if denominador > Decimal("0.02"):
                minimo = Decimal(custo_medio) / denominador
                sugerido = _arredondar_90(minimo)
        linhas.append(
            {
                "sku": registro["sku"],
                "nome": registro["nome"],
                "unidades": registro["unidades"],
                "pedidos": len(registro["pedidos"]),
                "receita_bruta_centavos": registro["receita_bruta"],
                "receita_liquida_centavos": registro["receita_liquida"],
                "cmv_centavos": registro["cmv"],
                "margem_centavos": margem,
                "margem_pct": margem / bruta if bruta else None,
                "taxas_pct": taxa_pct,
                "preco_medio_centavos": int(round(preco_medio)),
                "custo_medio_centavos": int(round(custo_medio)) if custo_medio else None,
                "custo_conhecido": registro["custo_conhecido"],
                "preco_sugerido_centavos": int(sugerido * 100) if sugerido else None,
            }
        )

    linhas.sort(key=lambda item: item["receita_bruta_centavos"], reverse=True)

    total_bruta = sum(item["receita_bruta_centavos"] for item in linhas)
    acumulado_pct = 0.0
    for item in linhas:
        acumulado_pct += (
            item["receita_bruta_centavos"] / total_bruta if total_bruta else 0.0
        )
        if acumulado_pct <= 0.80:
            item["classe_abc"] = "A"
        elif acumulado_pct <= 0.95:
            item["classe_abc"] = "B"
        else:
            item["classe_abc"] = "C"
        item["fmt"] = {
            "receita_bruta": fmt_brl(item["receita_bruta_centavos"]),
            "receita_liquida": fmt_brl(item["receita_liquida_centavos"]),
            "cmv": fmt_brl(item["cmv_centavos"]),
            "margem": fmt_brl(item["margem_centavos"]),
            "margem_pct": fmt_pct(item["margem_pct"]),
            "taxas_pct": fmt_pct(item["taxas_pct"]),
            "preco_medio": fmt_brl(item["preco_medio_centavos"]),
            "custo_medio": fmt_brl(item["custo_medio_centavos"]) if item["custo_medio_centavos"] else "-",
            "preco_sugerido": fmt_brl(item["preco_sugerido_centavos"]) if item["preco_sugerido_centavos"] else "-",
        }

    if limite:
        linhas = linhas[: int(limite)]

    negativas = [
        item["sku"]
        for item in linhas
        if item["custo_conhecido"] and (item["margem_centavos"] or 0) < 0
    ]
    sem_custo = [item["sku"] for item in linhas if not item["custo_conhecido"]]

    resposta = {
        "criterio": "margem de contribuicao por SKU (taxas rateadas por receita)",
        "periodo": rotulo,
        "periodo_tipo": marcador_periodo,
        "mes": mes,
        "marketplace": marketplace or "todos",
        "margem_alvo": fmt_pct(margem_alvo),
        "totais": {
            "skus": len(linhas),
            "unidades": sum(item["unidades"] for item in linhas),
            "receita_bruta": fmt_brl(total_bruta),
            "receita_bruta_centavos": total_bruta,
            "receita_liquida": fmt_brl(
                sum(item["receita_liquida_centavos"] for item in linhas)
            ),
            "cmv": fmt_brl(sum(item["cmv_centavos"] for item in linhas)),
            "margem": fmt_brl(sum(item["margem_centavos"] for item in linhas)),
        },
        "skus": linhas,
        "skus_margem_negativa": negativas,
        "skus_sem_custo": sem_custo,
        "observacoes": [
            "A margem ja desconta comissao, taxa de servico, frete, desconto e cupom, "
            "rateados proporcionalmente entre os itens do pedido.",
            "SKU sem custo cadastrado aparece com margem otimista; use "
            "'mkt custos definir SKU VALOR' para corrigir.",
        ],
    }
    if negativas:
        resposta.setdefault("avisos", []).append(
            f"{len(negativas)} SKU(s) com margem negativa no periodo: "
            + ", ".join(negativas[:10])
        )
    if sem_custo:
        resposta.setdefault("avisos", []).append(
            f"{len(sem_custo)} SKU(s) sem custo cadastrado — margem nao confiavel."
        )
    return resposta


def _ultimo_mes(conn: sqlite3.Connection) -> str:
    from ..datas import mes_atual
    from ..db import ultimo_mes_com_pedidos

    return ultimo_mes_com_pedidos(conn) or mes_atual()


__all__ = ["margem_por_sku"]
