"""Testes do controle de pedidos manuais (B2B/consignacao) sem planilha."""

from __future__ import annotations

import json
import os
import subprocess
import sys

from tests.apoio import BIN, CasoBase


class TestPedidosManuais(CasoBase):
    def test_cria_pedido_b2b_e_atualiza_status(self):
        self.servico.registrar_custo("TUBETE", "4,13", preco_venda="15,00")
        criado = self.servico.criar_pedido(
            canal="consignacao",
            cliente="BARBEARIA",
            data="2026-10-20",
            itens=[
                {"sku": "TUBETE", "quantidade": 10, "preco_unitario": "12,00"},
                {"sku": "PORTA-ISQUEIRO", "quantidade": 4, "preco_unitario": "15,00"},
            ],
        )
        self.assertEqual(criado["total_centavos"], 18000)
        self.assertEqual(criado["situacao"], "pendente")
        self.assertTrue(criado["pedido"].startswith("MOC-"))

        linha = self.consultar("SELECT cliente, itens_total_centavos FROM pedidos")[0]
        self.assertEqual(linha["cliente"], "BARBEARIA")
        self.assertEqual(linha["itens_total_centavos"], 18000)
        itens = self.consultar(
            "SELECT sku, quantidade, custo_unitario_centavos FROM itens_pedido ORDER BY sku"
        )
        self.assertEqual(len(itens), 2)
        por_sku = {item["sku"]: item for item in itens}
        self.assertEqual(por_sku["TUBETE"]["custo_unitario_centavos"], 413)
        self.assertIsNone(por_sku["PORTA-ISQUEIRO"]["custo_unitario_centavos"])

        atualizado = self.servico.atualizar_status_pedido(criado["pedido"], "Pago")
        self.assertEqual(atualizado["situacao"], "aprovado")
        self.assertTrue(atualizado["entra_na_receita"])

        listados = self.servico.pedidos(cliente="BARB")
        self.assertEqual(listados["quantidade"], 1)
        self.assertEqual(listados["pedidos"][0]["cliente"], "BARBEARIA")

    def test_pedido_entra_no_dre_quando_pago(self):
        self.servico.registrar_custo("TUBETE", "4,13", preco_venda="15,00")
        self.servico.criar_pedido(
            canal="consignacao",
            cliente="BARBEARIA",
            data="2026-09-10",
            itens=[{"sku": "TUBETE", "quantidade": 10, "preco_unitario": "12,00"}],
            status="Pago",
        )
        dre = self.servico.dre("2026-09")
        self.assertEqual(dre["receita_bruta_centavos"], 12000)
        self.assertEqual(dre["cmv_centavos"], 4130)
        self.assertEqual(dre["margem_contribuicao_centavos"], 7870)

    def test_pendente_nao_entra_na_receita(self):
        self.servico.criar_pedido(
            canal="consignacao",
            itens=[{"sku": "TUBETE", "quantidade": 1, "preco_unitario": "12,00"}],
            status="Pendente",
        )
        dre = self.servico.dre("2026-10")
        self.assertEqual(dre["receita_bruta_centavos"], 0)
        self.assertEqual(dre["pedidos"]["pendentes"], 1)

    def test_status_invalido_e_pedido_duplicado(self):
        self.servico.criar_pedido(
            canal="direto",
            pedido_externo="X-1",
            itens=[{"sku": "A", "quantidade": 1, "preco_unitario": "10,00"}],
        )
        with self.assertRaises(ValueError):
            self.servico.atualizar_status_pedido("X-1", "Status Esquisito")
        with self.assertRaises(ValueError):
            self.servico.criar_pedido(
                canal="direto",
                pedido_externo="X-1",
                itens=[{"sku": "A", "quantidade": 1, "preco_unitario": "10,00"}],
            )

    def test_ferramentas_mcp_de_pedido(self):
        env = dict(os.environ)
        env["MKT_HOME"] = str(self._tmp)
        env["MKT_DB"] = str(self._tmp / "mkt.db")
        processo = subprocess.run(
            [sys.executable, str(BIN / "mkt-mcp"), "--listar-ferramentas"],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )
        nomes = {f["name"] for f in json.loads(processo.stdout)["ferramentas"]}
        self.assertIn("criar_pedido", nomes)
        self.assertIn("atualizar_status_pedido", nomes)
