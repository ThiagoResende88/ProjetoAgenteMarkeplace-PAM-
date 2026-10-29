"""Servidor MCP (Model Context Protocol) do mktagent sobre stdio.

Expõe as ferramentas que o agente usa no DSH. Protocolo JSON-RPC 2.0, uma
mensagem JSON por linha. Implementacao sem dependencias: apenas stdlib.

Nunca escreva em stdout fora do protocolo (mensagens de log vao para stderr).
"""

from __future__ import annotations

import json
import sys
from typing import Any

from . import __version__
from .config import MARKETPLACES
from .servico import Servico, _tipo_por_nome

NOME_SERVIDOR = "marketplaces"

INSTRUCOES = """\
Servidor de gestao de contas em marketplaces (Shopee e TikTok Shop).

Regras de uso:
- NUNCA invente numeros. Todo valor financeiro vem de uma ferramenta deste servidor.
- Antes de responder sobre receita, lucro, margem, repasses ou contas, chame a ferramenta
  correspondente (resumo, dre, margem_sku, fluxo_caixa, alertas).
- Valores monetarios podem ser enviados como texto brasileiro ("1.234,56" ou "R$ 12,90").
- Escritas (criar_conta, marcar_conta_paga, registrar_custo, importar_arquivo) alteram dados
  reais: confirme com o usuario antes, exceto quando ele ja pediu explicitamente.
- Importacao: aceita CSV/XLSX exportados dos paineis. Use dry_run=true primeiro quando o
  arquivo for novo, para o usuario conferir o mapeamento de colunas.
- Se um dado nao existe, diga que falta importar/ cadastrar e explique como fazer.
- O modo atual e importacao de planilhas; a API oficial depende de credenciais (status_integracoes).
- Responda em portugues do Brasil, com numeros e proximos passos concretos.
"""


# ── definicao das ferramentas ───────────────────────────────────────────────


def _ferramenta(nome: str, descricao: str, propriedades: dict, obrigatorios: list[str]) -> dict:
    return {
        "name": nome,
        "description": descricao,
        "inputSchema": {
            "type": "object",
            "properties": propriedades,
            "required": obrigatorios,
            "additionalProperties": False,
        },
    }


FERRAMENTAS = [
    _ferramenta(
        "resumo",
        "Panorama da operacao: dados importados, DRE do ultimo mes, alertas e contas a vencer. "
        "Comece por aqui quando o usuario perguntar 'como estao as contas?'.",
        {},
        [],
    ),
    _ferramenta(
        "status_integracoes",
        "Mostra o que esta configurado (credenciais Shopee/TikTok), o modo atual (planilhas) "
        "e as ultimas importacoes.",
        {},
        [],
    ),
    _ferramenta(
        "dre",
        "DRE mensal: receita bruta, descontos, frete, comissoes, taxas, cupom, imposto, CMV, "
        "margem de contribuicao, despesas operacionais e lucro liquido. Tambem compara repasses.",
        {
            "mes": {"type": "string", "description": "AAAA-MM. Padrao: ultimo mes com pedidos."},
            "marketplace": {"type": "string", "enum": list(MARKETPLACES)},
        },
        [],
    ),
    _ferramenta(
        "comparativo",
        "Compara a receita e o lucro do mes com o mes anterior (variacao percentual).",
        {"mes": {"type": "string", "description": "AAAA-MM (padrao: ultimo mes com pedidos)"}},
        [],
    ),
    _ferramenta(
        "margem_sku",
        "Margem de contribuicao por SKU (taxas e frete rateados por item), curva ABC e preco "
        "sugerido para a margem alvo. Use dias=90 para uma janela movel.",
        {
            "mes": {"type": "string", "description": "AAAA-MM (opcional se usar dias)"},
            "dias": {"type": "integer", "minimum": 1, "maximum": 730},
            "limite": {"type": "integer", "minimum": 1, "maximum": 200},
            "marketplace": {"type": "string", "enum": list(MARKETPLACES)},
            "margem_alvo": {
                "type": "number",
                "description": "Fracao alvo, ex.: 0.2 = 20% (padrao 0.2)",
            },
        },
        [],
    ),
    _ferramenta(
        "fluxo_caixa",
        "Projecao de entradas/saidas por semana a partir das contas cadastradas, mais o que "
        "esta vencido em aberto.",
        {"dias": {"type": "integer", "minimum": 1, "maximum": 365}},
        [],
    ),
    _ferramenta(
        "alertas",
        "Alertas acionaveis: contas vencidas, SKU sem custo, margem negativa, cancelamentos, "
        "queda de receita, estoque critico e conciliacao de repasses.",
        {},
        [],
    ),
    _ferramenta(
        "estoque",
        "Cobertura de estoque: dias de estoque por SKU com base na media de vendas do periodo.",
        {"dias": {"type": "integer", "minimum": 1, "maximum": 365}},
        [],
    ),
    _ferramenta(
        "listar_contas",
        "Lista contas a pagar/receber com vencimento, status e totais.",
        {"status": {"type": "string", "enum": ["aberta", "vencida", "paga"]}},
        [],
    ),
    _ferramenta(
        "criar_conta",
        "Cadastra uma conta a pagar ou a receber. Aceita valor como '1.234,56' e vencimento "
        "como '05/11/2026' ou '2026-11-05'. Confirme com o usuario antes.",
        {
            "tipo": {"type": "string", "enum": ["pagar", "receber"]},
            "descricao": {"type": "string"},
            "valor": {"type": "string", "description": "Ex.: '1.234,56' ou 'R$ 12,90'"},
            "vencimento": {"type": "string", "description": "DD/MM/AAAA ou AAAA-MM-DD"},
            "categoria": {
                "type": "string",
                "description": "marketing, fornecedor, insumo, frete, imposto, pessoal, software, "
                "estrutura, contabilidade ou outros",
            },
            "marketplace": {"type": "string", "enum": list(MARKETPLACES)},
            "observacao": {"type": "string"},
        },
        ["tipo", "descricao", "valor", "vencimento"],
    ),
    _ferramenta(
        "marcar_conta_paga",
        "Marca uma conta como paga (baixa). Use listar_contas para descobrir o id.",
        {
            "id": {"type": "integer", "minimum": 1},
            "pago_em": {"type": "string", "description": "Data do pagamento (padrao: hoje)"},
        },
        ["id"],
    ),
    _ferramenta(
        "listar_produtos",
        "Lista SKUs com custo, preco de venda e estoque atual. Mostra quais estao sem custo.",
        {},
        [],
    ),
    _ferramenta(
        "registrar_custo",
        "Cadastra/atualiza o custo unitario de um SKU (e opcionalmente o preco de venda). "
        "Isso torna a margem confiavel.",
        {
            "sku": {"type": "string"},
            "custo": {"type": "string", "description": "Ex.: '12,50'"},
            "preco_venda": {"type": "string", "description": "Opcional, ex.: '39,90'"},
            "nome": {"type": "string"},
        },
        ["sku", "custo"],
    ),
    _ferramenta(
        "listar_pedidos",
        "Lista pedidos com situacao financeira (aprovado/cancelado/devolvido/pendente), "
        "totais e itens.",
        {
            "mes": {"type": "string", "description": "AAAA-MM"},
            "marketplace": {"type": "string", "enum": list(MARKETPLACES)},
            "situacao": {
                "type": "string",
                "enum": ["aprovado", "cancelado", "devolvido", "pendente", "desconhecido"],
            },
            "cliente": {"type": "string"},
            "limite": {"type": "integer", "minimum": 1, "maximum": 200},
        },
        [],
    ),
    _ferramenta(
        "importar_arquivo",
        "Importa uma planilha CSV/XLSX (pedidos, contas, custos, repasses ou estoque). "
        "Use dry_run=true primeiro para conferir o mapeamento das colunas. "
        "Coloque arquivos em entradas/ ou passe o caminho completo.",
        {
            "caminho": {"type": "string", "description": "Nome do arquivo ou caminho completo"},
            "tipo": {
                "type": "string",
                "enum": ["pedidos", "contas", "custos", "repasses", "estoque"],
                "description": "Se omitido, tenta inferir pelo nome do arquivo",
            },
            "marketplace": {"type": "string", "enum": list(MARKETPLACES)},
            "conta": {"type": "string", "description": "Apelido da loja (padrao: principal)"},
            "dry_run": {"type": "boolean", "description": "Simula sem gravar"},
        },
        ["caminho"],
    ),
    _ferramenta(
        "importar_pasta",
        "Importa todos os CSV/XLSX presentes na pasta entradas/.",
        {
            "tipo": {"type": "string", "enum": ["pedidos", "contas", "custos", "repasses", "estoque"]},
            "marketplace": {"type": "string", "enum": list(MARKETPLACES)},
            "dry_run": {"type": "boolean"},
        },
        [],
    ),
    _ferramenta(
        "sincronizar",
        "Tenta sincronizar pedidos pela API oficial. Hoje responde que a API nao esta "
        "configurada e explica os passos (o modo planilha e o caminho ativo).",
        {
            "marketplace": {"type": "string", "enum": list(MARKETPLACES)},
            "desde": {"type": "string", "description": "AAAA-MM-DD"},
            "ate": {"type": "string", "description": "AAAA-MM-DD"},
        },
        ["marketplace"],
    ),
    _ferramenta(
        "insights",
        "Analise da loja com interpretacao: variacao de receita, concentracao de SKUs, matriz "
        "margem x volume, marketing, cancelamentos e acoes priorizadas. Use quando o usuario "
        "pedir 'o que os dados dizem?', 'onde melhorar?', 'me da insights'.",
        {"mes": {"type": "string", "description": "AAAA-MM (padrao: ultimo mes com pedidos)"}},
        [],
    ),
    _ferramenta(
        "gerar_criativo",
        "Gera a arte de um anuncio (card 1080x1080 ou 1080x1350) em PNG e SVG com nome, "
        "beneficios e preco do SKU. Salva em saidas/criativos/. Use quando o usuario pedir "
        "imagem/arte/criativo do anuncio.",
        {
            "sku": {"type": "string"},
            "beneficios": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ate 4 beneficios curtos (ex.: 'Material resistente')",
            },
            "formato": {"type": "string", "enum": ["quadrado", "vertical"]},
            "tema": {"type": "string", "enum": ["claro", "escuro"]},
            "preco": {"type": "string", "description": "Opcional (padrao: preco de venda do SKU)"},
            "titulo": {"type": "string", "description": "Opcional: texto principal diferente do nome"},
            "selo": {"type": "string", "description": "Opcional: selo curto (ex.: 'FRETE GRATIS')"},
            "foto": {"type": "string", "description": "Foto real do produto (obrigatoria no modelo limpo)"},
            "modelo": {
                "type": "string",
                "enum": ["card", "limpo"],
                "description": "card = promocional com preco; limpo = foto estilo anuncio (sem texto de preco)",
            },
            "logo": {"type": "string", "description": "Opcional: caminho da logo da marca"},
        },
        ["sku"],
    ),
    _ferramenta(
        "briefing_imagens",
        "Cria um briefing de imagens do produto: 6 prompts prontos para IA (Midjourney/DALL-E/"
        "Canva/Firefly), prompt negativo, checklist de publicacao e arquivo .md em saidas/briefings/. "
        "Use quando o usuario pedir fotos/imagens do anuncio.",
        {
            "sku": {"type": "string"},
            "beneficios": {"type": "array", "items": {"type": "string"}},
            "publico": {"type": "string", "description": "Ex.: 'maes que organizam a casa'"},
            "tom": {"type": "string", "description": "Ex.: 'clean e confiavel'"},
        },
        ["sku"],
    ),
    _ferramenta(
        "criar_pedido",
        "Cria um pedido manual (B2B, consignacao, venda direta): cliente, itens, preco "
        "e status. Substitui planilha de controle. Ex.: BARBEARIA pediu 10 tubetes.",
        {
            "canal": {"type": "string", "enum": list(MARKETPLACES), "description": "Padrao: consignacao"},
            "cliente": {"type": "string"},
            "data": {"type": "string", "description": "DD/MM/AAAA ou AAAA-MM-DD (padrao: hoje)"},
            "itens": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "sku": {"type": "string"},
                        "quantidade": {"type": "integer", "minimum": 1},
                        "preco_unitario": {"type": "string"},
                    },
                    "required": ["sku", "quantidade", "preco_unitario"],
                },
            },
            "status": {"type": "string", "description": "Pendente, Pago, Faturado, Entregue, Cancelado"},
            "pedido_externo": {"type": "string", "description": "Opcional; padrao MOC-0001"},
        },
        ["itens"],
    ),
    _ferramenta(
        "atualizar_status_pedido",
        "Atualiza o status de um pedido (ex.: Pendente -> Pago) e recalcula a situacao financeira.",
        {
            "pedido_externo": {"type": "string"},
            "status": {"type": "string"},
            "canal": {"type": "string", "enum": list(MARKETPLACES)},
        },
        ["pedido_externo", "status"],
    ),
    _ferramenta(
        "desempenho",
        "Desempenho diario de vendas (export 'Performance das Vendas'): periodo, ticket, "
        "cancelamento, semanas, dias da semana mais fortes, tendencia e projecao de 30 dias. "
        "Use quando o usuario perguntar 'como estao as vendas?', 'qual o melhor dia?'.",
        {
            "canal": {"type": "string", "enum": list(MARKETPLACES) + ["consolidado"]},
            "dias": {"type": "integer", "minimum": 7, "maximum": 365},
        },
        [],
    ),
    _ferramenta(
        "precificar_3d",
        "Calculadora de custo e preco para peca de impressao 3D (ou kit): filamento, maquina, "
        "falha, acabamento, embalagem, mao de obra, taxas do canal e frete. Devolve custo, "
        "preco de empate, preco para a margem alvo e cenarios. Use para Mocozim, cubos, "
        "chaveiros, trofeus etc.",
        {
            "peso_g": {"type": "string", "description": "Peso total em gramas (ex.: '10' ou '10,5')"},
            "custo_filamento_kg": {"type": "string", "description": "R$/kg do filamento (ex.: '120')"},
            "horas_impressao": {"type": "string", "description": "Horas de impressao (ex.: '0.83')"},
            "custo_maquina_hora": {"type": "string", "description": "R$/hora (energia+desgaste+manutencao)"},
            "taxa_falha_pct": {"type": "string", "description": "Fracao ou % (padrao 0.05 = 5%)"},
            "acabamento": {"type": "string", "description": "R$ de acabamento/lixa/pintura"},
            "embalagem": {"type": "string", "description": "R$ de embalagem por unidade"},
            "mao_de_obra": {"type": "string", "description": "R$ de mao de obra por unidade"},
            "canal": {"type": "string", "enum": list(MARKETPLACES)},
            "taxa_canal_pct": {"type": "string", "description": "Opcional: sobrescreve a taxa do canal"},
            "taxa_fixa_por_item": {"type": "string", "description": "R$ de taxa fixa por item"},
            "frete_pago_pelo_vendedor": {"type": "string", "description": "R$ de frete subsidiado"},
            "margem_alvo_pct": {"type": "string", "description": "Fracao ou % (padrao 0.30)"},
            "preco_venda": {"type": "string", "description": "Opcional: preco praticado para comparar"},
            "unidades": {"type": "integer", "minimum": 1, "description": "Unidades no kit (padrao 1)"},
        },
        ["peso_g", "custo_filamento_kg"],
    ),
    _ferramenta(
        "status_notificacoes",
        "Mostra se Telegram/WhatsApp estao configurados e como configurar.",
        {},
        [],
    ),
    _ferramenta(
        "enviar_telegram",
        "Envia mensagem ou resumo do dia no Telegram do usuario (se configurado).",
        {
            "texto": {"type": "string", "description": "Opcional; sem texto envia o resumo do dia"},
            "tipo": {"type": "string", "enum": ["texto", "digest"]},
        },
        [],
    ),
    _ferramenta(
        "upseller_status",
        "Status da integracao com o UpSeller (ERP): credenciais, o que da para sincronizar "
        "e quais passos faltam.",
        {},
        [],
    ),
    _ferramenta(
        "upseller_sincronizar_estoque",
        "Sincroniza a posicao de estoque direto do UpSeller (API aberta) para a base local.",
        {},
        [],
    ),
]


# ── servidor ────────────────────────────────────────────────────────────────


class ServidorMCP:
    def __init__(self, servico: Servico | None = None):
        self.servico = servico or Servico()

    # protocolo ------------------------------------------------------------

    def tratar(self, mensagem: dict) -> dict | None:
        if not isinstance(mensagem, dict):
            return _erro(None, -32600, "mensagem invalida")
        metodo = mensagem.get("method")
        identificador = mensagem.get("id")
        eh_notificacao = "id" not in mensagem

        if eh_notificacao:
            if metodo in {"notifications/initialized", "initialized"}:
                return None
            if metodo == "exit":
                raise SystemExit(0)
            return None

        try:
            if metodo == "initialize":
                return _ok(identificador, self._inicializar(mensagem.get("params") or {}))
            if metodo == "ping":
                return _ok(identificador, {})
            if metodo == "tools/list":
                return _ok(identificador, {"tools": FERRAMENTAS})
            if metodo == "tools/call":
                return _ok(identificador, self._chamar_ferramenta(mensagem.get("params") or {}))
            if metodo in {"resources/list", "prompts/list"}:
                return _ok(identificador, {metodo.split("/")[0]: []})
            if metodo in {"logging/setLevel"}:
                return _ok(identificador, {})
            return _erro(identificador, -32601, f"metodo nao suportado: {metodo}")
        except SystemExit:
            raise
        except Exception as erro:  # nunca derrubar o servidor por um erro de ferramenta
            _log(f"erro no metodo {metodo}: {erro!r}")
            return _erro(identificador, -32603, f"erro interno: {erro}")

    def _inicializar(self, params: dict) -> dict:
        versao = str(params.get("protocolVersion") or "2025-06-18")
        if not _versao_valida(versao):
            versao = "2025-06-18"
        return {
            "protocolVersion": versao,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": NOME_SERVIDOR, "version": __version__},
            "instructions": INSTRUCOES,
        }

    def _chamar_ferramenta(self, params: dict) -> dict:
        nome = params.get("name")
        argumentos = params.get("arguments") or {}
        if not nome:
            return _resultado_ferramenta("Erro: nome da ferramenta ausente", erro=True)
        if not isinstance(argumentos, dict):
            return _resultado_ferramenta("Erro: arguments deve ser um objeto", erro=True)
        metodo = getattr(self, f"tool_{nome}", None)
        if metodo is None:
            return _resultado_ferramenta(f"Erro: ferramenta desconhecida: {nome}", erro=True)
        try:
            valor = metodo(argumentos)
        except (ValueError, FileNotFoundError) as erro:
            return _resultado_ferramenta(f"Erro: {erro}", erro=True)
        except Exception as erro:  # pragma: no cover - diagnostico
            _log(f"falha na ferramenta {nome}: {erro!r}")
            return _resultado_ferramenta(f"Erro interno na ferramenta {nome}: {erro}", erro=True)
        return _resultado_ferramenta(_serializar(valor))

    # ferramentas ----------------------------------------------------------

    def tool_resumo(self, args: dict) -> dict:
        return self.servico.resumo()

    def tool_status_integracoes(self, args: dict) -> dict:
        return self.servico.status_integracoes()

    def tool_dre(self, args: dict) -> dict:
        return self.servico.dre(_texto(args, "mes"), _opcao(args, "marketplace"))

    def tool_comparativo(self, args: dict) -> dict:
        return self.servico.comparativo(_texto(args, "mes"))

    def tool_margem_sku(self, args: dict) -> dict:
        return self.servico.margem(
            mes=_texto(args, "mes"),
            dias=_inteiro(args, "dias"),
            limite=_inteiro(args, "limite"),
            marketplace=_opcao(args, "marketplace"),
            margem_alvo=float(args.get("margem_alvo") or 0.20),
        )

    def tool_fluxo_caixa(self, args: dict) -> dict:
        return self.servico.caixa(_inteiro(args, "dias") or 30)

    def tool_alertas(self, args: dict) -> dict:
        return self.servico.alertas()

    def tool_estoque(self, args: dict) -> dict:
        return self.servico.estoque(_inteiro(args, "dias") or 30)

    def tool_listar_contas(self, args: dict) -> dict:
        return self.servico.contas(_opcao(args, "status"))

    def tool_criar_conta(self, args: dict) -> dict:
        return self.servico.criar_conta(
            tipo=_texto(args, "tipo") or "pagar",
            descricao=_texto(args, "descricao") or "",
            valor=args.get("valor"),
            vencimento=args.get("vencimento"),
            categoria=_texto(args, "categoria") or "outros",
            marketplace=_opcao(args, "marketplace"),
            observacao=_texto(args, "observacao"),
        )

    def tool_marcar_conta_paga(self, args: dict) -> dict:
        identificador = _inteiro(args, "id")
        if not identificador:
            raise ValueError("id obrigatorio")
        return self.servico.marcar_paga(identificador, pago_em=_texto(args, "pago_em"))

    def tool_listar_produtos(self, args: dict) -> dict:
        return self.servico.produtos()

    def tool_registrar_custo(self, args: dict) -> dict:
        return self.servico.registrar_custo(
            sku=_texto(args, "sku") or "",
            custo=args.get("custo"),
            preco_venda=args.get("preco_venda"),
            nome=_texto(args, "nome"),
        )

    def tool_listar_pedidos(self, args: dict) -> dict:
        return self.servico.pedidos(
            mes=_texto(args, "mes"),
            marketplace=_opcao(args, "marketplace"),
            situacao=_opcao(args, "situacao"),
            limite=_inteiro(args, "limite") or 30,
            cliente=_texto(args, "cliente"),
        )

    def tool_importar_arquivo(self, args: dict) -> dict:
        caminho = _texto(args, "caminho")
        if not caminho:
            raise ValueError("caminho obrigatorio")
        tipo = _opcao(args, "tipo")
        if tipo is None:
            tipo = _tipo_por_nome(str(caminho))
        if tipo is None:
            raise ValueError(
                "nao consegui inferir o tipo pelo nome do arquivo; informe tipo="
                "pedidos|contas|custos|repasses|estoque"
            )
        return self.servico.importar(
            tipo,
            caminho,
            marketplace=_opcao(args, "marketplace"),
            conta=_texto(args, "conta") or "principal",
            dry_run=bool(args.get("dry_run")),
        )

    def tool_importar_pasta(self, args: dict) -> dict:
        return self.servico.importar_pasta(
            tipo=_opcao(args, "tipo"),
            marketplace=_opcao(args, "marketplace"),
            dry_run=bool(args.get("dry_run")),
        )

    def tool_sincronizar(self, args: dict) -> dict:
        from .api import sincronizar

        return sincronizar(
            _opcao(args, "marketplace") or "shopee",
            desde=_texto(args, "desde"),
            ate=_texto(args, "ate"),
            config=self.servico.config,
        )

    def tool_insights(self, args: dict) -> dict:
        return self.servico.insights(mes=_texto(args, "mes"))

    def tool_gerar_criativo(self, args: dict) -> dict:
        return self.servico.gerar_criativo(
            sku=_texto(args, "sku") or "",
            beneficios=args.get("beneficios") or None,
            formato=_texto(args, "formato") or "quadrado",
            tema=_texto(args, "tema") or "claro",
            preco=args.get("preco"),
            titulo=_texto(args, "titulo"),
            selo=_texto(args, "selo"),
            foto=_texto(args, "foto"),
            modelo=_texto(args, "modelo") or "card",
            logo=_texto(args, "logo"),
        )

    def tool_briefing_imagens(self, args: dict) -> dict:
        return self.servico.briefing_imagens(
            sku=_texto(args, "sku") or "",
            beneficios=args.get("beneficios") or None,
            publico=_texto(args, "publico"),
            tom=_texto(args, "tom") or "clean e confiavel",
        )

    def tool_criar_pedido(self, args: dict) -> dict:
        return self.servico.criar_pedido(
            canal=_opcao(args, "canal") or "consignacao",
            cliente=_texto(args, "cliente"),
            data=args.get("data"),
            itens=args.get("itens") or [],
            status=_texto(args, "status") or "Pendente",
            pedido_externo=_texto(args, "pedido_externo"),
        )

    def tool_atualizar_status_pedido(self, args: dict) -> dict:
        return self.servico.atualizar_status_pedido(
            pedido_externo=_texto(args, "pedido_externo") or "",
            status=_texto(args, "status") or "",
            canal=_opcao(args, "canal"),
        )

    def tool_desempenho(self, args: dict) -> dict:
        return self.servico.desempenho(canal=_opcao(args, "canal"), dias=_inteiro(args, "dias") or 30)

    def tool_precificar_3d(self, args: dict) -> dict:
        return self.servico.precificar_3d(
            peso_g=args.get("peso_g"),
            custo_filamento_kg=args.get("custo_filamento_kg"),
            horas_impressao=args.get("horas_impressao"),
            custo_maquina_hora=args.get("custo_maquina_hora"),
            taxa_falha_pct=args.get("taxa_falha_pct", 0.05),
            acabamento=args.get("acabamento", 0),
            embalagem=args.get("embalagem", 0),
            mao_de_obra=args.get("mao_de_obra", 0),
            canal=_opcao(args, "canal") or "shopee",
            taxa_canal_pct=args.get("taxa_canal_pct"),
            taxa_fixa_por_item=args.get("taxa_fixa_por_item", 0),
            frete_pago_pelo_vendedor=args.get("frete_pago_pelo_vendedor", 0),
            margem_alvo_pct=args.get("margem_alvo_pct", 0.30),
            preco_venda=args.get("preco_venda"),
            unidades=_inteiro(args, "unidades") or 1,
        )

    def tool_status_notificacoes(self, args: dict) -> dict:
        return self.servico.notificacoes_status()

    def tool_enviar_telegram(self, args: dict) -> dict:
        return self.servico.enviar_telegram(
            texto=_texto(args, "texto"), tipo=_opcao(args, "tipo") or "texto"
        )

    def tool_upseller_status(self, args: dict) -> dict:
        return self.servico.upseller_status()

    def tool_upseller_sincronizar_estoque(self, args: dict) -> dict:
        return self.servico.upseller_sincronizar_estoque()


# ── utilitarios de JSON-RPC ─────────────────────────────────────────────────


def _ok(identificador: Any, resultado: Any) -> dict:
    return {"jsonrpc": "2.0", "id": identificador, "result": resultado}


def _erro(identificador: Any, codigo: int, mensagem: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": identificador,
        "error": {"code": codigo, "message": mensagem},
    }


def _resultado_ferramenta(texto: str, erro: bool = False) -> dict:
    return {"content": [{"type": "text", "text": texto}], "isError": erro}


def _serializar(valor: Any) -> str:
    texto = json.dumps(valor, ensure_ascii=False, indent=2, default=str)
    limite = 80_000
    if len(texto) > limite:
        texto = texto[:limite] + "\n... (saida truncada)"
    return texto


def _versao_valida(versao: str) -> bool:
    partes = versao.split("-")
    return len(partes) == 3 and all(p.isdigit() for p in partes)


def _log(texto: str) -> None:
    print(f"[mkt-mcp] {texto}", file=sys.stderr, flush=True)


def _texto(args: dict, chave: str) -> str | None:
    valor = args.get(chave)
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _opcao(args: dict, chave: str) -> str | None:
    valor = _texto(args, chave)
    return valor.lower() if valor else None


def _inteiro(args: dict, chave: str) -> int | None:
    valor = args.get(chave)
    if valor is None or valor == "":
        return None
    return int(valor)


# ── loop principal ──────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if "--listar-ferramentas" in argv:
        print(_serializar({"servidor": NOME_SERVIDOR, "ferramentas": FERRAMENTAS}))
        return 0

    servidor = ServidorMCP()
    _log(f"servidor {NOME_SERVIDOR} v{__version__} pronto (stdio)")

    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        try:
            mensagem = json.loads(linha)
        except json.JSONDecodeError:
            _log("linha ignorada: JSON invalido")
            continue

        mensagens = mensagem if isinstance(mensagem, list) else [mensagem]
        resposta: list[dict] = []
        for item in mensagens:
            try:
                resultado = servidor.tratar(item)
            except SystemExit:
                return 0
            if resultado is not None:
                resposta.append(resultado)
        if resposta:
            saida = resposta[0] if len(resposta) == 1 else resposta
            sys.stdout.write(json.dumps(saida, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
