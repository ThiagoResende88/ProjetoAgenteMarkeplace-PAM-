"""Tipos de dominio usados na importacao."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


@dataclass
class ItemImportado:
    sku: str
    nome: str | None
    quantidade: int
    preco_unitario_centavos: int
    custo_unitario_centavos: int | None = None


@dataclass
class PedidoImportado:
    marketplace: str
    conta_id: int
    pedido_externo: str
    status: str
    situacao: str
    data_pedido: dt.date
    data_entrega: dt.date | None
    itens_total_centavos: int
    desconto_centavos: int
    frete_cobrado_centavos: int
    frete_pago_centavos: int
    comissao_centavos: int
    taxa_servico_centavos: int
    cupom_centavos: int
    imposto_centavos: int
    repasse_centavos: int | None
    itens: list[ItemImportado] = field(default_factory=list)
    moeda: str = "BRL"


@dataclass
class ResultadoImportacao:
    tipo: str
    arquivo: str
    marketplace: str | None = None
    conta: str | None = None
    linhas: int = 0
    inseridos: int = 0
    atualizados: int = 0
    ignorados: int = 0
    avisos: list[str] = field(default_factory=list)
    mapeamento: dict[str, str | None] = field(default_factory=dict)
    amostra: list[dict] = field(default_factory=list)
    secoes: dict = field(default_factory=dict)

    def adicionar_aviso(self, texto: str) -> None:
        if len(self.avisos) < 40:
            self.avisos.append(texto)

    def para_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "arquivo": self.arquivo,
            "marketplace": self.marketplace,
            "conta": self.conta,
            "linhas_lidas": self.linhas,
            "inseridos": self.inseridos,
            "atualizados": self.atualizados,
            "ignorados": self.ignorados,
            "avisos": self.avisos,
            "mapeamento_colunas": self.mapeamento,
            "amostra": self.amostra,
            "secoes": self.secoes,
        }
