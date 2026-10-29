"""Datas: parsing tolerante de planilhas BR/US e utilitarios de periodo.

Regra do projeto: datas sao guardadas como texto ISO ``YYYY-MM-DD`` no banco.
"""

from __future__ import annotations

import calendar
import datetime as dt

_FORMATOS_HORA = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d-%m-%Y %H:%M:%S",
)
_FORMATOS_DATA = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%y")

_SERIAL_MIN = 20000  # 1954
_SERIAL_MAX = 80000  # 2119


def hoje() -> dt.date:
    return dt.date.today()


def parse_data(texto: object, padrao: dt.date | None = None) -> dt.date | None:
    """Aceita ``2026-10-25``, ``25/10/2026``, ``10/25/2026`` e serial do Excel."""
    if texto is None or texto == "":
        return padrao
    if isinstance(texto, dt.datetime):
        return texto.date()
    if isinstance(texto, dt.date):
        return texto
    s = str(texto).strip()
    if not s:
        return padrao
    if s.endswith("Z"):
        s = s[:-1]
    s = s.replace("T", " ")
    if "." in s and ":" in s:
        s = s.split(".")[0]
    if " " in s:
        s = s.split(" ")[0]

    # serial do Excel (celulas numericas)
    try:
        num = float(s.replace(",", "."))
    except ValueError:
        num = None
    if num is not None and float(num).is_integer() and _SERIAL_MIN <= num <= _SERIAL_MAX:
        return dt.date(1899, 12, 30) + dt.timedelta(days=int(num))

    for formato in _FORMATOS_DATA:
        try:
            return dt.datetime.strptime(s, formato).date()
        except ValueError:
            continue
    # ambiguidade 10/25/2026 (mes/dia/ano)
    partes = s.replace("-", "/").split("/")
    if len(partes) == 3:
        try:
            a, b, c = (int(p) for p in partes)
            if a <= 12 and b > 12:
                return dt.date(c, a, b)
            if b <= 12 and a > 12:
                return dt.date(c, b, a)
        except ValueError:
            pass
    return padrao


def parse_data_hora(texto: object) -> dt.datetime | None:
    if texto is None or texto == "":
        return None
    if isinstance(texto, dt.datetime):
        return texto
    s = str(texto).strip().replace("T", " ").replace("Z", "")
    for formato in _FORMATOS_HORA:
        try:
            return dt.datetime.strptime(s, formato)
        except ValueError:
            continue
    data = parse_data(s)
    return dt.datetime.combine(data, dt.time()) if data else None


def iso(data: dt.date | None) -> str | None:
    return data.isoformat() if data else None


def fmt_data_br(data: str | dt.date | None) -> str:
    if not data:
        return "-"
    if isinstance(data, str):
        data = parse_data(data)
        if data is None:
            return "-"
    return data.strftime("%d/%m/%Y")


def mes_de(data: dt.date | str | None) -> str | None:
    if data is None:
        return None
    if isinstance(data, str):
        data = parse_data(data)
        if data is None:
            return None
    return f"{data.year:04d}-{data.month:02d}"


def mes_atual() -> str:
    return mes_de(hoje())  # type: ignore[return-value]


def normalizar_mes(texto: str | None) -> str | None:
    """Aceita ``2026-10``, ``10/2026``, ``outubro/2026``? Apenas numerico."""
    if not texto:
        return None
    s = str(texto).strip().replace("/", "-")
    partes = s.split("-")
    if len(partes) == 2:
        a, b = partes
        if len(a) == 4 and a.isdigit() and b.isdigit():
            return f"{a}-{int(b):02d}"
        if len(b) == 4 and b.isdigit() and a.isdigit():
            return f"{b}-{int(a):02d}"
    return None


def intervalo_mes(mes: str) -> tuple[dt.date, dt.date]:
    """``2026-10`` -> (2026-10-01, 2026-10-31)."""
    ano, m = (int(x) for x in normalizar_mes(mes).split("-"))  # type: ignore[union-attr]
    ultimo = calendar.monthrange(ano, m)[1]
    return dt.date(ano, m, 1), dt.date(ano, m, ultimo)


def mes_anterior(mes: str, passos: int = 1) -> str:
    ano, m = (int(x) for x in normalizar_mes(mes).split("-"))  # type: ignore[union-attr]
    total = ano * 12 + (m - 1) - passos
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def meses_entre(inicio: str, fim: str) -> list[str]:
    atual, fim_n = normalizar_mes(inicio), normalizar_mes(fim)
    resultado = []
    while atual and fim_n and atual <= fim_n:
        resultado.append(atual)
        if atual == fim_n:
            break
        atual = _proximo_mes(atual)
    return resultado


def _proximo_mes(mes: str) -> str:
    ano, m = (int(x) for x in mes.split("-"))
    if m == 12:
        return f"{ano + 1:04d}-01"
    return f"{ano:04d}-{m + 1:02d}"


def dias_ate(data: dt.date | str | None, referencia: dt.date | None = None) -> int | None:
    if data is None:
        return None
    if isinstance(data, str):
        data = parse_data(data)
        if data is None:
            return None
    return (data - (referencia or hoje())).days


def inicio_semana(data: dt.date) -> dt.date:
    return data - dt.timedelta(days=data.weekday())


def fmt_mes(mes: str | None) -> str:
    """``2026-10`` -> ``outubro/2026``."""
    if not mes:
        return "-"
    nomes = [
        "janeiro",
        "fevereiro",
        "marco",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro",
    ]
    try:
        ano, m = (int(x) for x in mes.split("-"))
        return f"{nomes[m - 1]}/{ano}"
    except (ValueError, IndexError):
        return mes
