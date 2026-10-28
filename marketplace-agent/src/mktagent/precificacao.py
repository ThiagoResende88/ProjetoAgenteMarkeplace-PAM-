"""Precificacao de pecas de impressao 3D e de produtos revendidos.

Feita para o negocio 3D Print Franca / Mocozim:
- custo real de producao (filamento, maquina, falha, acabamento, embalagem, mao de obra);
- taxas do canal (Shopee, TikTok, Mercado Livre, Instagram, consignacao, direto);
- preco minimo (empate) e preco para a margem alvo;
- cenarios para comparar precos (ex.: Mocozim R$ 9,90 x R$ 15 x kit).

Valores em reais na entrada e centavos internamente.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

from .config import MARKETPLACES, NOMES_MARKETPLACE, TAXAS_CANAL, normalizar_canal
from .dinheiro import fmt_brl, fmt_pct, para_centavos, parse_valor


def _arredondar_90(valor: Decimal) -> Decimal:
    """Arredonda para cima no proximo preco terminado em ,90."""
    base = valor.quantize(Decimal("1"), rounding=ROUND_CEILING)
    candidato = base - Decimal("0.10")
    if candidato < valor:
        candidato = base + Decimal("0.90")
    return candidato


def _centavos(valor: Decimal) -> int:
    """Decimal -> centavos com arredondamento (nunca truncar dinheiro)."""
    return int((valor * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _quantizar(valor: Decimal | None) -> Decimal | None:
    if valor is None:
        return None
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _decimal(valor: object, padrao: str = "0") -> Decimal:
    if valor is None or valor == "":
        return Decimal(padrao)
    if isinstance(valor, Decimal):
        return valor
    convertido = parse_valor(valor)
    return convertido if convertido is not None else Decimal(padrao)


def precificar_3d(
    peso_g: object,
    custo_filamento_kg: object,
    horas_impressao: object = 0,
    custo_maquina_hora: object = 0,
    taxa_falha_pct: object = 0.05,
    acabamento: object = 0,
    embalagem: object = 0,
    mao_de_obra: object = 0,
    canal: str = "shopee",
    taxa_canal_pct: object = None,
    taxa_fixa_por_item: object = 0,
    frete_pago_pelo_vendedor: object = 0,
    margem_alvo_pct: object = 0.30,
    preco_venda: object = None,
    unidades: int = 1,
) -> dict:
    """Calcula custo, precos e margem de uma peca 3D (ou kit).

    Todos os valores monetarios aceitam texto BR ("12,50"). ``taxa_falha_pct``,
    ``margem_alvo_pct`` e ``taxa_canal_pct`` aceitam fracao (0.05) ou percentual
    (5), com e sem ``%``.
    """
    canal = normalizar_canal(canal)
    unidades = max(1, int(unidades or 1))
    peso = _decimal(peso_g) * unidades
    custo_kg = _decimal(custo_filamento_kg)
    horas = _decimal(horas_impressao)
    maquina_hora = _decimal(custo_maquina_hora)
    falha = _decimal(taxa_falha_pct)
    if falha > 1:
        falha = falha / 100
    falha = min(max(falha, Decimal("0")), Decimal("0.9"))

    material = (peso / Decimal(1000)) * custo_kg
    maquina = horas * maquina_hora
    acabamento_d = _decimal(acabamento)
    embalagem_d = _decimal(embalagem)
    mao_obra_d = _decimal(mao_de_obra)
    direto = material + maquina + acabamento_d + embalagem_d + mao_obra_d
    perda = direto * falha
    custo_total = direto + perda

    if taxa_canal_pct in (None, ""):
        taxa_canal = Decimal(TAXAS_CANAL.get(canal, "0.10"))
    else:
        taxa_canal = _decimal(taxa_canal_pct)
        if taxa_canal > 1:
            taxa_canal = taxa_canal / 100
    taxa_fixa = _decimal(taxa_fixa_por_item) * unidades
    frete = _decimal(frete_pago_pelo_vendedor)

    alvo = _decimal(margem_alvo_pct)
    if alvo > 1:
        alvo = alvo / 100

    def preco_para(margem: Decimal) -> Decimal | None:
        denominador = Decimal(1) - taxa_canal - margem
        if denominador <= Decimal("0.02"):
            return None
        return (custo_total + taxa_fixa + frete) / denominador

    preco_empate = _quantizar(preco_para(Decimal("0")))
    preco_alvo = _quantizar(preco_para(alvo))
    preco_sugerido = _arredondar_90(preco_alvo) if preco_alvo else None

    cenarios = []
    precos_cenarios: list[tuple[str, Decimal | None]] = [
        ("preco informado", _decimal(preco_venda) if preco_venda not in (None, "") else None),
        ("preco de empate", preco_empate),
        ("preco para margem alvo", preco_alvo),
        ("preco sugerido (,90)", preco_sugerido),
    ]
    vistos: set[str] = set()
    for rotulo, preco in precos_cenarios:
        if preco is None:
            continue
        preco = preco.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        chave = f"{preco:.2f}"
        if chave in vistos:
            continue
        vistos.add(chave)
        taxas = preco * taxa_canal + taxa_fixa
        lucro = preco - taxas - frete - custo_total
        margem = lucro / preco if preco else Decimal("0")
        cenarios.append(
            {
                "rotulo": rotulo,
                "preco": fmt_brl(_centavos(preco)),
                "preco_centavos": _centavos(preco),
                "taxas": fmt_brl(_centavos(taxas)),
                "frete": fmt_brl(_centavos(frete)),
                "custo": fmt_brl(_centavos(custo_total)),
                "lucro": fmt_brl(_centavos(lucro)),
                "lucro_centavos": _centavos(lucro),
                "margem": fmt_pct(float(margem)),
                "margem_fracao": float(margem),
            }
        )

    avisos: list[str] = []
    if not horas and not maquina_hora:
        avisos.append(
            "Voce nao informou tempo de impressao nem custo/hora de maquina: o custo "
            "esta subestimado (energia, desgaste, manutencao)."
        )
    if not horas and maquina_hora:
        avisos.append("Custo/hora informado sem horas de impressao: nao foi aplicado.")
    if material == 0:
        avisos.append("Peso ou custo do filamento zerado: sem custo de material.")
    if falha == 0:
        avisos.append(
            "Taxa de falha 0%: em impressao 3D o realista e 3-10% (depende da peca)."
        )
    if frete > 0 and preco_sugerido and any(
        cenario["margem_fracao"] < 0 for cenario in cenarios
    ):
        avisos.append(
            "Com frete pago pelo vendedor algum cenario fica no prejuizo: em item de "
            "ticket baixo, frete gratis costuma inviabilizar. Prefira kit ou canal direto."
        )

    return {
        "canal": canal,
        "canal_nome": NOMES_MARKETPLACE.get(canal, canal),
        "unidades": unidades,
        "entradas": {
            "peso_total_g": float(peso),
            "custo_filamento_kg": fmt_brl(_centavos(custo_kg)),
            "horas_impressao": float(horas),
            "custo_maquina_hora": fmt_brl(_centavos(maquina_hora)),
            "taxa_falha": fmt_pct(float(falha)),
            "acabamento": fmt_brl(_centavos(acabamento_d)),
            "embalagem": fmt_brl(_centavos(embalagem_d)),
            "mao_de_obra": fmt_brl(_centavos(mao_obra_d)),
        },
        "custo": {
            "material": fmt_brl(_centavos(material)),
            "maquina": fmt_brl(_centavos(maquina)),
            "acabamento": fmt_brl(_centavos(acabamento_d)),
            "embalagem": fmt_brl(_centavos(embalagem_d)),
            "mao_de_obra": fmt_brl(_centavos(mao_obra_d)),
            "perda_falha": fmt_brl(_centavos(perda)),
            "custo_total": fmt_brl(_centavos(custo_total)),
            "custo_total_centavos": _centavos(custo_total),
        },
        "taxas_canal": {
            "percentual": fmt_pct(float(taxa_canal)),
            "taxa_fixa": fmt_brl(_centavos(taxa_fixa)),
            "frete_pago_pelo_vendedor": fmt_brl(_centavos(frete)),
        },
        "precos": {
            "empate": fmt_brl(_centavos(preco_empate)) if preco_empate else None,
            "empate_centavos": _centavos(preco_empate) if preco_empate else None,
            "para_margem_alvo": fmt_brl(_centavos(preco_alvo)) if preco_alvo else None,
            "sugerido": fmt_brl(_centavos(preco_sugerido)) if preco_sugerido else None,
            "sugerido_centavos": _centavos(preco_sugerido) if preco_sugerido else None,
            "margem_alvo": fmt_pct(float(alvo)),
        },
        "cenarios": cenarios,
        "avisos": avisos,
        "observacoes": [
            "Taxa de canal padrao da tabela do projeto; troque se seu plano/taxa real for outro.",
            "Custo/hora de maquina deve incluir energia, desgaste, manutencao e depreciacao.",
            "Para marketplace, o frete gratis/ subsidiado e a maior armadilha de ticket baixo.",
            "Canais disponiveis: " + ", ".join(MARKETPLACES),
        ],
    }


__all__ = ["precificar_3d"]
