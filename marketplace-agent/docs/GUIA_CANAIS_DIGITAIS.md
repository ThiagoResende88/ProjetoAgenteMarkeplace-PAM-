# Canais digitais: Google Drive, Google Sheets, WhatsApp e Telegram

Status em 25/10/2026 e o que já funciona.

## 1. Google Sheets (planilhas) — **já funciona**

As três planilhas compartilhadas por link público puderam ser lidas pelo agente
via exportação CSV:

```
https://docs.google.com/spreadsheets/d/<ID>/export?format=csv
```

Já usei isso para ler custos, pedidos Mocozim e plano de ação. Para virar rotina:

1. **Melhor caminho (estável):** mantenha uma aba "canônica" por assunto com o
   cabeçalho na **primeira linha** e sem linhas de resumo antes
   (ex.: `pedido;status;data_pedido;sku;produto;quantidade;preco_unitario`).
2. O agente baixa o CSV e importa com `mkt importar <tipo> arquivo.csv`.
3. Se o link deixar de ser público, é preciso OAuth (ver item 2).

> Observação: planilhas com blocos de resumo no topo confundem a detecção de
> cabeçalho. Ou exporte XLSX com uma aba limpa, ou peça para eu criar um
> importador específico para o layout de vocês.

## 2. Google Drive (mídias) — **dois caminhos**

### Caminho A (recomendado agora): pasta local sincronizada
1. Instale o **Google Drive para Desktop** e sincronize a pasta de fotos dos produtos.
2. Rode o agente com acesso a essa pasta (ele já tem ferramenta de arquivos).
3. Gere o criativo com foto real:
   ```sh
   ./bin/mkt criativo CUBO-INFINITO \
     --beneficio "Impressão 3D PETG" --beneficio "Acabamento premium" \
     --foto "/home/voce/Google Drive/3DPrintFranca/fotos/cubo-1.jpg"
   ```
   O card recorta a foto (cover), arredonda os cantos e monta a arte.
4. No chat: *"gera o criativo do CUBO-INFINITO usando a foto .../cubo-1.jpg"*.

Vantagem: zero configuração de API, funciona offline, você vê/organiza as fotos.

### Caminho B (automação): Drive API com OAuth
Permite listar pastas e baixar imagens por comando:
1. Criar projeto no Google Cloud, ativar **Drive API**.
2. Criar credenciais OAuth (Desktop) e baixar `client_secret.json`.
3. Na primeira execução, autorizar no navegador (escopo `drive.readonly`).
4. Eu implemento um script `scripts/drive_baixar.py --pasta <id> --saida fotos/`.

⚠️ Precisa de você criar o projeto e autorizar; os tokens ficam locais. Posso
implementar quando você disser que o Drive está organizado por produto/pasta.

## 3. Telegram — **fácil, recomendo para o dia a dia**

Bot próprio, gratuito, sem aprovação de empresa. Serve para:
- receber o **resumo do dia** (receita, alertas, contas);
- receber alerta quando algo importante aparecer;
- o agente enviar mensagens por ferramenta (`enviar_telegram`).

### Configurar (5 minutos)
1. No Telegram, fale com **@BotFather** → `/newbot` → escolha nome → copie o **token**.
2. Fale com **@userinfobot** → copie seu **chat_id**.
3. No `.env` do projeto:
   ```env
   TELEGRAM_BOT_TOKEN=123456:ABC...
   TELEGRAM_CHAT_ID=123456789
   ```
4. Teste:
   ```sh
   ./bin/mkt telegram status
   ./bin/mkt telegram testar
   ./bin/mkt telegram digest
   ```
5. Para envio automático diário: agendar no DSH (ferramenta `schedule`) ou no
   `cron` do sistema: `0 8 * * * cd .../marketplace-agent && ./bin/mkt telegram digest`.

## 4. WhatsApp — **possível, mas mais burocrático**

Só com a **WhatsApp Business Platform (Cloud API)** oficial:
- conta Meta Business verificada;
- número de telefone dedicado (não serve número pessoal comum);
- app no Meta for Developers com produto WhatsApp;
- token permanente e `phone_number_id`;
- (para receber mensagens) webhook público com HTTPS.

O projeto já tem o envio pronto (`mkt whatsapp status/testar/digest`), mas sem as
credenciais acima não há como testar. Alternativas sem API oficial (bibliotecas
não oficiais) têm risco de bloqueio do número — **não recomendo** para o negócio.

## 5. Controles do agente vs. canais

| Necessidade | Hoje | Próximo passo |
|---|---|---|
| Ler planilhas públicas | ✅ via CSV | padronizar abas canônicas |
| Fotos nos criativos | ✅ caminho local (`--foto`) | Drive API se quiser automatizar |
| Avisos no celular | ✅ Telegram (após token) | agendar digest diário |
| Conversar pelo WhatsApp | ❌ | só com Cloud API oficial |
| Receber comando por Telegram | ❌ | bot de entrada (polling) — dá para fazer |

## Segurança

- Tokens só no `.env` (fora do git) e nunca no banco.
- Se um token vazar: revogue no BotFather/Meta e gere outro.
- O agente não publica nada em marketplace; só prepara arquivos e mensagens.
