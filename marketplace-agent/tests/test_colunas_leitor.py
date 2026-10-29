"""Testes do mapeamento de colunas e leitura de planilhas."""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from mktagent.ingestao import colunas as col
from mktagent.ingestao.leitor import ler_tabela


class TestNormalizacao(unittest.TestCase):
    def test_acentos_e_simbolos(self):
        self.assertEqual(col.normalizar("Preço Unitário (R$)"), "preco_unitario_r")
        self.assertEqual(col.normalizar("Nº do pedido"), "no_do_pedido")
        self.assertEqual(col.normalizar("Order ID"), "order_id")


class TestMapaColunas(unittest.TestCase):
    def test_mapeamento_exato_e_fuzzy(self):
        cabecalhos = [
            "Nº do pedido",
            "Status do pedido",
            "Data de criação",
            "SKU do produto",
            "Quantidade",
            "Preço unitário (R$)",
            "Taxa de comissão (R$)",
            "Total do pedido (R$)",
        ]
        mapa = col.MapaColunas(cabecalhos, col.ALIASES_PEDIDOS)
        self.assertEqual(mapa.coluna("pedido"), "Nº do pedido")
        self.assertEqual(mapa.coluna("data_pedido"), "Data de criação")
        self.assertIsNone(mapa.coluna("produto"))  # nome nao presente
        self.assertEqual(mapa.coluna("preco_unitario"), "Preço unitário (R$)")
        self.assertEqual(mapa.coluna("comissao"), "Taxa de comissão (R$)")
        self.assertIn("Total do pedido (R$)", mapa.mapeamento().values())

    def test_nao_reaproveita_coluna(self):
        cabecalhos = ["Frete cobrado", "Frete pago pelo vendedor"]
        mapa = col.MapaColunas(cabecalhos, col.ALIASES_PEDIDOS)
        self.assertEqual(mapa.coluna("frete_cobrado"), "Frete cobrado")
        self.assertEqual(mapa.coluna("frete_pago"), "Frete pago pelo vendedor")

    def test_sugestao_marketplace(self):
        mercado, _ = col.sugerir_marketplace(["Order ID", "Order Status", "Seller SKU"])
        self.assertEqual(mercado, "tiktok")
        mercado, _ = col.sugerir_marketplace(["Nº do pedido", "Taxa de comissão", "Order SN"])
        self.assertEqual(mercado, "shopee")
        mercado, _ = col.sugerir_marketplace(["a", "b"])
        self.assertIsNone(mercado)


class TestLeitor(unittest.TestCase):
    def test_csv_ponto_e_virgula(self):
        with tempfile.TemporaryDirectory() as tmp:
            arquivo = Path(tmp) / "teste.csv"
            arquivo.write_text("a;b\n1;2\n", encoding="utf-8")
            tabela = ler_tabela(arquivo)
            self.assertEqual(tabela.colunas, ["a", "b"])
            self.assertEqual(tabela.linhas, [{"a": "1", "b": "2"}])

    def test_csv_com_titulo_antes_do_cabecalho(self):
        with tempfile.TemporaryDirectory() as tmp:
            arquivo = Path(tmp) / "teste.csv"
            arquivo.write_text(
                "Relatorio de pedidos;;;;\nPedido;SKU;Qtd\n1;A;2\n", encoding="utf-8"
            )
            tabela = ler_tabela(arquivo)
            self.assertEqual(tabela.colunas, ["Pedido", "SKU", "Qtd"])
            self.assertEqual(len(tabela.linhas), 1)

    def test_csv_encoding_cp1252(self):
        with tempfile.TemporaryDirectory() as tmp:
            arquivo = Path(tmp) / "teste.csv"
            arquivo.write_bytes("Pedido;Produto\n1;Café\n".encode("cp1252"))
            tabela = ler_tabela(arquivo)
            self.assertEqual(tabela.linhas[0]["Produto"], "Café")

    def test_xlsx_minimo(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "teste.xlsx"
            _criar_xlsx(caminho, [["pedido", "sku", "qtd"], ["SP1", "A", 2]])
            tabela = ler_tabela(caminho)
            self.assertEqual(tabela.colunas, ["pedido", "sku", "qtd"])
            self.assertEqual(tabela.linhas[0]["qtd"], "2")

    def test_extensao_xls_orienta_exportar(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "antigo.xls"
            caminho.write_bytes(b"nao e um xls real")
            with self.assertRaises(ValueError) as contexto:
                ler_tabela(caminho)
            self.assertIn(".xlsx", str(contexto.exception))


def _coluna(indice: int) -> str:
    coluna = ""
    numero = indice + 1
    while numero:
        numero, resto = divmod(numero - 1, 26)
        coluna = chr(ord("A") + resto) + coluna
    return coluna


def _criar_xlsx(caminho: Path, linhas: list[list]) -> None:
    """Escreve um XLSX minimo (inline strings) usando apenas zipfile."""
    xml_linhas = []
    for numero_linha, linha in enumerate(linhas, start=1):
        celulas = []
        for indice, valor in enumerate(linha):
            ref = f"{_coluna(indice)}{numero_linha}"
            if isinstance(valor, (int, float)):
                celulas.append(f'<c r="{ref}"><v>{valor}</v></c>')
            else:
                celulas.append(f'<c r="{ref}" t="inlineStr"><is><t>{valor}</t></is></c>')
        xml_linhas.append(f'<row r="{numero_linha}">{"".join(celulas)}</row>')

    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(xml_linhas)}</sheetData></worksheet>"
    )
    with zipfile.ZipFile(caminho, "w") as pacote:
        pacote.writestr("xl/worksheets/sheet1.xml", sheet)


if __name__ == "__main__":
    unittest.main()
