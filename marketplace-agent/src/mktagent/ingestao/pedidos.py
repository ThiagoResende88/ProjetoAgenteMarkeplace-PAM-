"""Importacao de pedidos (Shopee, TikTok Shop ou planilha modelo unificada).

O mesmo importador aceita exportacoes nativas dos paineis e o CSV modelo do
projeto. O mapeamento das colunas e tolerante (aliases PT/EN + fuzzy).

Regras importantes:
- Um pedido pode ocupar varias linhas (uma por item).
- Colunas de nivel do pedido (comissao, frete, desconto...) as vezes vem
  repetidas em todas as linhas: quando todos os valores sao iguais usamos 1,
  quando variam somamos (taxas rateadas por item). Isso esta documentado e
  coberto por teste.
- Reimportar o mesmo arquivo nao duplica pedidos (upsert por pedido externo).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from pathlib import Path

from .. import db
from ..config import (
    TAXA_TIKTOK_COMISSAO,
    TAXA_TIKTOK_FIXO_CENTAVOS,
    TAXA_TIKTOK_SFP,
    normalizar_canal,
)
from ..datas import iso, parse_data
from ..dinheiro import para_centavos, parse_valor
from ..dominio import ItemImportado, PedidoImportado, ResultadoImportacao
from . import colunas as col
from .leitor import ler_tabela

SITUACOES = ("aprovado", "cancelado", "devolvido", "pendente", "desconhecido")

_IGNORAR_PEDIDO = {"total", "totais", "total geral", "resumo", "soma"}


def classificar_situacao(status: str | None) -> str:
    """Normaliza o status bruto do marketplace em uma situacao financeira."""
    s = col.normalizar(status or "")
    if not s:
        return "desconhecido"
    if any(t in s for t in ("cancel", "cancelad")):
        return "cancelado"
    if any(t in s for t in ("devolv", "return", "refund", "estorno", "reembols")):
        return "devolvido"
    if any(
        t in s
        for t in (
            "aguardando_pagamento",
            "nao_pago",
            "unpaid",
            "pending_payment",
            "pendente_de_pagamento",
            "em_aberto",
            "to_pay",
            "awaiting_payment",
        )
    ):
        return "pendente"
    if any(
        t in s
        for t in (
            "pago",
            "paid",
            "aprovad",
            "enviad",
            "shipped",
            "entreg",
            "conclu",
            "finaliz",
            "complete",
            "delivered",
            "to_ship",
            "aguardando_envio",
            "ready_to_ship",
            "in_transit",
            "a_caminho",
            "processing",
            "processando",
            "despach",
            "postado",
        )
    ):
        return "aprovado"
    if any(t in s for t in ("pendente", "aguardando", "pending", "awaiting")):
        return "pendente"
    return "desconhecido"


def _limpar_id_pedido(valor: str | None) -> str | None:
    if not valor:
        return None
    texto = str(valor).strip().lstrip("'").strip()
    if not texto or col.normalizar(texto) in _IGNORAR_PEDIDO:
        return None
    if re.fullmatch(r"\d+\.0+", texto):
        texto = texto.split(".")[0]
    return texto


def _inteiro(valor: str | None, padrao: int = 1) -> int:
    numero = parse_valor(valor)
    if numero is None:
        return padrao
    return max(0, int(numero))


def _agregar(valores: list[int | None]) -> int | None:
    validos = [v for v in valores if v is not None]
    if not validos:
        return None
    if len(set(validos)) == 1:
        return validos[0]  # coluna repetida por item: conta uma vez
    return sum(validos)  # coluna rateada por item: soma


def _hash_arquivo(caminho: Path) -> str:
    try:
        return hashlib.sha256(caminho.read_bytes()).hexdigest()[:16]
    except OSError:
        return ""


def importar_pedidos(
    conn,
    caminho: str | Path,
    marketplace: str | None = None,
    conta: str = "principal",
    dry_run: bool = False,
) -> ResultadoImportacao:
    caminho = Path(caminho).expanduser()
    tabela = ler_tabela(caminho)
    resultado = ResultadoImportacao(
        tipo="pedidos", arquivo=str(caminho), conta=conta, marketplace=marketplace
    )
    resultado.avisos.extend(tabela.avisos)

    mapa = col.MapaColunas(tabela.colunas, col.ALIASES_PEDIDOS)
    resultado.mapeamento = mapa.mapeamento()

    if marketplace is None:
        sugerido, motivo = col.sugerir_marketplace(tabela.colunas)
        marketplace = sugerido
        if sugerido:
            resultado.avisos.append(f"marketplace detectado: {sugerido} ({motivo})")
    if not marketplace:
        raise ValueError(
            "nao consegui detectar o marketplace pelas colunas. "
            "Informe --marketplace shopee ou --marketplace tiktok."
        )
    marketplace = (
        normalizar_canal(marketplace, padrao=None)
        or re.sub(r"\s+", "", marketplace.strip().lower())
    )
    resultado.marketplace = marketplace

    # export nativo da Shopee: subtotal ja vem liquido de desconto e o frete e
    # ambíguo (subsídio da plataforma x vendedor). Não somar de novo.
    normalizadas = {col.normalizar(c) for c in tabela.colunas}
    export_shopee = "taxa_de_comissao_liquida" in normalizadas or "subtotal_do_produto" in normalizadas
    aviso_shopee_frete = False
    aviso_tiktok_taxas = False
    if export_shopee:
        # no export nativo, "Valor Total" inclui frete do comprador; o subtotal
        # do produto é a receita correta. "Taxa de transação" não é a taxa de serviço.
        for campo, candidato in (
            ("itens_total", "Subtotal do produto"),
            ("taxa_servico", "Taxa de serviço líquida"),
            ("comissao", "Taxa de comissão líquida"),
            ("cliente", "Nome de usuário (comprador)"),
        ):
            if candidato in tabela.colunas:
                mapa.mapear_exato(campo, candidato)

    obrigatorios = ["pedido", "data_pedido"]
    faltando = mapa.faltando(obrigatorios)
    if faltando:
        raise ValueError(
            "colunas obrigatorias nao encontradas: "
            + ", ".join(faltando)
            + ". Colunas do arquivo: "
            + ", ".join(tabela.colunas[:25])
        )
    if not mapa.tem("preco_unitario") and not mapa.tem("itens_total"):
        raise ValueError(
            "precisa de uma coluna de preco (preco unitario) ou de valor total "
            "dos produtos. Colunas do arquivo: "
            + ", ".join(tabela.colunas[:25])
        )

    contas_produtos = {}
    try:
        for linha in conn.execute("SELECT sku, custo_unitario_centavos FROM produtos"):
            contas_produtos[linha["sku"]] = linha["custo_unitario_centavos"]
    except Exception:  # banco ainda sem tabela (nao deve acontecer via servico)
        contas_produtos = {}

    conta_id = 0 if dry_run else db.obter_conta(conn, marketplace, conta)

    # agrupa linhas por pedido preservando a ordem de aparicao
    grupos: dict[str, list[dict]] = {}
    descartadas = 0
    for linha in tabela.linhas:
        resultado.linhas += 1
        pedido_id = _limpar_id_pedido(mapa.valor(linha, "pedido"))
        if not pedido_id:
            descartadas += 1
            continue
        grupos.setdefault(pedido_id, []).append(linha)
    if descartadas:
        resultado.ignorados += descartadas
        resultado.adicionar_aviso(
            f"{descartadas} linha(s) sem numero de pedido foram ignoradas "
            "(provavelmente linha de total/rodape)."
        )

    sem_custo = 0
    sem_data = 0
    status_desconhecido = 0
    sem_preco = 0
    preco_estimado = 0

    for pedido_externo, linhas in grupos.items():
        primeira = linhas[0]
        data = parse_data(mapa.valor(primeira, "data_pedido")) or parse_data(
            mapa.valor(primeira, "data_entrega")
        )
        if data is None:
            sem_data += 1
            resultado.ignorados += 1
            resultado.adicionar_aviso(
                f"pedido {pedido_externo} sem data valida; ignorado."
            )
            continue

        status = mapa.valor(primeira, "status") or mapa.valor(
            linhas[-1] if len(linhas) > 1 else primeira, "status"
        )
        situacao = classificar_situacao(status)
        if export_shopee:
            coluna_devolucao = next(
                (c for c in tabela.colunas if "devolu" in col.normalizar(c)), None
            )
            if coluna_devolucao:
                devolucao = col.normalizar(primeira.get(coluna_devolucao) or "")
                if "aprovad" in devolucao:
                    situacao = "devolvido"
            if not aviso_shopee_frete:
                resultado.adicionar_aviso(
                    "export Shopee: desconto, frete e cupom ignorados (subtotal já é líquido; "
                    "frete da Shopee é ambíguo entre subsídio da plataforma e custo do vendedor). "
                    "Concilie o frete pelo extrato/repasses."
                )
                aviso_shopee_frete = True
        if situacao == "desconhecido":
            status_desconhecido += 1

        itens_por_sku: dict[str, dict] = {}
        for linha in linhas:
            sku = mapa.valor(linha, "sku")
            produto = mapa.valor(linha, "produto")
            if not sku:
                base = col.normalizar(produto) if produto else ""
                sku = f"auto:{base[:40]}" if base else "SEM-SKU"
            quantidade = _inteiro(mapa.valor(linha, "quantidade"), padrao=1) or 1
            preco = para_centavos(parse_valor(mapa.valor(linha, "preco_unitario")))
            total_linha = para_centavos(parse_valor(mapa.valor(linha, "itens_total")))
            if preco is None:
                sem_preco += 1
                if total_linha is not None:
                    preco = int(round(total_linha / quantidade))
                    preco_estimado += 1
                else:
                    preco = 0
            registro = itens_por_sku.setdefault(
                sku,
                {
                    "nome": produto,
                    "quantidade": 0,
                    "valor_total": 0,
                },
            )
            registro["quantidade"] += quantidade
            registro["valor_total"] += preco * quantidade
            if produto and not registro["nome"]:
                registro["nome"] = produto

        if not itens_por_sku:
            resultado.ignorados += 1
            continue

        itens = []
        for sku, registro in itens_por_sku.items():
            quantidade = max(1, registro["quantidade"])
            preco_medio = int(round(registro["valor_total"] / quantidade))
            custo = contas_produtos.get(sku)
            if custo is None:
                sem_custo += 1
            itens.append(
                ItemImportado(
                    sku=sku,
                    nome=registro["nome"],
                    quantidade=quantidade,
                    preco_unitario_centavos=preco_medio,
                    custo_unitario_centavos=custo,
                )
            )

        itens_total = sum(i.preco_unitario_centavos * i.quantidade for i in itens)
        itens_total_coluna = _agregar(
            [para_centavos(parse_valor(mapa.valor(l, "itens_total"))) for l in linhas]
        )
        if itens_total_coluna:
            itens_total = itens_total_coluna

        def valores(campo: str) -> list[int | None]:
            return [para_centavos(parse_valor(mapa.valor(l, campo))) for l in linhas]

        comissao_centavos = _agregar(valores("comissao")) or 0
        taxa_servico_centavos = _agregar(valores("taxa_servico")) or 0
        if (marketplace == "tiktok" and not mapa.tem("comissao")
                and not mapa.tem("taxa_servico")):
            tarifa_comissao = 0
            tarifa_servico = 0
            for item in itens:
                base = item.preco_unitario_centavos * item.quantidade
                tarifa_comissao += int(round(base * TAXA_TIKTOK_COMISSAO))
                tarifa_servico += (
                    int(round(base * TAXA_TIKTOK_SFP))
                    + TAXA_TIKTOK_FIXO_CENTAVOS * item.quantidade
                )
            comissao_centavos = tarifa_comissao
            taxa_servico_centavos = tarifa_servico
            if not aviso_tiktok_taxas:
                resultado.adicionar_aviso(
                    "TikTok: export nao traz taxas; estimadas pela tela de liquidacao "
                    "(10% comissao + 6% SFP + R$ 4,00 por item, frete zero quando coberto). "
                    "Confira no extrato do Seller Center."
                )
                aviso_tiktok_taxas = True

        pedido = PedidoImportado(
            marketplace=marketplace,
            conta_id=conta_id,
            pedido_externo=pedido_externo,
            status=(status or "").strip(),
            situacao=situacao,
            data_pedido=data,
            data_entrega=parse_data(mapa.valor(primeira, "data_entrega")),
            itens_total_centavos=itens_total,
            desconto_centavos=0 if export_shopee else (_agregar(valores("desconto")) or 0),
            frete_cobrado_centavos=0 if export_shopee else (_agregar(valores("frete_cobrado")) or 0),
            frete_pago_centavos=0 if export_shopee else (_agregar(valores("frete_pago")) or 0),
            comissao_centavos=comissao_centavos,
            taxa_servico_centavos=taxa_servico_centavos,
            cupom_centavos=_agregar(valores("cupom")) or 0,
            imposto_centavos=_agregar(valores("imposto")) or 0,
            repasse_centavos=_agregar(valores("repasse")),
            itens=itens,
        )

        if dry_run:
            resultado.secoes.setdefault("pedidos_preview", []).append(
                {
                    "pedido": pedido.pedido_externo,
                    "data": iso(pedido.data_pedido),
                    "status": pedido.status,
                    "situacao": pedido.situacao,
                    "itens": len(pedido.itens),
                    "itens_total_centavos": pedido.itens_total_centavos,
                }
            )
            continue

        existente = conn.execute(
            "SELECT id FROM pedidos WHERE marketplace = ? AND pedido_externo = ?",
            (marketplace, pedido_externo),
        ).fetchone()
        if existente:
            pedido_id_banco = int(existente["id"])
            conn.execute(
                "UPDATE pedidos SET conta_id=?, cliente=COALESCE(?, cliente), status=?, situacao=?, data_pedido=?, "
                "data_entrega=?, itens_total_centavos=?, desconto_centavos=?, "
                "frete_cobrado_centavos=?, frete_pago_centavos=?, comissao_centavos=?, "
                "taxa_servico_centavos=?, cupom_centavos=?, imposto_centavos=?, "
                "repasse_centavos=?, origem_importacao=?, "
                "atualizado_em=datetime('now') WHERE id=?",
                (
                    pedido.conta_id,
                    (mapa.valor(primeira, "cliente") or "").strip() or None,
                    pedido.status,
                    pedido.situacao,
                    iso(pedido.data_pedido),
                    iso(pedido.data_entrega),
                    pedido.itens_total_centavos,
                    pedido.desconto_centavos,
                    pedido.frete_cobrado_centavos,
                    pedido.frete_pago_centavos,
                    pedido.comissao_centavos,
                    pedido.taxa_servico_centavos,
                    pedido.cupom_centavos,
                    pedido.imposto_centavos,
                    pedido.repasse_centavos,
                    caminho.name,
                    pedido_id_banco,
                ),
            )
            conn.execute("DELETE FROM itens_pedido WHERE pedido_id = ?", (pedido_id_banco,))
            resultado.atualizados += 1
        else:
            cursor = conn.execute(
                "INSERT INTO pedidos (conta_id, marketplace, pedido_externo, cliente, status, "
                "situacao, data_pedido, data_entrega, itens_total_centavos, "
                "desconto_centavos, frete_cobrado_centavos, frete_pago_centavos, "
                "comissao_centavos, taxa_servico_centavos, cupom_centavos, "
                "imposto_centavos, repasse_centavos, origem_importacao) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    pedido.conta_id,
                    pedido.marketplace,
                    pedido.pedido_externo,
                    (mapa.valor(primeira, "cliente") or "").strip() or None,
                    pedido.status,
                    pedido.situacao,
                    iso(pedido.data_pedido),
                    iso(pedido.data_entrega),
                    pedido.itens_total_centavos,
                    pedido.desconto_centavos,
                    pedido.frete_cobrado_centavos,
                    pedido.frete_pago_centavos,
                    pedido.comissao_centavos,
                    pedido.taxa_servico_centavos,
                    pedido.cupom_centavos,
                    pedido.imposto_centavos,
                    pedido.repasse_centavos,
                    caminho.name,
                ),
            )
            pedido_id_banco = int(cursor.lastrowid)
            resultado.inseridos += 1

        for item in itens:
            conn.execute(
                "INSERT OR REPLACE INTO itens_pedido (pedido_id, sku, nome_produto, "
                "quantidade, preco_unitario_centavos, custo_unitario_centavos) "
                "VALUES (?,?,?,?,?,?)",
                (
                    pedido_id_banco,
                    item.sku,
                    item.nome,
                    item.quantidade,
                    item.preco_unitario_centavos,
                    item.custo_unitario_centavos,
                ),
            )

    info: dict = {
        "pedidos_lidos": len(grupos),
        "pedidos_sem_custo": sem_custo,
        "pedidos_sem_data": sem_data,
        "pedidos_status_desconhecido": status_desconhecido,
        "itens_sem_preco": sem_preco,
        "itens_com_preco_estimado": preco_estimado,
        "colunas_nao_reconhecidas": mapa.nao_usadas(),
    }
    resultado.secoes["qualidade"] = info
    if sem_custo:
        resultado.adicionar_aviso(
            f"{sem_custo} item(ns) sem custo cadastrado — a margem por SKU fica "
            "otimista para eles. Cadastre com 'mkt custos definir'."
        )
    if status_desconhecido:
        resultado.adicionar_aviso(
            f"{status_desconhecido} pedido(s) com status nao reconhecido: "
            "ficaram como 'desconhecido' e NAO entram na receita do DRE."
        )
    if mapa.nao_usadas():
        resultado.adicionar_aviso(
            "colunas ignoradas: " + ", ".join(mapa.nao_usadas()[:12])
        )
    if not resultado.secoes.get("pedidos_preview"):
        resultado.secoes["pedidos_preview"] = [
            {
                "pedido": p,
                "situacao": conn.execute(
                    "SELECT situacao FROM pedidos WHERE marketplace=? AND pedido_externo=?",
                    (marketplace, p),
                ).fetchone()[0],
            }
            for p in list(grupos)[:3]
        ]

    if not dry_run:
        db.registrar_importacao(
            conn,
            {
                "arquivo": str(caminho),
                "hash": _hash_arquivo(caminho),
                "tipo": "pedidos",
                "marketplace": marketplace,
                "conta": conta,
                "linhas": resultado.linhas,
                "inseridos": resultado.inseridos,
                "atualizados": resultado.atualizados,
                "ignorados": resultado.ignorados,
                "avisos": " | ".join(resultado.avisos[:10]),
            },
        )
    return resultado
