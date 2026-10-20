# Etapa 3 — Análises e pesquisa

**Código:** E3  
**Título:** Análises e pesquisa  
**Projeto:** Agente Gerente de E-commerce  
**Fonte:** [abertura de projeto](../abertura_de_projeto.md), seções 2, 8, 9 e 11  
**Versão:** 1.0 — 20/10/2026  
**Depende de:** [etapa 1](etapa-1-mvp-do-gerente.md). A comparação antes/depois de anúncio usa versões da [etapa 2](etapa-2-fabrica-de-anuncios.md). Métricas de canal dependem do veredito de leitura da [etapa 0](etapa-0-validacao-tecnica.md).  
**Desbloqueia:** priorização de ações e o histórico que a etapa 5 pode usar para justificar automação.

## 1. Objetivo

Entregar relatório rastreável da operação e lista de oportunidades de produto, cada uma com evidência, estimativa e risco. O operador recebe ações priorizadas e consegue comparar o resultado de uma versão de anúncio com o período anterior.

## 2. Fora de escopo

- Publicar anúncio ou alterar preço por causa de um achado. A ação recomendada vira tarefa ou rascunho; o efeito externo continua na etapa 5.
- Definir meta numérica no lugar do operador.
- Tratar tendência encontrada numa única consulta como regra permanente de sortimento.

## 3. Papéis

- **Analista de e-commerce:** vendas, conversão, ticket, margem, devoluções, estoque e campanhas, quando o dado existir.
- **Pesquisador de mercado:** tendências, concorrentes, avaliações, lacunas e produtos em alta.
- **Gerente:** junta os achados, aponta inconsistência (por exemplo margem ausente tratada como zero) e propõe a próxima ação.

## 4. Requisitos funcionais

### 4.1 Relatório da operação

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-3-01 | Relatório por marca, canal e período | Obrigatório | O operador pede um relatório por marca, canal e período. O relatório lista só indicadores cuja origem exista. |
| RF-3-02 | Indicadores reconhecidos | Obrigatório | O conjunto de indicadores reconhecidos é: vendas brutas; repasse líquido; margem de contribuição estimada; margem de contribuição confirmada; visualizações; cliques; conversão; ticket médio; cancelamentos; devoluções; atraso; custo de modelo das tarefas no período. Indicador sem fonte fica de fora do cálculo e aparece na seção de lacunas. |
| RF-3-03 | Número com origem | Obrigatório | Cada número do relatório informa período, origem e natureza confirmado ou estimado (RF-T-06 Origem do número). |
| RF-3-04 | Margem com insumos vigentes | Obrigatório | Margem usa custo vigente, taxa vigente e a lista de preço do canal (RF-1-11 Margem só com insumos completos). Sem esses insumos a margem entra nas lacunas. |
| RF-3-05 | Realizado ao lado da meta | Obrigatório | Se o operador cadastrou objetivo para o período (RF-1-16 Objetivo sem meta inventada), o relatório mostra valor realizado ao lado do valor-alvo. Sem objetivo, o relatório não cria alvo. |
| RF-3-06 | Achados e ações priorizadas | Obrigatório | O analista devolve achados e ações priorizadas. Cada ação cita o indicador, o SKU ou canal, a evidência e o efeito esperado em linguagem qualitativa quando não houver número confiável. |
| RF-3-07 | Relatório recorrente e alerta | Obrigatório | O operador agenda relatório recorrente (diário ou semanal) e alerta quando um indicador escolhido cruzar um limite que ele mesmo definiu. Limite não definido não dispara alerta. |
| RF-3-08 | Exportação do relatório | Desejável | O operador exporta o relatório com as mesmas lacunas e origens vistas na tela. |

### 4.2 Experimentos de anúncio

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-3-09 | Abertura do experimento | Obrigatório | Para uma versão de anúncio da etapa 2, o operador abre um experimento com hipótese, data da mudança e período de comparação. |
| RF-3-10 | Antes e depois | Obrigatório | O experimento mostra métricas anteriores gravadas na versão e métricas do período posterior, lado a lado, com origem. Métrica posterior ainda não lida fica ausente. |
| RF-3-11 | Comparação inconclusiva | Obrigatório | O sistema não declara vencedor quando o período posterior não tem a mesma métrica da linha de base, ou quando a origem mudou. Ele registra a comparação como inconclusiva e diz qual dado falta. |
| RF-3-12 | Pedido de novo rascunho | Desejável | Uma ação do analista pode pedir à fábrica um novo rascunho, criando tarefa na etapa 2 sem aprovar esse rascunho. |

### 4.3 Pesquisa de oportunidades

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-3-13 | Registro da pesquisa | Obrigatório | Uma pesquisa registra tema, fontes consultadas, data e hora da consulta e o papel que executou. |
| RF-3-14 | Ficha da oportunidade | Obrigatório | Cada oportunidade contém: descrição do produto ou lacuna, evidências com fonte, estimativa de potencial, leitura de concorrência, custos conhecidos, riscos e o que ainda está ausente (custo, fornecedor, restrição de canal, direito de marca). |
| RF-3-15 | Oportunidade sem custo | Obrigatório | Oportunidade sem custo confiável não recebe margem nem recomendação de preço. O texto marca o custo como ausente. |
| RF-3-16 | Estado da oportunidade | Obrigatório | O operador classifica a oportunidade como rejeitada, aprovada para estudo, em teste ou lançada. A passagem para lançada é manual e não cria anúncio sozinha. |
| RF-3-17 | Pesquisa nova não reescreve a anterior | Obrigatório | Achados de uma pesquisa ficam ligados à data da fonte. Repetir a pesquisa cria registro novo; não reescreve o anterior. |
| RF-3-18 | Ranking com critério visível | Desejável | O ranking de oportunidades ordena por um critério que o operador escolhe entre evidência disponível, aderência à marca e risco. O critério fica visível no ranking. |

### 4.4 Aprendizado operacional

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-3-19 | Feedback do operador | Obrigatório | Feedback do operador sobre um relatório ou uma oportunidade grava na memória operacional o que foi aceito ou rejeitado e o motivo (RF-1-18 Memória operacional). |
| RF-3-20 | Padrão vira regra versionada | Obrigatório | Incorporar um padrão (“sempre evitar esta promessa”, “priorizar esta faixa de preço”) exige nova versão de regra, com o operador como autor. O relatório seguinte usa a regra nova só a partir da vigência dela. |

## 5. Requisitos não funcionais

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RNF-3-01 | Números repetíveis | Obrigatório | Dado o mesmo cadastro, as mesmas leituras de canal e o mesmo período, os totais numéricos do relatório se repetem. Texto de comentário do modelo pode variar; número e lacuna, não. |
| RNF-3-02 | Evidência com fonte e data | Obrigatório | Fonte externa de pesquisa guarda URL ou identificador e a data de consulta. Afirmação sem fonte não entra na lista de evidências. |
| RNF-3-03 | Custo de relatório e pesquisa | Obrigatório | Relatório e pesquisa registram custo de modelo na tarefa (RNF-1-06 Custo de modelo somável). |
| RNF-3-04 | Alerta falho sem número parcial | Obrigatório | Alerta recorrente que falhar (conector ou modelo indisponível) registra a falha e não envia número parcial como se o período estivesse fechado. |
| RNF-3-05 | Pesquisa só em leitura | Obrigatório | Consulta à web ou a canal usa apenas conector de leitura. A etapa não ganha credencial de escrita. |
| RNF-3-06 | Instantâneo do relatório | Desejável | O operador reabre um relatório antigo e vê os números daquele momento, mesmo que o cadastro de custo tenha mudado depois. |

## 6. Critérios de aceite

1. Um período com leitura parcial de Shopee produz relatório com números só onde houve leitura e uma seção de lacunas para o restante, incluindo TikTok Shop se ele não tiver métrica.
2. Margem sem custo fica na seção de lacunas.
3. Um experimento de versão da etapa 2 mostra antes e depois quando as duas leituras existem, e inconclusivo quando a posterior falta.
4. Uma oportunidade gravada mostra fonte, data, risco e custo ausente, e só muda de estado pela ação do operador.
5. Um alerta com limite definido pelo operador dispara; outro indicador sem limite permanece em silêncio.
6. Rejeitar uma recomendação grava motivo e não altera a regra vigente.

## 7. Insumos para a arquitetura

- Separação entre agregação determinística dos números e redação do achado.
- Retenção do instantâneo do relatório (RNF-3-06) se a arquitetura for adotá-lo já nesta etapa.
- Contrato do pesquisador: evidência com fonte e data, estimativa e risco em campos distintos.
