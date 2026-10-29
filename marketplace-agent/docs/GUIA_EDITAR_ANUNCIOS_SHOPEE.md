# Editar anúncios direto na Shopee (API oficial) — viabilidade e plano

Pergunta: **"Você pode se conectar à minha conta Shopee para subir as alterações
nos anúncios diretamente?"**

Resposta curta: **sim, pelo caminho oficial (Shopee Open Platform), que é grátis** —
mas depende de você criar um app de desenvolvedor e autorizar a loja uma vez.
Não é possível hoje, sem isso, e não recomendo automação de navegador.

## Por que não dá "sem mais nada"

| Caminho | Funciona? | Problema |
|---|---|---|
| API pública anônima | ❌ | A Shopee **não tem** API pública de anúncio; a interna responde 403 |
| API oficial Open Platform | ✅ | Precisa de app + autorização da loja (OAuth) |
| UpSeller | ❌ no seu plano | API/MCP só no Profissional (~R$ 583/mês); e o MCP dele hoje só vê estoque |
| Automatizar o navegador com seu login | ⚠️ não recomendo | Viola termos, quebra com frequência e expõe sua sessão/conta |

## O que é preciso (uma vez)

1. **Conta de desenvolvedor** em <https://open.shopee.com> (Brasil: `open.shopee.com.br`).
2. Criar um **app** no Console → copiar **Partner ID** e **Partner Key**
   (comece pelo **test partner ID**, que só funciona no sandbox).
3. Cadastrar a **Redirect URL** do app (ex.: `http://localhost:8765/shopee/callback`).
4. **Autorizar a loja**: abrir o link de autorização, logar na conta e aprovar.
   O callback devolve `code` + `shop_id`; trocamos por `access_token` (4 h) e
   `refresh_token` (30 dias) — a renovação é automática.
5. Para produção (`live`), a app passa por aprovação da Shopee. No sandbox dá para
   validar todo o fluxo antes.

O código de assinatura HMAC, hosts, links e troca de token **já estão prontos** em
`src/mktagent/api/shopee.py`. Falta: armazenamento seguro do token, servidor local
de callback e as chamadas de edição.

## O que eu consigo fazer depois de autorizado

- **Ler**: lista de anúncios, detalhe (título, descrição, preço, estoque, imagens).
- **Atualizar**: título, descrição, preço, estoque e imagens do anúncio.
  Endpoints previstos (validar no sandbox):
  - `GET /api/v2/product/get_item_list`
  - `GET /api/v2/product/get_item_base_info`
  - `POST /api/v2/product/update_item`
  - `POST /api/v2/product/update_price`
  - `POST /api/v2/product/update_stock`
  - `POST /api/v2/media_space/upload_image` (upload da imagem e uso do `image_id`)
- **Fluxo seguro** (importante, porque edição errada derruba venda):
  1. o agente monta a alteração e mostra **diff** (antes → depois);
  2. você confirma na conversa;
  3. aplica e registra em log local (`saidas/edicoes/`) com os valores antigos
     para **rollback**;
  4. valida o resultado lendo o anúncio de volta.

## Regras e limites que preciso respeitar

- Título/descrição/imagem seguem as políticas da Shopee (sem marca de terceiro,
  sem promessa proibida, imagem principal dentro do padrão).
- Limite diário de chamadas por app (`error_limit`, reset 00:00 UTC+8) e rate limit;
  operações em massa precisam de fila e backoff.
- Tokens são por loja; você tem 2 contas hoje e uma 3ª em criação — o fluxo precisa
  autorizar cada loja separadamente.
- Não publico nada sem sua confirmação explícita.

## Passo a passo para começar (do seu lado, ~15 min)

1. Criar/entrar em <https://open.shopee.com> → Console → App list → criar app
   (tipo **seller**/self-developed).
2. Copiar **Partner ID** e **Partner Key** (test) e cadastrar a redirect URL.
3. Me passar os dois valores e a redirect URL por aqui ou preencher no `.env`
   (`SHOPEE_PARTNER_ID`, `SHOPEE_PARTNER_KEY`, `SHOPEE_REDIRECT_URL`).
4. Eu implemento `mkt shopee conectar` (abre o link, recebe o callback, guarda o
   token), validamos leitura no sandbox e só depois habilito edição com diff.

## Estimativa de implementação

- Conectar + ler anúncio: **1 rodada** (depois que você criar o app).
- Editar título/descrição/preço/estoque com diff e rollback: **1–2 rodadas**.
- Upload de imagens: mais **1 rodada** (validar formato/limite no sandbox).

## Alternativa imediata (sem app)

Você cola o texto no painel/UpSeller — eu preparo título, descrição, FAQ e as
imagens das variações. É o que já está funcionando hoje.
