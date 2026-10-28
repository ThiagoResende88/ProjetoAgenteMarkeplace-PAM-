"""Fluxo de caixa projetado a partir das contas a pagar/receber.

Nao existe saldo bancario no sistema: o que este relatorio mostra e o
compromisso ja cadastrado (contas com vencimento na janela) dividido por
semana, mais o que ja esta vencido e ainda em aberto.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from ..datas import dias_ate, fmt_data_br, hoje, inicio_semana
from ..dinheiro import fmt_brl, parse_valor


def fluxo_caixa(conn: sqlite3.Connection, dias: int = 30) -> dict:
    dias = max(1, int(dias))
    referencia = hoje()
    fim = referencia + dt.timedelta(days=dias)

    contas = list(
        conn.execute(
            "SELECT * FROM contas_financeiras WHERE pago_em IS NULL "
            "AND vencimento <= ? ORDER BY vencimento",
            (fim.isoformat(),),
        )
    )
    vencidas = [c for c in contas if c["vencimento"] < referencia.isoformat()]
    futuras = [c for c in contas if c["vencimento"] >= referencia.isoformat()]

    entradas = sum(int(c["valor_centavos"]) for c in futuras if c["tipo"] == "receber")
    saidas = sum(int(c["valor_centavos"]) for c in futuras if c["tipo"] == "pagar")
    vencido_pagar = sum(int(c["valor_centavos"]) for c in vencidas if c["tipo"] == "pagar")
    vencido_receber = sum(int(c["valor_centavos"]) for c in vencidas if c["tipo"] == "receber")

    # agrupa as futuras por semana
    semanas: dict[str, dict] = {}
    for conta in futuras:
        data = dt.date.fromisoformat(conta["vencimento"])
        chave = inicio_semana(data).isoformat()
        bloco = semanas.setdefault(
            chave,
            {
                "inicio": chave,
                "fim": (dt.date.fromisoformat(chave) + dt.timedelta(days=6)).isoformat(),
                "entradas": 0,
                "saidas": 0,
                "contas": [],
            },
        )
        valor = int(conta["valor_centavos"])
        if conta["tipo"] == "receber":
            bloco["entradas"] += valor
        else:
            bloco["saidas"] += valor
        bloco["contas"].append(
            {
                "id": conta["id"],
                "tipo": conta["tipo"],
                "descricao": conta["descricao"],
                "categoria": conta["categoria"],
                "vencimento": conta["vencimento"],
                "valor": fmt_brl(valor),
                "valor_centavos": valor,
            }
        )

    lista_semanas = []
    for chave in sorted(semanas):
        bloco = semanas[chave]
        bloco["saldo"] = bloco["entradas"] - bloco["saidas"]
        bloco["rotulo"] = f"{fmt_data_br(bloco['inicio'])} a {fmt_data_br(bloco['fim'])}"
        bloco["fmt"] = {
            "entradas": fmt_brl(bloco["entradas"]),
            "saidas": fmt_brl(bloco["saidas"]),
            "saldo": fmt_brl(bloco["saldo"]),
        }
        lista_semanas.append(bloco)

    ultimos_repasses = conn.execute(
        "SELECT COALESCE(SUM(valor_centavos), 0) FROM repasses WHERE data >= ?",
        ((referencia - dt.timedelta(days=30)).isoformat(),),
    ).fetchone()[0]

    resposta = {
        "janela_dias": dias,
        "hoje": referencia.isoformat(),
        "ate": fim.isoformat(),
        "entradas_previstas": fmt_brl(entradas),
        "entradas_previstas_centavos": entradas,
        "saidas_previstas": fmt_brl(saidas),
        "saidas_previstas_centavos": saidas,
        "saldo_do_periodo": fmt_brl(entradas - saidas),
        "saldo_do_periodo_centavos": entradas - saidas,
        "vencido_a_pagar": fmt_brl(vencido_pagar),
        "vencido_a_pagar_centavos": vencido_pagar,
        "vencido_a_receber": fmt_brl(vencido_receber),
        "vencido_a_receber_centavos": vencido_receber,
        "contas_vencidas": [
            {
                "id": c["id"],
                "tipo": c["tipo"],
                "descricao": c["descricao"],
                "vencimento": c["vencimento"],
                "dias_atraso": -dias_ate(c["vencimento"], referencia),
                "valor": fmt_brl(int(c["valor_centavos"])),
            }
            for c in vencidas
        ],
        "semanas": lista_semanas,
        "repasses_recebidos_30d_centavos": int(ultimos_repasses or 0),
        "repasses_recebidos_30d": fmt_brl(int(ultimos_repasses or 0)),
        "observacoes": [
            "Projecao baseada apenas em contas cadastradas (nao inclui saldo bancario "
            "nem repasses futuros do marketplace).",
            "Contas vencidas aparecem separadas do periodo.",
        ],
    }
    negativas = [semana for semana in lista_semanas if semana["saldo"] < 0]
    if negativas:
        resposta.setdefault("avisos", []).append(
            "Semana(s) com saldo negativo: "
            + "; ".join(
                f"{s['rotulo']} ({s['fmt']['saldo']})" for s in negativas[:4]
            )
        )
    if vencido_pagar:
        resposta.setdefault("avisos", []).append(
            f"Existe {fmt_brl(vencido_pagar)} vencido a pagar."
        )
    return resposta


def resumo_contas(conn: sqlite3.Connection, status: str | None = None) -> dict:
    """Lista contas a pagar/receber com filtro de status."""
    referencia = hoje().isoformat()
    sql = "SELECT * FROM contas_financeiras"
    parametros: list = []
    if status == "aberta":
        sql += " WHERE pago_em IS NULL AND vencimento >= ?"
        parametros.append(referencia)
    elif status == "vencida":
        sql += " WHERE pago_em IS NULL AND vencimento < ?"
        parametros.append(referencia)
    elif status == "paga":
        sql += " WHERE pago_em IS NOT NULL"
    sql += " ORDER BY vencimento"
    contas = list(conn.execute(sql, parametros))

    total_pagar = sum(int(c["valor_centavos"]) for c in contas if c["tipo"] == "pagar")
    total_receber = sum(int(c["valor_centavos"]) for c in contas if c["tipo"] == "receber")
    return {
        "filtro": status or "todas",
        "quantidade": len(contas),
        "total_a_pagar": fmt_brl(total_pagar),
        "total_a_pagar_centavos": total_pagar,
        "total_a_receber": fmt_brl(total_receber),
        "total_a_receber_centavos": total_receber,
        "contas": [
            {
                "id": c["id"],
                "tipo": c["tipo"],
                "descricao": c["descricao"],
                "categoria": c["categoria"],
                "marketplace": c["marketplace"],
                "valor": fmt_brl(int(c["valor_centavos"])),
                "valor_centavos": int(c["valor_centavos"]),
                "vencimento": c["vencimento"],
                "vencimento_fmt": fmt_data_br(c["vencimento"]),
                "pago_em": c["pago_em"],
                "status": "paga" if c["pago_em"] else (
                    "vencida" if c["vencimento"] < referencia else "aberta"
                ),
                "dias_para_vencer": dias_ate(c["vencimento"]),
            }
            for c in contas
        ],
    }


def criar_conta(
    conn: sqlite3.Connection,
    tipo: str,
    descricao: str,
    valor: object,
    vencimento: object,
    categoria: str = "outros",
    marketplace: str | None = None,
    observacao: str | None = None,
) -> dict:
    """Cadastra uma conta a pagar/receber. Aceita valor em texto e data ISO/BR."""
    from ..datas import parse_data
    from ..dinheiro import para_centavos

    tipo = (tipo or "pagar").strip().lower()
    if tipo not in {"pagar", "receber"}:
        raise ValueError("tipo deve ser 'pagar' ou 'receber'")
    valor_centavos = para_centavos(parse_valor(valor))
    if not valor_centavos:
        raise ValueError("valor invalido")
    data = parse_data(vencimento)
    if data is None:
        raise ValueError("vencimento invalido (use 2026-11-05 ou 05/11/2026)")
    if not descricao or not str(descricao).strip():
        raise ValueError("descricao obrigatoria")

    existente = conn.execute(
        "SELECT id FROM contas_financeiras WHERE tipo=? AND descricao=? AND "
        "valor_centavos=? AND vencimento=?",
        (tipo, str(descricao).strip(), valor_centavos, data.isoformat()),
    ).fetchone()
    if existente:
        return {"id": int(existente["id"]), "status": "ja_existia"}

    cursor = conn.execute(
        "INSERT INTO contas_financeiras (tipo, descricao, categoria, marketplace, "
        "valor_centavos, vencimento, status, observacao, origem) "
        "VALUES (?,?,?,?,?,?, 'aberta', ?, 'manual')",
        (
            tipo,
            str(descricao).strip(),
            categoria or "outros",
            (marketplace or "").strip().lower() or None,
            valor_centavos,
            data.isoformat(),
            observacao,
        ),
    )
    return {
        "id": int(cursor.lastrowid),
        "status": "criada",
        "tipo": tipo,
        "descricao": descricao,
        "valor": fmt_brl(valor_centavos),
        "vencimento": data.isoformat(),
    }


def marcar_paga(conn: sqlite3.Connection, conta_id: int, pago_em: object = None) -> dict:
    from ..datas import parse_data
    from ..dinheiro import fmt_brl

    linha = conn.execute(
        "SELECT * FROM contas_financeiras WHERE id = ?", (conta_id,)
    ).fetchone()
    if not linha:
        raise ValueError(f"conta {conta_id} nao encontrada")
    if linha["pago_em"]:
        return {"id": conta_id, "status": "ja_estava_paga", "pago_em": linha["pago_em"]}
    data = parse_data(pago_em) or hoje()
    conn.execute(
        "UPDATE contas_financeiras SET pago_em=?, status='paga', "
        "atualizado_em=datetime('now') WHERE id=?",
        (data.isoformat(), conta_id),
    )
    return {
        "id": conta_id,
        "status": "paga",
        "descricao": linha["descricao"],
        "valor": fmt_brl(int(linha["valor_centavos"])),
        "pago_em": data.isoformat(),
    }


__all__ = ["fluxo_caixa", "resumo_contas", "criar_conta", "marcar_paga"]
