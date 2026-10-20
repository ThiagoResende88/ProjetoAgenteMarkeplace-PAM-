# Etapa 5 — Automação controlada

**Código:** E5  
**Título:** Automação controlada  
**Projeto:** Agente Gerente de E-commerce  
**Fonte:** [abertura de projeto](../abertura_de_projeto.md), seções 10 e 11  
**Versão:** 1.0 — 20/10/2026  
**Depende de:** veredito **confirmada** da [etapa 0](etapa-0-validacao-tecnica.md) para a operação de escrita, fluxo estável da [etapa 2](etapa-2-fabrica-de-anuncios.md) e/ou da [etapa 4](etapa-4-atendimento.md), e uma política explícita do operador para aquela operação.  
**Desbloqueia:** efeito externo pontual, com limite, log e reversão. Não desbloqueia autonomia geral.

## 1. Objetivo

Ligar, uma a uma, operações de escrita que já tenham sido feitas com aprovação humana vezes suficientes. Cada operação tem limite, modo de aprovação, registro e caminho de reversão testado. As demais permanecem como nas etapas anteriores.

## 2. Fora de escopo

- Ligar um pacote inteiro de “automação do marketplace” de uma vez.
- Executar sem política escrita da operação.
- Automatizar sem supervisão: emitir ou cancelar documento fiscal, reembolsar, gastar em anúncio, comprar insumo, alterar dado cadastral de cliente ou da loja, conceder desconto fora da regra, assumir compromisso de prazo ou estoque com o cliente.
- Automação de navegador no painel. Se a etapa 0 tiver deixado a escrita por API como indisponível, o caminho continua sendo a exportação manual da etapa 2, até existir uma decisão nova de arquitetura para automação de navegador autorizada.

## 3. Catálogo de operações que podem ser ligadas

Cada linha é uma classe de ação independente. O estado inicial de todas é **desligada**.

| Classe | Pré-condição de produto | Efeito |
|---|---|---|
| Salvar rascunho na plataforma | Etapa 0 confirmou rascunho real; existe versão aprovada pelo operador na etapa 2 | Cria ou atualiza rascunho não publicado |
| Publicar anúncio | Etapa 0 confirmou publicação; a mesma versão foi aprovada para publicar | Torna o anúncio visível no canal |
| Alterar conteúdo de anúncio já publicado | Etapa 0 confirmou edição; diff aprovado na etapa 2 | Atualiza campos aprovados |
| Alterar preço | Etapa 0 confirmou edição de preço; novo preço respeita preço mínimo e a lista vigente | Atualiza só o preço |
| Alterar estoque | Etapa 0 confirmou edição de estoque; quantidade veio de fonte confirmada | Atualiza só o estoque |
| Enviar resposta rotineira ao lead | Etapa 4 estável; a intenção está na lista permitida da política | Envia o texto já aprovado pela política |

Operações da seção 2 deste documento não entram nesse catálogo.

## 4. Requisitos funcionais

### 4.1 Política por operação

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-5-01 | Política versionada da classe | Obrigatório | Ligar uma classe exige uma política versionada com: canal, marcas abrangidas, modo de aprovação, limites, janela de horário, quantidade máxima por dia, critério de parada e procedimento de reversão. |
| RF-5-02 | Modo de aprovação | Obrigatório | O modo de aprovação de cada classe é um destes: **sempre humano**, **humano quando cruzar o limite**, **sem nova confirmação dentro do limite**. Publicar anúncio nasce e permanece em **sempre humano** até o operador criar uma versão de política que diga o contrário. |
| RF-5-03 | Limites da política | Obrigatório | Limites mínimos que a política declara quando fizerem sentido para a classe: variação máxima de preço em relação ao vigente, SKUs ou marcas permitidas, intenções de mensagem permitidas, tamanho máximo do lote. |
| RF-5-04 | Ensaio antes de ligar | Obrigatório | Antes de ligar a classe, o operador registra um ensaio supervisionado: quantidade de execuções corretas seguidas definida na própria política, mais um ensaio de reversão bem-sucedido no ambiente seguro. Sem esse registro a classe permanece desligada. |
| RF-5-05 | Desligamento imediato | Obrigatório | O operador desliga a classe a qualquer momento. Desligar interrompe execuções ainda não confirmadas e impede novas. |

### 4.2 Execução

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-5-06 | Vínculo da execução | Obrigatório | Uma execução de escrita referencia a versão de anúncio, a política e a tarefa que a originou. Execução sem esses três vínculos é recusada. |
| RF-5-07 | Payload já aprovado | Obrigatório | O payload enviado é o que o operador aprovou na etapa 2 ou o texto autorizado na etapa 4. A etapa 5 não regera título, preço ou resposta no momento do envio. |
| RF-5-08 | Recusa local fora da política | Obrigatório | Preço abaixo do preço mínimo, modalidade de lista trocada ou SKU fora da política é recusado antes da chamada externa, com motivo na tarefa. |
| RF-5-09 | Conferência do estado final | Obrigatório | Depois da chamada, o sistema lê o estado no canal e grava se coincide com o pedido (RNF-T-03 Escrita confirmada). Divergência dispara alerta ao operador e não marca a tarefa como concluída. |
| RF-5-10 | Execução idempotente | Obrigatório | Repetir a mesma tarefa não aplica o efeito duas vezes. A segunda tentativa devolve o resultado da primeira quando o estado já coincidir. |
| RF-5-11 | Falha na fila do operador | Obrigatório | Falha deixa a tarefa em estado de falha, com a resposta mascarada do canal, e aparece na lista de pendências do operador. |
| RF-5-12 | Reversão ou compensação manual | Obrigatório | Reversão, quando a política a prevê, restaura o estado anterior guardado e grava a reversão na auditoria (RF-T-03 Trilha da execução). Se o canal não oferecer reversão, a política exige compensação manual e a classe não pode usar o modo **sem nova confirmação**. |

### 4.3 Mensagens

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-5-13 | Envio só na intenção permitida | Obrigatório | Envio automático só ocorre para intenções listadas na política e quando nenhum gatilho de handoff de RF-4-14 Condições de handoff estiver ativo. |
| RF-5-14 | Handoff prevalece sobre o automático | Obrigatório | Qualquer gatilho de RF-4-14 Condições de handoff força modo humano, mesmo que a classe de resposta rotineira esteja ligada. |
| RF-5-15 | Marca de envio automático | Obrigatório | A mensagem enviada automaticamente fica na conversa com a marca de envio automático, a política usada e o texto exato. |

### 4.4 Visão do operador

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-5-16 | Painel da classe | Obrigatório | O operador vê, por classe: ligada ou desligada, modo de aprovação, uso do limite no dia, última falha e última reversão. |
| RF-5-17 | Automação no relatório | Obrigatório | Relatório da etapa 3 passa a poder incluir contagem de execuções automáticas, falhas e reversões no período, com a mesma regra de origem e lacuna. |
| RF-5-18 | Exportação do histórico | Desejável | O operador exporta o histórico de uma classe para revisão da política. |

## 5. Requisitos não funcionais

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RNF-5-01 | Credencial de escrita separada | Obrigatório | A credencial de escrita é distinta da credencial de leitura quando o provedor permitir, e segue o menor privilégio da classe ligada (RNF-T-04 Privilégio mínimo). Classe desligada não tem caminho de código acionável pela conversa do gerente. |
| RNF-5-02 | Idempotência e estado final | Obrigatório | Toda escrita é idempotente por identificador de tarefa (RF-5-10 Execução idempotente) e confirma estado final (RF-5-09 Conferência do estado final). |
| RNF-5-03 | Alerta de falha | Obrigatório | Alerta de falha ou divergência chega ao operador por um canal que ele definiu na política (interface e, se configurado, o mesmo tipo de aviso já usado na etapa 3). |
| RNF-5-04 | Limite no fuso de São Paulo | Obrigatório | Relógio e limite diário usam o fuso America/Sao_Paulo. O contador zera na virada desse fuso, não na virada do UTC exibida por engano. |
| RNF-5-05 | Log sem segredo | Obrigatório | Log de escrita guarda identificadores de negócio e resultado. Segredo e dado pessoal além do necessário à auditoria seguem RNF-T-01 Segredos fora do repositório e RNF-4-01 Retenção da conversa. |
| RNF-5-06 | Política vigente na largada | Obrigatório | Uma política alterada não vale para execução já iniciada. A execução termina com a versão de política que a autorizou. |
| RNF-5-07 | Repetir ensaio de reversão | Desejável | Ensaio de reversão da RF-5-04 Ensaio antes de ligar pode ser repetido sob demanda, sem afetar produção, no ambiente seguro da etapa 0. |

## 6. Critérios de aceite

1. Com todas as classes desligadas, um pedido do gerente para publicar produz recusa registrada e zero chamada de escrita.
2. Depois do ensaio supervisionado e da política em modo **sempre humano**, salvar rascunho na plataforma só ocorre após confirmação, e a leitura posterior confere o estado.
3. A segunda confirmação da mesma tarefa não cria segundo rascunho.
4. Preço abaixo do mínimo é recusado localmente.
5. Desligar a classe no meio de uma fila impede os itens ainda não enviados.
6. Uma conversa com gatilho de handoff não é enviada pela classe de resposta rotineira.
7. Divergência entre pedido e estado lido gera alerta e deixa a tarefa fora de “concluída”.

## 7. Insumos para a arquitetura

- Ponto único de despacho de escrita, usado por todas as classes, com a política aplicada antes da chamada.
- Como o estado anterior fica guardado para reversão em cada canal que a etapa 0 confirmar.
- Como o runtime do gerente perde a ferramenta de escrita quando a classe está desligada (RNF-5-01).
