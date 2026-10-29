"""Relatorios financeiros e operacionais."""

from .alertas import alertas, cobertura_estoque
from .caixa import criar_conta, fluxo_caixa, marcar_paga, resumo_contas
from .consultas import dados_disponiveis
from .dre import comparativo, dre
from .insights import insights
from .margem import margem_por_sku

__all__ = [
    "alertas",
    "cobertura_estoque",
    "comparativo",
    "criar_conta",
    "dados_disponiveis",
    "dre",
    "fluxo_caixa",
    "insights",
    "marcar_paga",
    "margem_por_sku",
    "resumo_contas",
]
