# Etapa 2 — Fábrica de anúncios

**Código:** E2  
**Título:** Fábrica de anúncios  
**Projeto:** Agente Gerente de E-commerce  
**Fonte:** [abertura de projeto](../abertura_de_projeto.md), seções 4, 7 e 11  
**Versão:** 1.0 — 20/10/2026  
**Depende de:** [etapa 1](etapa-1-mvp-do-gerente.md) e da decisão de rascunho da [etapa 0](etapa-0-validacao-tecnica.md).  
**Desbloqueia:** comparação antes/depois da etapa 3 e, mais adiante, publicação assistida da etapa 5.

## 1. Objetivo

A partir de uma ficha confiável, produzir título, descrição, atributos, palavras-chave, FAQs e imagens por canal, passar por revisor, gravar rascunho comparável ao anúncio atual e só marcar como aprovado depois da revisão humana.

Publicar no marketplace fica fora desta etapa. A saída pronta para o operador é o rascunho interno e, quando a etapa 0 tiver decidido exportação manual, o pacote de campos e arquivos.

## 2. Fora de escopo

- Publicar, alterar preço ou alterar estoque no canal.
- Automação de navegador no painel do marketplace.
- Inventar medida, material, acessório, resistência, vedação ou desempenho que não esteja na ficha.
- Pesquisa ampla de mercado (etapa 3). A fábrica pode usar um concorrente ou uma métrica já gravados no SKU.

## 3. Fluxo que os requisitos cobrem

1. Operador escolhe SKU, marca e canal (Shopee ou TikTok Shop).
2. O sistema reúne a ficha: materiais, medidas, variações, fotos reais, custo, preço mínimo, estoque conhecido e restrições.
3. Se existir anúncio atual ou métrica já lida, eles entram como contexto, com origem e data.
4. Copywriter entrega o texto estruturado e a justificativa.
5. Designer entrega o conjunto de imagens do canal e o checklist.
6. Revisor aprova para a fila humana, devolve com correção ou bloqueia.
7. O rascunho guarda original e proposta.
8. Operador pede ajuste ou aprova.
9. A versão guardada registra data, responsável, motivo e o retrato das métricas anteriores, se existirem.

## 4. Requisitos funcionais

### 4.1 Entrada

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-2-01 | Ficha mínima para iniciar | Obrigatório | A fábrica só inicia para um SKU com marca, nome, descrição factual e ao menos uma foto real. Faltando item, a tarefa abre pendência nomeando o campo e não chama copywriter nem designer. |
| RF-2-02 | Canal por execução | Obrigatório | O operador escolhe um canal por execução: Shopee ou TikTok Shop. Regras de dimensão, atributo e tom daquele canal acompanham o pedido. |
| RF-2-03 | Preço sugerido dentro do mínimo | Obrigatório | Preço sugerido no rascunho sai da lista vigente escolhida para o canal e respeita o preço mínimo do SKU. Sem preço vigente, o campo de preço do rascunho fica ausente e o revisor bloqueia publicação futura desse campo. |
| RF-2-04 | Promessa só com dado confirmado | Obrigatório | Estoque, prazo e promessa técnica só entram no texto se constarem como dado confirmado da ficha ou do canal. Caso contrário o texto omite a promessa. |

### 4.2 Copywriter

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-2-05 | Texto estruturado do anúncio | Obrigatório | A saída do copywriter contém, separados: título, descrição, atributos, palavras-chave, FAQs e justificativa do que mudou em relação ao anúncio atual. |
| RF-2-06 | Atributo com frase de suporte | Obrigatório | A justificativa aponta a frase da ficha que sustenta cada atributo novo. Atributo sem frase de suporte volta para correção. |
| RF-2-07 | Variações distintas | Obrigatório | Variações do SKU (medida, cor, material) permanecem distintas no texto. O anúncio não funde duas variações num único conjunto de atributos. |
| RF-2-08 | Ajuste de trecho | Desejável | O operador pede nova versão indicando o trecho a ajustar, e o rascunho anterior permanece comparável. |

### 4.3 Designer

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-2-09 | Foto fiel e arte auxiliar | Obrigatório | O conjunto separa duas famílias: **foto fiel** (recorte, fundo, iluminação, enquadramento da foto real) e **arte auxiliar** (infográfico, imagem de contexto, peça gráfica). Cada arquivo declara a família. |
| RF-2-10 | Fidelidade da foto | Obrigatório | Foto fiel preserva material, medida aparente, acessórios incluídos e características funcionais visíveis na foto de origem. A arte auxiliar não substitui a foto fiel como imagem principal enquanto o operador não marcar essa troca. |
| RF-2-11 | Checklist da imagem | Obrigatório | Cada imagem traz o checklist do canal: dimensão exigida, margem de segurança, texto legível, identidade visual combinada e fidelidade ao produto. Item reprovado no checklist impede a imagem de seguir como pronta. |
| RF-2-12 | Verificação visual | Obrigatório | A imagem final do rascunho fica disponível para verificação visual do operador antes da aprovação. |
| RF-2-13 | Comparação com a foto de origem | Desejável | O operador compara lado a lado a foto de origem e a foto fiel gerada. |

### 4.4 Revisor

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-2-14 | Três resultados do revisor | Obrigatório | O revisor emite um de três resultados: **liberado para fila humana**, **correção solicitada** (com a lista de itens) ou **bloqueado** (com o motivo). |
| RF-2-15 | Checagem de factualidade e canal | Obrigatório | A checagem cobre: factualidade contra a ficha; promessa técnica; preço e preço mínimo; modalidade de preço usada; duplicidade de variação; direito de imagem e de marca; regra conhecida do canal. |
| RF-2-16 | Bloqueio fora da fila | Obrigatório | Resultado **bloqueado** ou **correção solicitada** não entra na fila de aprovação. O gerente devolve a pendência ao papel responsável. |
| RF-2-17 | Liberação só para a fila humana | Obrigatório | Liberação do revisor não publica e não marca o rascunho como aprovado pelo operador. |

### 4.5 Rascunho, versão e aprovação

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-2-18 | Rascunho original e proposta | Obrigatório | Toda proposta aprovada pelo revisor para a fila grava um rascunho com original (se houver anúncio lido) e proposta, campo a campo, mais o conjunto de imagens. |
| RF-2-19 | Aprovação, rejeição ou ajuste | Obrigatório | O operador aprova, rejeita ou pede ajuste. Aprovar exige confirmação explícita na interface. Rejeitar pede motivo, gravado na memória operacional. |
| RF-2-20 | Registro da versão | Obrigatório | A versão aprovada guarda: SKU, canal, número da versão, data, responsável humano, papéis que geraram, motivo da alteração e retrato das métricas anteriores quando a etapa 1 já tiver essa leitura. Métrica posterior fica reservada para a etapa 3. |
| RF-2-21 | Destino conforme a E0 | Obrigatório | O destino do rascunho aprovado segue a decisão da etapa 0 para o canal: permanecer como rascunho interno, preparar payload de rascunho de plataforma sem enviar, ou exportar campos e arquivos para lançamento manual. |
| RF-2-22 | Pacote de exportação manual | Obrigatório | Exportação manual entrega um pacote identificável (SKU, canal, versão) com textos separados e imagens nomeadas, suficiente para o operador lançar no painel sem reinterpretar o rascunho. |
| RF-2-23 | Hipótese da mudança | Desejável | O operador registra, na versão, a hipótese da mudança em uma frase. A etapa 3 usa essa frase no experimento. |

## 5. Requisitos não funcionais

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RNF-2-01 | Sem escrita externa | Obrigatório | Nenhuma chamada desta etapa escreve no marketplace ou no UpSeller. Envio de rascunho ou publicação é classe de ação desligada (RF-1-24 Interruptor de autonomia, RF-T-02 Efeito externo autorizado). |
| RNF-2-02 | Versão recuperável | Obrigatório | Imagens e textos de cada versão permanecem recuperáveis depois de uma versão nova. Apagar uma versão da interface, se existir, retira o item da fila e preserva o registro de auditoria. |
| RNF-2-03 | Arquivo em armazenamento de objetos | Obrigatório | Foto de origem e arte gerada ficam em armazenamento de objetos, referenciadas pela versão, com tipo de conteúdo e tamanho verificáveis. |
| RNF-2-04 | Rastro da afirmação | Obrigatório | O revisor e o operador conseguem ver qual frase da ficha sustenta cada afirmação do anúncio (RF-2-06 Atributo com frase de suporte). Afirmação sem suporte não chega a aprovada. |
| RNF-2-05 | Custo por papel | Obrigatório | Geração de texto e de imagem registra custo de modelo na tarefa (RNF-1-06 Custo de modelo somável), separado por papel. |
| RNF-2-06 | Versões sem sobrescrita | Obrigatório | Duas execuções para o mesmo SKU e canal não sobrescrevem a versão uma da outra. Cada execução nasce com identificador novo. |
| RNF-2-07 | Checklist repetível | Desejável | O checklist de imagem é repetível: a mesma imagem e as mesmas regras de canal produzem os mesmos itens reprovados. |
| RNF-2-08 | Anúncio em português | Obrigatório | Texto do anúncio sai em português (RNF-T-06 Português e estilo), adequado ao canal escolhido. |

## 6. Critérios de aceite

1. Um SKU completo gera rascunho de Shopee e, em outra execução, rascunho de TikTok Shop, com listas de preço distintas se o operador assim configurou.
2. SKU sem foto real ou sem descrição factual para na pendência, sem imagem gerada.
3. Uma promessa de resistência que não está na ficha é barrada pelo revisor.
4. Foto fiel e arte auxiliar aparecem em famílias diferentes, e a imagem principal continua sendo foto fiel até o operador trocar.
5. O operador aprova uma versão e recebe o pacote de exportação manual, ou o payload interno de rascunho, conforme a etapa 0. O canal externo permanece inalterado.
6. A versão guarda responsável, motivo e métricas anteriores quando essas métricas já existiam.

## 7. Insumos para a arquitetura

- Contrato de saída do copywriter, do designer e do revisor.
- Máquina de estados do rascunho: rascunho, correção, bloqueado, na fila, aprovado, rejeitado, exportado.
- Ponto único em que uma futura etapa 5 poderá enviar o payload já aprovado, sem reabrir a geração.
