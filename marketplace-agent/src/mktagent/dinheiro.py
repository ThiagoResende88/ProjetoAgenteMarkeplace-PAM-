"""Dinheiro: parsing tolerante e formatacao em Real.

Regra de ouro do projeto: todo valor monetario e guardado em CENTAVOS
(inteiro). Decimal so aparece na borda (parsing/formatacao) para evitar
erro de ponto flutuante em relatorio financeiro.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

ZERO = Decimal("0")
CENTAVO = Decimal("0.01")

_SUJOS = re.compile(r"[^0-9.,]")


def parse_valor(texto: object, padrao: Decimal | None = None) -> Decimal | None:
    """Converte texto livre de planilha em Decimal.

    Aceita: ``R$ 1.234,56``, ``1234.56``, ``1.234,56``, ``-12,90``,
    ``(12,90)`` (negativo contabil), ``1 234,56`` e ``""`` (-> ``padrao``).
    Retorna ``None`` quando nao ha numero (salvo ``padrao`` informado).
    """
    if texto is None:
        return padrao
    if isinstance(texto, Decimal):
        return texto
    if isinstance(texto, int):
        return Decimal(texto)
    if isinstance(texto, float):
        return Decimal(str(texto)).quantize(CENTAVO, rounding=ROUND_HALF_UP)

    s = str(texto).strip()
    if not s or s.lower() in {"nan", "none", "null", "-", "--", "n/a", "na"}:
        return padrao

    negativo = False
    if s.startswith("(") and s.endswith(")"):
        negativo = True
        s = s[1:-1]
    s = s.replace("R$", "").replace("r$", "").replace("BRL", "").replace("US$", "")
    s = s.replace("\u00a0", "").replace(" ", "").replace("+", "")
    s = s.replace("\u2212", "-")  # sinal de menos unicode
    if s.startswith("-") or s.endswith("-"):
        negativo = True
    s = s.replace("-", "")
    s = _SUJOS.sub("", s)
    if not s or s in {".", ","}:
        return padrao
    if not re.search(r"\d", s):
        return padrao

    if "," in s and "." in s:
        # o separador mais a direita e o decimal
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        partes = s.split(",")
        if len(partes) == 2 and (1 <= len(partes[1]) <= 2 or partes[0] in {"0", ""}):
            s = ".".join(partes)
        else:
            s = s.replace(",", "")
    elif "." in s:
        partes = s.split(".")
        if len(partes) > 2:
            s = s.replace(".", "")
        elif (
            len(partes) == 2
            and len(partes[1]) == 3
            and partes[0] not in {"0", ""}
            and len(partes[0]) <= 3
            and len(s) > 4
        ):
            # "1.234" -> mil duzentos e trinta e quatro (convencao BR)
            s = s.replace(".", "")

    try:
        valor = Decimal(s)
    except InvalidOperation:
        return padrao
    if not valor.is_finite():
        return padrao
    return -valor if negativo else valor


def parse_percentual(texto: object, padrao: Decimal | None = None) -> Decimal | None:
    """Converte ``14,5%`` ou ``0.145`` em Fracao (0.145). ``14,5%`` -> 0.145."""
    if texto is None:
        return padrao
    s = str(texto).strip()
    if not s:
        return padrao
    tem_simbolo = "%" in s
    valor = parse_valor(s.replace("%", ""))
    if valor is None:
        return padrao
    if tem_simbolo:
        return valor / Decimal(100)
    if valor > 0 and valor <= 1:
        return valor
    return valor / Decimal(100)


def para_centavos(valor: Decimal | int | float | str | None) -> int | None:
    """Decimal -> centavos (int). ``None`` continua ``None``."""
    if valor is None:
        return None
    if isinstance(valor, int):
        return valor
    if isinstance(valor, str):
        valor = parse_valor(valor)
        if valor is None:
            return None
    if isinstance(valor, float):
        valor = Decimal(str(valor))
    return int(valor.quantize(CENTAVO, rounding=ROUND_HALF_UP) * 100)


def de_centavos(centavos: int | None) -> Decimal:
    return Decimal(centavos or 0) / 100


def fmt_brl(centavos: int | None) -> str:
    """Formata centavos como ``R$ 1.234,56``."""
    valor = de_centavos(centavos)
    sinal = "-" if valor < 0 else ""
    valor = abs(valor)
    inteiro, decimal = f"{valor:.2f}".split(".")
    grupos = []
    while len(inteiro) > 3:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    grupos.insert(0, inteiro)
    return f"{sinal}R$ {'.'.join(grupos)},{decimal}"


def fmt_pct(valor: Decimal | float | None, casas: int = 1) -> str:
    """Formata fracao (0.152) como ``15,2%``."""
    if valor is None:
        return "-"
    valor = float(valor) * 100
    return f"{valor:.{casas}f}".replace(".", ",") + "%"


def fmt_decimal(valor: Decimal | float | None, casas: int = 2) -> str:
    if valor is None:
        return "-"
    return f"{Decimal(valor):.{casas}f}".replace(".", ",")


def dividir(a: Decimal, b: Decimal) -> Decimal:
    if not b:
        return ZERO
    return a / b
