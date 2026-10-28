"""Importadores de planilhas."""

from __future__ import annotations

from pathlib import Path

from ..dominio import ResultadoImportacao
from .contas import importar_contas
from .desempenho import importar_desempenho
from .estoque import importar_estoque
from .pedidos import classificar_situacao, importar_pedidos
from .produtos import importar_produtos
from .repasses import importar_repasses

TIPOS = {
    "pedidos": "pedidos (vendas)",
    "contas": "contas a pagar/receber",
    "custos": "custos por SKU",
    "repasses": "repasses recebidos",
    "estoque": "posicao de estoque",
    "desempenho": "desempenho diario de vendas",
}


def importar(
    conn,
    tipo: str,
    caminho: str | Path,
    marketplace: str | None = None,
    conta: str = "principal",
    dry_run: bool = False,
) -> ResultadoImportacao:
    """Despacha para o importador certo. ``tipo`` esta em ``TIPOS``."""
    tipo = (tipo or "").strip().lower()
    if tipo == "pedidos":
        return importar_pedidos(conn, caminho, marketplace=marketplace, conta=conta, dry_run=dry_run)
    if tipo == "contas":
        return importar_contas(conn, caminho, dry_run=dry_run)
    if tipo in {"custos", "produtos"}:
        return importar_produtos(conn, caminho, dry_run=dry_run)
    if tipo == "repasses":
        return importar_repasses(
            conn, caminho, marketplace=marketplace or "shopee", conta=conta, dry_run=dry_run
        )
    if tipo == "estoque":
        return importar_estoque(conn, caminho, dry_run=dry_run)
    if tipo == "desempenho":
        return importar_desempenho(conn, caminho, canal=marketplace, dry_run=dry_run)
    raise ValueError(
        f"tipo de importacao desconhecido: {tipo!r}. Use um de: " + ", ".join(TIPOS)
    )


__all__ = [
    "TIPOS",
    "classificar_situacao",
    "importar",
    "importar_contas",
    "importar_desempenho",
    "importar_estoque",
    "importar_pedidos",
    "importar_produtos",
    "importar_repasses",
]
