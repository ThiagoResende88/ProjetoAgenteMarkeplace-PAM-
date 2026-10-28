# Gestor de Marketplaces (Shopee + TikTok Shop)

Um agente local para **gerir as contas das suas lojas**: importa os relatórios que
Shopee e TikTok Shop exportam, calcula o DRE de verdade, mostra a margem por SKU,
projeta o caixa, concilia repasses e avisa o que precisa de decisão.

Além do financeiro, ele **escreve anúncios**, **produz criativos** (arte PNG/SVG e
prompts de imagem para IA) e **analisa a loja com insights acionáveis** — integrado
ao **UpSeller**, o ERP que você já usa.

Roda no seu computador, guarda tudo em um SQLite local (nada vai para a nuvem) e
expõe as ferramentas para o agente do DSH — você conversa em português e ele
consulta/grava os dados por ferramentas, nunca "de cabeça".

```
você: feche o mês de setembro pra mim
agente: [usa mcp__marketplaces__dre, margem_sku, alertas]
        DRE de setembro/2026 ... margem 29,9% ... lucro -R$ 3.235,14 ...
        3 ações prioritárias: ...
```

## Seu negócio (3D Print Franca + Mocozim)

O agente já está calibrado para o seu contexto: impressão 3D em Franca-SP, marca
Mocozim (tubete PETG, porta-isqueiro, banquinho), canais Shopee/Mercado Livre/
TikTok Shop/Instagram/consignação e UpSeller como ERP.

Leituras dos seus dados (25/10/2026, atualizado em 27/10/2026):
[docs/DADOS_NEGOCIO.md](docs/DADOS_NEGOCIO.md),
[custos padronizados](docs/CUSTOS_PADRONIZADOS.md) e
[docs/CONTEXTO_NEGOCIO.md](docs/CONTEXTO_NEGOCIO.md). Plano de lançamento:
[docs/PLANO_MOCOZIM.md](docs/PLANO_MOCOZIM.md). EasyPU:
[docs/EASYPU_ESTRATEGIA.md](docs/EASYPU_ESTRATEGIA.md). Canais digitais
(Drive/Sheets/WhatsApp/Telegram): [docs/GUIA_CANAIS_DIGITAIS.md](docs/GUIA_CANAIS_DIGITAIS.md).

Destaques que ele já sabe fazer:
- **custos padronizados por item** em planilha XLSX com 7 abas
  (`saidas/custos/Custos_Mocozim_3DPrintFranca_2026-10.xlsx`);
- **precificar peça 3D** com filamento + máquina + falha + acabamento + embalagem +
  taxa do canal + frete (`precificar_3d`);
- **ler desempenho diário** do export "Performance das Vendas" (`desempenho`);
- **gerar criativo com foto real** (`gerar_criativo(..., foto=...)`);
- **mandar resumo no Telegram** (`enviar_telegram`).

## Começando em 3 comandos

```sh
cd marketplace-agent
./bin/mkt demo          # carrega 3 meses de dados fictícios (só para experimentar)
./bin/mkt resumo        # panorama
./bin/mkt dre --mes 2026-09
```

Depois, para usar seus dados: coloque as planilhas exportadas dos painéis em
`entradas/` e peça no chat **"importe a pasta entradas"** (ou
`./bin/mkt importar-pasta`). O importador roda primeiro em modo simulação e mostra
o mapeamento das colunas antes de gravar.

## O que ele faz

| Área | O que você consegue |
|---|---|
| **Financeiro** | DRE mensal por marketplace (receita bruta → lucro líquido), comparativo mês a mês, conciliação de repasses |
| **Produtos** | Margem de contribuição por SKU com taxas rateadas, curva ABC, preço mínimo para a margem alvo |
| **Caixa** | Projeção por semana a partir das contas, contas vencidas/a vencer, alertas de semana negativa |
| **Operação** | Pedidos por situação (aprovado/cancelado/devolvido), custos por SKU, cobertura de estoque, taxa de cancelamento |
| **Contas** | Cadastro e baixa de contas a pagar/receber, despesas operacionais por categoria |
| **Alertas** | Prejuízo no mês, SKU sem custo, margem negativa, queda de receita, estoque crítico, repasse divergente |
| **Copy de anúncio** | Título (3 opções com contagem de caracteres), descrição, bullets, FAQ, palavras-chave e checklist de conformidade por marketplace |
| **Criativos** | Card PNG 1080x1080/1080x1350 (SVG editável) com nome, benefícios, preço e espaço para a foto + briefing com 6 prompts para IA |
| **Insights** | Análise do mês: variação MTD/fechada, concentração de SKUs, matriz margem × volume, marketing, cancelamentos e 3-5 ações priorizadas |
| **Desempenho diário** | Tendência, ticket, cancelamento, semanas, dias da semana mais fortes e projeção a partir do export de performance |
| **Precificação 3D** | Custo real (filamento, máquina, falha, acabamento, embalagem), preço de empate, preço para margem alvo e cenários por canal/frete |
| **Notificações** | Resumo diário e alertas no Telegram (e WhatsApp Cloud, se configurado) |
| **Pedidos B2B** | Cria pedido manual (cliente, itens, preço), muda status e acompanha a receber — substitui a planilha de controle |
| **UpSeller (ERP)** | Exportações do UpSeller entram no importador; e, com API Token, sincroniza estoque direto (`mkt upseller sincronizar-estoque`) |
| **Multi-canal** | Shopee, Mercado Livre, TikTok Shop, Instagram/direto, consignação e outros nos mesmos relatórios |
| **Importação** | CSV/XLSX da Shopee, TikTok Shop e UpSeller (PT/EN), planilha própria, mapeamento tolerante, reimportação sem duplicar |

## UpSeller (seu ERP)

O UpSeller continua sendo a fonte da verdade (pedidos, estoque, produtos, financeiro).
O agente trabalha **por cima** dele, de três formas:

1. **Exportar do UpSeller e importar** (funciona hoje): exporte pedidos, custos,
   repasses e estoque, jogue em `entradas/` e peça *"importe a pasta entradas"*.
2. **Sincronizar estoque pela API aberta** (requer plano Profissional+/Kit): preencha
   `UPSELLER_CLIENT_ID` e `UPSELLER_API_TOKEN` no `.env` e rode
   `./bin/mkt upseller sincronizar-estoque`.
3. **MCP oficial do UpSeller no DSH** (opcional): URL e headers oficiais no
   [guia do UpSeller](docs/GUIA_UPSELER.md) — hoje ele expõe 2 ferramentas
   (armazéns e estoque por SKU).

Detalhes, credenciais e limitações: [docs/GUIA_UPSELER.md](docs/GUIA_UPSELER.md).

## Como o agente é montado no DSH

O projeto tem duas peças:

1. **Servidor MCP** (`bin/mkt-mcp`) — expõe as ferramentas `mcp__marketplaces__*`
   (`resumo`, `dre`, `margem_sku`, `fluxo_caixa`, `alertas`, `importar_arquivo`,
   `criar_conta`, `registrar_custo`, ...).
2. **Preset de agente** "Gestor de Marketplaces" — persona em PT-BR, ferramentas
   de arquivo/bash, e quatro skills: operação/financeiro, copy de anúncios,
   estúdio de criativos e análise da loja.

Instalação (escreve no seu perfil do DSH, com backup e validação):

```sh
python3 scripts/instalar_dsh.py --dry-run   # mostra o que será gravado
python3 scripts/instalar_dsh.py             # aplica (backup + dsh --dump-config)
```

Depois abra uma **nova conversa** no DSH Web e escolha o agente
**"Gestor de Marketplaces"**. Se o seletor não atualizar, reinicie o `dsh web`.

Como funciona por dentro: [docs/ARQUITETURA.md](docs/ARQUITETURA.md).
Como ligar a API oficial: [GUIA_CREDENCIAIS.md](GUIA_CREDENCIAIS.md).

## Importando seus dados

### Opção A — exportações dos painéis (funciona hoje, sem credenciais)

**Shopee Seller Center** → Pedidos → Exportar (XLSX/CSV). Para repasses:
Finanças → Extrato/Repasses.

**TikTok Shop Seller Center** → Pedidos → Exportar. Para liquidações:
Finanças → Liquidações (settlements).

O importador reconhece cabeçalhos em português e inglês, com e sem acento,
separador `;` ou `,`, decimal vírgula ou ponto, datas BR/US e serial do Excel.
Se o cabeçalho não for reconhecido, ele lista as colunas e não grava nada.

### Opção B — planilha modelo do projeto

```sh
./bin/mkt modelo pedidos     # imprime o cabeçalho esperado
./bin/mkt modelo contas
./bin/mkt modelo custos
./bin/mkt modelo repasses
./bin/mkt modelo estoque
```

Use `./bin/mkt modelo <tipo> --salvar` para criar o arquivo em `entradas/`.

### Regras de importação que valem saber

- **Um pedido pode ter várias linhas** (uma por item): o importador agrega.
- Coluna repetida em todas as linhas (ex.: `Order Amount` do TikTok) conta **uma vez**;
  coluna rateada por item (ex.: comissão da Shopee) é **somada**. Há teste para isso.
- Reimportar o mesmo arquivo **atualiza** os pedidos, não duplica.
- `--dry-run` (ou `dry_run=true`) não grava nada.
- Pedido com status desconhecido fica **fora da receita** e aparece em alerta —
  melhor importar o relatório com status mais recente.

## DRE: como o lucro é calculado

```
receita bruta (itens vendidos)
- descontos + frete cobrado - frete pago
- comissão - taxa de serviço - cupom - imposto
= receita líquida
- CMV (custo x quantidade)
= margem de contribuição
- despesas operacionais (contas a pagar do mês)
+ outras receitas (contas a receber)
= lucro líquido
```

- Só entram pedidos com situação **aprovado** (pago/enviado/entregue). Cancelado e
  devolvido ficam fora; pendentes e desconhecidos também (com aviso).
- Despesas `insumo`, `fornecedor`, `frete`, `imposto`, `comissao` e `taxa` **não**
  entram de novo como despesa operacional — elas já estão no pedido/CMV.
- Repasses podem incluir pedidos de outros meses (lag); a diferença é um sinal de
  conferência, não uma auditoria contábil.
- O custo do SKU é **retroativo**: ao cadastrar/atualizar o custo, os pedidos já
  importados são recalculados (útil quando você importa pedidos antes dos custos).

## Comandos

```text
mkt init                     cria banco e pastas
mkt demo [--limpar]          carrega dados de exemplo
mkt limpar --confirmar       apaga os dados operacionais
mkt importar TIPO ARQUIVO    pedidos | contas | custos | repasses | estoque
                             [--marketplace shopee|tiktok] [--conta NOME] [--dry-run]
mkt importar-pasta           importa tudo que estiver em entradas/
mkt dre [--mes AAAA-MM] [--marketplace ...] [--por-marketplace] [--saida arq.csv]
mkt comparativo [--mes]      mês vs mês anterior
mkt margem [--mes|--dias 90] [--limite N] [--margem-alvo 0.20]
mkt caixa [--dias 30]        projeção semanal + vencidas
mkt alertas                  o que precisa de atenção
mkt estoque [--dias 30]      cobertura por SKU
mkt contas [--status aberta|vencida|paga]
mkt conta criar ...          --descricao --valor --vencimento --categoria
mkt conta pagar ID [--data]
mkt produtos                 SKUs, custo, preço e estoque
mkt custo SKU VALOR [--preco] [--nome]
mkt pedidos [--mes] [--marketplace] [--situacao] [--limite]
mkt resumo                   panorama da operação
mkt insights [--mes]         análise com ações priorizadas
mkt desempenho [--dias 30] [--canal]          tendência diária do marketplace
mkt precificar --peso 10 --custo-kg 120 --canal shopee [--horas ...] [--frete ...]
mkt pedido criar --cliente "BARBEARIA" --item "TUBETE:10:12,00"   pedido B2B manual
mkt pedido status MOC-0001 Pago               atualiza status do pedido
mkt pedidos --cliente BARBEARIA               lista/filtra pedidos
mkt telegram status|testar|digest             resumo no celular
mkt whatsapp status|testar|digest
mkt criativo SKU --beneficio ... --selo ...   gera arte PNG/SVG
mkt briefing SKU --publico ...                prompts de imagem para IA
mkt upseller status | sincronizar-estoque     integração com o ERP
mkt status                   credenciais e últimas importações
mkt modelo TIPO [--salvar]   modelo de planilha
```

Todo comando aceita `--json` (útil para depurar e para o agente).

## Ferramentas do agente (MCP)

| Ferramenta | Para quê |
|---|---|
| `resumo` | panorama: dados, último DRE, alertas, contas |
| `dre` | DRE mensal por marketplace |
| `comparativo` | variação de receita/lucro vs mês anterior |
| `margem_sku` | margem por SKU, ABC, preço sugerido |
| `fluxo_caixa` | entradas/saídas por semana |
| `alertas` | lista priorizada com ação sugerida |
| `estoque` | dias de cobertura |
| `listar_contas`, `criar_conta`, `marcar_conta_paga` | contas a pagar/receber |
| `listar_produtos`, `registrar_custo` | custos e preços |
| `listar_pedidos` | pedidos com situação |
| `importar_arquivo`, `importar_pasta` | ingestão de planilhas |
| `insights` | análise da loja com ações priorizadas |
| `gerar_criativo` | arte do anúncio (PNG/SVG) |
| `briefing_imagens` | 6 prompts de imagem para IA + checklist |
| `desempenho` | visão diária do marketplace (tendência/dias fortes) |
| `precificar_3d` | custo e preço de peça 3D por canal |
| `upseller_status`, `upseller_sincronizar_estoque` | integração com o ERP |
| `status_notificacoes`, `enviar_telegram` | avisos no celular |
| `criar_pedido`, `atualizar_status_pedido` | controle de pedidos B2B/consignação |
| `status_integracoes`, `sincronizar` | APIs oficiais (fase 2) |

## Skills do agente

O conhecimento de processo fica em arquivos recarregáveis (`.dsh/skills/`), não no código:

| Skill | Quando entra |
|---|---|
| `gestor-marketplaces` | rotina financeira/operacional: DRE, margem, caixa, importação |
| `criador-anuncios` | título, descrição, palavras-chave e conformidade |
| `estudio-criativos` | arte PNG/SVG, prompts de imagem e regras de imagem |
| `analise-loja` | revisão semanal/mensal, diagnóstico e relatório de insights |
| `precificacao-3d` | custo real e preço de peças 3D (Mocozim, cubos, troféus) |
| `lancamento-produto` | fluxo de lançamento: ficha técnica → custo → anúncio → imagens → cadastro |

## Privacidade e segurança

- Tudo local: SQLite em `marketplace-agent/dados/mkt.db`, sem telemetria, sem nuvem.
- `.env` (credenciais) e `dados/` estão no `.gitignore`.
- O agente só grava depois de confirmar; importações têm modo simulação.
- Nenhuma credencial fica no banco. O `status` nunca mostra o segredo, só se está preenchido.

## Plano de finalização (app de tarefas)

Abra [todo/index.html](todo/index.html) no navegador: 47 tarefas, prioridades, responsável, progresso e exportação (JSON/Markdown). Salva sozinho no navegador.

## Estado e próximos passos

- ✅ Modo planilhas completo (Shopee/TikTok/UpSeller, pedidos, repasses, custos, contas, estoque)
- ✅ DRE, margem, caixa, alertas, insights, MCP e preset no DSH
- ✅ Copy de anúncios + criativos (PNG/SVG) + briefing de imagens para IA
- ✅ Integração UpSeller: importação de exportações + sincronização de estoque via API
- ✅ Multi-canal (Shopee, ML, TikTok, Instagram, consignação) e desempenho diário
- ✅ Precificação 3D com cenários de frete/taxas + criativo com foto real
- ✅ Notificação por Telegram (e WhatsApp Cloud preparado)
- ✅ Controle de pedidos B2B/consignação dentro do agente (sem planilha)
- 🚧 UpSeller: MCP oficial só expõe estoque/armazém hoje; vendas seguem por export
- ✅ MCP oficial do UpSeller documentado (armazéns/estoque)
- 🚧 API oficial de Shopee/TikTok (OAuth + sync automático) — estrutura e assinatura
  prontas em `src/mktagent/api/`, falta validar contra o sandbox com credenciais reais
- 🚧 Notificações agendadas (usar o `schedule` do DSH para lembrar vencimentos)
- 🚧 Rateio de despesas gerais por marketplace

## Problemas comuns

| Sintoma | Solução |
|---|---|
| "colunas obrigatórias não encontradas" | exporte de novo outro relatório ou use `mkt modelo` |
| planilha `.xls` antiga | salve como `.xlsx` ou `.csv` |
| margem estranha | SKU sem custo: `registrar_custo` / `mkt custo SKU VALOR` |
| mês zerado | confira se importou o período e se o mês é `AAAA-MM` |
| agente não aparece no DSH | rode o instalador, abra nova conversa, reinicie o `dsh web` |
| UpSeller não sincroniza estoque | confira plano (Profissional+/Kit) e tokens no `.env`; rode `mkt upseller status` |
| PNG do criativo não gerou | instale Pillow (`pip install pillow`); o SVG é gerado mesmo sem ele |
| copy "genérica" | dê medidas, material e público na conversa — o skill pergunta o que faltar |
| Telegram não envia | rode `mkt telegram status`; token/chat_id no `.env` |
| Vendas do UpSeller desatualizadas | o MCP do UpSeller hoje só tem estoque; importe o export de Performance ou peça API de pedidos ao suporte |
| preço não fecha com frete grátis | rode `mkt precificar ... --frete 20 --preco 9,90`; considere kit/canal direto |
| MCP sem ferramentas | `cd marketplace-agent && ./bin/mkt-mcp --listar-ferramentas` |

## Desenvolvimento

```sh
python3 -m unittest discover -s tests -t .   # 96 testes, sem rede
python3 scripts/gerar_exemplos.py            # regenera examples/
```

Sem dependências externas: apenas Python 3.10+. O servidor MCP é JSON-RPC sobre
stdio feito com a stdlib. O pacote é `src/mktagent/` (instalável com
`pip install -e .` se quiser o comando `mkt` global). **Pillow é opcional** — só é
usado para gerar o PNG dos criativos; o SVG é gerado sempre.
