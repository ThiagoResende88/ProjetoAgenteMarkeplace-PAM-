"""Importacao de posicao de estoque por SKU."""

from __future__ import annotations

from pathlib import Path

from .. import db
from ..datas import iso, parse_data
from ..dinheiro import parse_valor
from ..dominio import ResultadoImportacao
from . import colunas as col
from .leitor import ler_tabela


def importar_estoque(
    conn,
    caminho: str | Path,
    dry_run: bool = False,
) -> ResultadoImportacao:
    caminho = Path(caminho).expanduser()
    tabela = ler_tabela(caminho)
    resultado = ResultadoImportacao(tipo="estoque", arquivo=str(caminho))
    resultado.avisos.extend(tabela.avisos)

    mapa = col.MapaColunas(tabela.colunas, col.ALIASES_ESTOQUE)
    resultado.mapeamento = mapa.mapeamento()
    faltando = mapa.faltando(["sku", "quantidade"])
    if faltando:
        raise ValueError(
            "colunas obrigatorias nao encontradas: "
            + ", ".join(faltando)
            + ". Colunas do arquivo: "
            + ", ".join(tabela.colunas[:25])
        )

    for linha in tabela.linhas:
        resultado.linhas += 1
        sku = (mapa.valor(linha, "sku") or "").strip()
        quantidade = parse_valor(mapa.valor(linha, "quantidade"))
        if not sku or quantidade is None:
            resultado.ignorados += 1
            continue
        qtd = max(0, int(quantidade))
        data = parse_data(mapa.valor(linha, "atualizado_em")) or None
        if dry_run:
            resultado.secoes.setdefault("estoque_preview", []).append(
                {"sku": sku, "quantidade": qtd}
            )
            continue
        conn.execute(
            "INSERT INTO estoque (sku, quantidade, atualizado_em) VALUES (?,?,?) "
            "ON CONFLICT(sku) DO UPDATE SET quantidade=excluded.quantidade, "
            "atualizado_em=COALESCE(excluded.atualizado_em, estoque.atualizado_em)",
            (sku, qtd, iso(data)),
        )
        resultado.atualizados += 1

    if not dry_run:
        db.registrar_importacao(
            conn,
            {
                "arquivo": str(caminho),
                "tipo": "estoque",
                "linhas": resultado.linhas,
                "inseridos": 0,
                "atualizados": resultado.atualizados,
                "ignorados": resultado.ignorados,
                "avisos": " | ".join(resultado.avisos[:10]),
            },
        )
    return resultado
