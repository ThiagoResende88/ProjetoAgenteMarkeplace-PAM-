#!/usr/bin/env python3
"""Gera os arquivos de exemplo (dados ficticios, deterministicos).

Uso: python3 scripts/gerar_exemplos.py
Os arquivos vao para marketplace-agent/examples/ e servem para:
- o comando ``mkt demo`` carregar um cenario completo;
- o usuario ver o formato esperado de cada planilha.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
EXEMPLOS = RAIZ / "examples"
SEED = 42

PRODUTOS = [
    ("ORG-001", "Organizador de gaveta acrilico", 12.50, 39.90, 0.22),
    ("LUM-002", "Luminaria LED de mesa", 24.00, 79.90, 0.18),
    ("CAP-003", "Capa de celular silicone", 6.80, 29.90, 0.20),
    ("FON-004", "Fone Bluetooth TWS", 45.00, 139.90, 0.14),
    ("SUP-005", "Suporte de celular para carro", 9.90, 34.90, 0.12),
    ("KIT-006", "Kit 3 organizadores", 32.00, 99.90, 0.08),
    ("ESP-007", "Espelho de bolso", 9.50, 24.90, 0.06),  # sem custo cadastrado
]

MESES = [(2026, 8), (2026, 9), (2026, 10)]
HOJE = date(2026, 10, 25)


def brl(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def num(valor: float) -> str:
    return f"{valor:.2f}"


def escolher_produto(rng: random.Random) -> tuple:
    total = sum(p[4] for p in PRODUTOS)
    alvo = rng.random() * total
    acumulado = 0.0
    for produto in PRODUTOS:
        acumulado += produto[4]
        if alvo <= acumulado:
            return produto
    return PRODUTOS[-1]


def preco_com_variacao(rng: random.Random, preco: float) -> float:
    variacao = rng.choice([1.0, 1.0, 1.0, 0.95, 1.05, 0.9])
    return round(preco * variacao, 2)


def gerar_pedidos(rng: random.Random, marketplace: str, quantidade: int) -> list[list[dict]]:
    """Devolve pedidos; cada pedido e uma lista de linhas (itens)."""
    pedidos = []
    sequencia = 0
    for ano, mes in MESES:
        for _ in range(quantidade):
            sequencia += 1
            dia_max = 25 if (ano, mes) == (2026, 10) else 28
            dia = rng.randint(1, dia_max)
            data = date(ano, mes, dia)
            hora = f"{rng.randint(8, 22):02d}:{rng.randint(0, 59):02d}"
            if rng.random() < 0.03:
                status = "cancelado"
            elif rng.random() < 0.02:
                status = "devolvido"
            elif rng.random() < 0.10:
                status = "enviado"
            else:
                status = "entregue"
            entrega = None
            if status in {"entregue"}:
                entrega = data + timedelta(days=rng.randint(2, 7))

            itens = [escolher_produto(rng)]
            if rng.random() < 0.30:
                segundo = escolher_produto(rng)
                if segundo[0] != itens[0][0]:
                    itens.append(segundo)
            itens_linhas = []
            for sku, nome, custo, preco, _peso in itens:
                quantidade_item = 1 if rng.random() > 0.08 else 2
                preco_final = preco_com_variacao(rng, preco)
                desconto_pct = rng.choice([0, 0, 0, 0.05, 0.1, 0.15])
                itens_linhas.append(
                    {
                        "sku": sku,
                        "nome": nome,
                        "quantidade": quantidade_item,
                        "preco": preco_final,
                        "desconto_pct": desconto_pct,
                    }
                )

            itens_total = sum(i["quantidade"] * i["preco"] for i in itens_linhas)
            desconto = round(
                sum(
                    i["quantidade"] * i["preco"] * i["desconto_pct"]
                    for i in itens_linhas
                ),
                2,
            )
            if marketplace == "shopee":
                frete_cobrado = 0.0 if rng.random() < 0.65 else 15.90
                frete_pago = round(rng.uniform(18.90, 29.90), 2)
                comissao = round(itens_total * 0.14, 2)
                taxa = round(itens_total * 0.02, 2)
            else:
                frete_cobrado = 0.0 if rng.random() < 0.75 else 12.90
                frete_pago = round(rng.uniform(14.90, 24.90), 2)
                comissao = round(itens_total * 0.08, 2)
                taxa = round(itens_total * 0.02, 2)
            cupom = round(itens_total * 0.05, 2) if rng.random() < 0.12 else 0.0
            imposto = 0.0
            liquido = (
                itens_total
                - desconto
                + frete_cobrado
                - frete_pago
                - comissao
                - taxa
                - cupom
                - imposto
            )
            pedido = {
                "id": (
                    f"SP{ano % 100:02d}{mes:02d}{sequencia:04d}"
                    if marketplace == "shopee"
                    else f"57{ano % 100:02d}{mes:02d}{sequencia:06d}"
                ),
                "data": data,
                "hora": hora,
                "entrega": entrega,
                "status": status,
                "itens": itens_linhas,
                "itens_total": round(itens_total, 2),
                "desconto": desconto,
                "frete_cobrado": frete_cobrado,
                "frete_pago": frete_pago,
                "comissao": comissao,
                "taxa": taxa,
                "cupom": cupom,
                "imposto": imposto,
                "liquido": round(liquido, 2),
            }
            pedidos.append(pedido)
    return pedidos


def status_shopee(status: str) -> str:
    return {
        "entregue": "Entregue",
        "enviado": "Enviado",
        "cancelado": "Cancelado",
        "devolvido": "Devolvido",
    }[status]


def status_tiktok(status: str) -> str:
    return {
        "entregue": "Delivered",
        "enviado": "Shipped",
        "cancelado": "Cancelled",
        "devolvido": "Returned",
    }[status]


def ratear(total: float, pesos: list[float]) -> list[float]:
    soma = sum(pesos) or 1.0
    partes = [round(total * (p / soma), 2) for p in pesos]
    diferenca = round(total - sum(partes), 2)
    if partes:
        partes[-1] = round(partes[-1] + diferenca, 2)
    return partes


def escrever_shopee(pedidos: list[dict], destino: Path) -> None:
    cabecalho = [
        "Nº do pedido",
        "Status do pedido",
        "Data de criação",
        "Data de entrega",
        "SKU",
        "Nome do produto",
        "Quantidade",
        "Preço unitário",
        "Desconto do vendedor",
        "Frete cobrado",
        "Frete pago pelo vendedor",
        "Taxa de comissão",
        "Taxa de serviço",
        "Cupom do vendedor",
        "Imposto",
        "Valor líquido",
    ]
    with destino.open("w", newline="", encoding="utf-8-sig") as fh:
        escritor = csv.writer(fh, delimiter=";")
        escritor.writerow(cabecalho)
        for pedido in pedidos:
            pesos = [i["quantidade"] * i["preco"] for i in pedido["itens"]]
            descontos = ratear(pedido["desconto"], pesos)
            fretes_c = ratear(pedido["frete_cobrado"], pesos)
            fretes_p = ratear(pedido["frete_pago"], pesos)
            comissoes = ratear(pedido["comissao"], pesos)
            taxas = ratear(pedido["taxa"], pesos)
            cupons = ratear(pedido["cupom"], pesos)
            liquidos = ratear(pedido["liquido"], pesos)
            for i, item in enumerate(pedido["itens"]):
                entrega = pedido["entrega"]
                escritor.writerow(
                    [
                        pedido["id"],
                        status_shopee(pedido["status"]),
                        f"{pedido['data'].strftime('%d/%m/%Y')} {pedido['hora']}",
                        entrega.strftime("%d/%m/%Y") if entrega else "",
                        item["sku"],
                        item["nome"],
                        item["quantidade"],
                        brl(item["preco"]),
                        brl(descontos[i]),
                        brl(fretes_c[i]),
                        brl(fretes_p[i]),
                        brl(comissoes[i]),
                        brl(taxas[i]),
                        brl(cupons[i]),
                        brl(0),
                        brl(liquidos[i]),
                    ]
                )


def escrever_tiktok(pedidos: list[dict], destino: Path) -> None:
    cabecalho = [
        "Order ID",
        "Order Status",
        "Created Time",
        "Delivered Time",
        "Seller SKU",
        "Product Name",
        "Quantity",
        "SKU Unit Price",
        "Order Amount",
        "Seller Discount",
        "Buyer Shipping Fee",
        "Seller Shipping Fee",
        "Platform Commission",
        "Payment Fee",
        "Seller Voucher",
        "Tax",
        "Settlement Amount",
    ]
    with destino.open("w", newline="", encoding="utf-8-sig") as fh:
        escritor = csv.writer(fh, delimiter=",")
        escritor.writerow(cabecalho)
        for pedido in pedidos:
            for item in pedido["itens"]:
                entrega = pedido["entrega"]
                escritor.writerow(
                    [
                        pedido["id"],
                        status_tiktok(pedido["status"]),
                        f"{pedido['data'].isoformat()} {pedido['hora']}:00",
                        f"{entrega.isoformat()} 10:00:00" if entrega else "",
                        item["sku"],
                        item["nome"],
                        item["quantidade"],
                        num(item["preco"]),
                        num(pedido["itens_total"]),
                        num(pedido["desconto"]),
                        num(pedido["frete_cobrado"]),
                        num(pedido["frete_pago"]),
                        num(pedido["comissao"]),
                        num(pedido["taxa"]),
                        num(pedido["cupom"]),
                        num(pedido["imposto"]),
                        num(pedido["liquido"]),
                    ]
                )


def gerar_repasses(rng: random.Random, pedidos: list[dict], marketplace: str) -> list[dict]:
    """Repasses semanais; deixa o ultimo mes parcialmente pendente."""
    por_mes: dict[tuple[int, int], list[dict]] = {}
    for pedido in pedidos:
        if pedido["status"] not in {"entregue", "enviado"}:
            continue
        por_mes.setdefault((pedido["data"].year, pedido["data"].month), []).append(pedido)
    repasses = []
    for (ano, mes), lista in sorted(por_mes.items()):
        liquido = sum(p["liquido"] for p in lista)
        # 3 repasses por mes, exceto outubro (parcial)
        partes = 3 if mes < 10 else 2
        valores = ratear(liquido * 0.995, [1 / partes] * partes)
        for i, valor in enumerate(valores, start=1):
            dia = 5 + (i - 1) * 9
            data = date(ano, mes, min(dia, 28))
            if data > HOJE:
                continue
            repasses.append(
                {
                    "data": data,
                    "valor": valor,
                    "referencia": f"REP-{ano}-{mes:02d}-{i}",
                }
            )
    # um estorno realista em setembro (justifica diferenca de conciliacao)
    if marketplace == "shopee" and any(ano == 2026 and mes == 9 for ano, mes in por_mes):
        repasses.append(
            {
                "data": date(2026, 9, 26),
                "valor": -180.0,
                "referencia": "ESTORNO-2026-09",
            }
        )
    repasses.sort(key=lambda r: r["data"])
    return repasses


def escrever_repasses(repasses: list[dict], destino: Path, formato: str) -> None:
    if formato == "shopee":
        cabecalho = ["Data do repasse", "Valor", "Referência"]
        with destino.open("w", newline="", encoding="utf-8-sig") as fh:
            escritor = csv.writer(fh, delimiter=";")
            escritor.writerow(cabecalho)
            for repasse in repasses:
                escritor.writerow(
                    [
                        repasse["data"].strftime("%d/%m/%Y"),
                        brl(repasse["valor"]),
                        repasse["referencia"],
                    ]
                )
    else:
        cabecalho = ["settlement_time", "net_amount", "settlement_id"]
        with destino.open("w", newline="", encoding="utf-8-sig") as fh:
            escritor = csv.writer(fh, delimiter=",")
            escritor.writerow(cabecalho)
            for repasse in repasses:
                escritor.writerow(
                    [repasse["data"].isoformat(), num(repasse["valor"]), repasse["referencia"]]
                )


def escrever_custos(destino: Path) -> None:
    cabecalho = ["sku", "produto", "custo_unitario", "preco_venda", "categoria"]
    with destino.open("w", newline="", encoding="utf-8-sig") as fh:
        escritor = csv.writer(fh, delimiter=";")
        escritor.writerow(cabecalho)
        for sku, nome, custo, preco, _peso in PRODUTOS:
            if sku == "ESP-007":
                continue  # propositalmente sem custo (gera alerta)
            escritor.writerow([sku, nome, brl(custo), brl(preco), "casa"])


def escrever_contas(destino: Path) -> None:
    cabecalho = ["tipo", "descricao", "categoria", "valor", "vencimento", "pago_em", "marketplace", "recorrente", "observacao"]
    linhas = []
    for ano, mes in MESES + [(2026, 11)]:
        dia = lambda d: date(ano, mes, min(d, 28))  # noqa: E731

        def pago(data):  # noqa: ANN001, ANN202
            return data.strftime("%d/%m/%Y") if data <= HOJE else None

        venc = {
            5: dia(5),
            8: dia(8),
            10: dia(10),
            12: dia(12),
            15: dia(15),
            18: dia(18),
            20: dia(20),
            22: dia(22),
        }
        linhas.extend(
            [
                ("pagar", "Fornecedor - reposicao de estoque", "fornecedor", 3800 + mes * 40, venc[10], pago(venc[10]), "", "sim", "lote mensal"),
                ("pagar", "Shopee Ads", "marketing", 900 + (mes - 8) * 150, venc[15], pago(venc[15]), "shopee", "sim", ""),
                ("pagar", "TikTok Ads", "marketing", 500 + (mes - 8) * 100, venc[15], pago(venc[15]), "tiktok", "sim", ""),
                ("pagar", "Assinatura ERP", "software", 129.90, venc[5], pago(venc[5]), "", "sim", ""),
                ("pagar", "Contabilidade", "contabilidade", 420, venc[20], pago(venc[20]), "", "sim", ""),
                ("pagar", "Prolabore", "pessoal", 2800, venc[5], pago(venc[5]), "", "sim", ""),
                ("pagar", "Aluguel do galpao", "estrutura", 1500, venc[8], pago(venc[8]), "", "sim", ""),
                ("pagar", "Energia eletrica", "estrutura", 240 + mes, venc[18], pago(venc[18]), "", "sim", ""),
                ("pagar", "Embalagens e insumos", "insumo", 310, venc[12], pago(venc[12]), "", "nao", ""),
                ("receber", "Reembolso de frete Shopee", "outros", 180, venc[22], None, "shopee", "nao", "aguardando"),
                ("receber", "Venda fora do marketplace (Pix)", "outros", 350 if mes == 11 else 0, venc[22], None, "", "nao", "cobrar cliente"),
            ]
        )
    # uma conta vencida em aberto (10/10/2026)
    linhas.append(("pagar", "Fornecedor - lote setembro (atrasado)", "fornecedor", 1240, date(2026, 10, 10), None, "", "nao", "negociar prazo"))
    with destino.open("w", newline="", encoding="utf-8-sig") as fh:
        escritor = csv.writer(fh, delimiter=";")
        escritor.writerow(cabecalho)
        for linha in linhas:
            tipo, descricao, categoria, valor, vencimento, pago_em, marketplace, recorrente, obs = linha
            if float(valor) <= 0:
                continue
            escritor.writerow(
                [
                    tipo,
                    descricao,
                    categoria,
                    brl(float(valor)),
                    vencimento.strftime("%d/%m/%Y"),
                    pago_em if pago_em else "",
                    marketplace,
                    recorrente,
                    obs,
                ]
            )


def escrever_estoque(destino: Path) -> None:
    quantidades = {
        "ORG-001": 40,
        "LUM-002": 12,
        "CAP-003": 120,
        "FON-004": 6,
        "SUP-005": 3,
        "KIT-006": 18,
        "ESP-007": 45,
    }
    with destino.open("w", newline="", encoding="utf-8-sig") as fh:
        escritor = csv.writer(fh, delimiter=";")
        escritor.writerow(["sku", "quantidade", "atualizado_em"])
        for sku, quantidade in quantidades.items():
            escritor.writerow([sku, quantidade, HOJE.strftime("%d/%m/%Y")])


def main() -> int:
    EXEMPLOS.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    pedidos_shopee = gerar_pedidos(rng, "shopee", 90)
    pedidos_tiktok = gerar_pedidos(rng, "tiktok", 40)

    escrever_shopee(pedidos_shopee, EXEMPLOS / "pedidos_shopee.csv")
    escrever_tiktok(pedidos_tiktok, EXEMPLOS / "pedidos_tiktok.csv")
    escrever_repasses(gerar_repasses(rng, pedidos_shopee, "shopee"), EXEMPLOS / "repasses_shopee.csv", "shopee")
    escrever_repasses(gerar_repasses(rng, pedidos_tiktok, "tiktok"), EXEMPLOS / "repasses_tiktok.csv", "tiktok")
    escrever_custos(EXEMPLOS / "custos_produtos.csv")
    escrever_contas(EXEMPLOS / "contas_a_pagar.csv")
    escrever_estoque(EXEMPLOS / "estoque.csv")

    print(f"Exemplos gerados em {EXEMPLOS}")
    for arquivo in sorted(EXEMPLOS.glob("*.csv")):
        linhas = sum(1 for _ in arquivo.open(encoding="utf-8-sig"))
        print(f"  {arquivo.name}: {linhas} linha(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
