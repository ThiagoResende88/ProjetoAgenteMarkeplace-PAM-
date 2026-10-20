# Recorte — Orquestrador, atendimento e orçamento

**Marcas:** 3D Print Franca e Mocozim  
**Versão:** 1.3 — 20/10/2026  
**Relação com o restante:** este recorte é o que seguimos agora. Os documentos em `docs/etapas/` permanecem como estão.

As duas marcas imprimem em 3D. A diferença entre elas é o público e o catálogo: a 3D Print Franca fala com um público geral; a Mocozim, com quem compra artigo de tabacaria. O caminho da conversa é o mesmo. O canal primário é o WhatsApp.

Há duas filas. A esteira de produção é o que a pessoa operadora vai imprimir. A esteira de atendimento é o que ela precisa decidir antes que o agente atendimento volte a falar com a pessoa cliente.

## 1. Pessoas e agentes

| Nome | Quem é | O que faz neste recorte |
|---|---|---|
| Pessoa cliente | Humano que escreve no WhatsApp | Pede, pergunta, confirma ou reclama |
| Pessoa operadora | Humano da operação | Preenche o formulário da ficha de atendimento e produz o que entrou na esteira de produção |
| Agente orquestrador | Agente | Direciona a mensagem ao agente adequado. Não abre ficha e não responde no WhatsApp |
| Agente atendimento | Agente | Conduz a conversa no WhatsApp, abre a ficha de atendimento e, quando a regra manda, abre a ficha de produção |
| Agente de orçamento | Agente | Grava o orçamento de item fora do catálogo. Não abre ficha e não escreve no WhatsApp |

O agente orquestrador não conversa com a pessoa cliente. Quem escreve no WhatsApp é o agente atendimento.

## 2. Motivo da mensagem

Motivo é o que a pessoa cliente quer com aquela mensagem. O agente orquestrador usa o motivo só para escolher o agente e encaminhar a mensagem, com a marca e o histórico. Quem conduz o caminho, responde e abre ficha é o agente atendimento. Uma conversa muda de motivo se a pessoa cliente mudar de assunto; o orquestrador então encaminha de novo.

| Motivo | Exemplo | Quem conduz | Efeito |
|---|---|---|---|
| Pedido de catálogo | "Quero dois porta-incenso" | Agente atendimento, até a confirmação | Na confirmação da pessoa cliente, o agente atendimento abre a ficha na esteira de produção, em **Recebido** |
| Pedido fora do catálogo | "Faz igual a esta foto?" | Agente atendimento coleta; agente de orçamento orça; pessoa operadora confere | O orçamento entra na esteira de atendimento. A ficha de produção só nasce depois que a pessoa cliente aceita o valor devolvido pelo formulário |
| Dúvida de produto | "Qual o tamanho do tubete?" | Agente atendimento | Não abre ficha. Sem dado na ficha do catálogo, abre ficha de atendimento |
| Estado do pedido | "O de ontem já foi impresso?" | Agente atendimento | Lê a esteira de produção. Sem pedido correspondente, abre ficha de atendimento |
| Reclamação | "Veio errado" | Pessoa operadora, pela esteira de atendimento | O agente atendimento abre a ficha e espera o formulário para responder |
| Fora de produto | "Quero revender" ou "precisam emitir nota?" | Pessoa operadora, pela esteira de atendimento | O agente atendimento abre a ficha e espera o formulário para responder |

Dúvida de produto não é pedido. Perguntar a medida, o material ou a cor não cria ficha de produção.

## 3. De onde vem a resposta

| Pergunta | Fonte | Quando abre ficha de atendimento |
|---|---|---|
| O que é o produto, medida, material, variação, preço de catálogo | Ficha do catálogo da marca | O campo necessário está ausente na ficha |
| Este item existe para compra direta? | Catálogo da marca | O item não está no catálogo: segue o caminho de orçamento |
| Em que pé está o pedido? | Esteira de produção | Não há pedido que corresponda à pessoa cliente e à marca |
| Em que pé está a reclamação, o orçamento ou outro assunto com a pessoa operadora? | Esteira de atendimento | A ficha desse assunto já está **Aberta** |

O agente atendimento responde com o que essa fonte trouxer. Campo ausente permanece ausente. Ele não completa medida, prazo, estoque, resistência ou preço que a pessoa operadora ainda não tenha devolvido no formulário.

## 4. Esteira de atendimento

A esteira de atendimento é a fila da pessoa operadora. Cada item é uma ficha de atendimento, aberta pelo agente atendimento. O agente orquestrador não abre essa ficha.

Entram aqui os casos em que a resposta à pessoa cliente depende de uma decisão humana:

1. Reclamação, troca ou defeito.
2. Assunto que não é sobre produto nem sobre pedido já feito, como revenda ou nota fiscal.
3. Dúvida de produto cuja ficha de catálogo não tem o dado pedido.
4. Estado de pedido sem registro correspondente na esteira de produção.
5. Orçamento de item fora do catálogo, pronto para a pessoa operadora conferir.
6. Mensagem cujo motivo não fica claro para o agente atendimento.

A ficha guarda: marca, telefone, motivo, resumo, dados já coletados, dados ausentes, última mensagem da pessoa cliente e, no orçamento, a proposta do agente de orçamento.

| Estado | Significado |
|---|---|
| Aberto | Está com a pessoa operadora. O agente atendimento não responde nesse assunto, salvo para dizer que ele aguarda essa conferência |
| Resolvido | A pessoa operadora preencheu o formulário. O conteúdo volta ao agente atendimento |

Ao marcar **Resolvido**, o formulário devolve ao agente atendimento o que ele usa para compor a mensagem no WhatsApp. A resposta sai desse formulário. O agente não acrescenta preço, prazo ou decisão que o formulário não traga.

O formulário tem, em qualquer motivo, o texto de orientação à resposta e a decisão tomada. No orçamento, traz também o valor conferido, o que esse valor inclui e se a proposta está confirmada, ajustada ou recusada.

Pedido de catálogo confirmado pela pessoa cliente não passa por esta esteira. O agente atendimento abre direto a ficha de produção.

## 5. Esteira de produção

A esteira de produção é a fila do que a pessoa operadora vai produzir. Ela também é a fonte do estado do pedido. Sem esse registro, o agente atendimento não tem como responder "cadê meu pedido".

Cada ficha guarda:

- marca;
- identificação da pessoa cliente no WhatsApp;
- origem: **catálogo** ou **orçamento**;
- o que produzir;
- quantidade;
- data de entrada;
- estado;
- no caso de orçamento, o vínculo com a ficha de atendimento já **Resolvida**.

| Estado | Significado para a pessoa cliente |
|---|---|
| Recebido | O pedido entrou na fila |
| Em produção | A peça está sendo impressa ou acabada |
| Pronto | A peça está pronta e ainda não saiu |
| Enviado | A peça foi despachada ou entregue para envio |
| Cancelado | O pedido não será produzido |

A pessoa operadora atualiza o estado depois que a ficha existe. O agente atendimento abre a ficha e, quando o assunto é estado do pedido, só lê.

A ficha de produção nasce **Recebida** em dois momentos:

- a pessoa cliente confirma um item do catálogo;
- a pessoa cliente aceita o orçamento que o agente atendimento informou a partir do formulário **Resolvido**.

Confirmação da pessoa operadora no formulário ainda não produz. Recusa da pessoa cliente também não abre ficha de produção.

## 6. Caminho do orçamento

1. O agente atendimento reúne foto ou referência e os dados que a pessoa cliente informar.
2. O agente orquestrador encaminha esse material ao agente de orçamento.
3. O agente de orçamento devolve a proposta: o que será produzido, quantidade, medidas, material e cor quando informados, valor quando a regra de custo da marca cobre o caso, o que o valor inclui e o que permanece ausente.
4. O agente atendimento abre a ficha na esteira de atendimento, em **Aberto**, com essa proposta.
5. A pessoa operadora confere e preenche o formulário. A ficha passa a **Resolvido**.
6. O agente atendimento compõe a mensagem com o formulário e pergunta à pessoa cliente se ela concorda com o orçamento.
7. Se a pessoa cliente concorda, o agente atendimento abre a ficha na esteira de produção, em **Recebido**.
8. Se a pessoa cliente não concorda, ou se o formulário recusou a proposta, não nasce ficha de produção.

Sem foto ou referência, o agente de orçamento não inventa a proposta. Devolve o material ao agente atendimento para pedir isso à pessoa cliente. Sem regra de custo que cubra o caso, a proposta segue sem valor e o formulário da pessoa operadora é quem define o preço.

## 7. Contratos

### Agente orquestrador

**Entrada:** mensagem do WhatsApp, marca e histórico da conversa.

**Saída:** o agente para quem a mensagem foi encaminhada.

**Regras:**

- encaminha pedido, dúvida de produto, estado do pedido, reclamação e assunto fora de produto ao agente atendimento;
- encaminha ao agente de orçamento o material que o agente atendimento reuniu para item fora do catálogo, quando chega a hora de orçar;
- não abre ficha de atendimento, não abre ficha de produção, não altera estado e não escreve no WhatsApp.

### Agente atendimento

**Entrada:** mensagem encaminhada pelo agente orquestrador, marca, histórico, ficha dos produtos citados, fichas de atendimento daquela pessoa cliente e, no motivo estado do pedido, as fichas de produção dela.

**Saída:** resposta para o WhatsApp, ficha de atendimento quando a decisão é humana, ou ficha de produção quando a pessoa cliente confirmou catálogo ou aceitou orçamento já conferido.

**Regras:**

- abre a ficha de produção de catálogo só depois da confirmação explícita da pessoa cliente, já em **Recebido**, sem passar pela esteira de atendimento;
- abre a ficha de atendimento quando o caso é um dos da seção 4, em **Aberto**, e para de resolver aquele assunto até o estado **Resolvido**;
- com a ficha **Resolvida**, compõe a resposta só com o formulário e envia à pessoa cliente;
- no orçamento, a mensagem pede o aceite da pessoa cliente; a ficha de produção nasce somente com esse aceite;
- dúvida de produto com dado na ficha do catálogo e estado de pedido encontrado na esteira de produção não abrem ficha de atendimento nem ficha de produção.

### Agente de orçamento

**Entrada:** material reunido pelo agente atendimento, com marca, foto ou referência, quantidade, dados já coletados e a regra de custo da marca.

**Saída:** a proposta de orçamento, ou a devolução do material por falta de foto ou referência.

**Regras:**

- descreve a peça a partir do que a pessoa cliente enviou;
- preenche valor só quando a regra de custo da marca cobre o caso;
- deixa o valor ausente quando a regra não cobre, para o formulário da pessoa operadora definir;
- não abre ficha, não confirma o orçamento, não fala com a pessoa cliente e não cria ficha de produção.

## 8. Fora deste recorte

- Gestão de estoque, campanha e desenvolvimento de produto além da ficha que o atendimento consulta.
- Resolver reclamação, negociar revenda ou emitir nota no lugar da pessoa operadora.
- Publicar anúncio em marketplace.
