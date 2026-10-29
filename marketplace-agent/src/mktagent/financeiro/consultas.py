"""Consultas e formatacao compartilhadas pelos relatorios."""

from __future__ import annotations

import sqlite3

from ..datas import (
    fmt_data_br,
    intervalo_mes,
    mes_anterior,
    mes_atual,
    normalizar_mes,
)
from ..dinheiro import fmt_brl, fmt_pct


class Bloco:
    """Acumula metricas ja formatadas (texto + centavos) para JSON/terminal."""

    def __init__(self) -> None:
        self.dados: dict = {}

    def dinheiro(self, nome: str, centavos: int | None) -> None:
        self.dados[nome] = fmt_brl(centavos)
        self.dados[f"{nome}_centavos"] = int(centavos or 0)

    def percentual(self, nome: str, fracao: float | None) -> None:
        self.dados[nome] = fmt_pct(fracao)

    def numero(self, nome: str, valor) -> None:
        self.dados[nome] = valor

    def texto(self, nome: str, valor) -> None:
        self.dados[nome] = valor

    def juntar(self, outro: "Bloco") -> None:
        self.dados.update(outro.dados)


def pedidos_do_mes(
    conn: sqlite3.Connection,
    mes: str | None = None,
    marketplace: str | None = None,
    situacoes: tuple[str, ...] = ("aprovado",),
) -> list[sqlite3.Row]:
    inicio, fim = intervalo_mes(mes or _mes_padrao(conn))
    marcadores = ",".join("?" for _ in situacoes)
    sql = (
        "SELECT p.* FROM pedidos p WHERE p.data_pedido BETWEEN ? AND ? "
        f"AND p.situacao IN ({marcadores})"
    )
    parametros: list = [inicio.isoformat(), fim.isoformat(), *situacoes]
    if marketplace:
        sql += " AND p.marketplace = ?"
        parametros.append(marketplace)
    sql += " ORDER BY p.data_pedido"
    return list(conn.execute(sql, parametros))


def _mes_padrao(conn: sqlite3.Connection) -> str:
    from ..db import ultimo_mes_com_pedidos

    return ultimo_mes_com_pedidos(conn) or mes_atual()


def contar_por_situacao(
    conn: sqlite3.Connection, mes: str, marketplace: str | None = None
) -> dict[str, int]:
    inicio, fim = intervalo_mes(mes)
    sql = (
        "SELECT situacao, COUNT(*) AS total FROM pedidos "
        "WHERE data_pedido BETWEEN ? AND ?"
    )
    parametros: list = [inicio.isoformat(), fim.isoformat()]
    if marketplace:
        sql += " AND marketplace = ?"
        parametros.append(marketplace)
    sql += " GROUP BY situacao"
    contagem = {s: 0 for s in ("aprovado", "cancelado", "devolvido", "pendente", "desconhecido")}
    for linha in conn.execute(sql, parametros):
        contagem[linha["situacao"]] = int(linha["total"])
    return contagem


def despesas_do_mes(
    conn: sqlite3.Connection, mes: str, marketplace: str | None = None
) -> list[dict]:
    """Contas a pagar com vencimento no mes (competencia), por categoria."""
    inicio, fim = intervalo_mes(mes)
    sql = (
        "SELECT categoria, marketplace, SUM(valor_centavos) AS total, COUNT(*) AS quantidade "
        "FROM contas_financeiras WHERE tipo='pagar' AND vencimento BETWEEN ? AND ?"
    )
    parametros: list = [inicio.isoformat(), fim.isoformat()]
    if marketplace:
        sql += " AND marketplace = ?"
        parametros.append(marketplace)
    sql += " GROUP BY categoria, marketplace"
    return [dict(linha) for linha in conn.execute(sql, parametros)]


def receitas_do_mes(
    conn: sqlite3.Connection, mes: str, marketplace: str | None = None
) -> list[dict]:
    inicio, fim = intervalo_mes(mes)
    sql = (
        "SELECT categoria, SUM(valor_centavos) AS total FROM contas_financeiras "
        "WHERE tipo='receber' AND vencimento BETWEEN ? AND ?"
    )
    parametros: list = [inicio.isoformat(), fim.isoformat()]
    if marketplace:
        sql += " AND (marketplace = ? OR marketplace IS NULL)"
        parametros.append(marketplace)
    sql += " GROUP BY categoria"
    return [dict(linha) for linha in conn.execute(sql, parametros)]


def repasses_do_mes(
    conn: sqlite3.Connection, mes: str, marketplace: str | None = None
) -> list[dict]:
    inicio, fim = intervalo_mes(mes)
    sql = (
        "SELECT c.marketplace, SUM(r.valor_centavos) AS total, COUNT(*) AS quantidade "
        "FROM repasses r JOIN contas_loja c ON c.id = r.conta_id "
        "WHERE r.data BETWEEN ? AND ?"
    )
    parametros: list = [inicio.isoformat(), fim.isoformat()]
    if marketplace:
        sql += " AND c.marketplace = ?"
        parametros.append(marketplace)
    sql += " GROUP BY c.marketplace"
    return [dict(linha) for linha in conn.execute(sql, parametros)]


def periodo_dias(dias: int) -> tuple[str, str]:
    import datetime as dt

    fim = dt.date.today()
    inicio = fim - dt.timedelta(days=max(1, dias))
    return inicio.isoformat(), fim.isoformat()


def rotulo_periodo(inicio: str, fim: str) -> str:
    return f"{fmt_data_br(inicio)} a {fmt_data_br(fim)}"


def dados_disponiveis(conn: sqlite3.Connection) -> dict:
    """Panorama do que ja foi importado (usado no resumo e no status)."""
    def um(sql: str):
        linha = conn.execute(sql).fetchone()
        return linha[0] if linha else 0

    meses = [linha[0] for linha in conn.execute(
        "SELECT DISTINCT substr(data_pedido,1,7) m FROM pedidos ORDER BY m"
    )]
    return {
        "pedidos": um("SELECT COUNT(*) FROM pedidos"),
        "itens": um("SELECT COUNT(*) FROM itens_pedido"),
        "produtos_com_custo": um(
            "SELECT COUNT(*) FROM produtos WHERE custo_unitario_centavos IS NOT NULL"
        ),
        "produtos": um("SELECT COUNT(*) FROM produtos"),
        "repasses": um("SELECT COUNT(*) FROM repasses"),
        "contas_financeiras": um("SELECT COUNT(*) FROM contas_financeiras"),
        "contas_abertas": um(
            "SELECT COUNT(*) FROM contas_financeiras WHERE pago_em IS NULL"
        ),
        "estoque_itens": um("SELECT COUNT(*) FROM estoque"),
        "meses_com_pedidos": meses,
        "ultimo_mes": meses[-1] if meses else None,
        "mes_anterior": mes_anterior(meses[-1]) if meses else None,
    }


__all__ = [
    "Bloco",
    "contar_por_situacao",
    "dados_disponiveis",
    "despesas_do_mes",
    "normalizar_mes",
    "pedidos_do_mes",
    "periodo_dias",
    "receitas_do_mes",
    "repasses_do_mes",
    "rotulo_periodo",
]
