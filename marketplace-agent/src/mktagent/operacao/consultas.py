"""Consultas operacionais: pedidos, produtos e custos."""

from __future__ import annotations

import sqlite3

from ..datas import fmt_data_br, intervalo_mes, normalizar_mes
from ..dinheiro import fmt_brl, para_centavos, parse_valor


def listar_pedidos(
    conn: sqlite3.Connection,
    mes: str | None = None,
    marketplace: str | None = None,
    situacao: str | None = None,
    limite: int = 30,
    cliente: str | None = None,
) -> dict:
    sql = "SELECT p.* FROM pedidos p WHERE 1=1"
    parametros: list = []
    if mes:
        inicio, fim = intervalo_mes(normalizar_mes(mes) or mes)
        sql += " AND p.data_pedido BETWEEN ? AND ?"
        parametros.extend([inicio.isoformat(), fim.isoformat()])
    if marketplace:
        sql += " AND p.marketplace = ?"
        parametros.append(marketplace.strip().lower())
    if situacao:
        sql += " AND p.situacao = ?"
        parametros.append(situacao.strip().lower())
    if cliente:
        sql += " AND p.cliente LIKE ?"
        parametros.append(f"%{cliente.strip()}%")
    sql += " ORDER BY p.data_pedido DESC LIMIT ?"
    parametros.append(max(1, int(limite)))

    pedidos = list(conn.execute(sql, parametros))
    total = sum(int(p["itens_total_centavos"]) for p in pedidos)
    linhas = []
    for pedido in pedidos:
        itens = list(
            conn.execute(
                "SELECT sku, quantidade, preco_unitario_centavos FROM itens_pedido "
                "WHERE pedido_id = ?",
                (pedido["id"],),
            )
        )
        linhas.append(
            {
                "pedido": pedido["pedido_externo"],
                "cliente": pedido["cliente"],
                "marketplace": pedido["marketplace"],
                "data": fmt_data_br(pedido["data_pedido"]),
                "status": pedido["status"],
                "situacao": pedido["situacao"],
                "total": fmt_brl(int(pedido["itens_total_centavos"])),
                "total_centavos": int(pedido["itens_total_centavos"]),
                "itens": [
                    {
                        "sku": item["sku"],
                        "quantidade": item["quantidade"],
                        "preco": fmt_brl(int(item["preco_unitario_centavos"])),
                    }
                    for item in itens
                ],
            }
        )
    return {
        "filtro": {
            "mes": mes,
            "marketplace": marketplace,
            "situacao": situacao,
            "cliente": cliente,
            "limite": limite,
        },
        "quantidade": len(linhas),
        "total_listado": fmt_brl(total),
        "total_listado_centavos": total,
        "pedidos": linhas,
    }


def listar_produtos(conn: sqlite3.Connection) -> dict:
    produtos = list(
        conn.execute(
            "SELECT p.*, e.quantidade AS estoque FROM produtos p "
            "LEFT JOIN estoque e ON e.sku = p.sku ORDER BY p.sku"
        )
    )
    return {
        "quantidade": len(produtos),
        "produtos": [
            {
                "sku": produto["sku"],
                "nome": produto["nome"],
                "custo": fmt_brl(produto["custo_unitario_centavos"])
                if produto["custo_unitario_centavos"] is not None
                else None,
                "custo_centavos": produto["custo_unitario_centavos"],
                "preco_venda": fmt_brl(produto["preco_venda_centavos"])
                if produto["preco_venda_centavos"] is not None
                else None,
                "categoria": produto["categoria"],
                "estoque": produto["estoque"],
            }
            for produto in produtos
        ],
        "sem_custo": [p["sku"] for p in produtos if p["custo_unitario_centavos"] is None],
    }


def registrar_custo(
    conn: sqlite3.Connection,
    sku: str,
    custo: object,
    preco_venda: object = None,
    nome: str | None = None,
) -> dict:
    sku = (sku or "").strip()
    if not sku:
        raise ValueError("sku obrigatorio")
    custo_centavos = para_centavos(parse_valor(custo))
    if custo_centavos is None:
        raise ValueError("custo invalido (ex.: 12.50 ou 'R$ 12,50')")
    preco_centavos = para_centavos(parse_valor(preco_venda)) if preco_venda not in (None, "") else None

    existente = conn.execute("SELECT sku FROM produtos WHERE sku=?", (sku,)).fetchone()
    conn.execute(
        "INSERT INTO produtos (sku, nome, custo_unitario_centavos, preco_venda_centavos, "
        "ativo, atualizado_em) VALUES (?,?,?,?,1,datetime('now')) "
        "ON CONFLICT(sku) DO UPDATE SET "
        "custo_unitario_centavos=excluded.custo_unitario_centavos, "
        "preco_venda_centavos=COALESCE(excluded.preco_venda_centavos, produtos.preco_venda_centavos), "
        "nome=COALESCE(excluded.nome, produtos.nome), atualizado_em=datetime('now')",
        (sku, nome, custo_centavos, preco_centavos),
    )
    # custo e retroativo por padrao: atualiza o snapshot dos itens ja importados
    # para que os relatorios de meses anteriores reflitam o custo correto.
    cursor = conn.execute(
        "UPDATE itens_pedido SET custo_unitario_centavos=? WHERE sku=?",
        (custo_centavos, sku),
    )
    return {
        "sku": sku,
        "acao": "atualizado" if existente else "criado",
        "custo": fmt_brl(custo_centavos),
        "preco_venda": fmt_brl(preco_centavos) if preco_centavos is not None else None,
        "itens_atualizados": cursor.rowcount,
        "observacao": "o custo foi aplicado retroativamente aos pedidos ja importados",
    }


__all__ = ["listar_pedidos", "listar_produtos", "registrar_custo"]
