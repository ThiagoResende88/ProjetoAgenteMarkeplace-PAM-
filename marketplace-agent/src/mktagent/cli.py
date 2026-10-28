#!/usr/bin/env python3
"""CLI do mktagent: ``mkt <comando>``.

Todos os comandos aceitam ``--json`` para saida estruturada (usada por testes
e por automacoes). Sem ``--json``, a saida e em portugues, pensada para leitura.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import MARKETPLACES, Config
from .datas import fmt_mes
from .servico import Servico
from .ingestao import TIPOS as TIPOS_IMPORTACAO

VERDE = "\033[32m"
AMARELO = "\033[33m"
VERMELHO = "\033[31m"
NEGRITO = "\033[1m"
CINZA = "\033[90m"
FIM = "\033[0m"


def _cor(texto: str, cor: str, destino=sys.stdout) -> str:
    if not getattr(destino, "isatty", lambda: False)():
        return texto
    return f"{cor}{texto}{FIM}"


def _imprimir_json(dados: dict) -> None:
    print(json.dumps(dados, ensure_ascii=False, indent=2, default=str))


def _titulo(texto: str) -> None:
    print()
    print(_cor(texto, NEGRITO))
    print(_cor("─" * max(20, len(texto)), CINZA))


def _linha(rotulo: str, valor, nivel: int = 0) -> None:
    prefixo = "  " * nivel
    print(f"{prefixo}{rotulo:<34}{valor:>16}")


def _tabela(cabecalhos: list[str], linhas: list[list[str]]) -> None:
    larguras = [len(c) for c in cabecalhos]
    for linha in linhas:
        for i, celula in enumerate(linha[: len(larguras)]):
            larguras[i] = max(larguras[i], len(str(celula)))
    formato = "  ".join(f"{{:<{l}}}" for l in larguras)
    print(_cor(formato.format(*cabecalhos), CINZA))
    for linha in linhas:
        print(formato.format(*[str(c) for c in linha[: len(larguras)]]))


# ── comandos ────────────────────────────────────────────────────────────────


def cmd_init(args: argparse.Namespace, servico: Servico) -> int:
    from . import db

    with servico._conexao() as conn:  # noqa: SLF001 - comando de administracao
        db.garantir_esquema(conn)
        contagem = conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    if args.json:
        _imprimir_json(
            {
                "banco": str(servico.config.banco),
                "existe": servico.config.banco.exists(),
                "pedidos": contagem,
                "pastas": {
                    "entradas": str(servico.config.entradas),
                    "saidas": str(servico.config.saidas),
                },
            }
        )
        return 0
    print(_cor("Banco pronto.", VERDE))
    print(f"  banco:    {servico.config.banco}")
    print(f"  entradas: {servico.config.entradas}  (coloque as planilhas aqui)")
    print(f"  saidas:   {servico.config.saidas}")
    print(f"  pedidos importados: {contagem}")
    print()
    print("Proximo passo: 'mkt demo' para carregar dados de exemplo,")
    print("ou 'mkt importar pedidos <arquivo.csv>' para comecar com seus dados.")
    return 0


def cmd_demo(args: argparse.Namespace, servico: Servico) -> int:
    resultado = servico.demo(limpar=args.limpar)
    if args.json:
        _imprimir_json(resultado)
        return 0
    _titulo("Dados de exemplo")
    for item in resultado["importacoes"]:
        print(
            f"  {item['tipo']:<10} {item['arquivo']:<28} "
            f"{item['inseridos']} inserido(s), {item['atualizados']} atualizado(s)"
        )
    print()
    print(resultado["proximo_passo"])
    return 0


def cmd_limpar(args: argparse.Namespace, servico: Servico) -> int:
    if not args.confirmar:
        print(
            "Isso apaga pedidos, produtos, contas, repasses e estoque do banco. "
            "Rode com --confirmar se for isso mesmo.",
            file=sys.stderr,
        )
        return 1
    resultado = servico.limpar()
    if args.json:
        _imprimir_json(resultado)
        return 0
    print(resultado["mensagem"])
    print(f"banco: {resultado['banco']}")
    return 0


def cmd_importar(args: argparse.Namespace, servico: Servico) -> int:
    resultado = servico.importar(
        args.tipo,
        args.arquivo,
        marketplace=args.marketplace,
        conta=args.conta,
        dry_run=args.dry_run,
    )
    if args.json:
        _imprimir_json(resultado)
        return 0
    _titulo(f"Importacao de {resultado['tipo']} — {'SIMULACAO' if args.dry_run else 'gravado'}")
    print(f"  arquivo:     {resultado['arquivo']}")
    print(f"  marketplace: {resultado.get('marketplace') or '-'}")
    print(f"  linhas:      {resultado['linhas_lidas']}")
    print(f"  inseridos:   {resultado['inseridos']}")
    print(f"  atualizados: {resultado['atualizados']}")
    print(f"  ignorados:   {resultado['ignorados']}")
    print()
    mapeamento = resultado.get("mapeamento_colunas") or {}
    reconhecidas = {k: v for k, v in mapeamento.items() if v}
    if reconhecidas:
        print(_cor("Colunas reconhecidas:", CINZA))
        for campo, coluna in reconhecidas.items():
            print(f"  {campo:<18} <- {coluna}")
    qualidade = (resultado.get("secoes") or {}).get("qualidade") or {}
    if qualidade:
        print()
        print(_cor("Qualidade:", CINZA))
        for chave, valor in qualidade.items():
            if chave == "colunas_nao_reconhecidas":
                continue
            print(f"  {chave}: {valor}")
    for aviso in resultado.get("avisos", []):
        print(_cor(f"  ! {aviso}", AMARELO))
    print()
    print(resultado["mensagem"])
    return 0


def cmd_importar_pasta(args: argparse.Namespace, servico: Servico) -> int:
    resultado = servico.importar_pasta(
        tipo=args.tipo, marketplace=args.marketplace, dry_run=args.dry_run
    )
    if args.json:
        _imprimir_json(resultado)
        return 0
    _titulo("Importacao da pasta entradas/")
    if not resultado.get("importados"):
        print(resultado["mensagem"])
        return 0
    for item in resultado["importados"]:
        if item.get("status") in {"erro", "ignorado"}:
            print(_cor(f"  {item['arquivo']}: {item.get('motivo') or item.get('erro')}", AMARELO))
            continue
        print(
            f"  {item['arquivo']}: {item['inseridos']} inserido(s), "
            f"{item['atualizados']} atualizado(s), {item['ignorados']} ignorado(s)"
        )
        for aviso in item.get("avisos", [])[:3]:
            print(_cor(f"      ! {aviso}", AMARELO))
    return 0


def cmd_dre(args: argparse.Namespace, servico: Servico) -> int:
    dados = servico.dre(args.mes, args.marketplace)
    if args.json:
        _imprimir_json(dados)
        return 0
    _imprimir_dre(dados)
    if args.por_marketplace and "por_marketplace" in dados:
        for mercado, bloco in dados["por_marketplace"].items():
            _imprimir_dre(bloco, compacto=True)
    if args.saida:
        caminho = Path(args.saida).expanduser()
        _exportar_dre_csv(dados, caminho)
        print(f"\nDRE exportado para {caminho}")
    return 0


def _imprimir_dre(dados: dict, compacto: bool = False) -> None:
    mercado = dados.get("marketplace", "todos")
    rotulo = "todos os marketplaces" if mercado in {"todos", None} else mercado
    _titulo(f"DRE — {dados.get('mes_extenso', '')} — {rotulo}")
    pedidos = dados.get("pedidos") or {}
    print(
        f"  pedidos: {pedidos.get('total', 0)} "
        f"(aprovados {pedidos.get('aprovados', 0)}, cancelados {pedidos.get('cancelados', 0)}, "
        f"devolvidos {pedidos.get('devolvidos', 0)}, pendentes {pedidos.get('pendentes', 0)})"
    )
    print(f"  unidades: {dados.get('unidades', 0)}   ticket medio: {dados.get('ticket_medio')}")
    print()
    _linha("Receita bruta", dados.get("receita_bruta"))
    _linha("(-) Descontos", dados.get("descontos"), 1)
    _linha("(+) Frete cobrado", dados.get("frete_cobrado"), 1)
    _linha("(-) Frete pago", dados.get("frete_pago"), 1)
    _linha("(-) Comissao", dados.get("comissao"), 1)
    _linha("(-) Taxa de servico", dados.get("taxa_servico"), 1)
    _linha("(-) Cupom", dados.get("cupom"), 1)
    _linha("(-) Imposto", dados.get("imposto"), 1)
    _linha("(=) Receita liquida", dados.get("receita_liquida"))
    _linha("(-) CMV", dados.get("cmv"), 1)
    _linha("(=) Margem de contribuicao", f"{dados.get('margem_contribuicao')}  ({dados.get('margem_contribuicao_pct')})")
    _linha("(-) Despesas operacionais", dados.get("opex"), 1)
    if dados.get("outras_receitas_centavos"):
        _linha("(+) Outras receitas", dados.get("outras_receitas"), 1)
    _linha("(=) Lucro liquido", f"{dados.get('lucro_liquido')}  ({dados.get('lucro_liquido_pct')})")
    print()
    despesas = dados.get("despesas_por_categoria") or {}
    if despesas:
        print(_cor("  Despesas operacionais por categoria:", CINZA))
        for categoria, valor in despesas.items():
            print(f"    {categoria:<20}{valor:>16}")
    custos = dados.get("custos_ja_no_pedido") or {}
    if custos:
        print(_cor("  Custos ja embutidos no pedido (nao somados de novo):", CINZA))
        for categoria, valor in custos.items():
            print(f"    {categoria:<20}{valor:>16}")
    print()
    _linha("Repasses recebidos no mes", dados.get("repasses"))
    _linha("Diferenca de conciliacao", dados.get("diferenca_conciliacao"))
    completude = dados.get("completude") or {}
    if completude:
        print()
        print(
            _cor(
                "  Cobertura de custo: "
                f"{completude.get('cobertura_custo_itens_pct')} "
                f"({completude.get('itens_total', 0) - completude.get('itens_sem_custo', 0)}"
                f"/{completude.get('itens_total', 0)} itens com custo)",
                CINZA,
            )
        )
    if not compacto:
        for aviso in dados.get("avisos", []):
            print(_cor(f"  ! {aviso}", AMARELO))
        observacoes = dados.get("observacoes") or []
        if observacoes:
            print()
            print(_cor("  Como ler este DRE:", CINZA))
            for observacao in observacoes:
                print(f"    - {observacao}")


def _exportar_dre_csv(dados: dict, caminho: Path) -> None:
    import csv

    campos = [
        ("mes", dados.get("mes")),
        ("marketplace", dados.get("marketplace")),
        ("receita_bruta", dados.get("receita_bruta")),
        ("descontos", dados.get("descontos")),
        ("frete_cobrado", dados.get("frete_cobrado")),
        ("frete_pago", dados.get("frete_pago")),
        ("comissao", dados.get("comissao")),
        ("taxa_servico", dados.get("taxa_servico")),
        ("cupom", dados.get("cupom")),
        ("imposto", dados.get("imposto")),
        ("cmv", dados.get("cmv")),
        ("receita_liquida", dados.get("receita_liquida")),
        ("margem_contribuicao", dados.get("margem_contribuicao")),
        ("despesas_operacionais", dados.get("opex")),
        ("outras_receitas", dados.get("outras_receitas")),
        ("lucro_liquido", dados.get("lucro_liquido")),
        ("repasses", dados.get("repasses")),
        ("diferenca_conciliacao", dados.get("diferenca_conciliacao")),
    ]
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", newline="", encoding="utf-8-sig") as fh:
        escritor = csv.writer(fh, delimiter=";")
        escritor.writerow(["metrica", "valor"])
        for nome, valor in campos:
            escritor.writerow([nome, valor])


def cmd_comparativo(args: argparse.Namespace, servico: Servico) -> int:
    dados = servico.comparativo(args.mes)
    if args.json:
        _imprimir_json(dados)
        return 0
    _titulo(f"Comparativo {fmt_mes(dados['mes'])} vs {fmt_mes(dados['mes_anterior'])}")
    _linha("Receita bruta", dados["receita_bruta"])
    _linha("Receita mes anterior", dados["receita_bruta_anterior"])
    _linha("Variacao da receita", dados["variacao_receita"])
    _linha("Lucro liquido", dados["lucro_liquido"])
    _linha("Lucro mes anterior", dados["lucro_liquido_anterior"])
    _linha("Variacao do lucro", dados["variacao_lucro"])
    return 0


def cmd_margem(args: argparse.Namespace, servico: Servico) -> int:
    dados = servico.margem(
        mes=args.mes,
        dias=args.dias,
        limite=args.limite,
        marketplace=args.marketplace,
        margem_alvo=args.margem_alvo,
    )
    if args.json:
        _imprimir_json(dados)
        return 0
    _titulo(f"Margem por SKU — {dados['periodo']}")
    print(f"  alvo de margem: {dados['margem_alvo']}   marketplace: {dados['marketplace']}")
    print()
    linhas = []
    for item in dados["skus"]:
        formato = item["fmt"]
        linhas.append(
            [
                item["sku"],
                str(item["unidades"]),
                formato["receita_bruta"],
                formato["cmv"],
                formato["margem"],
                formato["margem_pct"],
                item["classe_abc"],
                "" if item["custo_conhecido"] else "SEM CUSTO",
            ]
        )
    _tabela(["SKU", "Un.", "Receita", "CMV", "Margem", "%", "ABC", "Alerta"], linhas)
    totais = dados["totais"]
    print()
    _linha("Receita bruta total", totais["receita_bruta"])
    _linha("CMV total", totais["cmv"])
    _linha("Margem total", totais["margem"])
    for aviso in dados.get("avisos", []):
        print(_cor(f"  ! {aviso}", AMARELO))
    return 0


def cmd_caixa(args: argparse.Namespace, servico: Servico) -> int:
    dados = servico.caixa(args.dias)
    if args.json:
        _imprimir_json(dados)
        return 0
    _titulo(f"Fluxo de caixa — {args.dias} dias")
    _linha("Entradas previstas", dados["entradas_previstas"])
    _linha("Saidas previstas", dados["saidas_previstas"])
    _linha("Saldo do periodo", dados["saldo_do_periodo"])
    _linha("Vencido a pagar", dados["vencido_a_pagar"])
    print()
    for semana in dados["semanas"]:
        print(
            f"  {semana['rotulo']:<26} "
            f"entradas {semana['fmt']['entradas']:>14}  "
            f"saidas {semana['fmt']['saidas']:>14}  "
            f"saldo {semana['fmt']['saldo']:>14}"
        )
    if dados["contas_vencidas"]:
        print()
        print(_cor("  Vencidas em aberto:", VERMELHO))
        for conta in dados["contas_vencidas"]:
            print(
                f"    {conta['descricao']:<34} {conta['valor']:>14}  "
                f"venceu {conta['vencimento']} ({conta['dias_atraso']} dias)"
            )
    for aviso in dados.get("avisos", []):
        print(_cor(f"  ! {aviso}", AMARELO))
    return 0


def cmd_alertas(args: argparse.Namespace, servico: Servico) -> int:
    dados = servico.alertas()
    if args.json:
        _imprimir_json(dados)
        return 0
    _titulo(f"Alertas ({dados['total']})")
    if not dados["alertas"]:
        print(_cor("  Nenhum alerta. Tudo em ordem.", VERDE))
        return 0
    for alerta in dados["alertas"]:
        cor = {"alta": VERMELHO, "media": AMARELO, "baixa": CINZA}.get(alerta["severidade"], CINZA)
        print(_cor(f"  [{alerta['severidade'].upper()}] {alerta['titulo']}", cor))
        print(f"      {alerta['detalhe']}")
        print(f"      acao: {alerta['acao']}")
        print()
    return 0


def cmd_estoque(args: argparse.Namespace, servico: Servico) -> int:
    dados = servico.estoque(args.dias)
    if args.json:
        _imprimir_json(dados)
        return 0
    _titulo(f"Cobertura de estoque — media dos ultimos {dados['periodo_dias']} dias")
    if dados["sem_estoque_importado"]:
        print("  Nenhuma posicao de estoque importada.")
        return 0
    linhas = [
        [
            item["sku"],
            str(item["estoque"]),
            str(item["vendas_periodo"]),
            f"{item['dias_cobertura']}" if item["dias_cobertura"] is not None else "-",
        ]
        for item in dados["itens"]
    ]
    _tabela(["SKU", "Estoque", "Vendas periodo", "Dias de cobertura"], linhas)
    return 0


def cmd_contas(args: argparse.Namespace, servico: Servico) -> int:
    dados = servico.contas(args.status)
    if args.json:
        _imprimir_json(dados)
        return 0
    _titulo(f"Contas a pagar/receber — {dados['filtro']}")
    print(f"  a pagar: {dados['total_a_pagar']}   a receber: {dados['total_a_receber']}")
    print()
    linhas = [
        [
            str(conta["id"]),
            "PAGAR" if conta["tipo"] == "pagar" else "RECEBER",
            conta["descricao"],
            conta["categoria"],
            conta["valor"],
            conta["vencimento_fmt"],
            conta["status"],
        ]
        for conta in dados["contas"]
    ]
    _tabela(["ID", "Tipo", "Descricao", "Categoria", "Valor", "Vencimento", "Status"], linhas)
    return 0


def cmd_conta_criar(args: argparse.Namespace, servico: Servico) -> int:
    resultado = servico.criar_conta(
        tipo=args.tipo,
        descricao=args.descricao,
        valor=args.valor,
        vencimento=args.vencimento,
        categoria=args.categoria,
        marketplace=args.marketplace,
        observacao=args.observacao,
    )
    if args.json:
        _imprimir_json(resultado)
        return 0
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


def cmd_conta_pagar(args: argparse.Namespace, servico: Servico) -> int:
    resultado = servico.marcar_paga(args.id, pago_em=args.data)
    if args.json:
        _imprimir_json(resultado)
        return 0
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


def cmd_pedido_criar(args: argparse.Namespace, servico: Servico) -> int:
    itens = []
    for bruto in args.item:
        partes = bruto.split(":")
        if len(partes) != 3:
            raise ValueError(f"item invalido: {bruto!r}. Use SKU:QUANTIDADE:PRECO")
        itens.append(
            {"sku": partes[0].strip(), "quantidade": int(partes[1]), "preco_unitario": partes[2]}
        )
    resultado = servico.criar_pedido(
        canal=args.canal,
        cliente=args.cliente,
        data=args.data,
        itens=itens,
        status=args.status,
        pedido_externo=args.pedido,
    )
    if args.json:
        _imprimir_json(resultado)
        return 0
    _titulo(f"Pedido criado — {resultado['pedido']}")
    print(f"  cliente:  {resultado['cliente'] or '-'}")
    print(f"  canal:    {resultado['canal']}")
    print(f"  status:   {resultado['status']} -> situacao {resultado['situacao']}")
    for item in resultado["itens"]:
        print(f"  {item['sku']}: {item['quantidade']} x R$ {item['preco_unitario_centavos']/100:.2f}")
    print()
    print(f"  total: {resultado['total']}")
    print(f"  {resultado['proximo_passo']}")
    return 0


def cmd_pedido_status(args: argparse.Namespace, servico: Servico) -> int:
    resultado = servico.atualizar_status_pedido(
        args.pedido, args.status, canal=args.canal
    )
    if args.json:
        _imprimir_json(resultado)
        return 0
    _titulo(f"Status atualizado — {resultado['pedido']}")
    print(f"  {resultado['status_anterior']} -> {resultado['status_novo']} "
          f"(situacao {resultado['situacao']})")
    print(f"  total: {resultado['total']} | entra na receita: "
          f"{'sim' if resultado['entra_na_receita'] else 'nao'}")
    return 0


def cmd_produtos(args: argparse.Namespace, servico: Servico) -> int:
    dados = servico.produtos()
    if args.json:
        _imprimir_json(dados)
        return 0
    _titulo(f"Produtos ({dados['quantidade']})")
    linhas = [
        [
            produto["sku"],
            (produto["nome"] or "")[:30],
            produto["custo"] or "SEM CUSTO",
            produto["preco_venda"] or "-",
            str(produto["estoque"]) if produto["estoque"] is not None else "-",
        ]
        for produto in dados["produtos"]
    ]
    _tabela(["SKU", "Produto", "Custo", "Preco", "Estoque"], linhas)
    return 0


def cmd_custo(args: argparse.Namespace, servico: Servico) -> int:
    resultado = servico.registrar_custo(
        args.sku, args.valor, preco_venda=args.preco, nome=args.nome
    )
    if args.json:
        _imprimir_json(resultado)
        return 0
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


def cmd_pedidos(args: argparse.Namespace, servico: Servico) -> int:
    dados = servico.pedidos(
        mes=args.mes,
        marketplace=args.marketplace,
        situacao=args.situacao,
        limite=args.limite,
        cliente=args.cliente,
    )
    if args.json:
        _imprimir_json(dados)
        return 0
    _titulo(f"Pedidos ({dados['quantidade']})")
    linhas = [
        [
            pedido["pedido"],
            pedido.get("cliente") or "-",
            pedido["marketplace"],
            pedido["data"],
            pedido["situacao"],
            pedido["total"],
        ]
        for pedido in dados["pedidos"]
    ]
    _tabela(["Pedido", "Cliente", "Canal", "Data", "Situacao", "Total"], linhas)
    print()
    print(f"  total listado: {dados['total_listado']}")
    return 0


def cmd_resumo(args: argparse.Namespace, servico: Servico) -> int:
    dados = servico.resumo()
    if args.json:
        _imprimir_json(dados)
        return 0
    _titulo("Resumo da operacao")
    info = dados["dados"]
    print(f"  pedidos: {info['pedidos']}   produtos: {info['produtos']} "
          f"(com custo: {info['produtos_com_custo']})")
    print(f"  contas em aberto: {info['contas_abertas']}   repasses: {info['repasses']}")
    if info["meses_com_pedidos"]:
        print(f"  meses com dados: {', '.join(info['meses_com_pedidos'])}")
    print()
    ultimo = dados["ultimo_mes"]
    dre_mes = ultimo["dre"]
    if "receita_bruta" in dre_mes:
        _titulo(f"Ultimo mes — {ultimo['mes_extenso']}")
        _linha("Receita bruta", dre_mes.get("receita_bruta"))
        _linha("Margem de contribuicao", dre_mes.get("margem_contribuicao"))
        _linha("Lucro liquido", dre_mes.get("lucro_liquido"))
    print()
    alertas = dados["alertas"]
    print(f"  alertas: {alertas['total']} "
          f"(alta {alertas['resumo'].get('alta', 0)}, "
          f"media {alertas['resumo'].get('media', 0)}, "
          f"baixa {alertas['resumo'].get('baixa', 0)})")
    for titulo in alertas["titulos"]:
        print(f"    - {titulo}")
    print()
    print(f"  modo atual: {dados['modo_atual']}")
    print()
    for instrucao in dados["como_usar"]:
        print(f"  · {instrucao}")
    return 0


def cmd_status(args: argparse.Namespace, servico: Servico) -> int:
    dados = servico.status_integracoes()
    if args.json:
        _imprimir_json(dados)
        return 0
    _titulo("Integracoes")
    print(f"  modo: {dados['modo']}")
    print(f"  banco: {servico.config.banco}")
    for mercado in ("shopee", "tiktok"):
        info = dados[mercado]
        print()
        print(f"  {mercado.upper()}")
        print(f"    app id:     {info.get('app_id') or '-'}")
        print(f"    secreto:    {info.get('app_secret_configurado')}")
        print(f"    ambiente:   {info.get('ambiente')}")
        print(f"    status:     {info.get('status')}")
        for passo in info.get("passos", []):
            print(f"      - {passo}")
    print()
    print(dados["proximo_passo"])
    return 0


def cmd_insights(args: argparse.Namespace, servico: Servico) -> int:
    dados = servico.insights(args.mes)
    if args.json:
        _imprimir_json(dados)
        return 0
    _titulo(f"Insights — {dados['mes_extenso']}")
    numeros = dados["numeros"]
    _linha("Receita bruta", numeros["receita_bruta"])
    _linha("Margem de contribuicao", f"{numeros['margem_contribuicao']} ({numeros['margem_contribuicao_pct']})")
    _linha("Lucro liquido", f"{numeros['lucro_liquido']} ({numeros['lucro_liquido_pct']})")
    _linha("Pedidos aprovados / ticket", f"{numeros['pedidos_aprovados']} / {numeros['ticket_medio']}")
    _linha("Variacao de receita", numeros["variacao_receita"])
    _linha("Gasto de marketing", f"{numeros['gasto_marketing']} ({numeros['marketing_pct_receita']})")
    _linha("Cancelamentos/devolucoes", numeros["taxa_cancelamento"])
    _linha("Saldo projetado 30 dias", numeros["saldo_caixa_30d"])
    print()
    print(_cor("O que os dados dizem:", CINZA))
    for item in dados["insights"]:
        print(f"  - {item}")
    if dados["acoes_prioritarias"]:
        print()
        print(_cor("Acoes priorizadas:", CINZA))
        for posicao, acao in enumerate(dados["acoes_prioritarias"], start=1):
            print(f"  {posicao}. [prioridade {acao['prioridade']}] {acao['acao']}")
            print(f"     ferramenta: {acao['ferramenta']}")
    print()
    print(_cor(f"  Concentracao: top3 {dados['concentracao']['top3_pct']} | "
               f"classe A {dados['concentracao']['classe_a_pct']} | "
               f"{dados['alertas_abertos']} alerta(s) aberto(s)", CINZA))
    return 0


def cmd_criativo(args: argparse.Namespace, servico: Servico) -> int:
    resultado = servico.gerar_criativo(
        sku=args.sku,
        beneficios=args.beneficio,
        formato=args.formato,
        tema=args.tema,
        preco=args.preco,
        titulo=args.titulo,
        selo=args.selo,
        foto=args.foto,
        modelo=args.modelo,
        logo=args.logo,
    )
    if args.json:
        _imprimir_json(resultado)
        return 0
    _titulo(f"Criativo gerado — {resultado['produto']}")
    print(f"  formato: {resultado['formato']}   tema: {resultado['tema']}   preco: {resultado['preco']}")
    for nome, caminho in resultado["arquivos"].items():
        if caminho:
            print(f"  {nome}: {caminho}")
    for aviso in resultado["avisos"]:
        print(_cor(f"  ! {aviso}", AMARELO))
    print()
    print(resultado["proximo_passo"])
    return 0


def cmd_briefing(args: argparse.Namespace, servico: Servico) -> int:
    resultado = servico.briefing_imagens(
        sku=args.sku,
        beneficios=args.beneficio,
        publico=args.publico,
        tom=args.tom,
    )
    if args.json:
        _imprimir_json(resultado)
        return 0
    _titulo(f"Briefing de imagens — {resultado['produto']}")
    print(f"  arquivo: {resultado['arquivo']}")
    print(f"  prompts: {resultado['total_prompts']}")
    print()
    for prompt in resultado["prompts"]:
        print(f"  · {prompt['uso']} ({prompt['proporcao']})")
    print()
    print(resultado["proximo_passo"])
    return 0


def cmd_upseller(args: argparse.Namespace, servico: Servico) -> int:
    if args.acao == "status":
        dados = servico.upseller_status()
        if args.json:
            _imprimir_json(dados)
            return 0
        _titulo("UpSeller (ERP)")
        print(f"  client id:      {dados.get('app_id') or '-'}")
        print(f"  api token:      {dados.get('app_secret_configurado')}")
        print(f"  mcp token:      {dados.get('mcp_token_configurado')}")
        print(f"  status:         {dados.get('status')}")
        print(f"  mcp oficial:    {dados.get('mcp_url')}")
        print()
        for passo in dados.get("passos", []):
            print(f"  - {passo}")
        return 0

    dados = servico.upseller_sincronizar_estoque()
    if args.json:
        _imprimir_json(dados)
        return 0
    _titulo("Sincronizacao de estoque via UpSeller")
    print(f"  paginas:          {dados.get('paginas')}")
    print(f"  SKUs atualizados: {dados.get('skus_atualizados')}")
    if dados.get("nao_mapeados_amostra"):
        print(_cor(f"  itens nao mapeados (amostra): {dados['nao_mapeados_amostra'][:2]}", AMARELO))
    for aviso in dados.get("avisos", []):
        print(_cor(f"  ! {aviso}", AMARELO))
    return 0


def cmd_desempenho(args: argparse.Namespace, servico: Servico) -> int:
    dados = servico.desempenho(canal=args.canal, dias=args.dias)
    if args.json:
        _imprimir_json(dados)
        return 0
    if not dados.get("periodo"):
        print(dados.get("mensagem", "sem dados"))
        print(dados.get("como_importar", ""))
        return 0
    _titulo(f"Desempenho diario — {dados['periodo']} ({dados['canal']})")
    _linha("Pedidos validos", dados["pedidos_validos"])
    _linha("Receita valida", dados["receita_valida"])
    _linha("Ticket medio", dados["ticket_medio"])
    _linha("Cancelamento", dados["taxa_cancelamento"])
    _linha("Dias com venda", f"{dados['dias_com_venda']} de {dados['dias_com_dado']}")
    _linha("Media pedidos/dia", dados["media_pedidos_por_dia"])
    _linha("Tendencia (2a metade)", dados["tendencia"]["variacao"])
    _linha("Projecao 30 dias", dados["projecao_30_dias"])
    print()
    print(_cor("Semanas:", CINZA))
    for semana in dados["semanas"]:
        print(f"  {semana['rotulo']:<26} {semana['receita_fmt']:>14}  "
              f"{semana['pedidos']:>3} pedidos  ticket {semana['ticket_fmt']}")
    print()
    print(_cor("Dias da semana (receita):", CINZA))
    for item in dados["dias_da_semana"]:
        print(f"  {item['dia']:<10} {item['receita']:>14}  {item['pedidos']:>3} pedidos")
    if dados.get("por_canal"):
        print()
        print(_cor("Canais:", CINZA))
        for canal in dados["por_canal"]:
            print(f"  {canal['rotulo']:<18} {canal['receita_fmt']:>14}  pedidos {canal['pedidos']}  ticket {canal['ticket_fmt']}")
    for alerta in dados.get("alertas", []):
        print(_cor(f"  ! {alerta}", AMARELO))
    return 0


def cmd_precificar(args: argparse.Namespace, servico: Servico) -> int:
    dados = servico.precificar_3d(
        peso_g=args.peso,
        custo_filamento_kg=args.custo_kg,
        horas_impressao=args.horas,
        custo_maquina_hora=args.maquina_hora,
        taxa_falha_pct=args.falha,
        acabamento=args.acabamento,
        embalagem=args.embalagem,
        mao_de_obra=args.mao_de_obra,
        canal=args.canal,
        taxa_canal_pct=args.taxa_canal,
        taxa_fixa_por_item=args.taxa_fixa,
        frete_pago_pelo_vendedor=args.frete,
        margem_alvo_pct=args.margem_alvo,
        preco_venda=args.preco,
        unidades=args.unidades,
    )
    if args.json:
        _imprimir_json(dados)
        return 0
    _titulo(f"Precificacao 3D — {dados['canal_nome']} ({dados['unidades']} un.)")
    print(f"  peso total: {dados['entradas']['peso_total_g']} g | filamento: {dados['entradas']['custo_filamento_kg']}/kg")
    print()
    custo = dados["custo"]
    for rotulo in ("material", "maquina", "acabamento", "embalagem", "mao_de_obra", "perda_falha"):
        print(f"  {rotulo:<18}{custo[rotulo]:>14}")
    _linha("Custo total", custo["custo_total"])
    print()
    precos = dados["precos"]
    _linha("Preco de empate", precos["empate"])
    _linha(f"Preco p/ margem {precos['margem_alvo']}", precos["para_margem_alvo"])
    _linha("Preco sugerido", precos["sugerido"])
    print()
    print(_cor("Cenarios:", CINZA))
    linhas = []
    for cenario in dados["cenarios"]:
        linhas.append(
            [
                cenario["rotulo"],
                cenario["preco"],
                cenario["taxas"],
                cenario["frete"],
                cenario["lucro"],
                cenario["margem"],
            ]
        )
    _tabela(["Cenario", "Preco", "Taxas", "Frete", "Lucro", "Margem"], linhas)
    for aviso in dados.get("avisos", []):
        print(_cor(f"  ! {aviso}", AMARELO))
    return 0


def cmd_telegram(args: argparse.Namespace, servico: Servico) -> int:
    from . import notificacoes

    if args.acao == "status":
        dados = servico.notificacoes_status()["telegram"]
        if args.json:
            _imprimir_json(dados)
            return 0
        _titulo("Telegram")
        print(f"  configurado: {'sim' if dados['configurado'] else 'nao'}")
        print(f"  chat_id:     {dados['chat_id'] or '-'}")
        for passo in dados["como_configurar"]:
            print(f"  - {passo}")
        return 0
    if args.acao == "testar":
        resultado = servico.enviar_telegram(
            texto="Teste do Gestor de Marketplaces: notificacao funcionando.",
            tipo="texto",
        )
    else:
        resultado = notificacoes.enviar_digest(servico, "telegram")
    if args.json:
        _imprimir_json(resultado)
        return 0
    print(f"Enviado pelo Telegram ({resultado.get('caracteres', 0)} caracteres).")
    return 0


def cmd_whatsapp(args: argparse.Namespace, servico: Servico) -> int:
    from . import notificacoes

    if args.acao == "status":
        dados = servico.notificacoes_status()["whatsapp"]
        if args.json:
            _imprimir_json(dados)
            return 0
        _titulo("WhatsApp Cloud API")
        print(f"  configurado: {'sim' if dados['configurado'] else 'nao'}")
        print(f"  destino:     {dados['destino'] or '-'}")
        for passo in dados["como_configurar"]:
            print(f"  - {passo}")
        return 0
    if args.acao == "testar":
        resultado = servico.enviar_whatsapp(
            texto="Teste do Gestor de Marketplaces: notificacao funcionando.", tipo="texto"
        )
    else:
        resultado = notificacoes.enviar_digest(servico, "whatsapp")
    if args.json:
        _imprimir_json(resultado)
        return 0
    print(f"Enviado pelo WhatsApp ({resultado.get('caracteres', 0)} caracteres).")
    return 0


MODELOS = {
    "pedidos": (
        "pedido;status;data_pedido;data_entrega;sku;produto;quantidade;preco_unitario;"
        "desconto;frete_cobrado;frete_pago;comissao;taxa_servico;cupom;imposto;repasse",
        "SP0001;Entregue;05/08/2026;09/08/2026;ORG-001;Organizador de gaveta;1;39,90;0;0;18,90;5,59;0,80;0;0;13,61",
    ),
    "custos": (
        "sku;produto;custo;preco_venda;categoria",
        "ORG-001;Organizador de gaveta;12,50;39,90;casa",
    ),
    "contas": (
        "tipo;descricao;categoria;valor;vencimento;pago_em;marketplace;recorrente;observacao",
        "pagar;Shopee Ads;marketing;900,00;15/08/2026;15/08/2026;shopee;sim;",
    ),
    "repasses": ("data;valor;referencia;pedido", "05/08/2026;1234,56;REP-001;"),
    "estoque": ("sku;quantidade;atualizado_em", "ORG-001;40;25/10/2026"),
}


def cmd_modelo(args: argparse.Namespace, servico: Servico) -> int:
    if args.tipo not in MODELOS:
        print(f"Tipo desconhecido. Use: {', '.join(MODELOS)}", file=sys.stderr)
        return 1
    cabecalho, exemplo = MODELOS[args.tipo]
    if args.salvar:
        destino = servico.config.entradas / f"modelo_{args.tipo}.csv"
        destino.write_text(cabecalho + "\n" + exemplo + "\n", encoding="utf-8-sig")
        print(f"Modelo salvo em {destino}")
    else:
        print(cabecalho)
        print(exemplo)
    return 0


# ── parser ──────────────────────────────────────────────────────────────────


def _adicionar_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="saida em JSON")


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mkt",
        description="Agente de gestao de contas em marketplaces (Shopee/TikTok Shop).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  mkt init\n"
            "  mkt demo\n"
            "  mkt importar pedidos exemplos/pedidos_shopee.csv --marketplace shopee\n"
            "  mkt importar contas entradas/contas_novembro.csv --dry-run\n"
            "  mkt dre --mes 2026-10\n"
            "  mkt margem --dias 90 --limite 10\n"
            "  mkt caixa --dias 30\n"
            "  mkt alertas\n"
        ),
    )
    parser.add_argument("--version", action="version", version=f"mktagent {__version__}")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("init", help="cria o banco e as pastas")
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_init)

    p = sub.add_parser("demo", help="carrega os dados de exemplo")
    p.add_argument("--limpar", action="store_true", help="apaga os dados antes de carregar")
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_demo)

    p = sub.add_parser("limpar", help="apaga os dados operacionais (banco vazio)")
    p.add_argument("--confirmar", action="store_true", help="confirma a exclusao")
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_limpar)

    p = sub.add_parser("importar", help="importa uma planilha")
    p.add_argument("tipo", choices=list(TIPOS_IMPORTACAO), help="tipo de dados")
    p.add_argument("arquivo", help="caminho do CSV/XLSX")
    p.add_argument("--marketplace", choices=["consolidado"] + list(MARKETPLACES), default=None)
    p.add_argument("--conta", default="principal", help="apelido da loja")
    p.add_argument("--dry-run", action="store_true", help="simula sem gravar")
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_importar)

    p = sub.add_parser("importar-pasta", help="importa tudo que estiver em entradas/")
    p.add_argument("--tipo", choices=list(TIPOS_IMPORTACAO), default=None)
    p.add_argument("--marketplace", choices=list(MARKETPLACES), default=None)
    p.add_argument("--dry-run", action="store_true")
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_importar_pasta)

    p = sub.add_parser("dre", help="DRE do mes")
    p.add_argument("--mes", default=None, help="AAAA-MM (padrao: ultimo mes com pedidos)")
    p.add_argument("--marketplace", choices=list(MARKETPLACES), default=None)
    p.add_argument("--por-marketplace", action="store_true", help="detalha cada marketplace")
    p.add_argument("--saida", default=None, help="exporta o DRE para um CSV")
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_dre)

    p = sub.add_parser("comparativo", help="mes atual vs anterior")
    p.add_argument("--mes", default=None)
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_comparativo)

    p = sub.add_parser("margem", help="margem por SKU e curva ABC")
    p.add_argument("--mes", default=None)
    p.add_argument("--dias", type=int, default=None, help="janela em dias (ex.: 90)")
    p.add_argument("--limite", type=int, default=None)
    p.add_argument("--marketplace", choices=list(MARKETPLACES), default=None)
    p.add_argument("--margem-alvo", type=float, default=0.20, help="ex.: 0.20 = 20%%")
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_margem)

    p = sub.add_parser("caixa", help="fluxo de caixa projetado")
    p.add_argument("--dias", type=int, default=30)
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_caixa)

    p = sub.add_parser("alertas", help="o que precisa de atencao")
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_alertas)

    p = sub.add_parser("estoque", help="cobertura de estoque")
    p.add_argument("--dias", type=int, default=30)
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_estoque)

    p = sub.add_parser("contas", help="lista contas a pagar/receber")
    p.add_argument("--status", choices=["aberta", "vencida", "paga"], default=None)
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_contas)

    p = sub.add_parser("conta", help="cria conta (conta criar) ou baixa (conta pagar)")
    sub_conta = p.add_subparsers(dest="acao", required=True)
    criar = sub_conta.add_parser("criar")
    criar.add_argument("--tipo", choices=["pagar", "receber"], default="pagar")
    criar.add_argument("--descricao", required=True)
    criar.add_argument("--valor", required=True)
    criar.add_argument("--vencimento", required=True)
    criar.add_argument("--categoria", default="outros")
    criar.add_argument("--marketplace", choices=list(MARKETPLACES), default=None)
    criar.add_argument("--observacao", default=None)
    _adicionar_json(criar)
    criar.set_defaults(funcao=cmd_conta_criar)
    pagar = sub_conta.add_parser("pagar")
    pagar.add_argument("id", type=int)
    pagar.add_argument("--data", default=None, help="data do pagamento (padrao: hoje)")
    _adicionar_json(pagar)
    pagar.set_defaults(funcao=cmd_conta_pagar)

    p = sub.add_parser("insights", help="analise da loja com acoes priorizadas")
    p.add_argument("--mes", default=None)
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_insights)

    p = sub.add_parser("criativo", help="gera arte de anuncio (PNG/SVG) para um SKU")
    p.add_argument("sku")
    p.add_argument("--beneficio", action="append", default=None, help="repita ate 4 vezes")
    p.add_argument("--formato", choices=["quadrado", "vertical"], default="quadrado")
    p.add_argument("--tema", choices=["claro", "escuro"], default="claro")
    p.add_argument("--preco", default=None)
    p.add_argument("--titulo", default=None)
    p.add_argument("--selo", default=None)
    p.add_argument("--foto", default=None, help="caminho de uma foto real do produto")
    p.add_argument("--modelo", choices=["card", "limpo"], default="card",
                   help="card = promocional com preco; limpo = foto estilo anuncio")
    p.add_argument("--logo", default=None, help="caminho da logo (para modelo limpo)")
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_criativo)

    p = sub.add_parser("briefing", help="briefing de imagens com prompts para IA")
    p.add_argument("sku")
    p.add_argument("--beneficio", action="append", default=None)
    p.add_argument("--publico", default=None)
    p.add_argument("--tom", default="clean e confiavel")
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_briefing)

    p = sub.add_parser("upseller", help="integracao com o UpSeller (ERP)")
    sub_upseller = p.add_subparsers(dest="acao", required=True)
    status_upseller = sub_upseller.add_parser("status")
    _adicionar_json(status_upseller)
    status_upseller.set_defaults(funcao=cmd_upseller)
    sincronizar = sub_upseller.add_parser("sincronizar-estoque")
    _adicionar_json(sincronizar)
    sincronizar.set_defaults(funcao=cmd_upseller)

    p = sub.add_parser("desempenho", help="desempenho diario (export Performance das Vendas)")
    p.add_argument("--dias", type=int, default=30)
    p.add_argument("--canal", choices=["consolidado"] + list(MARKETPLACES), default=None)
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_desempenho)

    p = sub.add_parser("precificar", help="calculadora de custo/preco de impressao 3D")
    p.add_argument("--peso", required=True, help="peso em gramas (total)")
    p.add_argument("--custo-kg", required=True, help="custo do filamento por kg")
    p.add_argument("--horas", default=0, help="horas de impressao")
    p.add_argument("--maquina-hora", default=0, help="custo por hora de maquina")
    p.add_argument("--falha", default=0.05, help="taxa de falha (0.05 ou 5)")
    p.add_argument("--acabamento", default=0)
    p.add_argument("--embalagem", default=0)
    p.add_argument("--mao-de-obra", default=0)
    p.add_argument("--canal", choices=list(MARKETPLACES), default="shopee")
    p.add_argument("--taxa-canal", default=None)
    p.add_argument("--taxa-fixa", default=0)
    p.add_argument("--frete", default=0, help="frete pago pelo vendedor")
    p.add_argument("--margem-alvo", default=0.30)
    p.add_argument("--preco", default=None, help="preco praticado para comparar")
    p.add_argument("--unidades", type=int, default=1)
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_precificar)

    p = sub.add_parser("telegram", help="notificacoes no Telegram")
    sub_tg = p.add_subparsers(dest="acao", required=True)
    for acao in ("status", "testar", "digest"):
        sp = sub_tg.add_parser(acao)
        _adicionar_json(sp)
        sp.set_defaults(funcao=cmd_telegram)

    p = sub.add_parser("whatsapp", help="notificacoes no WhatsApp Cloud API")
    sub_wa = p.add_subparsers(dest="acao", required=True)
    for acao in ("status", "testar", "digest"):
        sp = sub_wa.add_parser(acao)
        _adicionar_json(sp)
        sp.set_defaults(funcao=cmd_whatsapp)

    p = sub.add_parser("produtos", help="lista produtos e custos")
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_produtos)

    p = sub.add_parser("custo", help="registra o custo de um SKU")
    p.add_argument("sku")
    p.add_argument("valor")
    p.add_argument("--preco", default=None, help="preco de venda")
    p.add_argument("--nome", default=None)
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_custo)

    p = sub.add_parser("pedido", help="pedido manual (B2B/consignacao): criar ou mudar status")
    sub_pedido = p.add_subparsers(dest="acao", required=True)
    criar_pedido = sub_pedido.add_parser("criar")
    criar_pedido.add_argument("--canal", choices=list(MARKETPLACES), default="consignacao")
    criar_pedido.add_argument("--cliente", default=None)
    criar_pedido.add_argument("--data", default=None)
    criar_pedido.add_argument("--item", action="append", required=True,
                              help="SKU:QUANTIDADE:PRECO (repita por item)")
    criar_pedido.add_argument("--status", default="Pendente")
    criar_pedido.add_argument("--pedido", default=None, help="numero do pedido (opcional)")
    _adicionar_json(criar_pedido)
    criar_pedido.set_defaults(funcao=cmd_pedido_criar)
    status_pedido = sub_pedido.add_parser("status")
    status_pedido.add_argument("pedido")
    status_pedido.add_argument("status")
    status_pedido.add_argument("--canal", choices=list(MARKETPLACES), default=None)
    _adicionar_json(status_pedido)
    status_pedido.set_defaults(funcao=cmd_pedido_status)

    p = sub.add_parser("pedidos", help="lista pedidos")
    p.add_argument("--mes", default=None)
    p.add_argument("--marketplace", choices=list(MARKETPLACES), default=None)
    p.add_argument("--situacao", choices=["aprovado", "cancelado", "devolvido", "pendente", "desconhecido"], default=None)
    p.add_argument("--limite", type=int, default=20)
    p.add_argument("--cliente", default=None)
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_pedidos)

    p = sub.add_parser("resumo", help="panorama rapido da operacao")
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_resumo)

    p = sub.add_parser("status", help="situacao das integracoes e credenciais")
    _adicionar_json(p)
    p.set_defaults(funcao=cmd_status)

    p = sub.add_parser("modelo", help="mostra um modelo de planilha para importar")
    p.add_argument("tipo", choices=list(MODELOS))
    p.add_argument("--salvar", action="store_true", help="salva em entradas/")
    p.set_defaults(funcao=cmd_modelo)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    servico = Servico()
    try:
        return int(args.funcao(args, servico) or 0)
    except (ValueError, FileNotFoundError, IsADirectoryError) as erro:
        if getattr(args, "json", False):
            _imprimir_json({"erro": str(erro)})
        else:
            print(_cor(f"Erro: {erro}", VERMELHO), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelado.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
