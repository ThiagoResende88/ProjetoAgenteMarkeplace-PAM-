"""Alertas acionaveis: o que precisa de decisao do dono da loja.

Cada alerta tem severidade, titulo, detalhe e uma acao sugerida concreta
(comando do mkt ou ferramenta do agente).
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from ..datas import dias_ate, fmt_data_br, hoje, mes_atual
from ..db import ultimo_mes_com_pedidos
from ..dinheiro import fmt_brl, fmt_pct
from .caixa import fluxo_caixa
from .consultas import periodo_dias
from .dre import comparativo, dre
from .margem import margem_por_sku

ORDEM = {"alta": 0, "media": 1, "baixa": 2}


def _alerta(severidade: str, titulo: str, detalhe: str, acao: str) -> dict:
    return {
        "severidade": severidade,
        "titulo": titulo,
        "detalhe": detalhe,
        "acao": acao,
    }


def alertas(conn: sqlite3.Connection, dias_estoque: int = 30) -> dict:
    referencia = hoje()
    itens: list[dict] = []

    # 1) contas vencidas e a vencer
    vencidas = list(
        conn.execute(
            "SELECT * FROM contas_financeiras WHERE pago_em IS NULL AND vencimento < ? "
            "ORDER BY vencimento",
            (referencia.isoformat(),),
        )
    )
    vencidas_pagar = [c for c in vencidas if c["tipo"] == "pagar"]
    vencidas_receber = [c for c in vencidas if c["tipo"] == "receber"]
    if vencidas_pagar:
        total = sum(int(c["valor_centavos"]) for c in vencidas_pagar)
        nomes = ", ".join(c["descricao"] for c in vencidas_pagar[:4])
        itens.append(
            _alerta(
                "alta",
                f"{len(vencidas_pagar)} conta(s) vencida(s) a pagar — {fmt_brl(total)}",
                f"Vencidas: {nomes}.",
                "Pague ou reprograme: use a ferramenta de contas a pagar "
                "(ou 'mkt contas --status vencida') e marque como paga.",
            )
        )
    if vencidas_receber:
        total = sum(int(c["valor_centavos"]) for c in vencidas_receber)
        nomes = ", ".join(c["descricao"] for c in vencidas_receber[:4])
        itens.append(
            _alerta(
                "media",
                f"{len(vencidas_receber)} conta(s) vencida(s) a receber — {fmt_brl(total)}",
                f"Em atraso: {nomes}.",
                "Cobre o recebimento ou confira se o repasse do marketplace ja caiu; "
                "depois marque como recebida.",
            )
        )

    limite_7 = (referencia + dt.timedelta(days=7)).isoformat()
    a_vencer = list(
        conn.execute(
            "SELECT * FROM contas_financeiras WHERE pago_em IS NULL "
            "AND vencimento >= ? AND vencimento <= ? ORDER BY vencimento",
            (referencia.isoformat(), limite_7),
        )
    )
    if a_vencer:
        total = sum(int(c["valor_centavos"]) for c in a_vencer)
        itens.append(
            _alerta(
                "media",
                f"{len(a_vencer)} conta(s) vencem em ate 7 dias — {fmt_brl(total)}",
                "; ".join(
                    f"{c['descricao']} ({c['vencimento']}, {fmt_brl(int(c['valor_centavos']))})"
                    for c in a_vencer[:5]
                ),
                "Confira se ha saldo/repasse suficiente: peça o fluxo de caixa.",
            )
        )

    # 2) fluxo de caixa com semana negativa
    caixa = fluxo_caixa(conn, dias=30)
    semanas_negativas = [s for s in caixa["semanas"] if s["saldo"] < 0]
    if semanas_negativas:
        itens.append(
            _alerta(
                "media",
                "Semana com saldo negativo no fluxo de caixa",
                "; ".join(
                    f"{s['rotulo']}: {s['fmt']['saldo']}" for s in semanas_negativas[:3]
                ),
                "Antecipe recebiveis do marketplace ou renegocie vencimentos. "
                "A projecao nao inclui repasses futuros (eles ainda vao cair).",
            )
        )

    # 3) SKU sem custo (margem nao confiavel)
    inicio_90, fim_90 = periodo_dias(90)
    sem_custo = list(
        conn.execute(
            "SELECT i.sku, COUNT(*) AS itens, SUM(i.quantidade) AS unidades, "
            "SUM(i.quantidade * i.preco_unitario_centavos) AS receita "
            "FROM itens_pedido i JOIN pedidos p ON p.id = i.pedido_id "
            "WHERE i.custo_unitario_centavos IS NULL AND p.situacao='aprovado' "
            "AND p.data_pedido BETWEEN ? AND ? "
            "GROUP BY i.sku ORDER BY receita DESC",
            (inicio_90, fim_90),
        )
    )
    if sem_custo:
        receita = sum(int(s["receita"] or 0) for s in sem_custo)
        nomes = ", ".join(s["sku"] for s in sem_custo[:5])
        itens.append(
            _alerta(
                "media",
                f"{len(sem_custo)} SKU(s) sem custo cadastrado",
                f"Afetam {fmt_brl(receita)} em vendas nos ultimos 90 dias: {nomes}.",
                "Cadastre o custo unitario com 'registrar_custo' (ou "
                "'mkt custos definir SKU 12.50') para ter margem real.",
            )
        )

    # 4) margem negativa
    try:
        margens = margem_por_sku(conn, dias=90)
        negativas = [
            item
            for item in margens["skus"]
            if item["custo_conhecido"] and (item["margem_centavos"] or 0) < 0
        ]
        if negativas:
            top = negativas[:5]
            itens.append(
                _alerta(
                    "alta",
                    f"{len(negativas)} SKU(s) vendendo com margem negativa (90 dias)",
                    "; ".join(
                        f"{i['sku']} ({i['fmt']['margem']}, {i['fmt']['margem_pct']})"
                        for i in top
                    ),
                    "Reajuste o preco ou reduza custo/frete. A ferramenta de margem "
                    "sugere um preco minimo para a margem alvo.",
                )
            )
    except Exception as erro:  # nao deixar um alerta quebrar o relatorio
        itens.append(
            _alerta(
                "baixa",
                "Nao foi possivel calcular margem por SKU",
                f"Erro: {erro}",
                "Verifique se os pedidos foram importados corretamente.",
            )
        )

    # 5) cancelamentos do mes corrente
    mes = mes_atual()
    linha = conn.execute(
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN situacao='cancelado' THEN 1 ELSE 0 END) AS cancelados, "
        "SUM(CASE WHEN situacao='devolvido' THEN 1 ELSE 0 END) AS devolvidos "
        "FROM pedidos WHERE data_pedido LIKE ?",
        (f"{mes}%",),
    ).fetchone()
    if linha and linha["total"]:
        taxa = (linha["cancelados"] + linha["devolvidos"]) / linha["total"]
        if taxa > 0.05:
            itens.append(
                _alerta(
                    "media",
                    f"Cancelamentos/devolucoes em {fmt_pct(taxa)} no mes",
                    f"{linha['cancelados']} cancelado(s) e {linha['devolvidos']} "
                    f"devolvido(s) de {linha['total']} pedido(s).",
                    "Revise prazo de envio, descricao do anuncio e qualidade do "
                    "produto — cancelamento derruba reputacao e receita.",
                )
            )

    # 6) queda de receita contra o mes anterior
    if conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]:
        from ..datas import mes_anterior

        ultimo_pedido = ultimo_mes_com_pedidos(conn)
        alvo_queda = (
            mes_anterior(mes_atual()) if ultimo_pedido == mes_atual() else ultimo_pedido
        )
        comparacao = comparativo(conn, alvo_queda)
        if comparacao["variacao_receita_pct"] is not None and comparacao["variacao_receita_pct"] < -0.2:
            itens.append(
                _alerta(
                    "alta",
                    f"Receita caiu {fmt_pct(abs(comparacao['variacao_receita_pct']))} "
                    f"em relacao a {comparacao['mes_anterior']}",
                    f"Atual {comparacao['receita_bruta']} vs anterior "
                    f"{comparacao['receita_bruta_anterior']}.",
                    "Investigue: anuncios pausados, estoque zerado, queda de visitas "
                    "ou concorrencia de preco.",
                )
            )

    # 7) estoque com cobertura curta
    try:
        cobertura = _cobertura_estoque(conn, dias_estoque)
        criticos = [item for item in cobertura if item["dias_cobertura"] is not None and item["dias_cobertura"] < 7]
        if criticos:
            itens.append(
                _alerta(
                    "alta",
                    f"{len(criticos)} SKU(s) com estoque para menos de 7 dias",
                    "; ".join(
                        f"{c['sku']}: {c['estoque']} un ({c['dias_cobertura']} dias)"
                        for c in criticos[:5]
                    ),
                    "Reponha agora; ruptura derruba ranking e vendas.",
                )
            )
    except Exception:
        pass

    # 8) conciliacao de repasses do ultimo mes fechado
    ultimo = ultimo_mes_com_pedidos(conn)
    canais_com_repasse = {"shopee", "tiktok", "mercadolivre"}
    if ultimo:
        from ..datas import mes_anterior

        alvo = mes_anterior(ultimo) if ultimo == mes_atual() else ultimo
        canais_do_mes = {
            linha["marketplace"]
            for linha in conn.execute(
                "SELECT DISTINCT marketplace FROM pedidos WHERE data_pedido LIKE ?",
                (f"{alvo}%",),
            )
        }
        dados = dre(conn, alvo, incluir_por_marketplace=False) if canais_do_mes & canais_com_repasse else None
        if dados and dados["repasses_centavos"] and dados["receita_liquida_centavos"]:
            diferenca_pct = abs(
                dados["diferenca_conciliacao_centavos"] / dados["receita_liquida_centavos"]
            )
            if diferenca_pct > 0.02:
                itens.append(
                    _alerta(
                        "media",
                        f"Repasses de {dados['mes_extenso']} diferem {fmt_pct(diferenca_pct)} "
                        "do esperado",
                        f"Recebido {dados['repasses']} vs liquido calculado "
                        f"{dados['receita_liquida']}.",
                        "Importe o extrato completo de repasses do periodo e confira "
                        "taxas/estornos antes de fechar o mes.",
                    )
                )
        elif (
            dados
            and dados["pedidos"]["aprovados"]
            and not dados["repasses_centavos"]
        ):
            itens.append(
                _alerta(
                    "baixa",
                    f"Repasses de {dados['mes_extenso']} ainda nao importados",
                    f"{dados['pedidos']['aprovados']} pedido(s) aprovados sem extrato "
                    "de repasse no sistema.",
                    "Importe o relatorio de repasses para conciliar o que caiu na conta.",
                )
            )

    # 9) mes fechado com prejuizo
    if ultimo:
        alvo_prejuizo = mes_anterior(ultimo) if ultimo == mes_atual() else ultimo
        dados_prejuizo = dre(conn, alvo_prejuizo, incluir_por_marketplace=False)
        if dados_prejuizo.get("receita_bruta_centavos") and dados_prejuizo["lucro_liquido_centavos"] < 0:
            itens.append(
                _alerta(
                    "alta",
                    f"Prejuizo de {fmt_brl(abs(dados_prejuizo['lucro_liquido_centavos']))} em "
                    f"{dados_prejuizo['mes_extenso']}",
                    f"Margem de contribuicao {dados_prejuizo['margem_contribuicao']} "
                    f"vs despesas operacionais {dados_prejuizo['opex']}.",
                    "Revise despesas fixas e precos: o mes fechou no negativo mesmo "
                    "antes de retirar lucro.",
                )
            )

    # 10) pedidos pendentes antigos (B2B/consignacao costumam ficar esquecidos)
    limite_pendente = (referencia - dt.timedelta(days=30)).isoformat()
    pendentes = list(
        conn.execute(
            "SELECT pedido_externo, data_pedido, itens_total_centavos, marketplace "
            "FROM pedidos WHERE situacao='pendente' AND data_pedido < ? "
            "ORDER BY data_pedido",
            (limite_pendente,),
        )
    )
    if pendentes:
        total = sum(int(p["itens_total_centavos"]) for p in pendentes)
        itens.append(
            _alerta(
                "media",
                f"{len(pendentes)} pedido(s) pendente(s) ha mais de 30 dias — {fmt_brl(total)}",
                "; ".join(
                    f"{p['pedido_externo']} ({fmt_data_br(p['data_pedido'])}, "
                    f"{fmt_brl(int(p['itens_total_centavos']))})"
                    for p in pendentes[:5]
                ),
                "Cobre o pagamento ou atualize o status (ex.: pedidos B2B/consignacao). "
                "Pendente nao entra na receita do DRE.",
            )
        )

    # 11) status desconhecido
    total_desconhecido = conn.execute(
        "SELECT COUNT(*) FROM pedidos WHERE situacao='desconhecido'"
    ).fetchone()[0]
    if total_desconhecido:
        itens.append(
            _alerta(
                "baixa",
                f"{total_desconhecido} pedido(s) com status nao reconhecido",
                "Esses pedidos nao entram na receita do DRE.",
                "Veja o status bruto na importacao e ajuste o mapeamento se for um "
                "status novo do marketplace.",
            )
        )

    itens.sort(key=lambda alerta: ORDEM.get(alerta["severidade"], 9))
    resumo = {"alta": 0, "media": 0, "baixa": 0}
    for alerta in itens:
        resumo[alerta["severidade"]] = resumo.get(alerta["severidade"], 0) + 1

    return {
        "gerado_em": dt.datetime.now().isoformat(timespec="seconds"),
        "total": len(itens),
        "resumo": resumo,
        "alertas": itens,
        "observacoes": [
            "Alertas usam os ultimos 90 dias para margem e o mes corrente para "
            "cancelamentos; estoque depende de importacao da posicao.",
        ],
    }


def _cobertura_estoque(conn: sqlite3.Connection, dias: int) -> list[dict]:
    inicio, fim = periodo_dias(dias)
    vendas = {
        linha["sku"]: int(linha["unidades"] or 0)
        for linha in conn.execute(
            "SELECT i.sku, SUM(i.quantidade) AS unidades "
            "FROM itens_pedido i JOIN pedidos p ON p.id = i.pedido_id "
            "WHERE p.situacao='aprovado' AND p.data_pedido BETWEEN ? AND ? "
            "GROUP BY i.sku",
            (inicio, fim),
        )
    }
    resultado = []
    for linha in conn.execute("SELECT sku, quantidade FROM estoque"):
        sku = linha["sku"]
        estoque = int(linha["quantidade"] or 0)
        vendas_periodo = vendas.get(sku, 0)
        por_dia = vendas_periodo / max(1, dias)
        dias_cobertura = (estoque / por_dia) if por_dia > 0 else None
        resultado.append(
            {
                "sku": sku,
                "estoque": estoque,
                "vendas_periodo": vendas_periodo,
                "dias_cobertura": round(dias_cobertura, 1) if dias_cobertura is not None else None,
            }
        )
    return resultado


def cobertura_estoque(conn: sqlite3.Connection, dias: int = 30) -> dict:
    itens = _cobertura_estoque(conn, dias)
    itens.sort(
        key=lambda item: (item["dias_cobertura"] is None, item["dias_cobertura"] or 9999)
    )
    return {
        "periodo_dias": dias,
        "itens": itens,
        "sem_estoque_importado": not itens,
        "observacoes": [
            "A cobertura usa a media de vendas do periodo dividida pelo estoque atual.",
            "SKU sem giro aparece com dias_cobertura nulo.",
        ],
    }


__all__ = ["alertas", "cobertura_estoque"]
