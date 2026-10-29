"""Mapeamento de colunas: tolera cabecalhos diferentes de cada painel/versao.

Cada campo logico tem uma lista de aliases (PT-BR e EN). O mapeamento tenta
primeiro igualdade exata (normalizada), depois "contem", e nunca reaproveita
a mesma coluna para dois campos.
"""

from __future__ import annotations

import re
import unicodedata


def normalizar(texto: str) -> str:
    """``Preço Unitário (R$)`` -> ``preco_unitario_r``."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")


class MapaColunas:
    def __init__(self, cabecalhos: list[str], aliases: dict[str, list[str]]):
        self.cabecalhos = cabecalhos
        self.aliases = aliases
        self.normalizados = {normalizar(c): c for c in cabecalhos if normalizar(c)}
        self._usadas: set[str] = set()
        self._origem: dict[str, str] = {}
        self._mapear()

    def _mapear(self) -> None:
        # 1a passada: igualdade exata
        for campo, lista in self.aliases.items():
            for mesmo in [campo, *lista]:
                chave = normalizar(mesmo)
                if chave in self.normalizados:
                    cabecalho = self.normalizados[chave]
                    if cabecalho not in self._usadas:
                        self._origem[campo] = cabecalho
                        self._usadas.add(cabecalho)
                        break
        # 2a passada: "contem", do alias mais longo para o mais curto
        for campo, lista in self.aliases.items():
            if campo in self._origem:
                continue
            candidatos = sorted(
                (normalizar(a) for a in [campo, *lista] if a),
                key=len,
                reverse=True,
            )
            for alias in candidatos:
                if len(alias) < 4:
                    continue
                for chave, cabecalho in sorted(
                    self.normalizados.items(), key=lambda item: -len(item[0])
                ):
                    if cabecalho in self._usadas:
                        continue
                    if alias == chave or (alias in chave and len(alias) >= 5):
                        self._origem[campo] = cabecalho
                        self._usadas.add(cabecalho)
                        break
                if campo in self._origem:
                    break

    def mapear_exato(self, campo: str, coluna: str | None) -> None:
        """Força um campo para uma coluna específica (usado em exports nativos)."""
        if not coluna:
            return
        atual = self._origem.get(campo)
        if atual and atual != coluna:
            self._usadas.discard(atual)
        self._origem[campo] = coluna
        self._usadas.add(coluna)

    # ── consulta ────────────────────────────────────────────────────────────

    def tem(self, campo: str) -> bool:
        return campo in self._origem

    def coluna(self, campo: str) -> str | None:
        return self._origem.get(campo)

    def valor(self, linha: dict[str, str], campo: str) -> str | None:
        coluna = self._origem.get(campo)
        if not coluna:
            return None
        valor = linha.get(coluna)
        if valor is None:
            return None
        valor = str(valor).strip()
        return valor or None

    def faltando(self, obrigatorios: list[str]) -> list[str]:
        return [campo for campo in obrigatorios if campo not in self._origem]

    def mapeamento(self) -> dict[str, str | None]:
        return {campo: self._origem.get(campo) for campo in self.aliases}

    def nao_usadas(self) -> list[str]:
        return [c for c in self.cabecalhos if c not in self._usadas and normalizar(c)]


def sugerir_marketplace(cabecalhos: list[str]) -> tuple[str | None, str]:
    """Tenta adivinhar o marketplace pelos nomes das colunas."""
    normalizados = [normalizar(c) for c in cabecalhos]
    juntos = " ".join(normalizados)
    if "shopee" in juntos:
        return "shopee", "cabecalho menciona Shopee"
    if "tiktok" in juntos:
        return "tiktok", "cabecalho menciona TikTok"

    pistas_shopee = {
        "order_sn",
        "numero_de_referencia_do_pedido",
        "taxa_de_comissao",
        "taxa_de_servico",
        "nome_do_produto",
        "hora_do_pagamento",
        "opcao_de_envio",
    }
    pistas_tiktok = {
        "order_id",
        "order_status",
        "seller_sku",
        "order_amount",
        "platform_commission",
        "created_time",
        "payment_fee",
        "settlement_amount",
    }
    pontos_shopee = sum(1 for p in pistas_shopee if p in juntos)
    pontos_tiktok = sum(1 for p in pistas_tiktok if p in juntos)
    if pontos_shopee > pontos_tiktok:
        return "shopee", f"{pontos_shopee} colunas tipicas da Shopee"
    if pontos_tiktok > pontos_shopee:
        return "tiktok", f"{pontos_tiktok} colunas tipicas do TikTok Shop"
    return None, "cabecalho sem pistas claras"


# ── aliases canonicos ───────────────────────────────────────────────────────

ALIASES_PEDIDOS: dict[str, list[str]] = {
    "pedido": [
        "pedido",
        "numero do pedido",
        "n do pedido",
        "no do pedido",
        "numero pedido",
        "id do pedido",
        "pedido externo",
        "order id",
        "order no",
        "order sn",
        "order number",
        "numero de referencia do pedido",
        "order sn list",
        "pedido_id",
        "id do pedido",
    ],
    "status": [
        "status",
        "status do pedido",
        "situacao",
        "situacao do pedido",
        "order status",
        "order_status",
        "status do pedido marketplace",
    ],
    "data_pedido": [
        "data do pedido",
        "data de criacao",
        "data criacao",
        "data",
        "data da compra",
        "created time",
        "create time",
        "order create time",
        "data de criacao do pedido",
        "hora do pagamento",
        "paid time",
        "order_created_at",
        "data de criação do pedido",
        "data criacao do pedido",
    ],
    "data_entrega": [
        "data de entrega",
        "data de conclusao",
        "data entregue",
        "delivered time",
        "delivery time",
        "completed time",
        "data de finalizacao",
    ],
    "sku": [
        "sku",
        "sku do produto",
        "seller sku",
        "product sku",
        "sku do vendedor",
        "codigo do produto",
        "sku id",
        "id do sku",
        "item sku",
        "seller_sku",
        "número de referência sku",
        "numero de referencia sku",
        "nº de referência do sku principal",
    ],
    "cliente": [
        "cliente",
        "customer",
        "comprador",
        "buyer",
        "buyer name",
        "cliente nome",
        "razao social",
        "nome de usuário (comprador)",
        "nome de usuario (comprador)",
    ],
    "produto": [
        "produto",
        "nome do produto",
        "product name",
        "nome produto",
        "item name",
        "descricao do produto",
        "titulo do produto",
    ],
    "quantidade": [
        "quantidade",
        "qtd",
        "qty",
        "quantity",
        "quantidade do produto",
        "item quantity",
        "unidades",
    ],
    "preco_unitario": [
        "preco unitario",
        "preco",
        "valor unitario",
        "unit price",
        "item price",
        "sku unit price",
        "preco do item",
        "preco de venda",
        "price",
        "preço acordado",
        "preco acordado",
    ],
    "itens_total": [
        "valor total dos produtos",
        "total dos produtos",
        "valor dos produtos",
        "subtotal do pedido",
        "subtotal",
        "valor total do pedido",
        "order amount",
        "total do pedido",
        "valor total",
        "receita de produtos",
        "subtotal do produto",
    ],
    "desconto": [
        "desconto",
        "desconto total",
        "desconto do vendedor",
        "desconto aplicado",
        "order discount",
        "seller discount",
        "total discount",
        "desconto da loja",
        "voucher do vendedor",
    ],
    "frete_cobrado": [
        "frete cobrado",
        "frete do comprador",
        "frete pago pelo comprador",
        "buyer shipping fee",
        "shipping fee paid by buyer",
        "valor do frete",
        "frete",
        "frete recebido",
    ],
    "frete_pago": [
        "frete pago pelo vendedor",
        "frete pago",
        "custo de frete",
        "seller shipping fee",
        "shipping fee paid by seller",
        "frete real",
        "custo do envio",
        "shipping cost",
    ],
    "comissao": [
        "comissao",
        "taxa de comissao",
        "commission",
        "platform commission",
        "taxa comissao",
        "comissao do marketplace",
        "commission fee",
        "taxa de comissão líquida",
        "taxa de comissao liquida",
    ],
    "taxa_servico": [
        "taxa de servico",
        "taxa de transacao",
        "taxa de processamento",
        "service fee",
        "transaction fee",
        "payment fee",
        "taxa de pagamento",
        "taxa administrativa",
        "taxa de serviço líquida",
        "taxa de servico liquida",
    ],
    "cupom": [
        "cupom",
        "cupom do vendedor",
        "cupom aplicado",
        "voucher",
        "voucher do vendedor",
        "seller voucher",
        "desconto de cupom",
        "cupom do vendedor",
    ],
    "imposto": [
        "imposto",
        "tax",
        "icms",
        "taxa de imposto",
        "impostos",
        "valor do imposto",
    ],
    "repasse": [
        "repasse",
        "valor liquido",
        "valor do repasse",
        "valor a receber",
        "receita liquida",
        "payout",
        "net amount",
        "settlement amount",
        "total settlement",
        "valor liquido do pedido",
    ],
}

ALIASES_CONTAS: dict[str, list[str]] = {
    "tipo": ["tipo", "tipo de conta", "pagar ou receber", "natureza"],
    "descricao": [
        "descricao",
        "conta",
        "nome",
        "titulo",
        "lancamento",
        "historico",
        "descricao da conta",
        "item",
    ],
    "categoria": ["categoria", "grupo", "centro de custo", "tipo de despesa", "classificacao"],
    "valor": [
        "valor",
        "valor total",
        "montante",
        "total",
        "valor da conta",
        "valor a pagar",
        "valor a receber",
    ],
    "vencimento": [
        "vencimento",
        "data de vencimento",
        "vence em",
        "data vencimento",
        "due date",
        "prazo",
    ],
    "pago_em": [
        "pago em",
        "data de pagamento",
        "data pagamento",
        "pagamento",
        "pago",
        "paid at",
        "baixa",
    ],
    "marketplace": ["marketplace", "canal", "loja", "marketplace relacionado"],
    "recorrente": ["recorrente", "fixa", "mensal", "repetir"],
    "observacao": ["observacao", "observacoes", "nota", "detalhe", "obs"],
}

ALIASES_PRODUTOS: dict[str, list[str]] = {
    "sku": ["sku", "codigo", "codigo do produto", "seller sku", "sku do produto", "product sku"],
    "nome": ["nome", "produto", "nome do produto", "descricao", "product name", "titulo"],
    "custo": [
        "custo",
        "custo unitario",
        "cmv",
        "valor de custo",
        "custo do produto",
        "preco de custo",
        "custo unitario do produto",
    ],
    "preco_venda": [
        "preco de venda",
        "preco",
        "preco venda",
        "valor de venda",
        "preco unitario",
        "sale price",
    ],
    "categoria": ["categoria", "grupo", "linha"],
}

ALIASES_REPASSES: dict[str, list[str]] = {
    "data": ["data", "data do repasse", "data de pagamento", "payout date", "settlement time"],
    "valor": ["valor", "valor do repasse", "valor liquido", "payout", "net amount", "total"],
    "referencia": [
        "referencia",
        "id do repasse",
        "identificador",
        "payout id",
        "settlement id",
        "descricao",
    ],
    "pedido": ["pedido", "numero do pedido", "order id", "order sn", "pedido externo"],
}

ALIASES_ESTOQUE: dict[str, list[str]] = {
    "sku": ["sku", "codigo", "codigo do produto", "seller sku", "sku do produto"],
    "quantidade": ["quantidade", "estoque", "qtd", "quantity", "saldo", "disponivel"],
    "atualizado_em": ["atualizado em", "data", "ultima atualizacao", "updated at"],
}
