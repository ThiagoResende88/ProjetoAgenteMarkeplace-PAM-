# TODO — recorte orquestrador, atendimento e orçamento

Fonte: [requisitos](docs/recortes/requisitos-orquestrador-atendimento-orcamento.md) e [recorte](docs/recortes/orquestrador-e-atendimento.md).

## Analisar

- [ ] Escolher o provedor de WhatsApp e o número de cada marca (RF-REC-01, RF-REC-02)
- [ ] Definir a origem do catálogo inicial da 3D Print Franca e da Mocozim, com nome, medida, material, variação e preço (RF-REC-36)
- [ ] Definir a regra de custo de cada marca: quando o agente de orçamento preenche valor e quando deixa ausente (RF-REC-37, RF-REC-31)
- [ ] Fechar o formulário da pessoa operadora: decisão, texto de orientação e, no orçamento, valor, inclusão e confirmada, ajustada ou recusada (RF-REC-20)
- [ ] Listar exemplos reais de mensagem para cada motivo, um de cada marca, para servir de ensaio

## Arquitetura

- [ ] Desenhar os componentes deste recorte: WhatsApp, agente orquestrador, agente atendimento, agente de orçamento, catálogo, esteira de atendimento e esteira de produção
- [ ] Modelar conversa, ficha de catálogo, regra de custo, ficha de atendimento, formulário e ficha de produção, com o vínculo do orçamento aceito (RF-REC-23)
- [ ] Fixar no desenho que só o agente atendimento abre ficha e escreve no WhatsApp (RF-REC-06, RF-REC-35)
- [ ] Definir como o estado Resolvido devolve o formulário ao agente atendimento (RF-REC-21)

## Desenvolver

- [ ] Receber e enviar mensagem de WhatsApp, incluindo foto e referência (RF-REC-01, RF-REC-03)
- [ ] Identificar a marca pelo número e carregar o catálogo e a regra de custo dela (RF-REC-02, RNF-REC-03)
- [ ] Implementar o agente orquestrador: motivo, encaminhamento e novo encaminhamento quando o assunto muda (RF-REC-04, RF-REC-05, RF-REC-07)
- [ ] Implementar o agente atendimento para dúvida de produto e para estado do pedido (RF-REC-08, RF-REC-10, RF-REC-12)
- [ ] Abrir ficha de atendimento nos casos humanos: reclamação, fora de produto, dúvida sem dado, pedido não encontrado, motivo pouco claro e orçamento (RF-REC-09, RF-REC-11, RF-REC-14, RF-REC-15, RF-REC-16, RF-REC-17)
- [ ] Tela da pessoa operadora para a fila Aberta e o formulário (RF-REC-19, RF-REC-20)
- [ ] Ao resolver, devolver o formulário e enviar a resposta composta só com ele (RF-REC-21, RF-REC-22, RNF-REC-12)
- [ ] Implementar o agente de orçamento, com devolução sem foto e valor ausente sem regra de custo (RF-REC-28 a RF-REC-32, RF-REC-35)
- [ ] Pedir o aceite da pessoa cliente e só então abrir a ficha de produção do orçamento (RF-REC-33, RF-REC-34, RF-REC-25)
- [ ] Abrir ficha de produção de catálogo na confirmação, sem esteira de atendimento (RF-REC-13, RF-REC-24)
- [ ] Permitir que a pessoa operadora atualize Recebido, Em produção, Pronto, Enviado e Cancelado (RF-REC-26, RF-REC-27)
- [ ] Garantir que a mesma mensagem de WhatsApp não duplique ficha nem resposta (RNF-REC-02)

## Infraestrutura

- [ ] Definir onde o sistema roda
- [ ] Subir banco para conversa, catálogo, regra de custo e as duas esteiras
- [ ] Guardar foto e referência em armazenamento recuperável pela ficha (RNF-REC-05)
- [ ] Colocar token de WhatsApp, chave de modelo e segredo de banco fora do repositório (RNF-REC-01)
- [ ] Separar o ambiente de ensaio das esteiras da operação (RNF-REC-08)

## DevOps

- [ ] Empacotar a aplicação e as dependências para subir num comando só
- [ ] Documentar as variáveis de ambiente, sem valores secretos
- [ ] Garantir que o ensaio e a operação não compartilhem a mesma base (RNF-REC-08)

## Observabilidade

- [ ] Registrar log de execução: erro, falha de envio e falha de recebimento, sem marcar ficha indevidamente (RNF-REC-11)
- [ ] Registrar cada encaminhamento com motivo, agente de destino, duração, tokens e custo quando existirem (RNF-REC-09)
- [ ] Persistir o histórico de mensagens e respostas por conversa (RNF-REC-10, RF-REC-38)
- [ ] Gravar quem abriu cada ficha e quem mudou cada estado, com o instante (RNF-REC-04)
