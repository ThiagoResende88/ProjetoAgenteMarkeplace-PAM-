"""Importacao de relatorios de desempenho diario (UpSeller/painel).

Formato tipico (export "Performance das Vendas"): uma linha por dia com
pedidos, pedidos validos, receita, cancelamentos e clientes. Nao substitui a
importacao de pedidos: e a visao agregada do canal/dia.
"""

from __future__ import annotations

from pathlib import Path

from .. import db
from ..config import MARKETPLACES, normalizar_canal
from ..datas import iso, parse_data
from ..dinheiro import para_centavos, parse_valor
from ..dominio import ResultadoImportacao
from . import colunas as col
from .leitor import ler_tabela

ALIASES_DESEMPENHO: dict[str, list[str]] = {
    "data": ["data", "dia", "date", "data do dia"],
    "pedidos": ["total de pedidos", "pedidos", "orders", "pedidos totais"],
    "pedidos_validos": ["pedidos validos", "valid orders", "pedidos aprovados", "pedidos pagos"],
    "pedidos_cancelados": ["pedidos cancelados", "cancelados", "cancelled orders", "canceled orders"],
    "clientes": ["clientes", "customers", "compradores"],
    "receita_total": [
        "valor total de vendas",
        "valor total",
        "receita total",
        "gmv",
        "total de vendas",
    ],
    "receita_valida": [
        "valor de vendas validas",
        "receita valida",
        "valor valido",
        "receita de vendas validas",
    ],
}


def _inteiro(valor: str | None) -> int:
    numero = parse_valor(valor)
    return int(numero) if numero is not None else 0


def importar_desempenho(
    conn,
    caminho: str | Path,
    canal: str | None = None,
    dry_run: bool = False,
) -> ResultadoImportacao:
    caminho = Path(caminho).expanduser()
    tabela = ler_tabela(caminho)
    resultado = ResultadoImportacao(tipo="desempenho", arquivo=str(caminho), marketplace=canal)
    resultado.avisos.extend(tabela.avisos)

    mapa = col.MapaColunas(tabela.colunas, ALIASES_DESEMPENHO)
    resultado.mapeamento = mapa.mapeamento()
    faltando = mapa.faltando(["data"])
    if faltando:
        raise ValueError(
            "coluna de data nao encontrada. Colunas do arquivo: "
            + ", ".join(tabela.colunas[:25])
        )
    if not mapa.tem("pedidos") and not mapa.tem("receita_total") and not mapa.tem("receita_valida"):
        raise ValueError(
            "precisa de ao menos uma coluna de pedidos ou receita. Colunas: "
            + ", ".join(tabela.colunas[:25])
        )

    tem_validos = mapa.tem("pedidos_validos")
    tem_receita_valida = mapa.tem("receita_valida")
    canal_final = normalizar_canal(canal, padrao="consolidado") if canal else "consolidado"
    if canal_final not in MARKETPLACES and canal_final != "consolidado":
        canal_final = "consolidado"
    resultado.marketplace = canal_final

    for linha in tabela.linhas:
        resultado.linhas += 1
        data = parse_data(mapa.valor(linha, "data"))
        if data is None:
            resultado.ignorados += 1
            continue
        pedidos = _inteiro(mapa.valor(linha, "pedidos"))
        validos = _inteiro(mapa.valor(linha, "pedidos_validos"))
        cancelados = _inteiro(mapa.valor(linha, "pedidos_cancelados"))
        clientes = _inteiro(mapa.valor(linha, "clientes"))
        receita_total = para_centavos(parse_valor(mapa.valor(linha, "receita_total"))) or 0
        receita_valida = para_centavos(parse_valor(mapa.valor(linha, "receita_valida"))) or 0
        if not tem_validos:
            validos = max(0, pedidos - cancelados)
        if not tem_receita_valida:
            receita_valida = receita_total

        if dry_run:
            resultado.secoes.setdefault("desempenho_preview", []).append(
                {
                    "data": data.isoformat(),
                    "pedidos_validos": validos,
                    "receita_valida_centavos": receita_valida,
                }
            )
            continue

        existente = conn.execute(
            "SELECT id FROM desempenho_diario WHERE canal=? AND data=?",
            (canal_final, data.isoformat()),
        ).fetchone()
        valores = (
            pedidos,
            validos,
            cancelados,
            clientes,
            receita_total,
            receita_valida,
            caminho.name,
        )
        if existente:
            conn.execute(
                "UPDATE desempenho_diario SET pedidos=?, pedidos_validos=?, "
                "pedidos_cancelados=?, clientes=?, receita_total_centavos=?, "
                "receita_valida_centavos=?, origem=? WHERE id=?",
                (*valores, int(existente["id"])),
            )
            resultado.atualizados += 1
        else:
            conn.execute(
                "INSERT INTO desempenho_diario (canal, data, pedidos, pedidos_validos, "
                "pedidos_cancelados, clientes, receita_total_centavos, "
                "receita_valida_centavos, origem) VALUES (?,?,?,?,?,?,?,?,?)",
                (canal_final, data.isoformat(), *valores),
            )
            resultado.inseridos += 1

    resultado.secoes.setdefault("qualidade", {})["canal"] = canal_final
    if not dry_run:
        db.registrar_importacao(
            conn,
            {
                "arquivo": str(caminho),
                "tipo": "desempenho",
                "marketplace": canal_final,
                "linhas": resultado.linhas,
                "inseridos": resultado.inseridos,
                "atualizados": resultado.atualizados,
                "ignorados": resultado.ignorados,
                "avisos": " | ".join(resultado.avisos[:10]),
            },
        )
    return resultado
