"""Insights da loja: leitura sintetica dos numeros com acoes priorizadas.

Nao e um relatorio bruto: e a interpretacao que o dono da loja usa para decidir
(o que cresceu, o que concentra risco, onde a margem nao compensa, onde agir).
"""

from __future__ import annotations

import sqlite3
import statistics

from ..datas import fmt_mes, mes_atual, normalizar_mes
from ..db import ultimo_mes_com_pedidos
from ..dinheiro import fmt_brl, fmt_pct
from . import consultas
from .alertas import alertas as relatorio_alertas
from .caixa import fluxo_caixa
from .dre import comparativo, dre
from .margem import margem_por_sku


def _classe_matriz(margem_pct: float, unidades: int, mediana_margem: float, mediana_unidades: int) -> str:
    margem_alta = margem_pct >= mediana_margem
    volume_alto = unidades >= mediana_unidades
    if margem_alta and volume_alto:
        return "motor"  # margem boa + volume: proteger e escalar
    if margem_alta and not volume_alto:
        return "oportunidade"  # margem boa, pouca venda: investir em anuncio
    if not margem_alta and volume_alto:
        return "volume_que_segura"  # vende muito, margem baixa: revisar preco/custo
    return "revisar"  # pouca margem e pouca venda


def insights(conn: sqlite3.Connection, mes: str | None = None) -> dict:
    mes = normalizar_mes(mes) or ultimo_mes_com_pedidos(conn) or mes_atual()
    dados_dre = dre(conn, mes, incluir_por_marketplace=False)
    comp = comparativo(conn, mes)
    margens = margem_por_sku(conn, mes=mes)
    contagem = consultas.contar_por_situacao(conn, mes)

    skus = [item for item in margens["skus"] if item["unidades"] > 0]
    receita_total = sum(item["receita_bruta_centavos"] for item in skus) or 1
    top3 = sorted(skus, key=lambda item: item["receita_bruta_centavos"], reverse=True)[:3]
    top3_pct = sum(item["receita_bruta_centavos"] for item in top3) / receita_total
    classe_a = [item for item in skus if item["classe_abc"] == "A"]
    classe_a_pct = sum(item["receita_bruta_centavos"] for item in classe_a) / receita_total

    com_margem = [item for item in skus if item["margem_pct"] is not None]
    mediana_margem = statistics.median([item["margem_pct"] for item in com_margem]) if com_margem else 0.0
    mediana_unidades = statistics.median([item["unidades"] for item in skus]) if skus else 0
    matriz = []
    for item in skus:
        if item["margem_pct"] is None:
            continue
        matriz.append(
            {
                "sku": item["sku"],
                "nome": item["nome"],
                "classe": _classe_matriz(
                    item["margem_pct"], item["unidades"], mediana_margem, mediana_unidades
                ),
                "receita": item["fmt"]["receita_bruta"],
                "margem_pct": item["fmt"]["margem_pct"],
                "unidades": item["unidades"],
            }
        )

    cancelados = contagem.get("cancelado", 0) + contagem.get("devolvido", 0)
    total_pedidos = sum(contagem.values())
    taxa_cancelamento = cancelados / total_pedidos if total_pedidos else 0.0
    gasto_marketing = sum(
        int(despesa["total"] or 0)
        for despesa in consultas.despesas_do_mes(conn, mes)
        if (despesa["categoria"] or "") == "marketing"
    )
    marketing_pct = gasto_marketing / dados_dre["receita_bruta_centavos"] if dados_dre["receita_bruta_centavos"] else 0.0

    caixa = fluxo_caixa(conn, 30)
    alertas_calc = relatorio_alertas(conn)
    risco_estoque = [a for a in alertas_calc["alertas"] if "estoque" in a["titulo"].lower()]

    lista_insights: list[str] = []
    acoes: list[dict] = []

    variacao = comp.get("variacao_receita_pct")
    if comp.get("parcial"):
        lista_insights.append(
            "Mes em andamento (dados parciais): a comparacao de receita e MTD, com os "
            "mesmos dias do mes anterior. Insights de fechamento ficam completos no mes seguinte."
        )
    elif variacao is not None:
        if variacao > 0.05:
            lista_insights.append(
                f"Receita cresceu {fmt_pct(variacao)} vs {fmt_mes(comp['mes_anterior'])} "
                f"({comp['receita_bruta']} contra {comp['receita_bruta_anterior']})."
            )
        elif variacao < -0.05:
            lista_insights.append(
                f"Receita caiu {fmt_pct(abs(variacao))} vs {fmt_mes(comp['mes_anterior'])}. "
                "Vale separar efeito de volume (pedidos) de efeito de preco/ticket."
            )
            acoes.append(
                {
                    "prioridade": 1,
                    "acao": "Investigar a queda: comparar pedidos por dia, anuncios ativos e "
                    "ruptura de estoque dos SKUs A.",
                    "ferramenta": "margem_sku + listar_pedidos + estoque",
                }
            )

    if top3_pct > 0.6:
        lista_insights.append(
            f"Concentracao alta: os 3 principais SKUs respondem por {fmt_pct(top3_pct)} "
            f"da receita ({', '.join(i['sku'] for i in top3)})."
        )
        acoes.append(
            {
                "prioridade": 2,
                "acao": "Reduzir risco de concentracao: dar tracao a um SKU da classe B com "
                "margem acima da mediana (teste de anuncio + kit).",
                "ferramenta": "margem_sku",
            }
        )
    else:
        lista_insights.append(
            f"Receita distribuida: top 3 SKUs = {fmt_pct(top3_pct)}; classe A = {fmt_pct(classe_a_pct)}."
        )

    oportunidades = [item for item in matriz if item["classe"] == "oportunidade"]
    volume_baixo = [item for item in matriz if item["classe"] == "volume_que_segura"]
    revisar = [item for item in matriz if item["classe"] == "revisar"]
    if volume_baixo:
        lista_insights.append(
            "Vendem bem mas com margem abaixo da mediana: "
            + ", ".join(f"{item['sku']} ({item['margem_pct']})" for item in volume_baixo[:4])
            + ". Cada ponto de margem aqui tem impacto grande na receita."
        )
        acoes.append(
            {
                "prioridade": 1,
                "acao": "Renegociar custo/frete ou subir preco dos SKUs de volume com margem baixa "
                "(use o preco sugerido da ferramenta de margem).",
                "ferramenta": "margem_sku",
            }
        )
    if oportunidades:
        lista_insights.append(
            "Margem boa mas pouco volume (candidatos a impulsionar): "
            + ", ".join(f"{item['sku']} ({item['margem_pct']})" for item in oportunidades[:4])
            + "."
        )
        acoes.append(
            {
                "prioridade": 3,
                "acao": "Testar anuncio/cupom nos SKUs de margem alta com pouco volume; "
                "acompanhar receita por 14 dias.",
                "ferramenta": "margem_sku + comparativo",
            }
        )
    if revisar:
        lista_insights.append(
            "Pouca margem e pouco giro (revisar mix): "
            + ", ".join(item["sku"] for item in revisar[:5])
            + "."
        )

    if taxa_cancelamento > 0.05:
        lista_insights.append(
            f"Cancelamentos/devolucoes em {fmt_pct(taxa_cancelamento)}: derrubam receita e reputacao."
        )
        acoes.append(
            {
                "prioridade": 2,
                "acao": "Revisar prazo de postagem, embalagem e promessa do anuncio "
                "(descricao/primeira imagem).",
                "ferramenta": "listar_pedidos + alertas",
            }
        )

    if marketing_pct > 0.15:
        lista_insights.append(
            f"Marketing consome {fmt_pct(marketing_pct)} da receita bruta "
            f"({fmt_brl(gasto_marketing)}). Sem dados de atribuicao, trate como teto: "
            "compare receita incremental com este gasto."
        )
        acoes.append(
            {
                "prioridade": 2,
                "acao": "Revisar campanhas: pausar as de maior custo por pedido e concentrar "
                "nos SKUs 'motor'.",
                "ferramenta": "dre + margem_sku",
            }
        )

    if dados_dre["lucro_liquido_centavos"] < 0:
        lista_insights.append(
            f"Mes fechou no prejuizo ({dados_dre['lucro_liquido']}): margem de contribuicao "
            f"{dados_dre['margem_contribuicao']} nao cobre {dados_dre['opex']} de despesas operacionais."
        )
        acoes.append(
            {
                "prioridade": 1,
                "acao": "Cortar/renegociar despesas fixas e revisar precos; o problema e de "
                "estrutura, nao de volume.",
                "ferramenta": "dre + fluxo_caixa",
            }
        )

    if risco_estoque:
        lista_insights.append(
            "Risco de ruptura: " + risco_estoque[0]["detalhe"]
        )
        acoes.append(
            {
                "prioridade": 1,
                "acao": "Repor os SKUs com cobertura menor que 7 dias antes de investir em trafego.",
                "ferramenta": "estoque",
            }
        )

    if dados_dre["completude"]["itens_sem_custo"]:
        lista_insights.append(
            f"{dados_dre['completude']['itens_sem_custo']} item(ns) sem custo: a margem desses "
            "SKUs esta otimista (custo tratado como zero)."
        )
        acoes.append(
            {
                "prioridade": 2,
                "acao": "Cadastrar custo unitario dos SKUs sem custo para o lucro ficar confiavel.",
                "ferramenta": "registrar_custo",
            }
        )

    if not lista_insights:
        lista_insights.append("Sem dados suficientes no mes para gerar insights. Importe pedidos e contas.")

    acoes_ordenadas = sorted(acoes, key=lambda item: item["prioridade"])[:5]
    return {
        "mes": mes,
        "mes_extenso": fmt_mes(mes),
        "numeros": {
            "receita_bruta": dados_dre["receita_bruta"],
            "receita_liquida": dados_dre["receita_liquida"],
            "margem_contribuicao": dados_dre["margem_contribuicao"],
            "margem_contribuicao_pct": dados_dre["margem_contribuicao_pct"],
            "lucro_liquido": dados_dre["lucro_liquido"],
            "lucro_liquido_pct": dados_dre["lucro_liquido_pct"],
            "pedidos_aprovados": dados_dre["pedidos"]["aprovados"],
            "ticket_medio": dados_dre["ticket_medio"],
            "unidades": dados_dre["unidades"],
            "taxa_cancelamento": fmt_pct(taxa_cancelamento),
            "gasto_marketing": fmt_brl(gasto_marketing),
            "marketing_pct_receita": fmt_pct(marketing_pct),
            "variacao_receita": comp.get("variacao_receita", "-"),
            "comparacao": comp.get("comparacao", "-"),
            "saldo_caixa_30d": caixa["saldo_do_periodo"],
            "vencido_a_pagar": caixa["vencido_a_pagar"],
        },
        "concentracao": {
            "top3_pct": fmt_pct(top3_pct),
            "classe_a_pct": fmt_pct(classe_a_pct),
            "skus_analisados": len(skus),
            "top3": [item["sku"] for item in top3],
        },
        "matriz_sku": matriz,
        "insights": lista_insights,
        "acoes_prioritarias": acoes_ordenadas,
        "alertas_abertos": alertas_calc["total"],
        "observacoes": [
            "Insights calculados sobre o DRE do mes + margem por SKU + despesas de marketing.",
            "Sem dados de visitas/conversao, nao ha como afirmar causalidade: use como hipotese "
            "para testar, nao como verdade absoluta.",
        ],
    }


__all__ = ["insights"]
