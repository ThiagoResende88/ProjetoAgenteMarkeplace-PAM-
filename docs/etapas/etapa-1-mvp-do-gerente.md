# Etapa 1 — MVP do gerente

**Código:** E1  
**Título:** MVP do gerente  
**Projeto:** Agente Gerente de E-commerce  
**Fonte:** [abertura de projeto](../abertura_de_projeto.md), seções 2, 3, 8, 9, 10 e 11  
**Versão:** 1.0 — 20/10/2026  
**Depende de:** [etapa 0](etapa-0-validacao-tecnica.md) para cada conector de leitura que for ligado. O cadastro local pode começar antes do relatório.  
**Desbloqueia:** etapas 2, 3 e 4.

## 1. Objetivo

Colocar no ar um ambiente único em que o operador cadastra produto, preço, objetivo e regra, pede trabalho ao gerente, acompanha tarefas e consulta o que foi feito. Integrações externas, quando existirem, operam em leitura.

Nesta etapa o gerente e os especialistas cumprem contratos de entrada e saída. Um papel vira processo ou agente independente só quando a arquitetura mostrar benefício claro de custo, isolamento ou ferramenta.

## 2. Fora de escopo

- Gerar o anúncio completo e o conjunto de imagens (etapa 2).
- Relatório periódico, alerta e pesquisa de mercado (etapa 3).
- Conversa com cliente (etapa 4).
- Qualquer escrita em UpSeller, Shopee ou TikTok Shop (etapa 5).
- Preencher meta numérica que o operador não tenha informado.

## 3. Atores e superfícies

- **Operador**, numa interface administrativa: conversa com o gerente, cadastro, tarefas, fila de aprovação (ainda vazia ou só de ensaio) e logs.
- **Gerente**, recebendo a solicitação e devolvendo plano, recomendação e pendências.
- **Papéis** com tarefa, entrada e saída definidas: copywriter, designer, analista, pesquisador, atendimento e revisor. Na etapa 1 eles podem responder a um pedido interno de ensaio; o fluxo de anúncio real é a etapa 2 e o de atendimento real é a etapa 4.

## 4. Requisitos funcionais

### 4.1 Acesso e ambiente

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-1-01 | Autenticação do operador | Obrigatório | O operador autentica-se para ver cadastro, tarefas, logs e controles de autonomia. Sessão expirada volta à autenticação. |
| RF-1-02 | Ambiente reproduzível | Obrigatório | O ambiente de execução sobe de forma reproduzível na VPS, com a API de regras, o banco e o runtime do gerente descritos na decisão de arquitetura. |
| RF-1-03 | Base de ensaio separada | Obrigatório | Há um ambiente separado de ensaio. Dados de ensaio e dados da operação não compartilham a mesma base. |

### 4.2 Catálogo mestre

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-1-04 | Ficha do SKU | Obrigatório | O operador cria e edita um SKU com: marca (3D Print Franca ou Mocozim), nome, variações, medidas, material, fotos reais, descrição factual e status. |
| RF-1-05 | Campo ausente e descrição factual | Obrigatório | Campo não preenchido fica ausente (RF-T-01 Natureza do dado). Descrição factual aceita só o que o operador ou uma fonte confirmada gravou. |
| RF-1-06 | Histórico de alteração cadastral | Obrigatório | Cada alteração de cadastro guarda autor, instante e valor anterior. |
| RF-1-07 | Foto real anexada | Desejável | O operador anexa a foto real ao SKU e vê a miniatura no cadastro. O arquivo original permanece recuperável. |

### 4.3 Economia e listas de preço

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-1-08 | Componentes de custo | Obrigatório | O operador registra, por SKU e com vigência e origem, os componentes de custo que conhecer: filamento ou material, tempo de máquina, mão de obra, embalagem, taxas, impostos, frete subsidiado, custo de anúncios e preço mínimo. Componente desconhecido fica ausente. |
| RF-1-09 | Quatro modalidades comerciais | Obrigatório | As quatro modalidades comerciais existem como listas separadas (RF-T-05 Listas de preço separadas). Cada preço tem valor, moeda BRL, vigência e marca **vigente** ou **referência não confirmada**. |
| RF-1-10 | Tabela do Festival Jaguara | Obrigatório | A tabela do PDF do Festival Jaguara pode ser lançada uma vez como referência não confirmada. Ela só passa a vigente quando o operador confirmar o valor para o SKU e a modalidade. |
| RF-1-11 | Margem só com insumos completos | Obrigatório | Margem por canal só é calculada quando existem custo do SKU e taxa vigente usados na conta, mais a lista de preço escolhida para o canal. Faltando um deles, a margem fica ausente e a tela explica qual insumo falta. |

### 4.4 Canais em leitura

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-1-12 | Vínculo do anúncio no canal | Obrigatório | O operador vincula um SKU a um anúncio de canal com os campos que a etapa 0 tiver marcado como leitura confirmada: identificador externo, status, preço publicado, estoque, conteúdo publicado e métricas disponíveis. |
| RF-1-13 | Leitura só se confirmada | Obrigatório | Conector de leitura só é habilitado para capacidade com veredito **confirmada** na etapa 0. |
| RF-1-14 | Cadastro local se o conector falhar | Obrigatório | Falha ou ausência de conector mantém o cadastro local utilizável. O campo externo correspondente fica ausente, com a data da última tentativa. |
| RF-1-15 | Leitura não sobrescreve o mestre | Obrigatório | Uma consulta externa bem-sucedida grava a origem e o instante. Valor lido não substitui preço vigente nem descrição factual do cadastro mestre; fica no registro do canal. |

### 4.5 Objetivos e regras

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-1-16 | Objetivo sem meta inventada | Obrigatório | O operador cadastra objetivo com período, indicador, valor-alvo, fonte e responsável. Indicador sem valor-alvo permanece sem meta. O sistema não sugere número de faturamento, lucro ou conversão. |
| RF-1-17 | Regra versionada | Obrigatório | O operador cadastra regra versionada de autonomia, formação de preço, restrição de produto e tom de comunicação. A versão nova passa a valer na data que ele definir; a anterior continua consultável. |
| RF-1-18 | Memória operacional | Obrigatório | Memória operacional guarda correção do operador, preferência de estilo, decisão aceita ou rejeitada e motivo. Promover esse registro a regra vigente é uma ação explícita de nova versão (RF-T-04 Mudança por versão). |

### 4.6 Interface do gerente

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-1-19 | Pedido em linguagem natural | Obrigatório | O operador pede, em linguagem natural, consulta de cadastro, leitura de canal habilitada, resumo de pendências ou ensaio de um papel. |
| RF-1-20 | Resposta com plano e pendências | Obrigatório | A resposta do gerente contém plano do que foi feito, recomendação e pendências, e cita os registros usados (SKU, regra, leitura externa) com a natureza confirmado, estimado ou ausente. |
| RF-1-21 | Contrato dos papéis | Obrigatório | Cada papel especialista tem contrato escrito de entrada e saída. A saída que não cumprir o contrato volta como pendência, sem ser gravada como fato de cadastro. |
| RF-1-22 | Lista de tarefas | Obrigatório | O operador vê a lista de tarefas com estado (recebida, em execução, concluída, falha, recusada por autonomia) e abre o detalhe de uma tarefa. |
| RF-1-23 | Detalhe e custo da tarefa | Obrigatório | O detalhe da tarefa mostra origem dos dados, ferramenta chamada, custo de modelo (tokens e valor quando o gateway informar), falha, duração, ação solicitada, autorização e resultado (RF-T-03 Trilha da execução). |
| RF-1-24 | Interruptor de autonomia | Obrigatório | O operador liga ou desliga classes de ação (RF-T-07 Classes de ação). No fechamento desta etapa as classes ligadas são somente: consultar cadastro, consultar canal em leitura, redigir material interno, recomendar. As demais nascem desligadas. |
| RF-1-25 | Visão consolidada da marca | Obrigatório | A visão inicial reúne, para a marca escolhida: produtos, anúncios vinculados, estoque conhecido, resultados já legíveis, pendências e prioridades abertas. Bloco sem dado mostra ausência, não zero inventado. |

### 4.7 Estruturas que as próximas etapas preenchem

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-1-26 | Registros das etapas seguintes | Obrigatório | Existem registros, ainda que sem fluxo completo, para: versão de anúncio, aprovação, lead, experimento e auditoria. A etapa 2, 3 ou 4 passa a preenchê-los sem migrar o significado desses registros. |
| RF-1-27 | Pendência manual | Desejável | O operador lança uma pendência manual e o gerente a devolve na lista de prioridades. |

## 5. Requisitos não funcionais

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RNF-1-01 | Segredos do ambiente | Obrigatório | Segredos de banco, gateway de modelo e conectores seguem RNF-T-01 Segredos fora do repositório. O repositório sobe sem arquivo de segredo. |
| RNF-1-02 | Cadastro via camada de regras | Obrigatório | Pedido do gerente que altere cadastro ou chame API passa pela camada de regras (RNF-T-02 Regras no caminho crítico). A interface recusa atualização direta feita só pelo texto do modelo. |
| RNF-1-03 | Cadastro síncrono, modelo assíncrono | Obrigatório | Cadastro e leitura de tarefa respondem na mesma sessão do operador. Trabalho de modelo pode seguir assíncrono, com estado visível em RF-1-22 Lista de tarefas. |
| RNF-1-04 | Cadastro independente de conector | Obrigatório | Indisponibilidade de um conector ou do gateway de modelo preserva consulta e edição do cadastro local. |
| RNF-1-05 | Cópia de segurança antes do dado real | Obrigatório | Antes de gravar preço vigente ou dado que venha de canal real, existe cópia de segurança do banco com um ensaio de restauração registrado. |
| RNF-1-06 | Custo de modelo somável | Obrigatório | Log de tarefa permite somar custo de modelo por tarefa e por dia. Valor monetário usa a unidade devolvida pelo gateway; se o gateway não devolver custo, a tarefa guarda tokens e marca o custo como ausente. |
| RNF-1-07 | Interface em português | Obrigatório | A interface administrativa e as respostas do gerente estão em português (RNF-T-06 Português e estilo). |
| RNF-1-08 | Duração visível da tarefa | Desejável | O tempo de uma tarefa de modelo fica visível para o operador comparar modelos depois, sem que esta etapa fixe o modelo definitivo. |

## 6. Critérios de aceite

1. O operador cadastra um SKU de cada marca, com custo parcial e as quatro modalidades, uma delas vigente e outra só referência.
2. Uma leitura confirmada na etapa 0 aparece no vínculo de canal; uma capacidade não verificada aparece como ausente.
3. Um pedido ao gerente devolve plano, recomendação e pendências citando o SKU real, e recusa uma classe de ação desligada.
4. O log dessa tarefa mostra ferramenta, duração e custo ou tokens.
5. Alterar uma regra cria versão nova e mantém a anterior consultável.
6. Margem sem custo ou sem taxa fica ausente, com o insumo faltante indicado.

## 7. Insumos para a arquitetura

- Contratos de entrada e saída dos seis papéis, mesmo que o runtime seja um só.
- Lista de classes de ação e o interruptor do operador.
- Separação entre cadastro mestre, registro de canal e preço vigente.
- O que precisa estar síncrono na interface (RF-1-03, RNF-1-03) e o que pode esperar fila.
