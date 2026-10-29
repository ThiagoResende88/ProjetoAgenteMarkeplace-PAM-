"""Importacao de custos e precos por SKU (a base para margem real)."""

from __future__ import annotations

from pathlib import Path

from .. import db
from ..dinheiro import para_centavos, parse_valor
from ..dominio import ResultadoImportacao
from . import colunas as col
from .leitor import ler_tabela


def importar_produtos(
    conn,
    caminho: str | Path,
    dry_run: bool = False,
) -> ResultadoImportacao:
    caminho = Path(caminho).expanduser()
    tabela = ler_tabela(caminho)
    resultado = ResultadoImportacao(tipo="custos", arquivo=str(caminho))
    resultado.avisos.extend(tabela.avisos)

    mapa = col.MapaColunas(tabela.colunas, col.ALIASES_PRODUTOS)
    resultado.mapeamento = mapa.mapeamento()
    if not mapa.tem("sku"):
        raise ValueError(
            "coluna de SKU nao encontrada. Colunas do arquivo: "
            + ", ".join(tabela.colunas[:25])
        )
    if not mapa.tem("custo") and not mapa.tem("preco_venda"):
        raise ValueError(
            "precisa de uma coluna de custo (ou de preco de venda). Colunas: "
            + ", ".join(tabela.colunas[:25])
        )

    for linha in tabela.linhas:
        resultado.linhas += 1
        sku = (mapa.valor(linha, "sku") or "").strip()
        if not sku:
            resultado.ignorados += 1
            continue
        custo = para_centavos(parse_valor(mapa.valor(linha, "custo")))
        preco = para_centavos(parse_valor(mapa.valor(linha, "preco_venda")))
        nome = mapa.valor(linha, "nome")
        categoria = mapa.valor(linha, "categoria")
        if custo is None and preco is None:
            resultado.ignorados += 1
            continue
        if custo is not None and custo < 0:
            resultado.ignorados += 1
            resultado.adicionar_aviso(f"SKU {sku}: custo negativo ignorado")
            continue

        if dry_run:
            resultado.secoes.setdefault("produtos_preview", []).append(
                {"sku": sku, "custo_centavos": custo, "preco_centavos": preco}
            )
            continue

        existente = conn.execute("SELECT sku FROM produtos WHERE sku=?", (sku,)).fetchone()
        conn.execute(
            "INSERT INTO produtos (sku, nome, custo_unitario_centavos, preco_venda_centavos, "
            "categoria, ativo, atualizado_em) VALUES (?,?,?,?,?,1,datetime('now')) "
            "ON CONFLICT(sku) DO UPDATE SET "
            "nome=COALESCE(excluded.nome, produtos.nome), "
            "custo_unitario_centavos=COALESCE(excluded.custo_unitario_centavos, produtos.custo_unitario_centavos), "
            "preco_venda_centavos=COALESCE(excluded.preco_venda_centavos, produtos.preco_venda_centavos), "
            "categoria=COALESCE(excluded.categoria, produtos.categoria), "
            "atualizado_em=datetime('now')",
            (sku, nome, custo, preco, categoria),
        )
        if existente:
            resultado.atualizados += 1
        else:
            resultado.inseridos += 1

    if not dry_run:
        db.registrar_importacao(
            conn,
            {
                "arquivo": str(caminho),
                "tipo": "custos",
                "linhas": resultado.linhas,
                "inseridos": resultado.inseridos,
                "atualizados": resultado.atualizados,
                "ignorados": resultado.ignorados,
                "avisos": " | ".join(resultado.avisos[:10]),
            },
        )
    return resultado
