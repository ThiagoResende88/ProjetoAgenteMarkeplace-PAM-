---
name: precificacao-3d
description: Precificar peças de impressão 3D (Mocozim, cubos, chaveiros, troféus, réplicas) com custo real de filamento, máquina, falha, acabamento, embalagem, taxas do canal e frete — e comparar cenários.
whenToUse: Quando o usuário perguntar "quanto custa?", "quanto posso cobrar?", "vale a pena nesse preço?", "qual a margem?", "frete grátis fecha?", ou for definir preço de lançamento, kit ou consignação.
---

# Precificação 3D (3D Print Franca / Mocozim)

Objetivo: **custo real e preço que sobrevive a taxas, frete e falha** — não margem
bruta de planilha.

## Ferramenta

`precificar_3d` (ou `./bin/mkt precificar`) recebe:
- `peso_g` — gramas de filamento da peça (total; peça + suporte + purge)
- `custo_filamento_kg` — R$/kg pago no filamento (PETG/PLA)
- `horas_impressao`, `custo_maquina_hora` — energia + desgaste + manutenção + depreciação
- `taxa_falha_pct` — 3% a 10% é realista (peças grandes/altas falham mais)
- `acabamento`, `embalagem`, `mao_de_obra` — opcionais
- `canal` (`shopee`, `tiktok`, `mercadolivre`, `instagram`, `consignacao`, `direto`, `outros`)
- `taxa_canal_pct`, `taxa_fixa_por_item`, `frete_pago_pelo_vendedor`
- `margem_alvo_pct`, `preco_venda` (para comparar), `unidades` (kit)

Devolve custo detalhado, preço de empate, preço para a margem alvo, preço sugerido
e cenários.

## Fórmulas (para explicar ao usuário)

```
material   = peso_g/1000 × custo_filamento_kg
máquina    = horas × custo_máquina_hora
custo_dir  = material + máquina + acabamento + embalagem + mão_de_obra
perda      = custo_dir × taxa_falha
custo_total = custo_dir + perda
preço_empate  = (custo_total + taxa_fixa + frete) / (1 − taxa_canal)
preço_alvo    = (custo_total + taxa_fixa + frete) / (1 − taxa_canal − margem_alvo)
```

## Rotina

1. **Levante os números reais** (não inventar): peso, tempo de fatiamento/impressão,
   preço do kg do filamento, custo/hora da máquina, frete médio, taxa do canal.
   Se o usuário não souber, rode com estimativas e marque "premissas".
2. Rode a ferramenta com **2-3 cenários** (empate, margem alvo, preço praticado).
3. Explique em uma linha o ponto crítico. Exemplos:
   - *"Com frete grátis de R$ 20, a R$ 9,90 você perde R$ 16,28 por peça."*
   - *"Sem frete, o preço para 30% de margem é R$ 8,51 (sugerido R$ 8,90)."*
4. Para kit, use `unidades=10` (multiplica material e tempo) e recalcule taxas.
5. Salve a conclusão: se o preço for aprovado, cadastre com `registrar_custo`
   (custo unitário real) e registre o preço de venda.

## Cautelas deste negócio

- **Taxa do canal é configurável**: Shopee/TikTok/ML variam por categoria/plano.
  Nunca apresente margem como garantida se a taxa real não foi confirmada.
- **Custo de máquina** não é zero: energia + manutenção + depreciação. Se o usuário
  não souber, use R$ 1,50–3,00/h e diga que é premissa.
- **Falha** não é zero: 3-10%. Peça grande (troféu) pode chegar a 15%.
- **Frete grátis em ticket baixo** é a armadilha principal; prefira kit, consignação
  ou venda direta.
- **Mão de obra** (acabamento, embalagem manual, atendimento) é o custo mais esquecido.
- **Não misture** o custo estimado histórico (ex.: R$ 2,50 do tubete) com o calculado
  sem avisar a diferença.
- **Mocozim (regra atual, 25/10/2026)**: custo por peça = **filamento + embalagem**
  (tubete: 8,45 g a R$ 90/kg = R$ 0,76 + embalagem R$ 0,80 = **R$ 1,56**).
  O tubete **não tem acabamento**; **máquina/manutenção vão para a despesa mensal**
  (planilha de custos), não para o custo unitário. Falha de 5% é opcional (+~R$ 0,08).
  Preços de referência: direto R$ 15, consignação R$ 11, kit 10 un R$ 95,
  lançamento R$ 9,90. Sempre recalcular com taxa/frete do canal.

## Saída esperada na conversa

1. Custo total e composição (em reais e % do preço).
2. Preço de empate e preço para a margem alvo.
3. Comparação do preço atual com esses números.
4. Premissas usadas + o que precisa ser confirmado.
5. Recomendação objetiva (subir preço, kit, canal direto, não lançar).
