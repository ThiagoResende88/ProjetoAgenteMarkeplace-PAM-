# Etapa 4 — Atendimento e qualificação

**Código:** E4  
**Título:** Atendimento e qualificação  
**Projeto:** Agente Gerente de E-commerce  
**Fonte:** [abertura de projeto](../abertura_de_projeto.md), seções 5, 7 e 11  
**Versão:** 1.0 — 20/10/2026  
**Depende de:** [etapa 1](etapa-1-mvp-do-gerente.md), em especial catálogo, listas de preço, custo e regras. A escolha do canal de mensagem é premissa desta etapa, não da etapa 0.  
**Desbloqueia:** resposta assistida a lead e, na etapa 5, o eventual envio automático de mensagens de baixo risco.

## 1. Objetivo

Receber um contato, identificar a intenção, completar os dados que faltam, consultar catálogo e custo, devolver uma resposta preliminar ou um pré-orçamento condicionado e transferir ao operador quando a conversa cruzar uma condição de handoff.

O cliente fala com o canal autorizado. O operador acompanha a ficha do lead, a resposta sugerida e o motivo de cada transferência.

## 2. Fora de escopo

- Negociar desconto fora da regra, prometer prazo de produção, fechar pedido ou cobrar.
- Atender por um canal ainda não escolhido e sem política de dados aprovada pelo operador.
- Usar conteúdo de anúncio não aprovado como afirmação ao cliente.
- Resposta plena sem revisão humana nos casos listados em RF-4-14. O envio automático de respostas rotineiras, se existir, espera a etapa 5.

## 3. Fluxo

`Nova mensagem → Identificar intenção → Coletar requisitos → Consultar catálogo e custos → Pré-análise → Resposta preliminar → Sinal de interesse → Transferir ao humano → Registrar desfecho`

## 4. Decisão que abre a implementação

Antes do conector de mensagem, o operador registra:

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-4-01 | Escolha do canal de mensagem | Obrigatório | Decisão do canal: WhatsApp Business Platform (API oficial) ou outro provedor autorizado, com o nome do provedor e o número usado pela marca. |
| RF-4-02 | Política de dados e handoff | Obrigatório | Política escrita de consentimento, janela de atendimento, conteúdo mínimo do registro da conversa, prazo de retenção e caminho de transferência para o humano. A política fica versionada como regra (RF-1-17 Regra versionada). |

Sem RF-4-01 e RF-4-02, o restante da etapa funciona apenas com conversa colada manualmente pelo operador, para ensaio do fluxo.

## 5. Requisitos funcionais

### 5.1 Conversa e intenção

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-4-03 | Conversa ligada à marca | Obrigatório | Cada mensagem recebida abre ou continua uma conversa de um lead, ligada a uma marca (3D Print Franca ou Mocozim). |
| RF-4-04 | Classificação da intenção | Obrigatório | O atendimento classifica a intenção em pelo menos: dúvida de catálogo, pedido de orçamento de item de catálogo, pedido personalizado, acompanhamento de pedido já feito, assunto fora da operação, intenção indeterminada. |
| RF-4-05 | Pergunta quando a intenção é indeterminada | Obrigatório | Intenção indeterminada gera pergunta objetiva do dado que falta, em vez de orçamento. |
| RF-4-06 | Revisão antes do envio | Obrigatório | O operador vê a conversa inteira, a intenção corrente e a resposta sugerida antes de qualquer envio ao cliente nesta etapa. |

### 5.2 Coleta

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-4-07 | Ficha do lead | Obrigatório | A ficha do lead guarda, quando o cliente informar, e deixa ausente quando não informar: produto ou serviço, quantidade, medidas, material ou cor, personalização, prazo desejado, cidade, necessidade de nota fiscal, referência visual ou arquivo 3D. |
| RF-4-08 | Pergunta só do que falta | Obrigatório | O atendimento pergunta só o que ainda falta para o tipo de intenção. Dado já informado não é pedido de novo. |
| RF-4-09 | Anexo sem virar especificação | Obrigatório | Arquivo ou referência visual fica anexado à ficha, com nome e instante, sem ser tratado como especificação técnica confirmada até o operador marcar. |

### 5.3 Catálogo e pré-orçamento

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-4-10 | Preço e estoque de catálogo | Obrigatório | Para item de catálogo identificado, a resposta usa preço da modalidade vigente adequada ao tipo de cliente (consumidor ou revenda) e estoque confirmado do canal ou do cadastro. Modalidade ambígua gera pergunta, não mistura de listas (RF-T-05 Listas de preço separadas). |
| RF-4-11 | Promessa só com confirmação | Obrigatório | Estoque, prazo, resistência, vedação e desempenho só aparecem na resposta se forem dados confirmados. Sem confirmação, a resposta diz que aquele ponto depende de verificação humana. |
| RF-4-12 | Estimativa condicionada | Obrigatório | Personalizado ou item fora do catálogo produz **estimativa condicionada**: valor ou faixa só quando os requisitos mínimos e a regra de custo aprovada estiverem presentes. A resposta lista as condições e o que falta. |
| RF-4-13 | Sem preço quando falta regra de custo | Obrigatório | Sem regra de custo aplicável, a ficha não leva número de preço. A resposta informa que o orçamento será fechado pelo operador e dispara handoff. |

### 5.4 Handoff

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-4-14 | Condições de handoff | Obrigatório | A conversa vai para o operador, com envio automático bloqueado, quando ocorrer ao menos um destes casos: intenção concreta de compra; pedido de negociação especial; personalização complexa; dúvida técnica ou jurídica; risco de prazo; custo sem regra confiável; divergência entre o que o cliente descreve e o cadastro. |
| RF-4-15 | Pacote entregue ao operador | Obrigatório | O handoff entrega ao operador: resumo, dados coletados, dados ausentes, intenção, pré-análise ou motivo de não orçar, trecho relevante da conversa e a condição de RF-4-14 Condições de handoff que disparou. |
| RF-4-16 | Desfecho do lead | Obrigatório | O operador registra o desfecho: em atendimento humano, orçamento enviado, ganho, perdido ou sem resposta. Desfecho ganho não cria pedido no ERP nesta etapa. |
| RF-4-17 | Edição da resposta como feedback | Obrigatório | Resposta sugerida que o operador editar grava a versão enviada e a diferença em relação à sugestão, como feedback (RF-1-18 Memória operacional). |

### 5.5 Ensaio sem canal

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-4-18 | Ensaio com mensagem colada | Obrigatório | O operador cola uma mensagem de ensaio e percorre classificação, coleta, pré-orçamento e handoff com os mesmos registros de uma mensagem de canal. O ensaio fica marcado como ensaio. |

## 6. Requisitos não funcionais

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RNF-4-01 | Retenção da conversa | Obrigatório | Mensagem de cliente, telefone e anexos seguem a retenção de RF-4-02 Política de dados e handoff. Acabando o prazo, o conteúdo da conversa deixa de ser exibido e o registro de auditoria mantém apenas identificador, marca, datas, intenção e desfecho. |
| RNF-4-02 | Credencial do provedor | Obrigatório | Credencial do provedor de mensagem segue RNF-T-01 Segredos fora do repositório. Log de conversa exibido não inclui token do provedor. |
| RNF-4-03 | Envio só pelo operador | Obrigatório | Nesta etapa o sistema não envia mensagem ao cliente por conta própria. Envio é ação do operador a partir da resposta sugerida ou de um texto que ele escreveu. |
| RNF-4-04 | Falha do provedor visível | Obrigatório | Falha do provedor deixa a mensagem recebida pendente, visível ao operador, sem classificar a conversa como concluída. |
| RNF-4-05 | Evento idempotente | Obrigatório | Duas entregas do mesmo evento do provedor não abrem dois leads nem duas respostas sugeridas para a mesma mensagem. |
| RNF-4-06 | Mensagem em português | Obrigatório | Texto ao cliente sai em português (RNF-T-06 Português e estilo), no estilo vigente da marca. |
| RNF-4-07 | Origem do preço na resposta | Obrigatório | Pré-orçamento e resposta citam a origem do preço (lista e vigência) e marcam estimativa como estimativa (RF-T-01 Natureza do dado, RF-T-06 Origem do número). |
| RNF-4-08 | Fila filtrável | Desejável | O operador filtra a fila de handoff por marca e por condição de transferência. |

## 7. Critérios de aceite

1. A política de canal e de dados está versionada antes do primeiro contato real.
2. Uma mensagem de catálogo com modalidade clara devolve preço vigente e omite prazo se o prazo não estiver confirmado.
3. Uma mensagem personalizada sem medida suficiente não devolve valor; devolve a lista do que falta.
4. Um pedido de desconto especial gera handoff com resumo, dados e a condição “negociação especial”.
5. O operador envia a resposta a partir da fila; o registro mostra o texto sugerido, o texto enviado e o desfecho.
6. Reentrega do mesmo evento de mensagem não duplica o lead.
7. Um ensaio colado manualmente percorre o mesmo fluxo e aparece marcado como ensaio.

## 8. Insumos para a arquitetura

- Fronteira entre o conector do provedor e a ficha do lead.
- Idempotência do evento de mensagem (RNF-4-05).
- Onde a resposta sugerida espera o operador, para a etapa 5 poder trocar esse ponto por uma política de envio por classe de intenção.
