# Guia de credenciais — APIs oficiais (Shopee e TikTok Shop)

> **Hoje você não precisa disso.** O agente funciona 100% com as planilhas
> exportadas dos painéis (e do UpSeller). Este guia é para quando quiser
> sincronização automática, sem depender de exportar arquivo.
>
> Pesquisa na documentação oficial em **25/10/2026**. Onde a fonte oficial não
> confirmou algo, está marcado como **NÃO CONFIRMADO** — não trate como verdade.

## Resumo do que já está pronto no código

| Item | Situação |
|---|---|
| Assinatura HMAC-SHA256 (Shopee e TikTok) | implementada em `src/mktagent/api/assinatura.py` |
| Montagem de URL de autorização + troca/renovação de token | implementada em `api/shopee.py` e `api/tiktok.py` |
| Endpoints de pedidos/repasses documentados abaixo | mapeados, **não validados** contra sandbox |
| Sincronização automática no agente | **fase 2**: depende de credenciais + teste no sandbox |
| Importação por planilha | ✅ pronto e testado |

Enquanto a fase 2 não fecha, o caminho é exportar do painel (ou do UpSeller) e
importar — ver [GUIA_UPSELER](GUIA_UPSELER.md) e o README.

---

## Shopee Open Platform (v2)

### 1. Criar a app

1. Acesse o portal: <https://open.shopee.com> (Brasil: <https://open.shopee.com.br>).
2. Crie a conta de desenvolvedor. A plataforma atende **ISVs** e **vendedores com
   capacidade de desenvolvimento**. Existe uma trilha específica para o Brasil
   ("BRASIL | Jornada do Desenvolvedor").
3. No Console → **App list** → crie a app. Copie o **Partner ID** e a **Partner Key**
   (a key aparece no detalhe do app).
4. Existem **credenciais de teste (sandbox)** e **de produção (live)** separadas:
   o Partner ID de teste só funciona no ambiente de teste.
5. Cadastre a **Redirect URL** (domínio) no Console. O domínio do `redirect_uri`
   precisa bater exatamente, senão a autorização falha.

### 2. URLs (confirmadas)

| Finalidade | Produção | Sandbox |
|---|---|---|
| API (global/SG) | `https://partner.shopeemobile.com` | `https://openplatform.sandbox.test-stable.shopee.sg` |
| API (Brasil/Américas) | `https://openplatform.shopee.com.br` | `https://openplatform.sandbox.test-stable.shopee.com.br` |
| Autorização (web) | `https://open.shopee.com/auth` (BR: `open.shopee.com.br/auth`) | sandbox equivalente |

⚠️ Host de **auth** ≠ host de **API**. Não misture.

### 3. Assinatura (a mesma do código)

```
base_string = partner_id + api_path + timestamp [+ access_token + shop_id]
sign        = HMAC-SHA256(partner_key, base_string) em hex minúsculo
```

- `api_path` sem host e **sem query string** (ex.: `/api/v2/shop/get_shop_info`).
- No **Merchant API** o último componente é `merchant_id`; no **Public API** os dois
  últimos não entram.
- Os parâmetros `partner_id`, `timestamp`, `sign` (+ `access_token`, `shop_id`) vão
  **na query string**, inclusive em POST. O body carrega só os campos de negócio.
- `timestamp` vale **5 minutos**.

### 4. OAuth

Link de autorização:

```
https://open.shopee.com/auth?partner_id={partner_id}&auth_type=seller
  &redirect_uri={redirect_uri}&response_type=code&state={state}
```

- Callback: `{redirect_uri}?code=...&shop_id=...` (ou `main_account_id`).
- `code`: uso único, expira em **10 minutos**.
- Troca: `POST /api/v2/auth/token/get` (body: `code`, `shop_id`, `partner_id`).
- `access_token`: **4 horas**; `refresh_token`: **30 dias**.
- Renovação: `POST /api/v2/auth/access_token/get` (body: `refresh_token`, `shop_id`,
  `partner_id`).
- Grant total de até 365 dias.

### 5. Endpoints úteis (paths confirmados)

| Uso | Endpoint | Particularidade |
|---|---|---|
| Listar pedidos | `GET /api/v2/order/get_order_list` | janela **máx. 15 dias**; retorna só `order_sn` |
| Detalhe do pedido | `GET /api/v2/order/get_order_detail` | até 50 `order_sn` por chamada |
| Repasse/extrato do pedido | `GET /api/v2/payment/get_escrow_detail` | **1 pedido por chamada**; traz `commission_fee`, `service_fee`, `seller_transaction_fee`, `campaign_fee`, `escrow_amount` |
| Receitas por período | `GET /api/v2/payment/get_income_detail` | janela **máx. 14 dias** |

⚠️ O coletor precisa **fatiar** os períodos, e o detalhe/escrow é N+1 chamadas —
planeje a cota antes de rodar em produção.

### 6. Limites e erros

- Existe teto diário por app (`error_limit`, reset 00:00 UTC+8) e limite de
  frequência (`error_rate_limit`). **Os números de QPS não são públicos**
  (NÃO CONFIRMADO) — a página do endpoint/app prevalece.
- Erros de negócio vêm em **HTTP 200** com o campo `error` preenchido
  (`error_auth`, `error_sign`, `error_param`, `error_limit`...). **Valide o campo
  `error`, não só o status HTTP.**

### 7. Configuração no `.env`

```env
SHOPEE_PARTNER_ID=...
SHOPEE_PARTNER_KEY=...
SHOPEE_REDIRECT_URL=http://localhost:8765/shopee/callback
SHOPEE_ENV=sandbox        # producao | sandbox
SHOPEE_REGIAO=br          # br | global | cn
```

Confira com `./bin/mkt status`.

---

## TikTok Shop Partner Center (Open API)

### 1. Criar a app

1. Partner Center: <https://partner.tiktokshop.com> (EUA: `partner.us.tiktokshop.com`).
2. **App & Service → Create app & service**: escolha **Public app** (exige review e
   listagem) ou **Custom app** (link privado de autorização).
3. Escolha **Service category**, **Market** e **Seller type** (Local × Cross-border).
   ⚠️ Market/seller type são escolhas de criação — podem não ser editáveis depois.
4. Ligue **Enable API**, configure **Redirect URL** e **Webhook URL**.
5. Em **App credentials** copie **App Key** e **App Secret**; o **Service ID**
   (identificador do OAuth client) aparece na app.

### 2. URLs (confirmadas)

| Finalidade | Resto do mundo (inclui BR) | EUA |
|---|---|---|
| Autorização seller | `https://services.tiktokshop.com/open/authorize` | `https://services.us.tiktokshop.com/open/authorize` |
| Token (get/refresh) | `https://auth.tiktok-shops.com/api/v2/token/{get,refresh}` | igual |
| OpenAPI (dados) | `https://open-api.tiktokglobalshop.com` | igual |

⚠️ Não misture domínio de autorização, de token e de dados.

### 3. Assinatura (a mesma do código)

```
1. pegue todos os query params; exclua sign e access_token
2. ordene as chaves (ASCII)
3. concatene {chave}{valor} sem = nem &
4. prefixe o path do endpoint (sem host/query)
5. se o Content-Type não for multipart/form-data, anexe o body cru
6. envolva com o app_secret dos dois lados: secret + input + secret
7. sign = HMAC-SHA256(app_secret, signInput) em hex minúsculo
```

- `sign` vai **na query string**. O `access_token` vai no header
  **`x-tts-access-token`**.
- ⚠️ **Não existe** header `x-tts-signature` na doc atual (é legado de terceiros).
- `timestamp` em **segundos** (10 dígitos), válido em ~[-5 min, +30 s].

### 4. OAuth

- Link: `https://services.tiktokshop.com/open/authorize?service_id={service_id}&state={state}`
- Callback: `{redirect_url}?code={auth_code}&state=...`; `auth_code` expira em **30 min**, uso único.
- Troca: `GET https://auth.tiktok-shops.com/api/v2/token/get`
  com `app_key`, `app_secret`, `auth_code` e **`grant_type=authorized_code`**
  (literalmente `authorized_code`).
- `access_token`: **7 dias**; `refresh_token` expira junto com a autorização.
- Refresh: `GET .../api/v2/token/refresh` com `grant_type=refresh_token`.

### 5. Endpoints úteis (paths confirmados)

| Uso | Endpoint | Particularidade |
|---|---|---|
| Buscar pedidos | `POST /order/202309/orders/search` | `shop_cipher` obrigatório; body com `create_time_ge/lt`, `order_status`; page 1–100 |
| Detalhe do pedido | `GET /order/202507/orders?ids=` | máx. 50 ids; traz `payment{}` e `line_items[]` |
| Statements (liquidação) | `GET /finance/202309/statements` | `settlement_amount`, `revenue_amount`, `fee_amount`, `adjustment_amount`, `net_sales_amount` |
| Transações de um pedido | `GET /finance/202501/orders/{order_id}/statement_transactions` | útil para conciliar pedido ↔ repasse |
| Ainda não liquidado | `GET /finance/202507/orders/unsettled` | |

Statements são gerados diariamente às 00:00 UTC (transações do dia anterior),
disponíveis desde 2023-07-01.

### 6. Limites e sandbox

- QPS **dinâmico** por App ID × Shop; não há API pública de cota. Sinais:
  **HTTP 429** e/ou código de negócio **36009002**. 503 é indisponibilidade (retry curto).
- Respostas trazem `code` (0 = sucesso) — **valide `code`**, não só o HTTP.
- Sandbox = **Development Shops**: Partner Center Console → Development Kits →
  Development Shops → Create test account.
  - **Core Function**: produtos/pedidos/fulfillment; **não** cobre finance.
  - **Full Function**: fluxo completo (finance/settlements), exige business/KYC.
- ⚠️ **NÃO CONFIRMADO**: host de sandbox dedicado. `open-api-sandbox.tiktokglobalshop.com`
  não resolveu no teste; assuma os mesmos hosts com tokens de dev shop e **teste**.

### 7. Configuração no `.env`

```env
TIKTOK_APP_KEY=...
TIKTOK_APP_SECRET=...
TIKTOK_SERVICE_ID=...
TIKTOK_REDIRECT_URL=http://localhost:8765/tiktok/callback
TIKTOK_ENV=sandbox
TIKTOK_REGIAO=row       # row | us
```

---

## O que ainda falta para a sincronização funcionar

1. **Criar as apps** (sandbox primeiro) e preencher o `.env`.
2. **Fluxo local de callback** (mini-servidor em `localhost:8765`) para receber o
   `code` e trocar por token — ainda não implementado.
3. **Persistir tokens** com segurança (arquivo local 600 ou chaveiro do sistema).
4. **Coletor**: fatiar janelas (Shopee 15 dias), paginar, tratar 429/backoff,
   converter respostas para o schema interno e importar via upsert.
5. **Validar no sandbox** e só depois ir para produção.

Se quiser que eu implemente a fase 2, o caminho é fazer o login OAuth no sandbox
com você e validar cada endpoint um por um.

## Onde isso está no código

- `src/mktagent/api/assinatura.py` — HMAC das duas plataformas
- `src/mktagent/api/shopee.py` — hosts, links, token, cliente HTTP
- `src/mktagent/api/tiktok.py` — hosts, links, token, cliente HTTP
- `src/mktagent/api/__init__.py` — `status_credenciais` e `sincronizar` (resposta honesta: não configurado)
- `src/mktagent/api/upseller.py` — integração do ERP (ver guia próprio)
- `docs/PESQUISA_APIS.md` — pesquisa completa com as URLs de origem
