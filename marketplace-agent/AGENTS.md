# Instrucoes para agentes de codigo que trabalharem neste projeto

Este e o `marketplace-agent`: agente local de gestao financeira e operacional de
contas em Shopee e TikTok Shop. Python 3.10+, **sem dependencias externas**
(sqlite3, csv, zipfile, hmac da stdlib). Nao adicione bibliotecas sem necessidade.

## Regras do projeto

- Dinheiro **sempre em centavos (int)** no banco e no meio do calculo; `Decimal`
  apenas na borda (parsing/formatacao). Nunca use `float` para somar dinheiro.
- Todo relatorio que o usuario ve deve sair de `Servico` (`src/mktagent/servico.py`).
  CLI e servidor MCP sao apenas bordas: nao duplique regra de negocio neles.
- Texto voltado ao usuario em **portugues do Brasil**; codigo em portugues simples
  (nomes como `pedidos`, `contas`, `margem`) — mantenha o padrao.
- O servidor MCP (`mcp_server.py`) escreve **apenas JSON-RPC em stdout**; logs vao
  para stderr.
- Importadores devem ser tolerantes (colunas em PT/EN, CSV/XLSX, encoding, datas
  BR/US) e **idempotentes** (reimportar nao duplica).
- Toda mudanca de comportamento precisa de teste em `tests/`.
- A integracao com as APIs oficiais e fase 2: nao afirme que sincroniza sem
  credenciais e sem teste contra o sandbox.
- `criativos.py` usa Pillow apenas para PNG (import local). Nunca torne Pillow
  dependencia obrigatoria: sem ele, o SVG deve continuar funcionando.
- Mês em andamento: comparativo de receita é MTD. Não comparar mês parcial com mês cheio.
- Canais: `config.MARKETPLACES` (inclui mercadolivre, instagram, consignacao, direto).
  Nao hardcode shopee/tiktok em novas telas; use a lista/normalizador.
- Precos: formule em `precificacao.py` (centavos, ROUND_HALF_UP) e nunca prometa margem
  sem a taxa real do canal.
- Custos do negocio (out/2026): filamento PETG R$ 64/kg (faixa 59-69), embalagem
  R$ 0,50/un, seda R$ 1,00/livreto, maquina estimada R$ 0,55/h. Tubete R$ 1,03/un;
  bico PU R$ 1,14/un (10 g / 47,5 min); banquinho com seda R$ 1,82.
  Shopee = 18% + R$ 4,00 + 2% por item; TikTok = 10% + 6% + R$ 4,00 por item
  (frete coberto no exemplo). Planilha:
  `saidas/custos/Custos_Mocozim_3DPrintFranca_2026-10.xlsx`.
- Export nativo Shopee: "Valor Total" inclui frete do comprador; usar "Subtotal do
  produto". O importador forca isso e ignora desconto/frete do export.
- Export TikTok "Todos pedido" veio achatado; converter com
  `scripts/converter_tiktok_flat.py` antes de importar. Se o export nao trouxer taxas,
  o importador estima 10% + 6% + R$ 4/item e avisa (conferir no Seller Center).
- Kit feminino: NAO usar marca/personagem de terceiro (Hello Kitty/Sanrio) em titulo,
  descricao, SKU, fotos ou nome de arquivo. Guia: `docs/KIT_FEMININO_SEGURO.md`.
- Negocio: 3D Print Franca + Mocozim; ver `docs/DADOS_NEGOCIO.md`. Nao afirmar
  originalidade/patente (EasyPU), nao usar marca de terceiros, vape tem restricao.
- Pedido manual (B2B/consignacao) usa `operacao/pedidos_manuais.py`; nao criar pedido
  direto no SQL em codigo novo.
- UpSeller: MCP/API oficial hoje cobre estoque/armazem; nao prometer sync de vendas.

## Comandos

```sh
python3 -m unittest discover -s tests -t .   # suite completa
python3 scripts/gerar_exemplos.py            # regenera examples/
./bin/mkt demo --limpar                      # carrega cenario ficticio
./bin/mkt resumo
python3 scripts/instalar_dsh.py --dry-run    # mostra o patch do DSH
```

## Estrutura

- `src/mktagent/ingestao/` — leitura CSV/XLSX e importadores
- `src/mktagent/financeiro/` — DRE, margem, caixa, alertas, insights
- `src/mktagent/operacao/` — pedidos (inclusive manuais/B2B), produtos, custos
- `src/mktagent/criativos.py` — arte PNG/SVG (Pillow opcional, inclui foto real) e briefing
- `src/mktagent/precificacao.py` — custo/preco de impressao 3D e taxas por canal
- `src/mktagent/notificacoes.py` — Telegram e WhatsApp Cloud (texto/digest)
- `src/mktagent/financeiro/desempenho.py` — tendencia diaria do marketplace
- `src/mktagent/api/` — OAuth/assinatura Shopee/TikTok e cliente UpSeller
- `dsh/` — patch do perfil DSH (MCP + preset); `skills/` — as 6 skills do agente
- `docs/` — arquitetura, UpSeller, credenciais, dados do negocio, plano Mocozim,
  estrategia EasyPU, canais digitais e pesquisa das APIs
- `tests/` — unittest; `examples/` — planilhas ficticias

Ao mexer no schema do banco, suba `VERSAO_ESQUEMA` e mantenha migracao idempotente.

- Marcas: Mocozim = headshop (tubete, banquinho, seda, porta Bic/isqueiro);
  3DPrintFranca = demais linhas (bico PU/EasyPU, rosario/chaveiro, pote, porta
  incenso). Nunca usar marca de terceiro (ex.: Veipar) em titulo/descricao/foto.
- Anuncios que venderam cairam depois do Ads: antes de reativar Ads, checar
  violacoes/denuncias e remover marcas de terceiro. Handoff em
  `docs/HANDOFF_ANUNCIOS.md`.
- Ads: R$ 300 no periodo (Set R$ 200 + Out R$ 100) ja lancados como marketing.
