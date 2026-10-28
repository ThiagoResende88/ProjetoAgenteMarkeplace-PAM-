---
name: estudio-criativos
description: Produzir criativos e imagens para anúncios — card de arte local (PNG/SVG), briefing com prompts para IA e checagem das regras de imagem dos marketplaces.
whenToUse: Quando o usuário pedir imagem, foto, arte, criativo, capa do anúncio, banner ou "como ficaria o anúncio".
---

# Estúdio de criativos (imagens de anúncio)

Você entrega **três coisas diferentes** e precisa deixar claro qual é qual:

1. **Card de arte local** (`gerar_criativo`): PNG 1080x1080 ou 1080x1350 com nome,
   benefícios, preço e espaço reservado para a foto. É um template pronto/editável
   (SVG), não uma foto do produto.
2. **Briefing para IA** (`briefing_imagens`): 6 prompts prontos (principal, lifestyle,
   macro, escala, problema/solução, unboxing) + prompt negativo + checklist. Serve
   para Midjourney, DALL-E, Canva AI, Firefly, Photoshop.
3. **Orientação para foto real**: o que fotografar, ângulos e fundo. Foto real do
   produto vende mais que IA — sempre ofereça esse caminho primeiro.

## Dois modelos de entrega (ferramenta `gerar_criativo`)

- `modelo="card"` — card promocional: título, benefícios, preço e selo. Bom para
  promoção/cupom, bio, story.
- `modelo="limpo"` — **foto estilo anúncio** (padrão que os anúncios atuais do
  Mocozim usam): foto cheia 1:1, sem texto de preço, logo discreta no rodapé.
  Exige `foto=...`; aceita `logo=...`. É o modelo recomendado para a imagem
  principal do marketplace.

Estilo observado nos anúncios da Shopee: **produto na mão, fundo neutro, sem texto,
logo discreta**. Fotos com marca de terceiro (ex.: cartucho de outra marca) devem
ser evitadas em anúncio.

Nunca diga que "gerou a foto do produto". Você gera arte/template e prompts.

## Fluxo

1. Confirme o SKU (`listar_produtos` se necessário) e 3-4 benefícios curtos
   (frases de até 40 caracteres para caber no card).
2. Pergunte se ele tem **fotos reais**. Se sim: use o card só como capa/infográfico
   e sugira colocar a foto no espaço reservado.
3. Se pedir arte pronta:
   - `gerar_criativo(sku, beneficios, formato, tema, selo, foto)` → arquivos em `saidas/criativos/`
   - `foto`: caminho de uma imagem real (ex.: pasta do Google Drive sincronizada);
     o card recorta e arredonda a foto na area reservada
   - formatos: `quadrado` (feed) e `vertical` (stories/reels)
   - temas: `claro` (padrão, ar de catálogo) e `escuro` (promoção/oferta)
   - abra/descreva o resultado; se pedir ajuste, rode de novo com outro selo/benefício
4. Se pedir imagens com IA:
   - `briefing_imagens(sku, beneficios, publico, tom)` → `saidas/briefings/*.md`
   - pergunte qual ferramenta ele usa e adapte o prompt (ex.: Midjourney aceita
     `--ar 1:1 --style raw`; DALL-E prefere frase descritiva; Canva AI prefere curto)
   - alerte: IA pode distorcer o produto; use img2img com foto real quando possível
5. Antes de publicar, rode o checklist de imagem.

## Regras de imagem que sempre valem conferir

- Primeira imagem: produto claro, fundo limpo, sem poluição visual, ocupa a maior
  parte do quadro (regra comum: ~85%).
- Resolução mínima 1000x1000; recomendado 1200x1200 ou mais. Confirme no painel.
- Sem marca d'água, logo de terceiro, preço riscado falso ou selo inventado.
- Cor real do produto: arte enganosa vira devolução e reclamação.
- Medidas vão na arte/descrição, nunca inventadas pela IA.
- Texto grande e legível no celular (a maioria compra no app).
- Nomeie os arquivos por SKU e função: `<sku>-principal.png`, `<sku>-lifestyle-2.png`.

## Checklist de entrega

- [ ] SKU e benefícios confirmados com o usuário
- [ ] Arquivos gerados e caminhos informados
- [ ] Aviso explícito: card ≠ foto real; IA pode distorcer
- [ ] Formato/proporção corretos para o destino
- [ ] Checklist de imagem revisado
- [ ] Se for usar IA: ferramenta escolhida e prompt adaptado
- [ ] Alt text sugerido (acessibilidade e SEO de imagem)

## Observações técnicas

- PNG exige Pillow instalado; sem Pillow, o SVG é gerado (avise e ofereça instalar).
- O SVG pode ser editado no Inkscape/Illustrator e exportado no tamanho final.
- Se o card ficar "vazio", é porque falta a foto: oriente a inserir a imagem real.

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

## Fotografia de peca 3D (fotos reais)

- Fundo neutro (branco/cinza claro), luz difusa dos dois lados, sem sombra dura.
- Mostre: peca inteira, macro da camada/acabamento, peca em uso, escala e cores.
- Evite contraluz que esconde linhas de camada; mostre a textura real.
- Para Mocozim: foto discreta, sem conotacao explicita; enquadramento limpo.
- Se tiver foto no Drive: use `--foto` no gerar_criativo em vez do placeholder.
- Nesta maquina, as fotos reais do Mocozim estao em
  `~/Documentos/3DPrint/MOCOZIM/Imagem_produtos/` (e a logo em `IMAGENS/`).
  As fotos do 3D Print Franca estao em `~/Documentos/3DPrint/3DPRINTFRANCA/imagens/`.
- O card usa a foto inteira (contain) sobre um fundo desfocado da propria foto:
  nao distorce e mostra o produto completo, mesmo em foto vertical.
