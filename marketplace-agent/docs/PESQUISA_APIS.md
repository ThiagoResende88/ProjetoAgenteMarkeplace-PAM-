# APIs oficiais de marketplaces — Shopee e TikTok Shop (pesquisa 2026)

**Objetivo:** insumo para um projeto Python local que autentica via OAuth e baixa pedidos, repasses e taxas.
**Método:** leitura da documentação oficial renderizada (as páginas de doc são SPA; o conteúdo abaixo foi extraído do DOM renderizado de `open.shopee.com` e `partner.tiktokshop.com`).
**Data da coleta:** 2026-10-25.
**Legenda:**
- ✅ = confirmado em página oficial (URL citada).
- ⚠️ NÃO CONFIRMADO = não achei na fonte oficial / não consegui abrir a página.
- ❌ não encontrado = procurei e não existe referência oficial localizada.

> Convenção: "path" sempre sem host. Em ambas as plataformas o path **entra na assinatura**, então ele precisa ser idêntico ao documentado (sem query string).

---

## 1. Shopee Open Platform (v2)

### 1.1 Como criar a app

✅ **Quem pode acessar:** a plataforma atende (a) *software service providers* (ISV) e (b) *sellers com capacidade de desenvolvimento*. Fonte: [Introduction – Who can access Shopee Open Platform?](https://open.shopee.com/developer-guide/17)

✅ **Onde ficam Partner ID / Partner Key:** o `partner_id` é obtido criando um App na **App list** do Console; a **Partner Key** aparece na página de detalhe do App. O doc é explícito: *"partner Key (obtained through the Shopee Open Platform Console App detail page)"*. Fonte: [API calls](https://open.shopee.com/developer-guide/16)

✅ **Test vs Live:** existe **test partner ID** e **live partner ID** separados — *"Test partner ID can only be used in the test environment, and Live partner ID can only be used in the production environment"*. Fonte: [API calls](https://open.shopee.com/developer-guide/16). Ou seja: a app de sandbox é uma app distinta, com credenciais próprias.

✅ **URLs do portal:**
- Console / documentação global: `https://open.shopee.com` (Console em `/console`)
- Brasil: `https://open.shopee.com.br` (host de auth/API; a home respondeu 403 ao fetch automatizado)
- China continental: `https://open.shopee.cn`

✅ **Requisitos para vendedor brasileiro (CNPJ, conta de vendedor):** ⚠️ NÃO CONFIRMADO. A doc oficial de *Getting Started* que li descreve os dois perfis de acesso, mas eu **não consegui abrir** as páginas "Developer account registration", "App management", "BR SPI App Creation User Guide" e "BRASIL | Jornada do Desenvolvedor" (aparecem no menu lateral, porém sem URL estável acessível — o roteamento é JS e os links não expõem `href`). Não vou afirmar exigência de CNPJ sem fonte. O que **é** verificável: existe uma trilha dedicada ao Brasil ("BRASIL | Jornada do Desenvolvedor" e "BR SPI App Creation User Guide"), e o fluxo inclui Sandbox **antes** do Go Live. Fonte do menu: [Authorization and Authentication](https://open.shopee.com/developer-guide/20)

✅ **Sandbox:** ambiente "test-stable", com hosts próprios e app/partner_id próprios. Ao criar a app no Console escolhe-se a versão sandbox; o Partner ID de teste só funciona lá.

### 1.2 URLs base

✅ Confirmado em [API calls](https://open.shopee.com/developer-guide/16) e no bloco "Request Address" de cada endpoint (ex.: [v2.order.get_order_list](https://open.shopee.com/documents/v2/v2.order.get_order_list?module=95&type=1)):

| Ambiente | Região | Host |
|---|---|---|
| Produção | SG / global | `https://partner.shopeemobile.com` |
| Produção | China continental | `https://openplatform.shopee.cn` |
| Produção | Brasil / Américas | `https://openplatform.shopee.com.br` |
| Sandbox | todos | `https://openplatform.sandbox.test-stable.shopee.sg` |
| Sandbox | China continental | `https://openplatform.sandbox.test-stable.shopee.cn` |

✅ Endpoints de **autorização** (páginas web, não API):
`https://open.shopee.com/auth` · `https://open.shopee.cn/auth` · `https://open.shopee.com.br/auth`
Sandbox: `https://open.sandbox.test-stable.shopee.com/auth`, `https://open.sandbox.test-stable.shopee.cn/auth`.
⚠️ Em 29/10/2026 os hosts `openplatform.sandbox.test-stable.shopee.com.br` e
`open.sandbox.test-stable.shopee.com.br` retornaram **NXDOMAIN** no DNS público;
o sandbox global em Singapura respondeu. O código usa o host global para BR.
Fonte: [Authorization and Authentication](https://open.shopee.com/developer-guide/20)

⚠️ Atenção: os hosts de *auth* (`open.shopee.com`) são diferentes dos hosts de *API* (`partner.shopeemobile.com`). Não confundir.

### 1.3 Algoritmo EXATO de assinatura (sign)

✅ Fonte: [API calls → Signature calculation](https://open.shopee.com/developer-guide/16) e [Authorization → Calculating the sign parameter](https://open.shopee.com/developer-guide/20).

**String base** = concatenação, **nesta ordem exata**, sem separador:

| Tipo de API | String base |
|---|---|
| Shop API | `partner_id` + `api_path` + `timestamp` + `access_token` + `shop_id` |
| Merchant API | `partner_id` + `api_path` + `timestamp` + `access_token` + `merchant_id` |
| Public API | `partner_id` + `api_path` + `timestamp` |

- `api_path` = path **sem host** e **sem query string**, ex.: `/api/v2/shop/get_shop_info`.
- Todos os componentes entram como **string** (o `partner_id` numérico vira texto, sem separadores).

Exemplo oficial:
```
partner_id: 2001887
api path:   /api/v2/shop/get_shop_info
timestamp:  1655714431
access_token: 59777174636562737266615546704c6d
shop id:    14701711
Base string = 2001887/api/v2/shop/get_shop_info165571443159777174636562737266615546704c6d14701711
```

**Hash:** HMAC-SHA256 usando a **partner_key** como chave; saída em **hexadecimal minúsculo** (64 chars).
```
sign = hmac.new(partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()
```
Exemplo oficial de resultado: `56f31d01aeda9d08bf456b37f6f6640ef8614b4d6ad49baafe30b39a061f0e26`

**Onde vão os parâmetros:** `partner_id`, `timestamp`, `sign` (+ `access_token`, `shop_id`/`merchant_id` nas Shop/Merchant APIs) vão **na query string**, inclusive nos POSTs. No POST, apenas os parâmetros de negócio vão no body JSON. Exemplo oficial de chamada autenticada:

```
POST https://partner.shopeemobile.com/api/v2/auth/token/get?partner_id={pid}&timestamp={ts}&sign={sign}
Content-Type: application/json

{"code": "...", "shop_id": 123, "partner_id": 123}
```

⚠️ NÃO CONFIRMADO: não achei indicação de que `sign` precise ser URL-encoded de forma especial (hex minúsculo é URL-safe) nem de que o `Content-Type` entre no cálculo.

**Validade do timestamp:** 5 minutos (doc: *"Each API request needs to be requested within 5 minutes of a timestamp"*).

### 1.4 Fluxo OAuth completo

✅ Fonte: [Authorization and Authentication](https://open.shopee.com/developer-guide/20) (Last Updated: 2026-07-23).

**(a) Link de autorização** (montado por você, não é chamada de API):
```
https://open.shopee.com/auth?partner_id={partner_id}&auth_type=seller&redirect_uri={redirect_uri}&response_type=code&state={state}
```
| Param | Obrigatório | Observação |
|---|---|---|
| `partner_id` | sim | int |
| `auth_type` | sim | `seller` (shop/merchant), `supplier`, `user` |
| `redirect_uri` | sim | precisa casar com o domínio cadastrado no Console (Test Redirect URL Domain / Live Redirect URL Domain) |
| `response_type` | sim | valor fixo `code` |
| `state` | não | anti-CSRF, devolvido como veio |

✅ O `sign` também pode compor o link (a doc diz que o timestamp do sign vale 5 min e o link expira junto). ⚠️ NÃO CONFIRMADO qual é o formato exato do link assinado; o exemplo oficial de link **não** inclui `sign` — é `?partner_id=10090&auth_type=seller&redirect_uri=https://open.shopee.com&response_type=code`.

**(b) Callback:** `{redirect_uri}?code=xxxx&shop_id=123` (autorização por shop) ou `...?code=xxxx&main_account_id=123` (main account).
- `code`: **uso único**, expira em **10 minutos**.
- Se o domínio do `redirect_uri` não bater com o Console: erro *"The domain of redirect_uri is not consistent with the Redirect URL Domain declared in console"*.

**(c) Troca do code por token** — `POST /api/v2/auth/token/get`
- Produção: `https://partner.shopeemobile.com/api/v2/auth/token/get`
- Sandbox: `https://openplatform.sandbox.test-stable.shopee.sg/api/v2/auth/token/get`
- Query: `partner_id`, `timestamp`, `sign` (Public API → base string sem access_token)
- Body: `code`, `partner_id`, e `shop_id` **ou** `main_account_id`
- Resposta: `access_token`, `refresh_token`, `expire_in` (segundos), e `merchant_id_list` / `shop_id_list` / `supplier_id_list` / `user_id_list` quando o input foi `main_account_id`

**(d) Refresh** — `POST /api/v2/auth/access_token/get`
- Produção: `https://partner.shopeemobile.com/api/v2/auth/access_token/get`
- Sandbox: `https://openplatform.sandbox.test-stable.shopee.sg/api/v2/auth/access_token/get`
- Body: `refresh_token`, `partner_id`, e `shop_id` **ou** `merchant_id`
- Resposta: novo `access_token`, novo `refresh_token`, `expire_in`, `shop_id`/`merchant_id`/`partner_id`

**(e) Validades (✅ oficiais):**
- `access_token`: **4 horas**, reutilizável dentro da validade. Após gerar um novo, o anterior continua válido por mais **5 minutos**.
- `refresh_token`: **30 dias**, uso único (cada refresh devolve um novo).
- Autorização (grant): **até 365 dias**; o vendedor escolhe 7/30/90/180/365 dias ou data custom.
- `code`: 10 min, uso único.
- Reautorizar renova access_token **e** refresh_token.
- Cada `shop_id` / `merchant_id` / `user_id` / `supplier_id` tem seu **próprio par de tokens** — armazenar separadamente.
- Para `main_account_id`, o token inicial é compartilhado; após o primeiro refresh por `shop_id`/`merchant_id`, cada um passa a ter tokens independentes.

### 1.5 Endpoints principais

✅ Todos abaixo foram lidos nas páginas de referência oficiais (bloco "Request Address" + tabelas de parâmetros).

#### 1.5.1 Listar pedidos — `v2.order.get_order_list`
- **GET** `/api/v2/order/get_order_list` — [doc](https://open.shopee.com/documents/v2/v2.order.get_order_list?module=95&type=1)
- Parâmetros:

| Param | Tipo | Obrig. | Notas |
|---|---|---|---|
| `time_range_field` | string | sim | `create_time` ou `update_time` |
| `time_from` | timestamp | sim | |
| `time_to` | timestamp | sim | **janela máxima de 15 dias** (erro `order.order_list_invalid_time`: *"Start time must be earlier than end time and diff in 15days"*) |
| `page_size` | int32 | sim | 1–100 |
| `cursor` | string | não | paginação por cursor |
| `order_status` | string | não | `UNPAID`/`READY_TO_SHIP`/`PROCESSED`/`SHIPPED`/`COMPLETED`/`IN_CANCEL`/`CANCELLED`/`INVOICE_PENDING` |
| `response_optional_fields` | string | não | `order_status` |
| `request_order_status_pending` | bool | não | habilita status `PENDING` |
| `logistics_channel_id` | int32 | não | "Valid only for BR" |

- Resposta: `response.more` (bool), `response.next_cursor` (usar como `cursor` na próxima), `response.order_list[].order_sn`, `.order_status`, `.booking_sn`.
- ⚠️ Este endpoint devolve **apenas `order_sn` + status** (não devolve valores). Para valores, chamar `get_order_detail` e/ou `get_escrow_detail`.

#### 1.5.2 Detalhe do pedido — `v2.order.get_order_detail`
- **GET** `/api/v2/order/get_order_detail` — [doc](https://open.shopee.com/documents/v2/v2.order.get_order_detail?module=95&type=1)
- Parâmetros: `order_sn` (lista separada por vírgula, **limite 1–50**), `response_optional_fields` (lista separada por vírgula).
- `response_optional_fields` aceita: `buyer_user_id`, `buyer_username`, `estimated_shipping_fee`, `recipient_address`, `actual_shipping_fee`, `goods_to_declare`, `note`, `note_update_time`, `item_list`, `pay_time`, `dropshipper`, `dropshipper_phone`, `split_up`, `buyer_cancel_reason`, `cancel_by`, `cancel_reason`, `actual_shipping_fee_confirmed`, `buyer_cpf_id`, `fulfillment_flag`, `pickup_done_time`, `package_list`, `shipping_carrier`, `payment_method`, `total_amount`, `invoice_data`, `order_chargeable_weight_gram`, `return_request_due_date`, `edt`, `payment_info`, `international_label`.
- Campos relevantes na resposta: `order_sn`, `order_status`, `currency`, `total_amount`, `cod`, `payment_method`, `shipping_carrier`, `estimated_shipping_fee`, `actual_shipping_fee`, `create_time`, `update_time`, `pay_time`, `ship_by_date`, `days_to_ship`, `message_to_seller`, `buyer_username`, `buyer_cpf_id`, `recipient_address`, `item_list[]` (`item_id`, `item_name`, `item_sku`, `model_sku`, `model_quantity_purchased`, `model_discounted_price`, `item_price`, `selling_price`, `settlement_price`, `promotion_id`, …), `package_list[]`, `invoice_data`, `credit_card_number`/`payment_info` (mascarados).
- ⚠️ `total_amount` é o valor pago pelo comprador, **não** o repasse.

#### 1.5.3 Escrow / repasses — `v2.payment.get_escrow_detail`
- **GET** `/api/v2/payment/get_escrow_detail` — [doc](https://open.shopee.com/documents/v2/v2.payment.get_escrow_detail?module=95&type=1)
- Parâmetros: **`order_sn`** (obrigatório, único).
- Resposta (objeto `response`): `order_sn`, `buyer_user_name`, `return_order_sn_list[]`, e **`order_income`** com:
  - `escrow_amount` — valor esperado de repasse (a doc publica a fórmula completa; inclui comissão, taxas, frete etc.)
  - `escrow_amount_pri` — repasse em moeda primária (só CB SIP affiliate)
  - `buyer_total_amount`, `order_original_price`, `order_discounted_price`, `order_selling_price`
  - `seller_discount`, `shopee_discount`, `voucher_from_seller`
  - **`commission_fee`** (comissão Shopee), **`service_fee`** (serviços adicionais), **`seller_transaction_fee`** (taxa de transação paga pelo vendedor), **`campaign_fee`**, **`order_ams_commission_fee`**
  - frete: `buyer_paid_shipping_fee`, `actual_shipping_fee`, `estimated_shipping_fee`, `final_shipping_fee`, `shopee_shipping_rebate`, `shipping_fee_discount_from_3pl`, `reverse_shipping_fee`
  - impostos/taxas BR: `escrow_tax`, `final_escrow_product_gst`, `withholding_tax`, `withholding_vat_tax`, `icms_tax_amount`, `import_tax_amount`, `iof_tax_amount`, `sales_tax_on_lvg`
  - outros: `cost_of_goods_sold`, `seller_return_refund`, `seller_coin_cash_back`, `fbs_fee`, `pay_per_sale`, `seller_order_processing_fee`
  - `items[]`: `item_id`, `item_name`, `item_sku`, `original_price`, `seller_discount`, `shopee_discount`, `activity_type`, `activity_id`, `is_main_item`, `quantity_purchased`
- **Fórmula oficial do `escrow_amount`** (não-CB-SIP): `original_cost_of_goods_sold - original_shopee_discount + seller_return_refund + shopee_discount - voucher_from_seller - seller_coin_cash_back + buyer_paid_shipping_fee - actual_shipping_fee + shopee_shipping_rebate + shipping_fee_discount_from_3pl - reverse_shipping_fee + rsf_seller_protection_fee_claim_amount - final_return_to_seller_shipping_fee - seller_transaction_fee - service_fee - commission_fee - campaign_fee - shipping_seller_protection_fee_amount - delivery_seller_protection_fee_premium_amount - final_escrow_product_gst - order_ams_commission_fee - escrow_tax - sales_tax_on_lvg - ... - withholding_tax - ... - fbs_fee - ads_escrow_top_up_fee_or_technical_support_fee - th_import_duty - pay_per_sale`. Para CB SIP: `escrow_amount = escrow_amount_pri * exchange_rate`.

#### 1.5.4 Outros endpoints de financeiro (mesmo módulo Payment)
Nomes confirmados no menu oficial de API Reference (paths no padrão `/api/v2/payment/<nome>`):

| Endpoint | Uso | Path |
|---|---|---|
| `v2.payment.get_escrow_detail_batch` | escrow em lote | `/api/v2/payment/get_escrow_detail_batch` ⚠️ params não lidos |
| `v2.payment.get_escrow_list` | lista de escrow por período | `/api/v2/payment/get_escrow_list` ⚠️ |
| `v2.payment.get_payout_detail` | repasses (payouts) por período | `/api/v2/payment/get_payout_detail` ⚠️ |
| `v2.payment.get_payout_info` | info de payout | `/api/v2/payment/get_payout_info` ⚠️ |
| `v2.payment.get_income_detail` | detalhe de receita | `/api/v2/payment/get_income_detail` ✅ |
| `v2.payment.get_income_statement` | extrato | `/api/v2/payment/get_income_statement` ⚠️ |
| `v2.payment.get_income_overview` | visão geral | `/api/v2/payment/get_income_overview` ⚠️ |
| `v2.payment.generate_income_statement` / `generate_income_report` | geração assíncrona de relatório | ⚠️ |

✅ `get_income_detail` (lido): **GET** `/api/v2/payment/get_income_detail`; params `date_from`, `date_to` (formato `YYYY-MM-DD`), `income_status` (int: Local `1`=Released, `2`=Pending; CB `0`=To Release, `1`=Released, `2`=Pending), `cursor`, `page_size`. **A janela de datas não pode exceder 14 dias** e `date_to` deve ser > `date_from` (o range só se aplica quando `income_status = Released`).

### 1.6 Rate limits e particularidades

✅ **Limite diário por app:** existe um teto diário de chamadas por APP — erro `error_limit`: *"The total API call number made by your APP has reached the daily API call limit, please try again after 00:00 (UTC+08:00)"*. Fonte: bloco "Common Error Codes" de qualquer endpoint, ex. [get_order_list](https://open.shopee.com/documents/v2/v2.order.get_order_list?module=95&type=1)
✅ **Rate limit por frequência:** erro `error_rate_limit`: *"Too many requests. You have reached the rate limit. Please try again later."* (mesma fonte).
⚠️ NÃO CONFIRMADO: **não encontrei os números** (QPS por endpoint / cota diária em unidades) em página pública — a doc de rate limit parece ficar no Console/app detail. Não inventei valores.
⚠️ NÃO CONFIRMADO: header de resposta com quota restante (não documentado nas páginas que li).

**Particularidades que impactam o projeto:**
- Janela máxima de **15 dias** por consulta em `get_order_list` (e 14 dias em `get_income_detail`) → o coletor precisa fatiar períodos.
- `get_order_list` retorna só `order_sn`; valores exigem `get_order_detail` (1–50 SNs por chamada) e/ou `get_escrow_detail` (1 SN por chamada) → N+1 chamadas, planejar orçamento de cota.
- `timestamp` vale 5 min → não reaproveitar URL assinada em fila longa.
- Tokens por shop (ou por merchant) — modelo multi-tenant obrigatório.
- Erros de negócio vêm em HTTP 200 com `error` não vazio (ex.: `error_auth`, `error_sign`, `error_param`, `error_limit`) → **validar `error`, não só o status HTTP**.
- Escrow só faz sentido depois que o pedido entra em estágio financeiro; pedidos `UNPAID`/`CANCELLED` podem não ter valores definitivos. ⚠️ NÃO CONFIRMADO (regra exata de quando `get_escrow_detail` passa a retornar dados).

### 1.7 Exportações do Seller Center (Shopee)

❌ **não encontrado** na documentação oficial da Open Platform: não há página pública descrevendo as colunas/formato dos relatórios exportáveis do Seller Center (Pedidos / Repasses / Taxas).
⚠️ NÃO CONFIRMADO (e deliberadamente não afirmado): existência de exportação CSV/XLSX, nomes de colunas e periodicidade. As páginas do Seller Education Hub por país existem (`https://seller.shopee.com.br/edu`), mas os artigos são SPA/atrás de login e não consegui abrir conteúdo verificável.
**Recomendação:** tratar a exportação do Seller Center como *fallback manual* e obter os mesmos dados via API (`get_order_detail` + `get_escrow_detail`), que são documentados.

---

## 2. TikTok Shop Partner Center (Open API)

### 2.1 Como criar a app

✅ Fonte: [Create your App](https://partner.tiktokshop.com/docv2/page/create-your-app).

Fluxo oficial: **Partner Center → App & Service → Create app & service**:
1. Escolher **Public app** (listado no App and Service Store, exige review) ou **Custom app** (link privado de autorização).
2. Escolher **Service category** (ex.: *Connector* — ERP/OMS/WMS/3PL) e nome.
3. Escolher **Market** e **Seller type** (Local × Cross-border) — *"Treat Market and Seller type as creation-time choices. They may not be editable after app creation"*.
4. Ligar **Enable API**.
5. Configurar **Redirect URL** e **Webhook URL**.
6. Create.

✅ **Onde ficam App Key / App Secret:** `Partner Center → App & Service → (sua app) → App credentials / Basic information`.
- **App Key** = identificador público; usado em token e nas chamadas assinadas.
- **App Secret** = chave privada; usada para assinar e para o token exchange; *"Store only on the server side"*.
- **Service ID** = identificador do "OAuth client"; é o que vai no link de autorização do seller.

✅ **Requisitos:** conta de desenvolvedor no Partner Center com onboarding concluído (status/tipo de developer definem o caminho de review); para *Full Function* dev shop, dados de business/KYC válidos. ⚠️ NÃO CONFIRMADO: exigência de CNPJ especificamente (o doc fala em "business / KYC information" de forma genérica).

✅ **Sandbox = "Development Shops"** — Fonte: [Seller Center development shops](https://partner.tiktokshop.com/docv2/page/seller-center-development-shops).
- Caminho: **Partner Center Console → Development Kits → Development Shops → Manage accounts → Create test account**.
- **Core Function Account:** produtos, pedidos, fulfillment, cancelamento, devolução; **não** cobre finance/settlement.
- **Full Function Account:** fluxo completo (checkout real com valores baixos, finance, settlements, customer service). Exige business/KYC.
- ⚠️ NÃO CONFIRMADO: **host de sandbox dedicado**. A doc descreve "development shops" (contas de teste) e não publica uma base URL sandbox distinta; `open-api-sandbox.tiktokglobalshop.com` **não resolveu** no teste. Assumir que o sandbox usa os mesmos hosts com tokens de dev shop — **testar**.

### 2.2 URLs base

✅ Fonte: [Create your App → "Authorization domains and token exchange"](https://partner.tiktokshop.com/docv2/page/create-your-app) e [Authorization overview](https://partner.tiktokshop.com/docv2/page/authorization).

| Finalidade | US | Resto do mundo (ROW) |
|---|---|---|
| Partner Center / docs | `https://partner.us.tiktokshop.com` | `https://partner.tiktokshop.com` |
| Autorização de **seller** | `https://services.us.tiktokshop.com/open/authorize` | `https://services.tiktokshop.com/open/authorize` |
| Autorização de **partner** (TAP) | `https://partner.us.tiktokshop.com/open/authorize` | `https://partner.tiktokshop.com/open/authorize` |
| Autorização de **creator** | `https://shop.tiktok.com/alliance/creator/auth` | idem |
| Token (get) | `https://auth.tiktok-shops.com/api/v2/token/get` | idem |
| Token (refresh) | `https://auth.tiktok-shops.com/api/v2/token/refresh` | idem |
| OpenAPI (recursos) | `https://open-api.tiktokglobalshop.com` | idem |

✅ `https://open-api.tiktokglobalshop.com` também consta como `servers[0]` do spec gerado da doc.
⚠️ A doc alerta: *"Do not mix authorization entry domains, token domains, and OpenAPI resource domains."*

### 2.3 Algoritmo EXATO de assinatura (sign)

✅ Fonte: [Sign your API request](https://partner.tiktokshop.com/docv2/page/sign-your-api-request) + [Common parameters](https://partner.tiktokshop.com/docv2/page/common-parameters).

**Algoritmo (passo a passo, como na doc e nos samples oficiais Go/Java/Node/Python):**

1. Pegar **todos os query params** da requisição.
2. **Excluir** `sign` **e** `access_token` (o `access_token` não entra na assinatura; em 202309+ ele vai no header `x-tts-access-token`).
3. **Ordenar as chaves alfabeticamente** (ASCII/lexicográfico).
4. Concatenar no formato `{key}{value}` (sem `=`, sem `&`), na ordem ordenada.
5. **Prefixar o path** da requisição: `input = path + concat(...)`. O path é o caminho do endpoint (ex.: `/order/202309/orders/search`), sem host e sem query.
6. Se o `Content-Type` **não** for `multipart/form-data`, **anexar o body cru** ao final (`input += body`). No caso JSON, o body é o JSON exato que será enviado (mesma string, mesma serialização).
7. **Envolver com o app_secret**: `signInput = app_secret + input + app_secret`.
8. `sign = HMAC-SHA256(key=app_secret, msg=signInput)` em **hex minúsculo**.

Pseudocódigo oficial (Go):
```go
keys := params except "sign" and "access_token"
sort(keys)
input := ""
for k in keys { input += k + params[k] }
input = path + input
if contentType != "multipart/form-data" { input += body }
input = secret + input + secret
sign = hex(hmac_sha256(secret, input))
```

**Onde vai cada coisa:**
- Query: `app_key`, `sign`, `timestamp` (+ params do endpoint, ex.: `page_size`, `shop_cipher`).
- Header: `x-tts-access-token: {access_token}` (202309+) e `content-type: application/json`.
- ⚠️ **Não existe header `x-tts-signature`** na documentação atual: o `sign` vai **sempre na query string**. Código de terceiros que usa `x-tts-signature` é legado — não seguir.
- `timestamp`: Unix em **segundos** (10 dígitos, não milissegundos). Válido em `[agora-5min, agora+30s]`; inválido → erro `36009004`.

Exemplo de request:
```
POST https://open-api.tiktokglobalshop.com/order/202309/orders/search?app_key={k}&page_size=50&shop_cipher={c}&sign={s}&timestamp={ts}
x-tts-access-token: {access_token}
content-type: application/json

{"create_time_ge": 1735689600, "create_time_lt": 1735776000}
```
⚠️ NÃO CONFIRMADO: se o `shop_cipher` entra no sign quando está no **body** em vez da query. A doc dos endpoints diz "Depends on endpoint... If the field is part of the signed request parameters for the endpoint, include it when generating sign". Regra prática: assinar **exatamente** os params que estão na query + o body.

### 2.4 Fluxo OAuth completo

✅ Fonte: [Authorization overview](https://partner.tiktokshop.com/docv2/page/authorization).

**(a) Link de autorização (seller):**
```
https://services.tiktokshop.com/open/authorize?service_id={service_id}&state={state}
```
(US: `https://services.us.tiktokshop.com/open/authorize?service_id=...`)
- `service_id` vem da app no Partner Center.
- `state` é recomendado (CSRF).
- Creator: `https://shop.tiktok.com/alliance/creator/auth?app_key={app_key}&state={state}`.
- Partner/TAP: `https://partner.tiktokshop.com/open/authorize?service_id={service_id}`.

**(b) Callback:** `{redirect_url}?code={auth_code}&state={state}`. Se o usuário recusar: `code=null&error=auth_denied`.
- `auth_code` expira em **30 minutos**, uso único.

**(c) Troca por token:** **GET** `https://auth.tiktok-shops.com/api/v2/token/get`
| Param | Obrig. | Valor |
|---|---|---|
| `app_key` | sim | |
| `app_secret` | sim | |
| `auth_code` | sim | code do callback |
| `grant_type` | sim | **`authorized_code`** (não é `authorization_code`; a doc insiste nisso) |

Resposta (`code=0` em sucesso):
```
data.access_token, data.access_token_expire_in (Unix ts; default 7 dias),
data.refresh_token, data.refresh_token_expire_in (Unix ts; = duração da autorização concedida),
data.open_id, data.seller_name, data.seller_base_region, data.user_type, data.granted_scopes[]
```
`user_type`: `0` Seller · `1` Creator · `2` Partner (legacy) · `3` Partner/TAP · `4`/`5` Global Selling seller.

**(d) Refresh:** **GET** `https://auth.tiktok-shops.com/api/v2/token/refresh`
params: `app_key`, `app_secret`, `refresh_token`, `grant_type=refresh_token`. Mesma shape de resposta.

**(e) Validades (✅):** access_token **7 dias** (default); refresh_token expira junto com a autorização concedida; auth_code 30 min.

### 2.5 Endpoints principais

✅ Todos com página oficial lida:

#### 2.5.1 Pedidos — busca
**POST** `/order/202309/orders/search` — [doc](https://partner.tiktokshop.com/docv2/page/get-order-list-202309)
- Escopo: `seller.order.info` ou `seller.fs.order&fufillment.management`.
- Query: `app_key`, `sign`, `timestamp`, `page_size` (**1–100**, default 20), `page_token`, `sort_field` (`create_time`|`update_time`), `sort_order` (`ASC`|`DESC`), **`shop_cipher`** (obrigatório).
- Body (JSON): `order_status` (`UNPAID`, `ON_HOLD`, `AWAITING_SHIPMENT`, `PARTIALLY_SHIPPING`, `AWAITING_COLLECTION`, `IN_TRANSIT`, `DELIVERED`, `COMPLETED`, `CANCELLED`), `create_time_ge`/`create_time_lt`, `update_time_ge`/`update_time_lt` (Unix s, intervalo semiaberto), `page_size`, `page_token`, `sort_field`, `sort_order`, e filtros extras (buyer_user_id, delivery_option_type, etc.).
- Resposta: `data.next_page_token`, `data.total_count`, `data.orders[]` (`id`, `status`, `create_time`, `update_time`, `buyer_message`, `cancellation_initiator`, `shipping_provider`, `shipping_provider_id`, `packages`, `user_id` ...).
- ⚠️ Não há indicação de janela máxima obrigatória (diferente da Shopee); a doc sugere usar incremental por `update_time`.

#### 2.5.2 Pedidos — detalhe
**GET** `/order/202507/orders?ids={id1,id2,...}` — [doc](https://partner.tiktokshop.com/docv2/page/get-order-detail-202507)
- Query: `ids` (**máx. 50**, CSV), `shop_cipher`; header `x-tts-access-token`.
- Resposta: `data.orders[]` com `id`, `status`, `user_id`, `create_time`, `rts_time`, `paid_time`, `cancellation_initiator`, `shipping_provider`, `payment{}`, `line_items[]`, `packages[]`, `recipient_address`, etc.
- Bloco `payment` (exemplo oficial): `currency`, `sub_total`, `shipping_fee`, `seller_discount`, `platform_discount`, `payment_platform_discount`, `payment_discount_service_fee`, `total_amount`, `original_total_product_price`.
- ⚠️ Versões anteriores: `/order/202309/orders/{order_id}` (Get Order Detail 202309). A referência atual aponta `202507`; confirmar qual versão sua app usa.

#### 2.5.3 Financeiro / settlements
**GET** `/finance/202309/statements` — [doc](https://partner.tiktokshop.com/docv2/page/get-statements-202309)
- Escopo: `seller.finance.info`.
- Query: `shop_cipher`, `statement_time_ge`, `statement_time_lt` (Unix s; intervalo semiaberto; default `lt = now`, `ge = earliest`), `payment_status` (`PAID`|`FAILED`|`PROCESSING`), `page_size` (1–100, default 20), `page_token`, `sort_field` (**só `statement_time`**), `sort_order` (`ASC` default).
- Datas: statements são gerados **diariamente às 00:00 UTC** e cobrem as transações do dia anterior. Dados disponíveis só a partir de **2023-07-01**.
- Resposta `data.statements[]`: `id`, `statement_time`, `settlement_amount`, `currency`, `revenue_amount`, `fee_amount`, `adjustment_amount`, `payment_status`, `payment_id`, `net_sales_amount`, `shipping_cost_amount`, `payment_time`.

Outros endpoints financeiros ✅ (paths confirmados na doc oficial + spec gerado):
| Endpoint | Método/Path | Uso |
|---|---|---|
| Get Statement Transactions | `GET /finance/202501/statements/{statement_id}/statement_transactions` | transações de um statement |
| Get Order Statement Transactions | `GET /finance/202501/orders/{order_id}/statement_transactions` | transações de um pedido (útil p/ conciliar pedido↔repasse) |
| Get Unsettled Transactions | `GET /finance/202507/orders/unsettled` | pedidos ainda não liquidados |
| Get Payments (202605) | `GET /finance/202605/payments` | pagamentos |
| Get Withdrawals / financial transactions | `GET /finance/202309/withdrawals` | saques |

#### 2.5.4 Produtos
| Endpoint | Método/Path |
|---|---|
| Get Product | `GET /product/202309/products/{product_id}` |
| Create Product | `POST /product/202309/products` |
| Update price | `POST /product/202309/products/{product_id}/prices/update` |
| Update inventory | `POST /product/202309/products/{product_id}/inventory/update` |
| Inventory search | `POST /product/202309/inventory/search` |
| Activate/Deactivate | `POST /product/202309/products/activate`, `/deactivate` |
| Get Categories | `GET /product/202309/categories` |

⚠️ NÃO CONFIRMADO: o path de **busca** de produtos (`/product/202309/products/search`) não aparece na lista que extraí do spec gerado; a doc oficial do endpoint não foi aberta. Tratar como "verificar".

### 2.6 Rate limits e particularidades

✅ Fonte: [Rate limits](https://partner.tiktokshop.com/docv2/page/rate-limits).
- Modelo **dinâmico de QPS**: a capacidade efetiva depende de nº de shops autorizadas, tipo de endpoint, carga da plataforma e proteções.
- **Não existe API pública para consultar a cota.**
- **Unidade mínima de isolamento:** `App ID × Authorized Shop`.
- Sinais de throttling: **HTTP 429** e/ou **código de negócio `36009002`**.
- **503 ≠ 429**: 503 é indisponibilidade, retry curto.
- Baseline sugerido (não garantido): heavy write/analytics 0,2–1 req/s; standard write 1–3; standard read 3–10; lightweight read/batch 5–20.
- Recomendação oficial: usar **batch endpoints** (contam 1 chamada por request), fila + limiter por app/shop/endpoint, backoff exponencial com **jitter**, cache de dados frios, idempotência em writes.

⚠️ NÃO CONFIRMADO: valores por endpoint (a doc diz que a página do endpoint, se publicar limite, prevalece — mas as páginas de `orders/search` e `statements` que li **não** publicam número).

**Particularidades:**
- Duas camadas de domínio (`auth.tiktok-shops.com` para token × `open-api.tiktokglobalshop.com` para dados) e domínios de autorização por mercado.
- `shop_cipher` (e não `shop_id`) identifica a loja; vem da autorização/`Get Authorized Shops`.
- Versão na URL (`202309`, `202501`, `202507`, `202605`…) — diferentes endpoints usam versões diferentes; não uniformizar.
- `timestamp` em segundos, janela curta (−5 min/+30 s).
- Respostas sempre com `code` (0 = sucesso) — validar `code`, não só HTTP.

### 2.7 Exportações do Seller Center (TikTok Shop)

❌ **não encontrado** documentação oficial descrevendo colunas/formato dos exports do Seller Center (Orders export, Statements/Settlement download).
⚠️ NÃO CONFIRMADO: formato (CSV/XLSX), nomes de colunas, limites de linhas e período máximo. Há páginas de "Finance(Non-us)" e "Finance guide (US only)", mas são guias de **parceiros** (CAP/TAP), não do Seller Center do vendedor.
**Recomendação:** usar `statements` + `statement_transactions` como fonte de liquidação e `orders/search` + `order detail` como fonte de pedidos; export do Seller Center apenas para conferência manual.

---

## 3. O que já dá para implementar sem credenciais × o que precisa de sandbox

| Item | Sem credenciais (já implementável) | Precisa testar no sandbox |
|---|---|---|
| Montagem da string base / assinatura Shopee (`partner_id+path+timestamp+access_token+shop_id`, HMAC-SHA256 hex) | ✅ Sim — algoritmo 100% documentado e com samples oficiais (Python incluso) | Validar contra a API (só o `sign` correto passa); confirmar comportamento do `sign` no link de auth |
| Montagem do `sign` TikTok (excluir `sign`/`access_token`, ordenar chaves, path+`k+v`, body JSON, wrap com app_secret, HMAC hex) | ✅ Sim — doc + samples oficiais em 4 linguagens | Confirmar tratamento de `shop_cipher` no body, body serializado exatamente como enviado, e se `content-type` influencia |
| Cliente HTTP com `partner_id/timestamp/sign` na query (Shopee) | ✅ Sim | Confirmar que POST aceita params na query + JSON no body |
| Cliente HTTP com `app_key/sign/timestamp` + header `x-tts-access-token` (TikTok) | ✅ Sim | Confirmar 202309+ e endpoints legados |
| Construção dos links de autorização (Shopee `/auth`, TikTok `/open/authorize`) | ✅ Sim (params documentados) | Validar `redirect_uri`/domínio cadastrado e o `state` |
| Fluxo de callback + troca de code (`/api/v2/auth/token/get`, `/api/v2/token/get`) | ✅ Parcial — request documentado | Precisa de app + loja autorizada (sandbox) para ver resposta real |
| Refresh automático (4 h Shopee / 7 d TikTok) | ✅ Sim (lógica) | Testar rotação de refresh_token de uso único (Shopee) e `grant_type=refresh_token` |
| Modelo multi-tenant (token por shop/merchant/shop_cipher) | ✅ Sim | Testar com 2+ lojas (main account Shopee / multi-shop TikTok) |
| Coleta de pedidos com janela de 15 dias (Shopee) e paginação por cursor | ✅ Sim | Validar `next_cursor`/`more` e erro `order.order_list_invalid_time` |
| Coleta de pedidos TikTok (`orders/search` + `orders?ids=`) | ✅ Sim (paths/params) | Validar `page_token`, `shop_cipher` e versão 202507 |
| Escrow/repasses Shopee (`get_escrow_detail`: commission/service/transaction fee) | ✅ Sim (campos e fórmula documentados) | Confirmar quando o escrow passa a existir e se `escrow_amount` bate com o Seller Center |
| Liquidação TikTok (`statements`, `statement_transactions`, `unsettled`) | ✅ Parcial (campos do statement documentados) | Confirmar `fee_amount`, `adjustment_amount`, `settlement_amount` vs. extrato real; testar `payment_status` |
| Rate limiting / backoff | ✅ Sim (erros `error_limit`/`error_rate_limit`; 429/36009002) | Descobrir QPS real por endpoint (não publicado) |
| Exportações do Seller Center (Shopee e TikTok) | ❌ Não — sem doc oficial de colunas/formato | Conferir manualmente na UI (fora de escopo de API) |

---

## 4. Fontes oficiais consultadas

**Shopee Open Platform**
- https://open.shopee.com/developer-guide/16 — API calls (domínios, tipos de API, assinatura)
- https://open.shopee.com/developer-guide/17 — Introduction (quem pode acessar)
- https://open.shopee.com/developer-guide/20 — Authorization and Authentication (OAuth, tokens, sign)
- https://open.shopee.com/documents/v2/v2.order.get_order_list?module=95&type=1
- https://open.shopee.com/documents/v2/v2.order.get_order_detail?module=95&type=1
- https://open.shopee.com/documents/v2/v2.payment.get_escrow_detail?module=95&type=1
- https://open.shopee.com/documents/v2/v2.payment.get_income_detail?module=95&type=1
- `https://open.shopee.com/api/v1/config/host` — lista oficial de hosts/sandbox

**TikTok Shop Partner Center**
- https://partner.tiktokshop.com/docv2/page/create-your-app — criação de app, credenciais, domínios
- https://partner.tiktokshop.com/docv2/page/authorization — OAuth, token get/refresh, user_type
- https://partner.tiktokshop.com/docv2/page/sign-your-api-request — algoritmo de assinatura
- https://partner.tiktokshop.com/docv2/page/common-parameters — parâmetros comuns e headers
- https://partner.tiktokshop.com/docv2/page/rate-limits — rate limits
- https://partner.tiktokshop.com/docv2/page/seller-center-development-shops — sandbox/development shops
- https://partner.tiktokshop.com/docv2/page/get-order-list-202309
- https://partner.tiktokshop.com/docv2/page/get-order-detail-202507
- https://partner.tiktokshop.com/docv2/page/get-statements-202309

**Fonte secundária (usada só para mapear paths/ids de doc, nunca como verdade)**
- `isaackogan/TikTok-Shop-Api-SDKs` — OpenAPI 3.1 gerado da doc oficial (usado para localizar as páginas oficiais por slug; os dados finais foram conferidos nas páginas oficiais acima).
