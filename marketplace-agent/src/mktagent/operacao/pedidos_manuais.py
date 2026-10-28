"""Pedidos manuais (B2B, consignacao, venda direta) sem planilha.

Substitui o controle manual: cria o pedido com cliente/itens, muda status e
deixa o historico no banco. Serve para o fluxo "BARBEARIA pediu 10 tubetes".
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from .. import db
from ..config import normalizar_canal
from ..datas import iso, parse_data
from ..dinheiro import fmt_brl, para_centavos, parse_valor
from ..ingestao.pedidos import classificar_situacao


def _proximo_id(conn: sqlite3.Connection, canal: str) -> str:
    prefixo = "MOC" if canal in {"consignacao", "direto", "instagram"} else "MAN"
    sequencia = conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0] + 1
    while True:
        candidato = f"{prefixo}-{sequencia:04d}"
        existe = conn.execute(
            "SELECT 1 FROM pedidos WHERE pedido_externo = ?", (candidato,)
        ).fetchone()
        if not existe:
            return candidato
        sequencia += 1


def criar_pedido(
    conn: sqlite3.Connection,
    canal: str = "consignacao",
    cliente: str | None = None,
    data: object = None,
    itens: list[dict] | None = None,
    status: str = "Pendente",
    pedido_externo: str | None = None,
    observacao: str | None = None,
) -> dict:
    """Cria um pedido com itens. ``itens`` = [{sku, quantidade, preco_unitario}]."""
    if not itens:
        raise ValueError("informe ao menos um item (sku, quantidade, preco_unitario)")
    canal = normalizar_canal(canal, padrao="consignacao")
    data_pedido = parse_data(data) or dt.date.today()
    situacao = classificar_situacao(status)
    pedido_externo = (pedido_externo or "").strip() or _proximo_id(conn, canal)
    conta_id = db.obter_conta(conn, canal, "principal")

    linhas = []
    for item in itens:
        sku = (item.get("sku") or "").strip()
        if not sku:
            raise ValueError("item sem sku")
        quantidade = int(item.get("quantidade") or 1)
        if quantidade <= 0:
            raise ValueError(f"quantidade invalida para {sku}")
        preco = para_centavos(parse_valor(item.get("preco_unitario")))
        if preco is None:
            preco = para_centavos(parse_valor(item.get("preco")))
        if preco is None:
            raise ValueError(f"preco invalido para {sku}")
        custo = conn.execute(
            "SELECT custo_unitario_centavos FROM produtos WHERE sku=?", (sku,)
        ).fetchone()
        linhas.append(
            {
                "sku": sku,
                "quantidade": quantidade,
                "preco_unitario_centavos": preco,
                "custo_unitario_centavos": custo["custo_unitario_centavos"] if custo else None,
            }
        )

    itens_total = sum(
        linha["quantidade"] * linha["preco_unitario_centavos"] for linha in linhas
    )

    if conn.execute(
        "SELECT 1 FROM pedidos WHERE marketplace=? AND pedido_externo=?",
        (canal, pedido_externo),
    ).fetchone():
        raise ValueError(f"ja existe pedido {pedido_externo} em {canal}")

    cursor = conn.execute(
        "INSERT INTO pedidos (conta_id, marketplace, pedido_externo, cliente, status, "
        "situacao, data_pedido, itens_total_centavos) VALUES (?,?,?,?,?,?,?,?)",
        (
            conta_id,
            canal,
            pedido_externo,
            (cliente or "").strip() or None,
            status,
            situacao,
            iso(data_pedido),
            itens_total,
        ),
    )
    pedido_id = int(cursor.lastrowid)
    for linha in linhas:
        conn.execute(
            "INSERT INTO itens_pedido (pedido_id, sku, quantidade, "
            "preco_unitario_centavos, custo_unitario_centavos) VALUES (?,?,?,?,?)",
            (
                pedido_id,
                linha["sku"],
                linha["quantidade"],
                linha["preco_unitario_centavos"],
                linha["custo_unitario_centavos"],
            ),
        )

    return {
        "acao": "pedido_criado",
        "pedido": pedido_externo,
        "canal": canal,
        "cliente": cliente,
        "data": iso(data_pedido),
        "situacao": situacao,
        "status": status,
        "itens": linhas,
        "total": fmt_brl(itens_total),
        "total_centavos": itens_total,
        "observacao": observacao,
        "proximo_passo": (
            "Atualize o status quando pagar/entregar: "
            f"atualizar_status_pedido(pedido_externo='{pedido_externo}', status='Pago')"
        ),
    }


def atualizar_status_pedido(
    conn: sqlite3.Connection,
    pedido_externo: str,
    status: str,
    canal: str | None = None,
) -> dict:
    """Atualiza status bruto e situacao financeira de um pedido."""
    pedido_externo = (pedido_externo or "").strip()
    if not pedido_externo:
        raise ValueError("pedido_externo obrigatorio")
    situacao = classificar_situacao(status)
    if situacao == "desconhecido":
        raise ValueError(
            f"status {status!r} nao reconhecido. Use algo como Pendente, Pago, "
            "Faturado, Entregue, Cancelado."
        )

    sql = "SELECT * FROM pedidos WHERE pedido_externo = ?"
    parametros: list = [pedido_externo]
    if canal:
        sql += " AND marketplace = ?"
        parametros.append(normalizar_canal(canal, padrao="consignacao"))
    linha = conn.execute(sql, parametros).fetchone()
    if not linha:
        raise ValueError(f"pedido {pedido_externo} nao encontrado")

    conn.execute(
        "UPDATE pedidos SET status=?, situacao=?, atualizado_em=datetime('now') WHERE id=?",
        (status, situacao, int(linha["id"])),
    )
    return {
        "acao": "status_atualizado",
        "pedido": pedido_externo,
        "status_anterior": linha["status"],
        "status_novo": status,
        "situacao": situacao,
        "total": fmt_brl(int(linha["itens_total_centavos"])),
        "entra_na_receita": situacao == "aprovado",
    }


__all__ = ["criar_pedido", "atualizar_status_pedido"]
