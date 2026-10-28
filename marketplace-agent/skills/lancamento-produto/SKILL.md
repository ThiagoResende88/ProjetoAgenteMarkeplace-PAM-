---
name: lancamento-produto
description: Fluxo completo para lançar um produto novo nos marketplaces — ficha técnica, custo real, preço por canal, anúncio, imagens, cadastro e acompanhamento.
whenToUse: Quando o usuário disser "quero lançar um produto", "subir anúncio novo", "cadastrar na Shopee/TikTok", ou pedir o passo a passo de lançamento.
---

# Lançamento de produto (Mocozim / 3D Print Franca)

Um produto novo passa por 7 etapas. Não pule a ficha técnica e o custo: é o que
evita lançar no prejuízo.

## 1. Ficha técnica (perguntar, não inventar)

- Nome e o que é (uso principal)
- Dimensões e peso (g)
- Material (PETG/PLA), cores disponíveis
- O que vem na embalagem
- Tempo de produção por unidade (e capacidade por semana)
- Acabamento (lixa? pintura? apenas impressão?)
- Garantia e cuidados
- Público e problema que resolve

Se for produto do catálogo Mocozim (tubete, porta-isqueiro, banquinho), confirme
qual versão/medida está sendo lançada.

## 2. Custo real

Ferramenta `precificar_3d` (ou `mkt precificar`):
- peso da peça (slicer), custo do filamento por kg
- horas de impressão, custo/h da máquina (energia + desgaste + depreciação)
- taxa de falha (3–10%), acabamento, embalagem, mão de obra
- canal + frete

Nunca aceite "custo de R$ 2,50" sem checar se inclui máquina, falha, embalagem e
mão de obra. O fatiador dá peso/tempo/filamento; máquina e embalagem são por fora.

## 3. Preço por canal

Calcule para: direto/Instagram, consignação, Shopee, TikTok Shop, Mercado Livre.
Considere frete: em ticket baixo, frete grátis pode zerar a margem. Prefira kit
(2, 3, 10 un) para subir ticket.

## 4. Anúncio (texto)

Use o skill `criador-anuncios`:
- 3 títulos com contagem de caracteres
- descrição com gancho, benefícios, especificações, cuidados, garantia
- FAQ e palavras-chave
- checagem de conformidade (sem marca de terceiro, sem promessa de saúde, sem
  "patenteado/original" sem registro)
- salvar em `saidas/anuncios/<sku>-<data>.md`

## 5. Imagens

Use o skill `estudio-criativos`:
- foto real (preferida) → `gerar_criativo(sku, foto=...)`
- card com benefícios/preço → PNG/SVG em `saidas/criativos/`
- briefing com prompts para IA quando faltar foto
- checklist de imagem (fundo, resolução, primeira imagem)

## 6. Cadastro e publicação

- O agente **não publica**: gera texto/arte prontos para colar no UpSeller ou no
  painel do marketplace.
- Registre o produto/custo na base: `registrar_custo(sku, custo, preco_venda)`.
- Anote a data de publicação e a loja (Shopee/TikTok 1/TikTok 2) na conversa.

## 7. Acompanhamento

- Semana 1: `desempenho` (pedidos/receita) e revisão de título/imagem.
- Semana 2–4: `insights` e `margem_sku`; se não vender, testar preço/kit/foto.
- Registrar aprendizados no relatório do mês.

## Checklist final

- [ ] Ficha técnica completa
- [ ] Custo calculado com premissas explícitas
- [ ] Preço por canal (com frete testado)
- [ ] Título/descrição/FAQ em arquivo
- [ ] Imagem principal pronta (foto real ou card)
- [ ] Produto/custo cadastrado na base
- [ ] Publicado no UpSeller/painel e data anotada
- [ ] Métrica de acompanhamento definida
