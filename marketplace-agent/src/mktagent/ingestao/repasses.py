"""Importacao de repasses/pagamentos recebidos dos marketplaces."""

from __future__ import annotations

from pathlib import Path

from .. import db
from ..datas import iso, parse_data
from ..dinheiro import para_centavos, parse_valor
from ..dominio import ResultadoImportacao
from . import colunas as col
from .leitor import ler_tabela


def importar_repasses(
    conn,
    caminho: str | Path,
    marketplace: str = "shopee",
    conta: str = "principal",
    dry_run: bool = False,
) -> ResultadoImportacao:
    caminho = Path(caminho).expanduser()
    tabela = ler_tabela(caminho)
    resultado = ResultadoImportacao(
        tipo="repasses", arquivo=str(caminho), marketplace=marketplace, conta=conta
    )
    resultado.avisos.extend(tabela.avisos)

    mapa = col.MapaColunas(tabela.colunas, col.ALIASES_REPASSES)
    resultado.mapeamento = mapa.mapeamento()
    faltando = mapa.faltando(["data", "valor"])
    if faltando:
        raise ValueError(
            "colunas obrigatorias nao encontradas: "
            + ", ".join(faltando)
            + ". Colunas do arquivo: "
            + ", ".join(tabela.colunas[:25])
        )

    marketplace = marketplace.strip().lower()
    conta_id = 0 if dry_run else db.obter_conta(conn, marketplace, conta)

    for linha in tabela.linhas:
        resultado.linhas += 1
        data = parse_data(mapa.valor(linha, "data"))
        valor = para_centavos(parse_valor(mapa.valor(linha, "valor")))
        if data is None or valor is None:
            resultado.ignorados += 1
            continue
        referencia = (mapa.valor(linha, "referencia") or "").strip() or None
        pedido = (mapa.valor(linha, "pedido") or "").strip() or None

        if dry_run:
            resultado.secoes.setdefault("repasses_preview", []).append(
                {"data": iso(data), "valor_centavos": valor, "referencia": referencia}
            )
            continue

        existente = conn.execute(
            "SELECT id FROM repasses WHERE conta_id=? AND data=? AND valor_centavos=? "
            "AND COALESCE(referencia,'') = COALESCE(?,'')",
            (conta_id, iso(data), valor, referencia),
        ).fetchone()
        if existente:
            resultado.atualizados += 1
            conn.execute(
                "UPDATE repasses SET pedido_externo=COALESCE(?, pedido_externo), origem=? "
                "WHERE id=?",
                (pedido, caminho.name, int(existente["id"])),
            )
            continue
        conn.execute(
            "INSERT INTO repasses (conta_id, data, valor_centavos, referencia, "
            "pedido_externo, origem) VALUES (?,?,?,?,?,?)",
            (conta_id, iso(data), valor, referencia, pedido, caminho.name),
        )
        resultado.inseridos += 1

    if not dry_run:
        db.registrar_importacao(
            conn,
            {
                "arquivo": str(caminho),
                "tipo": "repasses",
                "marketplace": marketplace,
                "conta": conta,
                "linhas": resultado.linhas,
                "inseridos": resultado.inseridos,
                "atualizados": resultado.atualizados,
                "ignorados": resultado.ignorados,
                "avisos": " | ".join(resultado.avisos[:10]),
            },
        )
    return resultado
