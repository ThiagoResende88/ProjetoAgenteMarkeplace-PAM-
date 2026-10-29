"""Testes dos relatorios financeiros com numeros calculados a mao."""

from __future__ import annotations

import unittest

from tests.apoio import CasoBase

CABECALHO = [
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


class CenarioFiscal(CasoBase):
    """Cenario com dois pedidos aprovados, um cancelado e despesas."""
    def setUp(self) -> None:
        super().setUp()
        custos = self.planilha(
            "custos.csv",
            ["sku", "custo"],
            [["A", "40,00"], ["B", "10,00"]],
        )
        self.importar("custos", custos)
        pedidos = self.planilha(
            "pedidos.csv",
            CABECALHO,
            [
                # vendido, liquido = 100 - 0 + 0 - 5 - 10 - 2 - 0 - 0 = 83
                ["P1", "Entregue", "01/09/2026", "A", "A", "1", "100,00", "0", "0", "5,00", "10,00", "2,00", "0", "0", ""],
                # 2 itens, liquido = 100 - 10 + 0 - 5 - 10 - 2 - 0 - 0 = 73
                ["P2", "Entregue", "02/09/2026", "B", "B", "2", "50,00", "10,00", "0", "5,00", "10,00", "2,00", "0", "0", ""],
                # cancelado: nao entra
                ["P3", "Cancelado", "03/09/2026", "A", "A", "1", "100,00", "0", "0", "0", "0", "0", "0", "0", ""],
            ],
        )
        self.importar("pedidos", pedidos, marketplace="shopee")
        contas = self.planilha(
            "contas.csv",
            ["tipo", "descricao", "categoria", "valor", "vencimento", "pago_em"],
            [
                ["pagar", "Shopee Ads", "marketing", "50,00", "10/09/2026", "10/09/2026"],
                ["pagar", "Fornecedor", "fornecedor", "500,00", "10/09/2026", "10/09/2026"],
            ],
        )
        self.importar("contas", contas)

    def test_numeros_do_dre(self):
        dados = self.servico.dre("2026-09")
        self.assertEqual(dados["receita_bruta_centavos"], 20000)  # 100 + 100
        self.assertEqual(dados["frete_pago_centavos"], 1000)  # 5 + 5
        self.assertEqual(dados["comissao_centavos"], 2000)
        self.assertEqual(dados["descontos_centavos"], 1000)
        self.assertEqual(dados["receita_liquida_centavos"], 8300 + 7300)
        self.assertEqual(dados["cmv_centavos"], 4000 + 2000)
        self.assertEqual(dados["margem_contribuicao_centavos"], 9600)
        self.assertEqual(dados["opex_centavos"], 5000)  # fornecedor excluido
        self.assertEqual(dados["lucro_liquido_centavos"], 4600)
        self.assertEqual(dados["pedidos"]["aprovados"], 2)
        self.assertEqual(dados["pedidos"]["cancelados"], 1)
        self.assertEqual(dados["completude"]["cobertura_custo_itens_pct"], "100,0%")

    def test_por_marketplace(self):
        dados = self.servico.dre("2026-09")
        self.assertIn("shopee", dados["por_marketplace"])
        self.assertEqual(
            dados["por_marketplace"]["shopee"]["receita_bruta_centavos"], 20000
        )

    def test_margem_por_sku_rateia_taxas(self):
        dados = self.servico.margem("2026-09")
        por_sku = {item["sku"]: item for item in dados["skus"]}
        self.assertEqual(por_sku["A"]["receita_bruta_centavos"], 10000)
        # A: liquido 83, cmv 40 => margem 43
        self.assertEqual(por_sku["A"]["margem_centavos"], 4300)
        # B: liquido 73, cmv 20 => margem 53
        self.assertEqual(por_sku["B"]["margem_centavos"], 5300)
        self.assertIn(por_sku["A"]["classe_abc"], {"A", "B"})

    def test_comparativo(self):
        dados = self.servico.comparativo("2026-09")
        self.assertEqual(dados["mes"], "2026-09")

    def test_dre_sem_dados(self):
        dados = self.servico.dre("2025-01")
        self.assertEqual(dados["receita_bruta_centavos"], 0)
        self.assertTrue(dados["avisos"])


class TestDRE(CenarioFiscal):
    pass


class TestCaixa(CenarioFiscal):
    def test_fluxo_agrupa_por_semana(self):
        from mktagent.datas import hoje
        import datetime as dt

        venc_futuro = (hoje() + dt.timedelta(days=3)).isoformat()
        venc_passado = (hoje() - dt.timedelta(days=3)).isoformat()
        with self.servico._conexao() as conn:  # noqa: SLF001
            conn.execute(
                "INSERT INTO contas_financeiras (tipo, descricao, categoria, valor_centavos, "
                "vencimento, status) VALUES ('pagar','Luz','estrutura',10000,?, 'aberta')",
                (venc_futuro,),
            )
            conn.execute(
                "INSERT INTO contas_financeiras (tipo, descricao, categoria, valor_centavos, "
                "vencimento, status) VALUES ('receber','Pix','outros',5000,?, 'aberta')",
                (venc_futuro,),
            )
            conn.execute(
                "INSERT INTO contas_financeiras (tipo, descricao, categoria, valor_centavos, "
                "vencimento, status) VALUES ('pagar','Atrasada','outros',2000,?, 'aberta')",
                (venc_passado,),
            )
        dados = self.servico.caixa(30)
        self.assertEqual(dados["saidas_previstas_centavos"], 10000)
        self.assertEqual(dados["entradas_previstas_centavos"], 5000)
        self.assertEqual(dados["vencido_a_pagar_centavos"], 2000)
        self.assertEqual(len(dados["semanas"]), 1)
        self.assertTrue(dados["contas_vencidas"])

    def test_criar_e_baixar_conta(self):
        criada = self.servico.criar_conta(
            "pagar", "Energia", "240,50", "2026-11-18", categoria="estrutura"
        )
        self.assertEqual(criada["status"], "criada")
        paga = self.servico.marcar_paga(criada["id"])
        self.assertEqual(paga["status"], "paga")
        self.assertEqual(
            self.consultar("SELECT status FROM contas_financeiras WHERE id=?", (criada["id"],))[0]["status"],
            "paga",
        )
        # cria duplicada: devolve a existente sem duplicar
        de_novo = self.servico.criar_conta(
            "pagar", "Energia", "240,50", "2026-11-18", categoria="estrutura"
        )
        self.assertEqual(de_novo["status"], "ja_existia")

    def test_registrar_custo_atualiza_snapshot(self):
        self.servico.registrar_custo("A", "45,00")
        item = self.consultar("SELECT custo_unitario_centavos FROM itens_pedido WHERE sku='A'")[0]
        self.assertEqual(item["custo_unitario_centavos"], 4500)
        produto = self.consultar("SELECT custo_unitario_centavos FROM produtos WHERE sku='A'")[0]
        self.assertEqual(produto["custo_unitario_centavos"], 4500)


class TestAlertas(CenarioFiscal):
    def test_alertas_priorizados(self):
        dados = self.servico.alertas()
        self.assertGreaterEqual(dados["total"], 1)
        severidades = [alerta["severidade"] for alerta in dados["alertas"]]
        ordem = {"alta": 0, "media": 1, "baixa": 2}
        self.assertEqual(severidades, sorted(severidades, key=lambda s: ordem[s]))
        for alerta in dados["alertas"]:
            self.assertTrue(alerta["titulo"])
            self.assertTrue(alerta["acao"])


if __name__ == "__main__":
    unittest.main()
