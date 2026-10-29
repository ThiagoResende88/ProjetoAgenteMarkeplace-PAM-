"""Testes de importacao: agregacao por pedido, upsert idempotente e qualidade."""

from __future__ import annotations

import unittest

from mktagent.ingestao.pedidos import classificar_situacao
from tests.apoio import CasoBase

CABECALHO_TEMPLATE = [
    "pedido",
    "status",
    "data_pedido",
    "sku",
    "produto",
    "quantidade",
    "preco_unitario",
    "desconto",
    "frete_cobrado",
    "frete_pago",
    "comissao",
    "taxa_servico",
    "cupom",
    "imposto",
    "repasse",
]


class TestClassificarSituacao(unittest.TestCase):
    def test_status_reais(self):
        casos = {
            "Entregue": "aprovado",
            "Enviado": "aprovado",
            "Aguardando envio": "aprovado",
            "Delivered": "aprovado",
            "To ship": "aprovado",
            "Cancelado": "cancelado",
            "Cancelled": "cancelado",
            "Devolvido": "devolvido",
            "Returned": "devolvido",
            "Aguardando pagamento": "pendente",
            "Unpaid": "pendente",
            "": "desconhecido",
            "Status novo do painel": "desconhecido",
        }
        for bruto, esperado in casos.items():
            self.assertEqual(classificar_situacao(bruto), esperado, bruto)


class TestImportacaoPedidos(CasoBase):
    def test_planilha_modelo_e_reimportacao_idempotente(self):
        arquivo = self.planilha(
            "pedidos.csv",
            CABECALHO_TEMPLATE,
            [
                ["P1", "Entregue", "01/09/2026", "ORG-001", "Organizador", "1", "100,00", "0", "0", "5,00", "10,00", "2,00", "0", "0", ""],
                ["P2", "Entregue", "02/09/2026", "ORG-001", "Organizador", "2", "50,00", "0", "0", "5,00", "10,00", "2,00", "0", "0", ""],
                ["P3", "Cancelado", "03/09/2026", "ORG-001", "Organizador", "1", "100,00", "0", "0", "0", "0", "0", "0", "0", ""],
                ["", "Total", "", "", "", "", "", "", "", "", "", "", "", "", ""],
            ],
        )
        resultado = self.importar("pedidos", arquivo, marketplace="shopee")
        self.assertEqual(resultado["inseridos"], 3)
        self.assertEqual(resultado["ignorados"], 1)
        self.assertEqual(resultado["dry_run"], False)

        pedidos = self.consultar("SELECT pedido_externo, situacao, itens_total_centavos FROM pedidos ORDER BY pedido_externo")
        self.assertEqual(len(pedidos), 3)
        self.assertEqual(pedidos[0]["situacao"], "aprovado")
        self.assertEqual(pedidos[2]["situacao"], "cancelado")
        self.assertEqual(pedidos[0]["itens_total_centavos"], 10000)

        # reimportar nao duplica
        self.importar("pedidos", arquivo, marketplace="shopee")
        total = self.consultar("SELECT COUNT(*) AS n FROM pedidos")[0]["n"]
        self.assertEqual(total, 3)
        itens = self.consultar("SELECT COUNT(*) AS n FROM itens_pedido")[0]["n"]
        self.assertEqual(itens, 3)

    def test_coluna_repetida_conta_uma_vez_e_rateada_soma(self):
        # formato TikTok: valores de pedido repetidos nas duas linhas de item
        tiktok = self.planilha(
            "tiktok.csv",
            [
                "Order ID",
                "Order Status",
                "Created Time",
                "Seller SKU",
                "Quantity",
                "SKU Unit Price",
                "Order Amount",
                "Platform Commission",
                "Payment Fee",
                "Seller Shipping Fee",
            ],
            [
                ["T1", "Delivered", "2026-09-01 10:00:00", "A", "1", "100.00", "200.00", "16.00", "4.00", "20.00"],
                ["T1", "Delivered", "2026-09-01 10:00:00", "B", "1", "100.00", "200.00", "16.00", "4.00", "20.00"],
            ],
            delimitador=",",
        )
        self.importar("pedidos", tiktok, marketplace="tiktok")
        pedido = self.consultar(
            "SELECT itens_total_centavos, comissao_centavos, taxa_servico_centavos, frete_pago_centavos "
            "FROM pedidos WHERE pedido_externo='T1'"
        )[0]
        self.assertEqual(pedido["itens_total_centavos"], 20000)
        self.assertEqual(pedido["comissao_centavos"], 1600, "valor repetido nao pode somar")
        self.assertEqual(pedido["taxa_servico_centavos"], 400)
        self.assertEqual(pedido["frete_pago_centavos"], 2000)

        # formato Shopee: taxa rateada por item (valores diferentes) soma
        shopee = self.planilha(
            "shopee.csv",
            ["Nº do pedido", "Status do pedido", "Data de criação", "SKU", "Quantidade", "Preço unitário", "Taxa de comissão"],
            [
                ["S1", "Entregue", "01/09/2026", "A", "1", "100,00", "5,00"],
                ["S1", "Entregue", "01/09/2026", "B", "1", "100,00", "7,00"],
            ],
        )
        self.importar("pedidos", shopee, marketplace="shopee")
        pedido = self.consultar(
            "SELECT comissao_centavos, itens_total_centavos FROM pedidos WHERE pedido_externo='S1'"
        )[0]
        self.assertEqual(pedido["comissao_centavos"], 1200)

    def test_mesmo_sku_em_linhas_diferentes_agrega(self):
        arquivo = self.planilha(
            "dup.csv",
            ["pedido", "status", "data_pedido", "sku", "quantidade", "preco_unitario"],
            [["P1", "Entregue", "2026-09-01", "A", "1", "10,00"]],
        )
        self.importar("pedidos", arquivo, marketplace="shopee")
        itens = self.consultar("SELECT quantidade, preco_unitario_centavos FROM itens_pedido")
        self.assertEqual(itens, [{"quantidade": 1, "preco_unitario_centavos": 1000}])

    def test_dry_run_nao_grava(self):
        arquivo = self.planilha(
            "dry.csv",
            ["pedido", "status", "data_pedido", "sku", "quantidade", "preco_unitario"],
            [["P1", "Entregue", "2026-09-01", "A", "1", "10,00"]],
        )
        resultado = self.importar("pedidos", arquivo, marketplace="shopee", dry_run=True)
        self.assertEqual(resultado["dry_run"], True)
        self.assertEqual(resultado["inseridos"], 0)
        self.assertEqual(self.consultar("SELECT COUNT(*) AS n FROM pedidos")[0]["n"], 0)

    def test_deteccao_automatica_de_marketplace(self):
        arquivo = self.planilha(
            "auto.csv",
            ["Order ID", "Order Status", "Created Time", "Seller SKU", "Quantity", "SKU Unit Price"],
            [["T9", "Delivered", "2026-09-01 10:00:00", "A", "1", "10.00"]],
            delimitador=",",
        )
        resultado = self.importar("pedidos", arquivo)
        self.assertEqual(resultado["marketplace"], "tiktok")

    def test_tiktok_estima_taxas_quando_export_nao_traz(self):
        arquivo = self.planilha(
            "tiktok_sem_taxas.csv",
            ["pedido", "status", "data_pedido", "sku", "produto", "quantidade",
             "preco_unitario", "itens_total"],
            [["586752000250119957", "Enviado", "2026-10-24", "1 tubo hermetico rosa",
              "Tubete Mocozim", "1", "15,90", "15,90"]],
        )
        resultado = self.importar("pedidos", arquivo, marketplace="tiktok")
        self.assertEqual(resultado["inseridos"], 1)
        pedido = self.consultar(
            "SELECT itens_total_centavos, comissao_centavos, taxa_servico_centavos FROM pedidos"
        )[0]
        self.assertEqual(pedido["itens_total_centavos"], 1590)
        self.assertEqual(pedido["comissao_centavos"], 159)   # 10%
        self.assertEqual(pedido["taxa_servico_centavos"], 495)  # 6% + R$ 4

    def test_export_nativo_shopee_usa_subtotal_e_taxas(self):
        arquivo = self.planilha(
            "shopee_nativo.csv",
            [
                "ID do pedido", "Status do pedido", "Data de criação do pedido",
                "Número de referência SKU", "Nome do Produto", "Quantidade",
                "Preço original", "Preço acordado", "Subtotal do produto",
                "Desconto do vendedor", "Valor Total", "Desconto de Frete Aproximado",
                "Taxa de comissão líquida", "Taxa de serviço líquida", "Cupom",
            ],
            [[
                "260900ABC", "Concluído", "2026-09-02 12:31", "TUBETE CINZA",
                "Tubete Mocozim", "1", "49,90", "15,90", "15,90", "34,00",
                "18,93", "19,72", "2,86", "4,32", "0,00",
            ]],
        )
        resultado = self.importar("pedidos", arquivo, marketplace="shopee")
        self.assertEqual(resultado["inseridos"], 1)
        pedido = self.consultar(
            "SELECT itens_total_centavos, comissao_centavos, taxa_servico_centavos, "
            "desconto_centavos, frete_cobrado_centavos, frete_pago_centavos FROM pedidos"
        )[0]
        self.assertEqual(pedido["itens_total_centavos"], 1590)
        self.assertEqual(pedido["comissao_centavos"], 286)
        self.assertEqual(pedido["taxa_servico_centavos"], 432)
        self.assertEqual(pedido["desconto_centavos"], 0)
        self.assertEqual(pedido["frete_cobrado_centavos"], 0)
        self.assertEqual(pedido["frete_pago_centavos"], 0)

    def test_importa_xlsx(self):
        from tests.test_colunas_leitor import _criar_xlsx

        caminho = self._tmp / "pedidos.xlsx"
        _criar_xlsx(
            caminho,
            [
                ["pedido", "status", "data_pedido", "sku", "quantidade", "preco_unitario"],
                ["X1", "Entregue", "45931", "A", 2, 39.9],
            ],
        )
        resultado = self.importar("pedidos", caminho, marketplace="shopee")
        self.assertEqual(resultado["inseridos"], 1)
        pedido = self.consultar("SELECT data_pedido, itens_total_centavos FROM pedidos")[0]
        self.assertEqual(pedido["data_pedido"], "2025-10-01")
        self.assertEqual(pedido["itens_total_centavos"], 7980)


class TestImportacaoOutras(CasoBase):
    def test_custos_e_contas(self):
        custos = self.planilha(
            "custos.csv",
            ["sku", "custo", "preco_venda"],
            [["A", "12,50", "39,90"], ["B", "0", ""]],
        )
        resultado = self.importar("custos", custos)
        self.assertEqual(resultado["inseridos"], 2)
        produtos = self.consultar("SELECT sku, custo_unitario_centavos FROM produtos ORDER BY sku")
        self.assertEqual(produtos[0]["custo_unitario_centavos"], 1250)

        contas = self.planilha(
            "contas.csv",
            ["tipo", "descricao", "categoria", "valor", "vencimento", "pago_em"],
            [
                ["pagar", "Shopee Ads", "marketing", "900,00", "15/09/2026", "15/09/2026"],
                ["receber", "Reembolso", "outros", "180,00", "22/09/2026", ""],
            ],
        )
        resultado = self.importar("contas", contas)
        self.assertEqual(resultado["inseridos"], 2)
        linhas = self.consultar(
            "SELECT tipo, categoria, status FROM contas_financeiras ORDER BY tipo"
        )
        self.assertEqual(linhas[0]["tipo"], "pagar")
        self.assertEqual(linhas[0]["status"], "paga")
        self.assertEqual(linhas[1]["tipo"], "receber")

        # reimporta: nao duplica e nao "despaga"
        resultado = self.importar("contas", contas)
        self.assertEqual(resultado["inseridos"], 0)
        self.assertEqual(resultado["atualizados"], 2)
        self.assertEqual(self.consultar("SELECT COUNT(*) AS n FROM contas_financeiras")[0]["n"], 2)

    def test_repasses_negativos_e_dedupe(self):
        arquivo = self.planilha(
            "repasses.csv",
            ["data", "valor", "referencia"],
            [
                ["05/09/2026", "1.000,00", "REP-1"],
                ["26/09/2026", "-180,00", "ESTORNO-1"],
            ],
        )
        resultado = self.importar("repasses", arquivo, marketplace="shopee")
        self.assertEqual(resultado["inseridos"], 2)
        self.importar("repasses", arquivo, marketplace="shopee")
        self.assertEqual(self.consultar("SELECT COUNT(*) AS n FROM repasses")[0]["n"], 2)
        total = self.consultar("SELECT SUM(valor_centavos) AS s FROM repasses")[0]["s"]
        self.assertEqual(total, 82000)


if __name__ == "__main__":
    unittest.main()
