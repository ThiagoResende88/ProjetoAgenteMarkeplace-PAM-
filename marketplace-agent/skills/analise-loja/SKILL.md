---
name: analise-loja
description: Fazer a análise periódica da loja com os dados reais — o que cresceu, o que concentra risco, onde a margem não compensa, o que fazer — e entregar um relatório curto com ações e KPIs.
whenToUse: Quando o usuário pedir insights, "como está a loja?", fechamento semanal/mensal, "o que eu melhoro?", diagnóstico de queda de vendas ou revisão de mix.
---

# Análise da loja (insights com dados reais)

Seu trabalho não é jogar números: é **dizer o que eles significam** e o que fazer
depois. Todo número vem das ferramentas `mcp__marketplaces__*`; hipótese é dita
como hipótese.

## Regra número 1: saiba se o mês está fechado

- Mês em andamento → a ferramenta de insights usa comparação **MTD** (mesmos dias
  no mês anterior). Não compare mês parcial com mês cheio.
- Para fechamento oficial, use um mês já encerrado.

## Rotina de análise (padrão)

1. `insights` do mês → leia `numeros`, `insights`, `acoes_prioritarias`,
   `concentracao` e `matriz_sku`.
   Complemente com `desempenho` (visão diária do marketplace) quando existir
   export de performance importado.
2. Valide as 2-3 hipóteses mais importantes com dados específicos:
   - queda de receita → `margem_sku` + `listar_pedidos` (por dia/categoria) + `estoque`
   - margem baixa → `margem_sku` (veja `taxas_pct`, `preco_sugerido`)
   - repasse estranho → `dre` (diferença de conciliação) + `listar_contas`
   - caixa apertado → `fluxo_caixa`
3. Classifique cada SKU na matriz margem x volume:
   - **motor** (margem e volume altos): proteger estoque, não mexer no preço sem testar
   - **oportunidade** (margem alta, volume baixo): testar anúncio/cupom/kit
   - **volume que segura** (volume alto, margem baixa): renegociar custo/frete ou subir preço
   - **revisar** (baixo/baixo): descontinuar ou reposicionar
4. Entregue relatório em `saidas/relatorios/<AAAA-MM-DD>-analise.md` com:
   - Resumo em 5 linhas
   - Números do período
   - 3-5 insights (cada um com o número que sustenta)
   - Ações ordenadas (o quê, por quê, como medir)
   - KPIs para acompanhar na próxima semana
   - O que **não** dá para afirmar com os dados atuais

## Perguntas de contexto que mudam a leitura

Pergunte (poucas, objetivas):
- Houve promoção/campanha no período? Quanto foi gasto?
- Algum SKU entrou/saiu do ar, mudou preço ou esgotou?
- Sazonalidade esperada do produto?
- Meta do mês (receita/lucro)? Capacidade de investir em ads?

Sem essas respostas, marque as hipóteses como não confirmadas.

## O que você NÃO pode afirmar

- **Causa de queda sem dados de visitas/conversão.** A base tem pedidos/financeiro,
  não tráfego. Diga "hipótese: queda de visitas/anúncio pausado" e proponha o teste.
- **ROI de anúncio** sem atribuição por campanha. Pode falar de gasto e de teto,
  não de retorno por real investido.
- **Projeção de lucro futura** como certeza. Use "cenário" e mostre a premissa.
- **Comparação com concorrente** sem fonte. Se usar web, cite e trate como referência.

## Formato do resumo semanal (1 página)

```markdown
# Análise — semana de DD/MM a DD/MM

## Em 5 linhas
- Receita: R$ ... (variação ...)
- Margem de contribuição: ... 
- Lucro: ...
- Principal risco: ...
- Principal oportunidade: ...

## Números
(tabela com receita, CMV, margem, opex, lucro, pedidos, ticket, cancelamentos)

## Insights
1. [número] → [leitura]
2. ...

## Ações (ordenadas)
| # | Ação | Por quê | Como medir | Prazo |
|---|---|---|---|---|

## KPIs da próxima semana
- ...

## Limitações dos dados
- ...
```

## Estilo

- Frases curtas, número na frente ("Margem caiu de 29,9% para 27,2% puxada por X").
- Nada de adjetivo vazio ("desempenho excelente"). Se não tem dado, não afirma.
- Sempre termine com 3 ações, não com 10.
- Se o usuário for leigo, explique o indicador em uma linha.

## Contexto do negocio (3D Print Franca + Mocozim)

- **3D Print Franca** (Franca-SP): impressao 3D, pecas personalizadas, trofeus,
  chaveiros, replicas de pets, caixas tecnicas e produto proprio. Impressora
  Anycubic Kobra 3 V2; PLA e PETG; filamentos verde, amarelo, branco, preto, cobre.
- **Mocozim**: marca/produto de tubete discreto em PETG (~14 cm), com linha
  tubete, porta-isqueiro e banquinho; venda direta, consignacao e marketplaces.
- **Canais**: Shopee, Mercado Livre, TikTok Shop, Instagram/direto, consignacao.
  UpSeller e o ERP (notas, estoque, pedidos).
- **Cautelas**: nao afirmar originalidade/patente (disputa sobre o bico PU EasyPU,
  BR202025011653-2); nao usar marca de terceiros (ex.: "Corinthians") sem licenca;
  vape tem restricao em marketplace; alegacoes do Mocozim (hermetico, agua/odores)
  so depois de teste. Sem consultoria juridica/fiscal.
- Dados detalhados em `docs/DADOS_NEGOCIO.md` e `docs/CONTEXTO_NEGOCIO.md`.

## Especificidades do negocio 3D

- Ticket baixo: acompanhar **ticket médio** e propor kits (2, 3, 10 un).
- Semana fraca: checar anúncio pausado, ruptura de filamento/estoque e concorrência.
- Produção sob encomenda: capacidade por semana limita promoção; perguntar antes de
  sugerir aumento de tráfego.
- Separe **venda direta/consignação** (B2B) de **marketplace**: margens e prazos
  diferentes.
- Não use o relatório diário para calcular margem: ele não tem custo/taxa por pedido.
