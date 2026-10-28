"""Relatorio de desempenho diario: tendencia, dias fortes e projecao.

Fonte: tabela ``desempenho_diario`` (importada de exportacoes tipo
"Performance das Vendas" do painel/UpSeller). Complementa o DRE: aqui a leitura
e por dia/semana, sem depender de pedido individual.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
import statistics

from ..config import NOMES_MARKETPLACE
from ..datas import fmt_data_br, fmt_mes, hoje
from ..dinheiro import fmt_brl, fmt_pct

DIAS_SEMANA = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]


def _periodo(conn: sqlite3.Connection, canal: str | None, dias: int) -> tuple[list[dict], str | None]:
    onde = ""
    parametros: list = []
    if canal:
        onde = " WHERE canal = ?"
        parametros.append(canal)
    ultima = conn.execute(
        f"SELECT MAX(data) FROM desempenho_diario{onde}", parametros
    ).fetchone()[0]
    if not ultima:
        return [], None
    fim = dt.date.fromisoformat(ultima)
    inicio = fim - dt.timedelta(days=max(1, dias) - 1)
    sql = (
        "SELECT * FROM desempenho_diario WHERE data BETWEEN ? AND ?"
        + (" AND canal = ?" if canal else "")
        + " ORDER BY data"
    )
    parametros_periodo: list = [inicio.isoformat(), fim.isoformat()]
    if canal:
        parametros_periodo.append(canal)
    linhas = [dict(linha) for linha in conn.execute(sql, parametros_periodo)]
    return linhas, f"{fmt_data_br(inicio)} a {fmt_data_br(fim)}"


def desempenho(
    conn: sqlite3.Connection,
    canal: str | None = None,
    dias: int = 30,
) -> dict:
    dias = max(7, min(365, int(dias)))
    linhas, periodo = _periodo(conn, canal, dias)
    if not linhas:
        return {
            "canal": canal or "todos",
            "periodo": None,
            "mensagem": (
                "Sem dados de desempenho diario. Importe o export 'Performance das Vendas' "
                "(tipo desempenho) para ver tendencia, ticket e dias fortes."
            ),
            "como_importar": "mkt importar desempenho ARQUIVO.xlsx --marketplace shopee",
        }

    pedidos = sum(int(l["pedidos_validos"]) for l in linhas)
    cancelados = sum(int(l["pedidos_cancelados"]) for l in linhas)
    receita = sum(int(l["receita_valida_centavos"]) for l in linhas)
    clientes = sum(int(l["clientes"]) for l in linhas)
    ticket = receita / pedidos if pedidos else 0
    taxa_cancelamento = cancelados / (pedidos + cancelados) if (pedidos + cancelados) else 0
    dias_com_venda = sum(1 for l in linhas if int(l["pedidos_validos"]) > 0)

    # semana ISO
    semanas: dict[str, dict] = {}
    for linha in linhas:
        data = dt.date.fromisoformat(linha["data"])
        ano, semana, _ = data.isocalendar()
        chave = f"{ano}-S{semana:02d}"
        bloco = semanas.setdefault(
            chave,
            {"semana": chave, "inicio": linha["data"], "fim": linha["data"], "receita": 0, "pedidos": 0},
        )
        bloco["receita"] += int(linha["receita_valida_centavos"])
        bloco["pedidos"] += int(linha["pedidos_validos"])
        bloco["fim"] = linha["data"]
    lista_semanas = []
    for chave in sorted(semanas):
        bloco = semanas[chave]
        bloco["ticket_centavos"] = int(bloco["receita"] / bloco["pedidos"]) if bloco["pedidos"] else 0
        bloco["receita_fmt"] = fmt_brl(bloco["receita"])
        bloco["ticket_fmt"] = fmt_brl(bloco["ticket_centavos"])
        bloco["rotulo"] = f"{fmt_data_br(bloco['inicio'])} a {fmt_data_br(bloco['fim'])}"
        lista_semanas.append(bloco)

    # por dia da semana
    por_dia_semana = {nome: {"receita": 0, "pedidos": 0} for nome in DIAS_SEMANA}
    for linha in linhas:
        data = dt.date.fromisoformat(linha["data"])
        bloco = por_dia_semana[DIAS_SEMANA[data.weekday()]]
        bloco["receita"] += int(linha["receita_valida_centavos"])
        bloco["pedidos"] += int(linha["pedidos_validos"])
    ranking_dias = sorted(
        (
            {"dia": nome, "receita_centavos": valor["receita"], "pedidos": valor["pedidos"]}
            for nome, valor in por_dia_semana.items()
        ),
        key=lambda item: item["receita_centavos"],
        reverse=True,
    )
    for item in ranking_dias:
        item["receita"] = fmt_brl(item["receita_centavos"])

    # tendencia: metade recente vs metade anterior do periodo
    meio = len(linhas) // 2 or 1
    primeira = linhas[:meio]
    segunda = linhas[meio:]
    receita_1 = sum(int(l["receita_valida_centavos"]) for l in primeira)
    receita_2 = sum(int(l["receita_valida_centavos"]) for l in segunda)
    variacao = (receita_2 - receita_1) / receita_1 if receita_1 else None

    # projecao simples (media diaria recente x 30)
    ultimos_7 = linhas[-7:]
    media_diaria_7 = sum(int(l["receita_valida_centavos"]) for l in ultimos_7) / len(ultimos_7)
    projecao_30 = int(media_diaria_7 * 30)

    # comparacao por canal (se houver mais de um)
    canais = [
        dict(linha)
        for linha in conn.execute(
            "SELECT canal, SUM(pedidos_validos) pedidos, SUM(receita_valida_centavos) receita, "
            "SUM(receita_valida_centavos)/NULLIF(SUM(pedidos_validos),0) ticket, "
            "MIN(data) inicio, MAX(data) fim "
            "FROM desempenho_diario GROUP BY canal ORDER BY receita DESC"
        )
    ]
    for item in canais:
        item["receita_fmt"] = fmt_brl(int(item["receita"] or 0))
        item["ticket_fmt"] = fmt_brl(int(item["ticket"] or 0))
        item["rotulo"] = NOMES_MARKETPLACE.get(item["canal"], item["canal"])

    resposta: dict = {
        "canal": canal or "todos",
        "periodo": periodo,
        "dias_com_dado": len(linhas),
        "dias_com_venda": dias_com_venda,
        "pedidos_validos": pedidos,
        "pedidos_cancelados": cancelados,
        "clientes": clientes,
        "receita_valida": fmt_brl(receita),
        "receita_valida_centavos": receita,
        "ticket_medio": fmt_brl(int(ticket)),
        "ticket_medio_centavos": int(ticket),
        "taxa_cancelamento": fmt_pct(taxa_cancelamento),
        "media_pedidos_por_dia": round(pedidos / len(linhas), 2),
        "semanas": lista_semanas,
        "dias_da_semana": ranking_dias,
        "tendencia": {
            "receita_primeira_metade": fmt_brl(receita_1),
            "receita_segunda_metade": fmt_brl(receita_2),
            "variacao": fmt_pct(variacao),
        },
        "projecao_30_dias": fmt_brl(projecao_30),
        "projecao_30_dias_centavos": projecao_30,
        "por_canal": canais,
        "observacoes": [
            "Projecao = media diaria dos ultimos 7 dias x 30; e referencia, nao promessa.",
            "Relatorio diario nao substitui a importacao de pedidos: use os dois juntos.",
        ],
    }

    alertas: list[str] = []
    if taxa_cancelamento > 0.05:
        alertas.append(
            f"Cancelamento em {fmt_pct(taxa_cancelamento)}: acima de 5% derruba reputacao."
        )
    if ticket < 2500:
        alertas.append(
            f"Ticket medio baixo ({fmt_brl(int(ticket))}): considere kits/combos e "
            "cuidado com frete gratis em itens baratos."
        )
    if variacao is not None and variacao < -0.25:
        alertas.append(
            f"Segunda metade do periodo caiu {fmt_pct(abs(variacao))} vs primeira: "
            "verifique anuncios pausados, estoque e concorrencia."
        )
    if dias_com_venda < len(linhas) * 0.5:
        alertas.append(
            f"Só {dias_com_venda} de {len(linhas)} dias tiveram venda: demanda instavel, "
            "vale trabalhar recorrencia/kit e revisar dias de anuncio."
        )
    melhor_dia = ranking_dias[0] if ranking_dias else None
    if melhor_dia and melhor_dia["pedidos"]:
        alertas.append(
            f"{melhor_dia['dia'].capitalize()} é o dia mais forte em receita "
            f"({melhor_dia['receita']}): concentre lancamentos/promocoes nele."
        )
    resposta["alertas"] = alertas
    return resposta


__all__ = ["desempenho"]
