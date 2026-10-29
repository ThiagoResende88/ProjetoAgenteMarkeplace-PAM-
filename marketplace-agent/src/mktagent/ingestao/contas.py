"""Importacao de contas a pagar / a receber (planilha propria ou do contador)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from .. import db
from ..datas import iso, parse_data
from ..dinheiro import para_centavos, parse_valor
from ..dominio import ResultadoImportacao
from . import colunas as col
from .leitor import ler_tabela

# categorias que ja estao embutidas no pedido do marketplace; nao entram de novo
# no DRE como despesa operacional (evita contar duas vezes).
CATEGORIAS_NO_PEDIDO = {"insumo", "fornecedor", "frete", "imposto", "comissao", "taxa"}

_SINONIMOS_CATEGORIA = {
    "marketing": {"marketing", "anuncio", "anuncios", "ads", "publicidade", "trafego", "trafego_pago"},
    "fornecedor": {"fornecedor", "fornecedores", "compra", "compras", "mercadoria", "mercadorias"},
    "insumo": {"insumo", "insumos", "embalagem", "embalagens", "material", "materiais"},
    "frete": {"frete", "fretes", "logistica", "transportadora", "correios"},
    "imposto": {"imposto", "impostos", "tributo", "tributos", "das", "simples", "icms", "taxa"},
    "pessoal": {"pessoal", "prolabore", "pro_labore", "salario", "salarios", "funcionario", "equipe"},
    "software": {"software", "assinatura", "assinaturas", "ferramenta", "ferramentas", "sistema"},
    "estrutura": {"aluguel", "estrutura", "galpao", "armazem", "energia", "agua", "internet"},
    "contabilidade": {"contabilidade", "contador", "contadora", "fiscal"},
}


def normalizar_categoria(texto: str | None) -> str:
    bruto = col.normalizar(texto or "")
    if not bruto:
        return "outros"
    for categoria, sinonimos in _SINONIMOS_CATEGORIA.items():
        if bruto in sinonimos:
            return categoria
    for categoria, sinonimos in _SINONIMOS_CATEGORIA.items():
        if any(s in bruto for s in sinonimos):
            return categoria
    return bruto if bruto in CATEGORIAS_NO_PEDIDO else "outros"


def normalizar_tipo(texto: str | None) -> str:
    s = col.normalizar(texto or "")
    if any(t in s for t in ("receber", "entrada", "receita", "a_receber")):
        return "receber"
    return "pagar"


def _verdadeiro(texto: str | None) -> bool:
    s = col.normalizar(texto or "")
    return s in {"1", "sim", "true", "yes", "s", "mensal", "recorrente", "fixa"}


def importar_contas(
    conn,
    caminho: str | Path,
    dry_run: bool = False,
) -> ResultadoImportacao:
    caminho = Path(caminho).expanduser()
    tabela = ler_tabela(caminho)
    resultado = ResultadoImportacao(tipo="contas", arquivo=str(caminho))
    resultado.avisos.extend(tabela.avisos)

    mapa = col.MapaColunas(tabela.colunas, col.ALIASES_CONTAS)
    resultado.mapeamento = mapa.mapeamento()
    faltando = mapa.faltando(["descricao", "valor", "vencimento"])
    if faltando:
        raise ValueError(
            "colunas obrigatorias nao encontradas: "
            + ", ".join(faltando)
            + ". Colunas do arquivo: "
            + ", ".join(tabela.colunas[:25])
        )

    vistos: set[tuple] = set()
    for linha in tabela.linhas:
        resultado.linhas += 1
        descricao = (mapa.valor(linha, "descricao") or "").strip()
        valor = para_centavos(parse_valor(mapa.valor(linha, "valor")))
        vencimento = parse_data(mapa.valor(linha, "vencimento"))
        if not descricao or valor is None or vencimento is None:
            resultado.ignorados += 1
            continue
        tipo = normalizar_tipo(mapa.valor(linha, "tipo"))
        categoria = normalizar_categoria(mapa.valor(linha, "categoria"))
        pago_em = parse_data(mapa.valor(linha, "pago_em"))
        marketplace = (mapa.valor(linha, "marketplace") or "").strip().lower() or None
        if marketplace and marketplace not in {"shopee", "tiktok"}:
            marketplace = None
        recorrente = 1 if _verdadeiro(mapa.valor(linha, "recorrente")) else 0
        observacao = mapa.valor(linha, "observacao")
        chave = (tipo, descricao, valor, iso(vencimento))
        if chave in vistos:
            resultado.ignorados += 1
            resultado.adicionar_aviso(f"conta duplicada no arquivo: {descricao} ({iso(vencimento)})")
            continue
        vistos.add(chave)

        if dry_run:
            resultado.secoes.setdefault("contas_preview", []).append(
                {
                    "tipo": tipo,
                    "descricao": descricao,
                    "valor_centavos": valor,
                    "vencimento": iso(vencimento),
                    "pago_em": iso(pago_em),
                }
            )
            continue

        existente = conn.execute(
            "SELECT id, pago_em FROM contas_financeiras "
            "WHERE tipo=? AND descricao=? AND valor_centavos=? AND vencimento=?",
            chave,
        ).fetchone()
        if existente:
            conn.execute(
                "UPDATE contas_financeiras SET categoria=?, marketplace=?, observacao=?, "
                "recorrente=?, pago_em=COALESCE(?, pago_em), "
                "status=CASE WHEN COALESCE(?, pago_em) IS NULL THEN 'aberta' ELSE 'paga' END, "
                "atualizado_em=datetime('now') WHERE id=?",
                (
                    categoria,
                    marketplace,
                    observacao,
                    recorrente,
                    iso(pago_em),
                    iso(pago_em),
                    int(existente["id"]),
                ),
            )
            resultado.atualizados += 1
        else:
            conn.execute(
                "INSERT INTO contas_financeiras (tipo, descricao, categoria, marketplace, "
                "valor_centavos, vencimento, pago_em, status, recorrente, observacao, origem) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    tipo,
                    descricao,
                    categoria,
                    marketplace,
                    valor,
                    iso(vencimento),
                    iso(pago_em),
                    "paga" if pago_em else "aberta",
                    recorrente,
                    observacao,
                    caminho.name,
                ),
            )
            resultado.inseridos += 1

    if not dry_run:
        db.registrar_importacao(
            conn,
            {
                "arquivo": str(caminho),
                "tipo": "contas",
                "linhas": resultado.linhas,
                "inseridos": resultado.inseridos,
                "atualizados": resultado.atualizados,
                "ignorados": resultado.ignorados,
                "avisos": " | ".join(resultado.avisos[:10]),
            },
        )
    return resultado
