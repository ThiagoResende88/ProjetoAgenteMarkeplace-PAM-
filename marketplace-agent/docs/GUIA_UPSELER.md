# UpSeller (ERP) — como o agente trabalha com ele

O UpSeller é o ERP que centraliza Shopee, TikTok Shop (e outros canais): pedidos,
estoque, produtos, financeiro e anúncios. O agente **não substitui** o UpSeller —
ele usa os dados dele para analisar, escrever e gerar criativos.

Verificado na Central de Ajuda do UpSeller em **25/10/2026**. Onde a documentação
não confirmou algo, está marcado como **NÃO CONFIRMADO**.

## Contas conectadas hoje (25/10/2026)

- **1 Shopee** + **1 TikTok Shop** conectadas ao UpSeller.
- **3ª loja TikTok Shop em criação** (o CNPJ permite até 5).
- O relatório "Performance das Vendas" que você exporta **vem do UpSeller** e já é
  importado pelo agente como `desempenho` (canal `consolidado` até você separar).

> ⚠️ **Importante sobre o MCP do UpSeller:** hoje ele expõe **somente 2 ferramentas**
> (listar armazéns e consultar estoque por SKU). **Não** há ferramenta de vendas,
> pedidos ou financeiro no MCP/API aberta documentada. Portanto:
> - **estoque atualizado:** dá para automatizar (MCP oficial ou `mkt upseller sincronizar-estoque`);
> - **vendas/pedidos atualizados:** por enquanto via export do UpSeller (Performance
>   das Vendas / pedidos) ou pelas APIs das próprias plataformas (fase 2);
> - vale abrir um chamado no UpSeller pedindo endpoints/MCP de pedidos e financeiro.

## Três formas de integrar (da mais simples para a mais automática)

| Modo | Precisa de quê | O que o agente faz |
|---|---|---|
| **A. Exportar planilhas** (funciona hoje) | nada além do UpSeller | você exporta pedidos/produtos/financeiro e pede "importe a pasta entradas" |
| **B. API de estoque** (pronto no código) | plano Profissional+ ou Kit + API Token | `mkt upseller sincronizar-estoque` atualiza o estoque local |
| **C. MCP oficial do UpSeller** | mesmas credenciais + cadastro no DSH | o agente ganha as ferramentas nativas do UpSeller (hoje: armazéns e estoque por SKU) |

⚠️ **Plano:** API aberta e MCP do UpSeller estão disponíveis nos planos
**Profissional e superiores** e no **Plano Kit**, sem custo adicional.

---

## A. Exportar do UpSeller e importar no agente

O importador do agente é tolerante a cabeçalhos (PT/EN) e a formatos CSV/XLSX,
então a maioria das exportações do UpSeller funciona direto:

1. No UpSeller, exporte:
   - **Pedidos** (período fechado, por loja/canal) → `mkt importar pedidos arquivo --marketplace shopee|tiktok`
   - **Produtos** com **custo** e preço → `mkt importar custos arquivo`
   - **Financeiro/liquidações** (repasse) → `mkt importar repasses arquivo --marketplace ...`
   - **Estoque** (se for usar a cobertura local) → `mkt importar estoque arquivo`
2. Nomeie os arquivos com a palavra-chave (`pedidos_shopee_outubro.xlsx`,
   `custos.csv`, `repasses_tiktok.csv`) e coloque em `entradas/`, ou passe o caminho.
3. Peca no chat: **"importe a pasta entradas"** — o agente roda primeiro em
   simulação e mostra o mapeamento das colunas.
4. Se alguma coluna não for reconhecida, o agente lista quais foram ignoradas.
   Mande o cabeçalho para acrescentarmos o alias (é rápido).

**Dica:** exporte **separado por canal** (Shopee e TikTok Shop) — evita misturar
taxas e ids diferentes no mesmo arquivo. Se exportar junto, use uma coluna
`marketplace`/`canal` com o nome do canal em cada linha.

---

## B. Sincronizar estoque pela API aberta

### Onde pegar as credenciais
Painel UpSeller → menu lateral **Plataforma Aberta → API Privada** → botão **Gerar**.
Você recebe três valores (guarde com segurança):

- **User ID** (ID do cliente)
- **API Token** (chamadas de API tradicionais)
- **MCP Token** (conexão com ferramentas de IA/MCP)

### Configurar
No `.env` do projeto:

```env
UPSELLER_CLIENT_ID=seu_user_id
UPSELLER_API_TOKEN=seu_api_token
UPSELLER_MCP_TOKEN=seu_mcp_token     # só se for usar o MCP oficial
```

### Usar
```sh
./bin/mkt upseller status
./bin/mkt upseller sincronizar-estoque
./bin/mkt estoque          # cobertura por SKU com o estoque atualizado
```

### Endpoints usados (confirmados na doc)
- `POST https://openapi.upseller.com/erp/inventory/getWarehouseList/v1`
- `POST https://openapi.upseller.com/erp/inventory/pageWarehouseSku/v1`
- Headers: `X-Upseller-Client-Id`, `X-Upseller-Api-Token`, `X-Upseller-Language`.

⚠️ **NÃO CONFIRMADO na doc pública**: o corpo exato do `pageWarehouseSku`
(nomes dos campos de paginação/filtro). O cliente usa `PageNo`/`PageSize` e devolve
o erro da API sem esconder. Se o estoque não mapear, o comando mostra uma amostra do
schema (`schema_amostra`) para ajustarmos os nomes.

---

## C. Conectar o MCP oficial do UpSeller no DSH (opcional)

O UpSeller expõe um servidor MCP (Streamable HTTP). Configuração oficial
(retirada das capturas da Central de Ajuda):

- URL: `https://openapi.upseller.com/mcp`
- Headers:
  - `X-Upseller-Client-Id`: seu **User ID**
  - `X-Upseller-Api-Token`: seu **MCP Token**
  - `X-Upseller-Language`: `pt`
- Hoje o MCP do UpSeller oferece: **listar armazéns** e **consultar estoque por SKU**
  (2 ferramentas). Para pedidos/financeiro, use as planilhas (modo A).

### Como registrar no DSH
Adicione ao final de `~/.dsh/profiles/web/cordis.patch.yml` (o bloco do agente é
instalado pelo `scripts/instalar_dsh.py`; este é separado):

```yaml
- insert:
    - id: mcp-upseller
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: upseller
        transport: streamable-http
        url: https://openapi.upseller.com/mcp
        headers:
          X-Upseller-Client-Id: 'SEU_USER_ID'
          X-Upseller-Api-Token: 'SEU_MCP_TOKEN'
          X-Upseller-Language: pt
        toolCallTimeoutMs: 60000
        failOnStartupError: false
```

Depois reinicie o DSH (ou deixe o HMR recarregar). As ferramentas aparecem como
`mcp__upseller__*`.

**Atalho:** preencha `UPSELLER_CLIENT_ID` e `UPSELLER_MCP_TOKEN` no `.env` e rode:

```sh
python3 scripts/instalar_dsh.py --com-upseller
```

O instalador injeta o bloco com backup e valida com `dsh --dump-config`.
Para remover: `python3 scripts/instalar_dsh.py --remover-upseller`.

**Cuidado com segredo:** esses dois valores ficam no arquivo de configuração do DSH
(dono: você, permissão 600). Se preferir não gravar ali, use o modo B (nossas
ferramentas leem do `.env`).

---

## O que o agente NÃO faz no UpSeller

- Não publica anúncio nem altera preço/estoque no UpSeller (sem API de escrita
  documentada para isso hoje). Ele **prepara** o texto/criativo/planilha; você aplica
  no UpSeller.
- Não substitui o UpSeller como fonte da verdade: o UpSeller segue sendo o ERP;
  o agente é a camada de análise e criação por cima.
- Sem acesso a métricas de visitas/conversão do UpSeller — insights de tráfego
  ficam limitados (ver skill `analise-loja`).

## Fluxo recomendado no dia a dia

1. **Semanal:** exportar pedidos e financeiro do UpSeller → importar → pedir análise
   (`insights`) → agir nas 3 prioridades.
2. **Mensal:** fechar o mês (`dre`), conferir repasses, atualizar custos de SKU,
   gerar insights de fechamento e salvar o relatório.
3. **Por produto:** usar `criador-anuncios` (texto) + `estudio-criativos` (card/prompts)
   e publicar no UpSeller.
4. **Estoque:** manter o estoque sincronizado (modo B) para os alertas de ruptura
   funcionarem.
