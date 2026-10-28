# Arquitetura do Gestor de Marketplaces

Documento para quem vai manter/estender o projeto. A ideia central: **um núcleo
em Python puro** (sem dependências obrigatórias), duas bordas finas (CLI e MCP) e
uma integração declarativa com o DSH (preset + skill).

```
┌────────────┐   ┌───────────────────────┐   ┌──────────────────────────┐
│  DSH Web   │──▶│ Agente "Gestor de     │──▶│ ferramentas MCP          │
│  (chat)    │   │ Marketplaces" (preset)│   │ mcp__marketplaces__*     │
└────────────┘   └───────────────────────┘   └────────────┬─────────────┘
                                                          │ stdio JSON-RPC
┌────────────┐   ┌───────────────────────┐   ┌────────────▼─────────────┐
│ Terminal   │──▶│ bin/mkt (CLI)         │──▶│ Servico (fachada)        │
└────────────┘   └───────────────────────┘   └────────────┬─────────────┘
                                                          │
   ┌──────────────────────────────────────────────────────▼──────────────┐
   │ Núcleo mktagent                                                      │
   │  ingestao (CSV/XLSX)   financeiro (DRE, margem, caixa, alertas,      │
   │  API (Shopee/TikTok/UpSeller)   insights)   operacao (pedidos,       │
   │  criativos (copy/imagem)   SQLite (dados/mkt.db)                     │
   └──────────────────────────────────────────────────────────────────────┘
```

## Camadas e regras

| Camada | Onde | Regra |
|---|---|---|
| Domínio/cálculo | `src/mktagent/{ingestao,financeiro,operacao,criativos}.py` | só regra de negócio; nada de `print`; testável isolado |
| Persistência | `src/mktagent/db.py` | schema SQLite versionado (`PRAGMA user_version`), centavos `INTEGER` |
| Fachada | `src/mktagent/servico.py` | único ponto de entrada; toda leitura/escrita passa aqui |
| Borda CLI | `src/mktagent/cli.py` | argparse, saída PT-BR, `--json` em tudo |
| Borda MCP | `src/mktagent/mcp_server.py` | JSON-RPC 2.0 sobre stdio, stdout só protocolo |
| Integração DSH | `dsh/` + `scripts/instalar_dsh.py` + `skills/` | declarativo, idempotente, com backup e validação |

**Dinheiro:** sempre centavos (`int`). `Decimal` só na borda (parsing/formatação).
Nunca `float` para somar valores.

**Importação idempotente:** pedidos têm `UNIQUE (marketplace, pedido_externo)`,
reimportar atualiza em vez de duplicar. Contas e repasses também têm chaves naturais.

## Modelo de dados (SQLite)

| Tabela | Papel | Chave |
|---|---|---|
| `contas_loja` | lojas por marketplace (Shopee/TikTok por apelido) | `(marketplace, apelido)` |
| `produtos` | SKU, custo unitário, preço de venda | `sku` |
| `pedidos` | pedido agregado (valores do pedido) | `(marketplace, pedido_externo)` |
| `itens_pedido` | itens (sku, qtd, preço, custo snapshot) | `(pedido_id, sku)` |
| `repasses` | extrato de repasses/liquidações | `(conta_id, data, valor, referência)` |
| `contas_financeiras` | contas a pagar/receber | `(tipo, descrição, valor, vencimento)` |
| `estoque` | posição atual por SKU | `sku` |
| `importacoes` | log de importações (auditoria) | autoincrement |

Visões derivadas são calculadas na hora (`dre`, `margem_por_sku`, `fluxo_caixa`,
`insights`) — não há tabela de relatório para ficar desatualizada.

## Fórmulas

**DRE (competência):**

```
receita_bruta  = Σ itens_total (só pedidos aprovado)
receita_liquida = receita_bruta - descontos + frete_cobrado - frete_pago
                  - comissao - taxa_servico - cupom - imposto
margem_contribuicao = receita_liquida - CMV
lucro_liquido = margem_contribuicao - despesas_operacionais + outras_receitas
```

- `despesas_operacionais`: contas a pagar do mês (vencimento), **exceto** categorias
  já embutidas no pedido: `insumo`, `fornecedor`, `frete`, `imposto`, `comissao`, `taxa`.
- **Situação financeira**: `aprovado` (pago/enviado/entregue) entra; `cancelado`,
  `devolvido`, `pendente`, `desconhecido` ficam fora (com aviso/completude).

**Margem por SKU:** as taxas do pedido são rateadas proporcionalmente à receita de
cada item, então a margem já é líquida de comissão/frete/desconto. Curva ABC por
receita acumulada (A ≤ 80%, B ≤ 95%, C resto).

**Comparativo:** mês fechado vs mês fechado. Se o mês estiver em andamento, a receita
é comparada **MTD** (mesmos dias nos dois meses) e a variação de lucro não é exibida.

**Conc iliação de repasses:** `repasses_do_mês - receita_liquida`. Lag de repasse é
normal; diferença > 2% gera alerta (não é auditoria contábil).

## Decisões (e por quê)

1. **Sem dependências obrigatórias.** stdlib só: `sqlite3`, `csv`, `zipfile`,
   `xml.etree`, `hmac`, `urllib`, `decimal`. O leitor XLSX foi escrito à mão
   (zip+XML, primeira aba) para não depender de openpyxl/pandas.
   *Exceção opcional:* Pillow para gerar PNG dos criativos (SVG sempre funciona).
2. **MCP à mão (JSON-RPC sobre stdio).** Evita dependência do SDK Python e nos dá
   controle total do protocolo. Testado com o SDK oficial JS (v2) e com o DSH.
3. **Custo retroativo.** Importar pedidos antes dos custos é o fluxo real; ao
   cadastrar custo, atualizamos o snapshot dos itens já importados. Documentado no DRE.
4. **Agregação de colunas por pedido.** Exportações variam: coluna repetida em todas
   as linhas (Order Amount do TikTok) conta **uma vez**; coluna rateada (comissão da
   Shopee) **soma**. Heurística testada em `tests/test_ingestao.py`.
5. **DSH como superfície de chat.** O agente é um preset (persona + ferramentas) e o
   "conhecimento de processo" mora em skills no disco (`.dsh/skills/`), recarregáveis
   sem reiniciar.
6. **Escritas confirmadas.** O servidor MCP não publica nada em marketplace; só lê/escreve
   na base local. A persona exige confirmação antes de gravar.

## Protocolo MCP implementado

- Transporte: stdio, uma mensagem JSON-RPC por linha.
- Métodos: `initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`;
  `resources/list`/`prompts/list` devolvem listas vazias.
- `initialize` responde com a versão pedida (fallback `2025-06-18`), capabilities `tools`
  e `instructions` (regras de uso que aparecem no prompt do agente).
- Erros de ferramenta voltam como `result.isError=true` com texto PT-BR (não derrubam
  o servidor). Erros de protocolo usam códigos JSON-RPC.
- Saída truncada em 80 kB para não estourar contexto.

## Integração com o DSH

`dsh/patch-marketplaces.yml` (modelo) é injetado em `~/.dsh/profiles/web/cordis.patch.yml`
por `scripts/instalar_dsh.py`:

1. registra o servidor MCP (`mcp-marketplaces`, stdio, `bin/mkt-mcp`);
2. cria o preset `marketplaces` (persona PT-BR; bash, fs, jobs, schedule, skill,
   compaction, ask-user, todo, web, present);
3. copia as skills de `skills/` para `<workspace>/.dsh/skills/`;
4. valida com `dsh --profile web --dump-config` e **restaura o backup** se falhar.

O bloco fica entre marcadores (`# >>> mktagent` / `# <<< mktagent`) — rodar de novo
substitui, não duplica. HMR do DSH recarrega o servidor MCP ao editar o patch.

## Como estender

- **Novo marketplace:** adicionar aliases em `ingestao/colunas.py`, normalização de
  status em `ingestao/pedidos.classificar_situacao`, e (se houver API) um módulo em `api/`.
- **Novo relatório:** função pura em `financeiro/`, expor em `servico.py`, depois na
  CLI e em `mcp_server.FERRAMENTAS` + `tool_*`.
- **Novo criativo:** `criativos.py` (SVG/PNG) e o skill `estudio-criativos`.
- **Nova skill:** pasta em `skills/<nome>/SKILL.md` com frontmatter; reinstalar.
- **Novo campo de dados:** migração idempotente em `db.ESQUEMA` + subir `VERSAO_ESQUEMA`,
  importador e testes.

## Testes

`python3 -m unittest discover -s tests -t .` — sem rede, banco temporário por teste
(`MKT_HOME`/`MKT_DB` em diretório temporário). Cobre parsing (dinheiro/datas/colunas),
leitura CSV/XLSX, importação idempotente, agregação, DRE/margem/caixa/alertas/insights,
criativos (SVG/PNG), protocolo MCP via subprocesso, CLI com `--json` e integração UpSeller
(sem rede).

## Performance e limites

- Base local pequena (dezenas de milhares de pedidos) roda em milissegundos; índices em
  `data_pedido`, `situacao`, `marketplace`, `sku`.
- WAL habilitado para leitura/escrita concorrente leve (ex.: CLI rodando enquanto o MCP lê).
- Não há multiusuário/permissões: é ferramenta pessoal, um banco por workspace.
