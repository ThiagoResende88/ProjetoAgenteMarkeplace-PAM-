"""Testes de parsing/formatacao de dinheiro e datas."""

from __future__ import annotations

import datetime as dt
import unittest
from decimal import Decimal

from mktagent import datas
from mktagent.dinheiro import (
    fmt_brl,
    fmt_pct,
    para_centavos,
    parse_percentual,
    parse_valor,
)


class TestDinheiro(unittest.TestCase):
    def test_formatos_brasileiros(self):
        self.assertEqual(parse_valor("R$ 1.234,56"), Decimal("1234.56"))
        self.assertEqual(parse_valor("1.234,56"), Decimal("1234.56"))
        self.assertEqual(parse_valor(" 12,90 "), Decimal("12.90"))
        self.assertEqual(parse_valor("0,005"), Decimal("0.005"))
        self.assertEqual(parse_valor("R$ -50,00"), Decimal("-50.00"))

    def test_formatos_internacionais(self):
        self.assertEqual(parse_valor("1,234.56"), Decimal("1234.56"))
        self.assertEqual(parse_valor("1234.56"), Decimal("1234.56"))
        self.assertEqual(parse_valor("1.234"), Decimal("1234"))
        self.assertEqual(parse_valor("1234"), Decimal("1234"))

    def test_negativos_contabeis(self):
        self.assertEqual(parse_valor("(1.234,56)"), Decimal("-1234.56"))
        self.assertEqual(parse_valor("-12,90"), Decimal("-12.90"))
        self.assertEqual(parse_valor("12,90-"), Decimal("-12.90"))

    def test_vazios(self):
        self.assertIsNone(parse_valor(""))
        self.assertIsNone(parse_valor("   "))
        self.assertIsNone(parse_valor("-"))
        self.assertIsNone(parse_valor("n/a"))
        self.assertIsNone(parse_valor(None))
        self.assertEqual(parse_valor("", Decimal("7")), Decimal("7"))

    def test_percentual(self):
        self.assertEqual(parse_percentual("14,5%"), Decimal("0.145"))
        self.assertEqual(parse_percentual("0.145"), Decimal("0.145"))
        self.assertEqual(parse_percentual("14.5"), Decimal("0.145"))

    def test_centavos(self):
        self.assertEqual(para_centavos(Decimal("12.345")), 1235)
        self.assertEqual(para_centavos("R$ 39,90"), 3990)
        self.assertEqual(para_centavos(None), None)
        self.assertEqual(para_centavos(-12.5), -1250)

    def test_formatacao(self):
        self.assertEqual(fmt_brl(123456), "R$ 1.234,56")
        self.assertEqual(fmt_brl(5), "R$ 0,05")
        self.assertEqual(fmt_brl(-123456), "-R$ 1.234,56")
        self.assertEqual(fmt_brl(0), "R$ 0,00")
        self.assertEqual(fmt_brl(123456789), "R$ 1.234.567,89")
        self.assertEqual(fmt_pct(0.152), "15,2%")
        self.assertEqual(fmt_pct(None), "-")


class TestDatas(unittest.TestCase):
    def test_formatos(self):
        esperado = dt.date(2026, 10, 25)
        self.assertEqual(datas.parse_data("25/10/2026"), esperado)
        self.assertEqual(datas.parse_data("2026-10-25"), esperado)
        self.assertEqual(datas.parse_data("25/10/2026 14:32"), esperado)
        self.assertEqual(datas.parse_data("2026-10-25T14:32:11"), esperado)

    def test_americano_ambiguo(self):
        self.assertEqual(datas.parse_data("10/25/2026"), dt.date(2026, 10, 25))
        self.assertEqual(datas.parse_data("25/10/2026"), dt.date(2026, 10, 25))

    def test_serial_excel(self):
        # 45931 = 2025-10-01 (base 1899-12-30)
        self.assertEqual(datas.parse_data("45931"), dt.date(2025, 10, 1))
        # numero fora da faixa de data nao vira data
        self.assertIsNone(datas.parse_data("123"))

    def test_invalidos(self):
        self.assertIsNone(datas.parse_data(""))
        self.assertIsNone(datas.parse_data("31/02/2026"))
        self.assertIsNone(datas.parse_data("abc"))

    def test_meses(self):
        self.assertEqual(datas.normalizar_mes("2026-10"), "2026-10")
        self.assertEqual(datas.normalizar_mes("10/2026"), "2026-10")
        self.assertEqual(datas.intervalo_mes("2026-02"), (dt.date(2026, 2, 1), dt.date(2026, 2, 28)))
        self.assertEqual(datas.mes_anterior("2026-01"), "2025-12")
        self.assertEqual(datas.mes_anterior("2026-10"), "2026-09")
        self.assertEqual(datas.meses_entre("2026-08", "2026-10"), ["2026-08", "2026-09", "2026-10"])
        self.assertEqual(datas.fmt_mes("2026-10"), "outubro/2026")


if __name__ == "__main__":
    unittest.main()
