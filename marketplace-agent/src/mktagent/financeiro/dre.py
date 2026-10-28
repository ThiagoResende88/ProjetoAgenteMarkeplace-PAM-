"""DRE mensal por marketplace (regime de competencia).

Formula (por mercado):

    receita_bruta              = soma dos itens vendidos (preco x quantidade)
    (-) descontos              = desconto do vendedor
    (+) frete_cobrado          = frete pago pelo comprador
    (-) frete_pago             = frete pago pelo vendedor
    (-) comissao               = comissao do marketplace
    (-) taxa_servico           = taxa de transacao/pagamento
    (-) cupom                  = cupom do vendedor
    (-) imposto                = impostos retidos
    = receita_liquida
    (-) cmv                    = custo das mercadorias vendidas
    = margem_contribuicao
    (-) despesas_operacionais  = contas a pagar do mes que NAO sao custo de
                                 produto/frete/imposto/comissao (evita duplicar)
    (+) outras_receitas        = contas a receber do mes
    = lucro_liquido
"""

from __future__ import annotations

import sqlite3

from ..datas import fmt_mes, intervalo_mes, mes_atual, normalizar_mes
from ..db import ultimo_mes_com_pedidos
from ..dinheiro import fmt_brl, fmt_pct
from . import consultas
from .consultas import Bloco

CATEGORIAS_EXCLUIDAS = {"insumo", "fornecedor", "frete", "imposto", "comissao", "taxa"}

OBSERVACOES_PADRAO = [
    "Despesas operacionais usam o vencimento como competencia; "
    "categorias ja embutidas no pedido (frete, imposto, comissao, insumo, fornecedor) "
    "nao entram de novo.",
    "Repasses podem incluir pedidos de outros meses (lag de repasse): "
    "a diferenca de conciliacao e um sinal, nao uma auditoria contabil.",
    "CMV usa o custo atual do SKU (atualizar um custo recalcula os pedidos ja importados); "
    "SKU sem custo entra como zero.",
]


def _coletar(
    conn: sqlite3.Connection, mes: str, marketplace: str | None
) -> dict:
    inicio, fim = intervalo_mes(mes)
    aprovados = consultas.pedidos_do_mes(conn, mes, marketplace)
    contagem = consultas.contar_por_situacao(conn, mes, marketplace)

    receita_bruta = sum(p["itens_total_centavos"] for p in aprovados)
    descontos = sum(p["desconto_centavos"] for p in aprovados)
    frete_cobrado = sum(p["frete_cobrado_centavos"] for p in aprovados)
    frete_pago = sum(p["frete_pago_centavos"] for p in aprovados)
    comissao = sum(p["comissao_centavos"] for p in aprovados)
    taxa_servico = sum(p["taxa_servico_centavos"] for p in aprovados)
    cupom = sum(p["cupom_centavos"] for p in aprovados)
    imposto = sum(p["imposto_centavos"] for p in aprovados)

    sql_cmv = (
        "SELECT COALESCE(SUM(i.quantidade * COALESCE(i.custo_unitario_centavos, 0)), 0) AS cmv, "
        "COALESCE(SUM(i.quantidade), 0) AS unidades, "
        "COALESCE(SUM(CASE WHEN i.custo_unitario_centavos IS NULL THEN 1 ELSE 0 END), 0) AS sem_custo, "
        "COUNT(i.id) AS itens "
        "FROM itens_pedido i JOIN pedidos p ON p.id = i.pedido_id "
        "WHERE p.situacao = 'aprovado' AND p.data_pedido BETWEEN ? AND ?"
    )
    parametros: list = [inicio.isoformat(), fim.isoformat()]
    if marketplace:
        sql_cmv += " AND p.marketplace = ?"
        parametros.append(marketplace)
    linha = conn.execute(sql_cmv, parametros).fetchone()
    cmv = int(linha["cmv"] or 0)
    unidades = int(linha["unidades"] or 0)
    itens_sem_custo = int(linha["sem_custo"] or 0)
    itens = int(linha["itens"] or 0)

    despesas = consultas.despesas_do_mes(conn, mes, marketplace)
    opex = 0
    opex_por_categoria: dict[str, int] = {}
    excluidas = 0
    excluidas_por_categoria: dict[str, int] = {}
    for despesa in despesas:
        categoria = (despesa["categoria"] or "outros").lower()
        total = int(despesa["total"] or 0)
        if categoria in CATEGORIAS_EXCLUIDAS:
            excluidas += total
            excluidas_por_categoria[categoria] = excluidas_por_categoria.get(categoria, 0) + total
        else:
            opex += total
            opex_por_categoria[categoria] = opex_por_categoria.get(categoria, 0) + total

    outras_receitas = sum(int(r["total"] or 0) for r in consultas.receitas_do_mes(conn, mes, marketplace))
    repasses = sum(int(r["total"] or 0) for r in consultas.repasses_do_mes(conn, mes, marketplace))

    receita_liquida = (
        receita_bruta - descontos + frete_cobrado - frete_pago - comissao
        - taxa_servico - cupom - imposto
    )
    margem = receita_liquida - cmv
    lucro = margem - opex + outras_receitas

    return {
        "mes": mes,
        "marketplace": marketplace,
        "periodo": (inicio, fim),
        "contagem": contagem,
        "aprovados": len(aprovados),
        "receita_bruta": receita_bruta,
        "descontos": descontos,
        "frete_cobrado": frete_cobrado,
        "frete_pago": frete_pago,
        "comissao": comissao,
        "taxa_servico": taxa_servico,
        "cupom": cupom,
        "imposto": imposto,
        "cmv": cmv,
        "unidades": unidades,
        "itens": itens,
        "itens_sem_custo": itens_sem_custo,
        "receita_liquida": receita_liquida,
        "margem_contribuicao": margem,
        "opex": opex,
        "opex_por_categoria": opex_por_categoria,
        "excluidas": excluidas,
        "excluidas_por_categoria": excluidas_por_categoria,
        "outras_receitas": outras_receitas,
        "lucro_liquido": lucro,
        "repasses": repasses,
        "diferenca_conciliacao": repasses - receita_liquida,
        "pedidos_sem_repasse_informado": sum(
            1 for p in aprovados if p["repasse_centavos"] is None
        ),
    }


def _bloco(dados: dict) -> dict:
    bloco = Bloco()
    bloco.texto("mes", dados["mes"])
    bloco.texto("mes_extenso", fmt_mes(dados["mes"]))
    bloco.texto("marketplace", dados["marketplace"] or "todos")
    contagem = dados["contagem"]
    bloco.texto(
        "pedidos",
        {
            "total": sum(contagem.values()),
            "aprovados": contagem["aprovado"],
            "cancelados": contagem["cancelado"],
            "devolvidos": contagem["devolvido"],
            "pendentes": contagem["pendente"],
            "desconhecidos": contagem["desconhecido"],
        },
    )
    bloco.numero("unidades", dados["unidades"])
    bloco.numero(
        "ticket_medio_centavos",
        int(dados["receita_bruta"] / dados["aprovados"]) if dados["aprovados"] else 0,
    )
    bloco.texto(
        "ticket_medio",
        fmt_brl(int(dados["receita_bruta"] / dados["aprovados"]) if dados["aprovados"] else 0),
    )

    for campo in (
        "receita_bruta",
        "descontos",
        "frete_cobrado",
        "frete_pago",
        "comissao",
        "taxa_servico",
        "cupom",
        "imposto",
        "cmv",
        "receita_liquida",
        "margem_contribuicao",
        "opex",
        "outras_receitas",
        "lucro_liquido",
        "repasses",
        "diferenca_conciliacao",
        "excluidas",
    ):
        bloco.dinheiro(campo, dados[campo])

    base = dados["receita_bruta"] or 1
    bloco.percentual("receita_liquida_pct", dados["receita_liquida"] / base)
    bloco.percentual("margem_contribuicao_pct", dados["margem_contribuicao"] / base)
    bloco.percentual("opex_pct", dados["opex"] / base)
    bloco.percentual("lucro_liquido_pct", dados["lucro_liquido"] / base)
    if dados["repasses"]:
        bloco.percentual(
            "diferenca_conciliacao_pct", dados["diferenca_conciliacao"] / base
        )

    bloco.texto(
        "despesas_por_categoria",
        {k: fmt_brl(v) for k, v in sorted(dados["opex_por_categoria"].items(), key=lambda x: -x[1])},
    )
    bloco.texto(
        "custos_ja_no_pedido",
        {k: fmt_brl(v) for k, v in sorted(dados["excluidas_por_categoria"].items(), key=lambda x: -x[1])},
    )

    cobertura = (
        (dados["itens"] - dados["itens_sem_custo"]) / dados["itens"] if dados["itens"] else 0.0
    )
    bloco.percentual("cobertura_custo_itens_pct", cobertura)
    bloco.texto(
        "completude",
        {
            "itens_sem_custo": dados["itens_sem_custo"],
            "itens_total": dados["itens"],
            "cobertura_custo_itens_pct": fmt_pct(cobertura),
            "pedidos_sem_repasse_informado": dados["pedidos_sem_repasse_informado"],
        },
    )
    return bloco.dados


def dre(
    conn: sqlite3.Connection,
    mes: str | None = None,
    marketplace: str | None = None,
    incluir_por_marketplace: bool = True,
) -> dict:
    mes = normalizar_mes(mes) or ultimo_mes_com_pedidos(conn) or mes_atual()
    marketplace = (marketplace or "").strip().lower() or None

    dados = _coletar(conn, mes, marketplace)
    resposta = _bloco(dados)

    if incluir_por_marketplace and marketplace is None:
        por_mercado: dict[str, dict] = {}
        for linha in conn.execute(
            "SELECT DISTINCT marketplace FROM pedidos WHERE data_pedido LIKE ?",
            (f"{mes}%",),
        ):
            chave = linha["marketplace"]
            por_mercado[chave] = _bloco(_coletar(conn, mes, chave))
        if por_mercado:
            resposta["por_marketplace"] = por_mercado
        # despesas gerais (sem marketplace) aparecem separadas
        gerais = conn.execute(
            "SELECT COALESCE(SUM(valor_centavos),0) FROM contas_financeiras "
            "WHERE tipo='pagar' AND vencimento LIKE ? AND marketplace IS NULL "
            "AND categoria NOT IN ('insumo','fornecedor','frete','imposto','comissao','taxa')",
            (f"{mes}%",),
        ).fetchone()[0]
        resposta["despesas_gerais_centavos"] = int(gerais or 0)
        resposta["despesas_gerais"] = fmt_brl(int(gerais or 0))

    resposta["observacoes"] = OBSERVACOES_PADRAO
    if not dados["itens"]:
        resposta.setdefault("avisos", []).append(
            "Nenhum pedido aprovado nesse mes. Importe as planilhas de pedidos "
            "ou confira o mes informado."
        )
    if dados["itens_sem_custo"]:
        resposta.setdefault("avisos", []).append(
            f"{dados['itens_sem_custo']} item(ns) sem custo cadastrado: "
            "o CMV e a margem estao otimistas para eles."
        )
    return resposta


def comparativo(conn: sqlite3.Connection, mes: str | None = None) -> dict:
    """Compara o mes com o anterior (receita e lucro).

    Quando o mes esta em andamento, a variacao de RECEITA e calculada MTD
    (mesma quantidade de dias nos dois meses) para nao comparar mes parcial com
    mes cheio. A variacao de lucro fica indisponivel nesse caso.
    """
    from ..datas import hoje, intervalo_mes, mes_anterior, mes_atual

    mes = normalizar_mes(mes) or ultimo_mes_com_pedidos(conn) or mes_atual()
    anterior_mes = mes_anterior(mes)
    atual = dre(conn, mes, incluir_por_marketplace=False)
    anterior = dre(conn, anterior_mes, incluir_por_marketplace=False)
    parcial = mes == mes_atual()

    resposta = {
        "mes": mes,
        "mes_anterior": anterior_mes,
        "parcial": parcial,
        "receita_bruta": atual["receita_bruta"],
        "receita_bruta_anterior": anterior["receita_bruta"],
        "lucro_liquido": atual["lucro_liquido"],
        "lucro_liquido_anterior": anterior["lucro_liquido"],
    }

    if parcial:
        inicio, _fim = intervalo_mes(mes)
        limite_atual = hoje()
        inicio_anterior, _ = intervalo_mes(anterior_mes)
        limite_anterior = inicio_anterior.replace(day=min(limite_atual.day, 28))
        receita_mtd = _receita_no_periodo(conn, inicio, limite_atual)
        receita_mtd_anterior = _receita_no_periodo(conn, inicio_anterior, limite_anterior)
        variacao = _variacao(receita_mtd, receita_mtd_anterior)
        resposta.update(
            {
                "comparacao": "MTD (mesmo numero de dias nos dois meses)",
                "receita_mtd": fmt_brl(receita_mtd),
                "receita_mtd_centavos": receita_mtd,
                "receita_mtd_anterior": fmt_brl(receita_mtd_anterior),
                "receita_mtd_anterior_centavos": receita_mtd_anterior,
                "variacao_receita_pct": variacao,
                "variacao_receita": fmt_pct(variacao),
                "variacao_lucro": "indisponivel no mes em andamento",
                "aviso": (
                    "Mes em andamento: a variacao de receita compara os dias 1 a "
                    f"{limite_atual.day} com o mesmo periodo de {anterior_mes}."
                ),
            }
        )
        return resposta

    variacao_receita = _variacao(
        atual["receita_bruta_centavos"], anterior["receita_bruta_centavos"]
    )
    variacao_lucro = _variacao(
        atual["lucro_liquido_centavos"], anterior["lucro_liquido_centavos"]
    )
    resposta.update(
        {
            "comparacao": "mes fechado vs mes fechado",
            "variacao_receita_pct": variacao_receita,
            "variacao_receita": fmt_pct(variacao_receita),
            "variacao_lucro": fmt_pct(variacao_lucro),
        }
    )
    return resposta


def _receita_no_periodo(conn: sqlite3.Connection, inicio, fim) -> int:
    linha = conn.execute(
        "SELECT COALESCE(SUM(itens_total_centavos), 0) FROM pedidos "
        "WHERE situacao='aprovado' AND data_pedido BETWEEN ? AND ?",
        (inicio.isoformat(), fim.isoformat()),
    ).fetchone()
    return int(linha[0] or 0)


def _variacao(atual: int, anterior: int) -> float | None:
    if not anterior:
        return None
    return (atual - anterior) / anterior


__all__ = ["dre", "comparativo"]
