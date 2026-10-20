# Requisitos — Orquestrador, atendimento e orçamento

**Fonte:** [recorte](orquestrador-e-atendimento.md)  
**Marcas:** 3D Print Franca e Mocozim  
**Versão:** 1.0 — 20/10/2026

Cada requisito tem código, título, prioridade e descrição. O título é o nome curto. A descrição é o que se verifica.

- **Obrigatório:** o recorte não fecha sem isso.
- **Desejável:** entra se não atrasar o obrigatório.

## 1. Requisitos funcionais

### 1.1 Canal e marcas

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-REC-01 | Mensagem de WhatsApp | Obrigatório | O sistema recebe a mensagem da pessoa cliente no WhatsApp e o agente atendimento envia a resposta por esse mesmo canal. |
| RF-REC-02 | Marca pelo número | Obrigatório | O número que recebeu a mensagem define a marca, 3D Print Franca ou Mocozim, e com ela o catálogo e a regra de custo. |
| RF-REC-03 | Foto e referência | Obrigatório | Foto, arquivo ou referência recebidos no WhatsApp ficam ligados à conversa e seguem com o material do orçamento e com a ficha que os usar. |

### 1.2 Agente orquestrador

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-REC-04 | Encaminhar pelo motivo | Obrigatório | O agente orquestrador reconhece o motivo, encaminha pedido, dúvida, estado do pedido, reclamação e assunto fora de produto ao agente atendimento, e entrega marca e histórico. |
| RF-REC-05 | Hora de orçar | Obrigatório | Quando o agente atendimento reuniu foto ou referência de item fora do catálogo, o agente orquestrador encaminha esse material ao agente de orçamento. |
| RF-REC-06 | Orquestrador só encaminha | Obrigatório | O agente orquestrador não abre ficha de atendimento, não abre ficha de produção, não altera estado e não escreve no WhatsApp. |
| RF-REC-07 | Assunto novo | Obrigatório | Se a pessoa cliente muda de assunto, o agente orquestrador encaminha de novo conforme o motivo novo. |

### 1.3 Respostas do agente atendimento

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-REC-08 | Dúvida com a ficha | Obrigatório | Dúvida de medida, material, variação ou preço de item do catálogo é respondida só com a ficha da marca. Isso não abre ficha de atendimento nem ficha de produção. |
| RF-REC-09 | Dúvida sem dado | Obrigatório | Se o campo pedido não está na ficha do catálogo, o agente atendimento abre ficha de atendimento e não completa o campo. |
| RF-REC-10 | Estado na esteira de produção | Obrigatório | Pergunta sobre pedido já feito é respondida com as fichas de produção daquela pessoa cliente e daquela marca. |
| RF-REC-11 | Estado sem pedido | Obrigatório | Sem ficha de produção correspondente, o agente atendimento abre ficha de atendimento. |
| RF-REC-12 | Aguardando conferência | Obrigatório | Com ficha de atendimento **Aberta** naquele assunto, o agente atendimento só informa que a conferência está com a pessoa operadora. |
| RF-REC-13 | Pedido de catálogo | Obrigatório | Confirmação explícita de item do catálogo abre ficha de produção em **Recebido**, sem passar pela esteira de atendimento. |
| RF-REC-14 | Reclamação | Obrigatório | Reclamação, troca ou defeito abre ficha de atendimento. O agente atendimento não resolve o caso. |
| RF-REC-15 | Fora de produto | Obrigatório | Revenda, nota fiscal e qualquer assunto que não seja produto nem pedido já feito abrem ficha de atendimento. O agente atendimento não resolve o caso. |
| RF-REC-16 | Motivo pouco claro | Obrigatório | Motivo que o agente atendimento não classifica abre ficha de atendimento. |

### 1.4 Esteira de atendimento

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-REC-17 | Quem abre a ficha | Obrigatório | Só o agente atendimento abre ficha de atendimento. Ela guarda marca, telefone, motivo, resumo, dados coletados, dados ausentes e a última mensagem. No orçamento, guarda também a proposta. |
| RF-REC-18 | Aberto e Resolvido | Obrigatório | A ficha nasce **Aberta**. Passa a **Resolvido** quando a pessoa operadora salva o formulário. |
| RF-REC-19 | Fila da pessoa operadora | Obrigatório | A pessoa operadora vê as fichas **Abertas**, abre uma e preenche o formulário. |
| RF-REC-20 | Formulário | Obrigatório | Todo formulário tem a decisão tomada e o texto de orientação da resposta. No orçamento, tem também o valor conferido, o que o valor inclui e se a proposta foi confirmada, ajustada ou recusada. |
| RF-REC-21 | Devolução ao agente | Obrigatório | O estado **Resolvido** devolve o formulário ao agente atendimento. |
| RF-REC-22 | Resposta composta do formulário | Obrigatório | A mensagem seguinte à pessoa cliente, nesse assunto, usa só o formulário. Preço, prazo e decisão que não estejam nele não entram na mensagem. |

### 1.5 Esteira de produção

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-REC-23 | Ficha de produção | Obrigatório | A ficha guarda marca, identificação da pessoa cliente no WhatsApp, origem **catálogo** ou **orçamento**, o que produzir, quantidade, data de entrada e estado. Origem orçamento guarda o vínculo com a ficha de atendimento **Resolvida**. |
| RF-REC-24 | Quando a ficha nasce | Obrigatório | A ficha nasce **Recebido** só quando a pessoa cliente confirma item de catálogo, ou quando aceita orçamento já informado a partir de formulário **Resolvido**. |
| RF-REC-25 | Conferência não produz | Obrigatório | Salvar o formulário, recusar a proposta nele, ou a pessoa cliente não aceitar o orçamento não cria ficha de produção. |
| RF-REC-26 | Estados de produção | Obrigatório | Os estados são **Recebido**, **Em produção**, **Pronto**, **Enviado** e **Cancelado**. A pessoa operadora é quem muda o estado depois da abertura. |
| RF-REC-27 | Leitura do estado | Obrigatório | No motivo estado do pedido, o agente atendimento lê a ficha e não altera o estado. |

### 1.6 Orçamento

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-REC-28 | Coleta para orçar | Obrigatório | O agente atendimento reúne foto ou referência, quantidade e os dados que a pessoa cliente informar antes do encaminhamento ao agente de orçamento. |
| RF-REC-29 | Proposta | Obrigatório | O agente de orçamento devolve o que será produzido, a quantidade, medidas, material e cor quando informados, o valor quando a regra de custo cobre o caso, o que o valor inclui e o que está ausente. |
| RF-REC-30 | Sem foto | Obrigatório | Sem foto ou referência, o agente de orçamento devolve o material ao agente atendimento, que pede isso à pessoa cliente. Não há proposta nem ficha de atendimento de orçamento. |
| RF-REC-31 | Sem regra de custo | Obrigatório | Sem regra de custo que cubra o caso, a proposta segue com valor ausente. O preço sai do formulário da pessoa operadora. |
| RF-REC-32 | Proposta na esteira de atendimento | Obrigatório | Com a proposta em mãos, o agente atendimento abre ficha de atendimento **Aberta**. |
| RF-REC-33 | Pedido de aceite | Obrigatório | Depois do **Resolvido**, o agente atendimento informa o valor do formulário e pergunta se a pessoa cliente concorda. |
| RF-REC-34 | Aceite vira produção | Obrigatório | O aceite explícito abre a ficha de produção em **Recebido**, com origem **orçamento**. |
| RF-REC-35 | Limite do agente de orçamento | Obrigatório | O agente de orçamento não abre ficha, não confirma proposta, não escreve no WhatsApp e não cria ficha de produção. |

### 1.7 Catálogo, custo e conversa

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-REC-36 | Catálogo da marca | Obrigatório | Cada marca tem fichas de produto consultáveis, com os campos usados na resposta: nome, medida, material, variação e preço, cada um presente ou ausente. |
| RF-REC-37 | Regra de custo | Obrigatório | Cada marca tem uma regra de custo que o agente de orçamento consulta para decidir se preenche valor. |
| RF-REC-38 | Histórico no encaminhamento | Obrigatório | O encaminhamento leva o histórico da conversa daquela pessoa cliente naquela marca. |

### 1.8 Desejáveis

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-REC-39 | Filtro por marca | Desejável | A pessoa operadora filtra cada esteira por marca. |
| RF-REC-40 | As duas filas na mesma visão | Desejável | A pessoa operadora vê a esteira de atendimento e a esteira de produção sem trocar de sistema. |

## 2. Requisitos não funcionais

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RNF-REC-01 | Segredos fora do repositório | Obrigatório | Token do WhatsApp, chave de modelo e segredo de banco ficam em variável de ambiente ou cofre. O repositório e o log exibido não mostram esses valores. |
| RNF-REC-02 | Mensagem idempotente | Obrigatório | A mesma entrega do WhatsApp não abre duas fichas nem dispara duas respostas. |
| RNF-REC-03 | Marca isolada | Obrigatório | Catálogo, regra de custo, conversa e fichas de uma marca não entram na resposta da outra. |
| RNF-REC-04 | Rastro da ficha | Obrigatório | Abertura e cada mudança de estado guardam quem fez, agente ou pessoa operadora, e quando. |
| RNF-REC-05 | Arquivo recuperável | Obrigatório | Foto e referência permanecem recuperáveis a partir da conversa e da ficha que as citam. |
| RNF-REC-06 | Resposta em português | Obrigatório | Mensagem à pessoa cliente sai em português. |
| RNF-REC-07 | Acesso da pessoa operadora | Obrigatório | Ver esteira, preencher formulário e mudar estado de produção exigem autenticação da pessoa operadora. |
| RNF-REC-08 | Ensaio separado | Obrigatório | Conversa e ficha de ensaio não entram nas esteiras da operação. |
| RNF-REC-09 | Log do encaminhamento | Obrigatório | Cada encaminhamento registra motivo, agente de destino, resultado, duração e, quando o modelo informar, tokens e custo. |
| RNF-REC-10 | Histórico persistido | Obrigatório | Mensagens da pessoa cliente e respostas enviadas permanecem consultáveis por conversa. |
| RNF-REC-11 | Falha do WhatsApp | Obrigatório | Falha ao receber ou enviar deixa a pendência visível. Não marca ficha como **Resolvido** nem pedido como **Recebido**. |
| RNF-REC-12 | Orçamento só depois do formulário | Obrigatório | Valor de item fora do catálogo não é enviado à pessoa cliente antes da ficha de atendimento correspondente estar **Resolvida**. |

## 3. Fora destes requisitos

- Gestão de estoque, campanha e desenvolvimento de produto além da consulta à ficha de catálogo.
- O agente resolver reclamação, negociar revenda ou emitir nota.
- Publicar anúncio em marketplace.
