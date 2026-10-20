# Projeto: Agente Gerente de E-commerce

**Marcas:** 3D Print Franca e Mocozim  
**Versão:** 1.0 — 13/10/2026  
**Objetivo deste documento:** transformar a ideia em um escopo inicial que possa orientar arquitetura, desenvolvimento e priorização do MVP.

## 1\. Visão do produto

Construir um **assistente pessoal e gerente de operação de e-commerce**, hospedado em uma VPS, que centralize informações, coordene agentes especializados e ajude a aumentar vendas e rentabilidade. O operador atualiza regras e objetivos; o sistema acompanha os resultados, identifica oportunidades, prepara ações e aprende com aprovações e resultados anteriores.

A operação utiliza atualmente **Shopee e TikTok Shop**, com o **UpSeller** como ERP/hub de operação, conforme informado pelo responsável. O primeiro foco é preparar anúncios melhores, analisar resultados, encontrar oportunidades de novos produtos e qualificar contatos comerciais. A publicação e as ações com impacto financeiro devem permanecer sob aprovação humana até que a integração esteja testada.

## 2\. Objetivos principais

1. **Gerenciar a operação:** oferecer uma visão consolidada de produtos, anúncios, estoque, resultados, leads, pendências e prioridades.
2. **Melhorar anúncios:** criar títulos, descrições, atributos, palavras-chave e imagens; preparar a ficha completa e salvar como rascunho para revisão antes da publicação.
3. **Aumentar vendas com margem:** analisar desempenho por produto/canal, identificar gargalos e recomendar ações mensuráveis.
4. **Pesquisar oportunidades:** estudar tendências, concorrentes e sinais de demanda, estimando potencial, concorrência, custos e riscos antes de sugerir novos produtos.
5. **Atender e qualificar clientes:** receber contatos, entender a necessidade, solicitar os dados faltantes, preparar uma pré-análise/orçamento indicativo e transferir oportunidades qualificadas para atendimento humano.
6. **Aprender com a operação:** guardar decisões, feedbacks, versões de anúncios, resultados e padrões de produtos, sem depender de “treinar o modelo” a cada interação.

## 3\. Agente gerente e agentes especialistas

O agente gerente recebe a solicitação, divide o trabalho, seleciona os especialistas, junta os resultados, verifica inconsistências e propõe a próxima ação. Os especialistas devem ter tarefas, entradas e saídas bem definidas.

|Agente lógico|Responsabilidade|Entrega esperada|
|-|-|-|
|**Gerente / Orquestrador**|Priorizar, delegar, revisar entregas e aplicar regras de autonomia|Plano de ação, decisão recomendada e pendências|
|**Copywriter de marketplace**|Títulos, descrições, SEO interno, atributos e variações por canal|Anúncio textual estruturado e justificativa|
|**Designer de produto**|Melhorar imagens existentes, criar artes auxiliares, infográficos e imagens de contexto|Conjunto de imagens por canal, com checklist de qualidade|
|**Analista de e-commerce**|Avaliar vendas, conversão, ticket, margem, devoluções, estoque e campanhas|Relatório com achados e ações priorizadas|
|**Pesquisador de mercado**|Buscar tendências, concorrentes, avaliações, lacunas e produtos em alta|Lista de oportunidades com evidências, estimativa e riscos|
|**Atendimento / Qualificação**|Classificar mensagens, entender demanda, coletar dados e pré-orçar|Resposta sugerida, ficha do lead e condição para handoff humano|
|**Revisor / Auditor**|Verificar precisão, compatibilidade de canal, preço, alegações, direitos e consistência|Aprovar, solicitar correção ou bloquear a entrega|

**Recomendação para o MVP:** começar com um único orquestrador e especialistas como papéis/funções separados por prompts, ferramentas e contratos de saída. Só transformar cada papel em processo/agente independente quando houver benefício claro. Isso reduz complexidade, chamadas de modelo e custo.

## 4\. Fluxo de criação e otimização de anúncios

1. Selecionar produto/SKU e canal (Shopee ou TikTok Shop).
2. Buscar ficha do produto: materiais, medidas, variações, fotos reais, custo, preço mínimo, estoque e restrições.
3. Analisar anúncio atual e, quando permitido, dados de desempenho e concorrentes.
4. Copywriter propõe título, descrição, atributos, palavras-chave e FAQs.
5. Designer prepara/otimiza imagens respeitando dimensões, regras do canal, identidade visual e fidelidade do produto real.
6. Revisor verifica factualidade, promessas técnicas, preço/margem, duplicidades, direitos de imagem/marca e regras da plataforma.
7. Gravar a versão em uma **área de rascunhos**, comparando original e proposta.
8. Usuário revisa, pede ajustes e aprova.
9. Só então publicar por API oficial ou pelo fluxo autorizado no painel.
10. Registrar versão, data, responsável, motivo da alteração e métricas antes/depois.

**Requisito de publicação:** o sistema deve preferir “rascunho local” até confirmar se a API oficial de cada canal permite salvar um anúncio não publicado. Não presumir que a API do UpSeller faça essa operação. Se não existir suporte de rascunho/publicação via API, entregar arquivos e campos prontos para revisão manual ou testar uma automação de navegador autorizada, com monitoramento e possibilidade de rollback.

## 5\. Atendimento e pré-orçamento

Fluxo sugerido:

`Nova mensagem → Identificar intenção → Coletar requisitos → Consultar catálogo/custos → Pré-análise → Resposta preliminar → Sinal de interesse → Transferir para humano → Registrar desfecho`

O bot deverá coletar, quando relevante: produto/serviço, quantidade, medidas, material/cor, personalização, prazo, cidade/frete, necessidade de nota e referência visual/arquivo 3D. Para produtos de catálogo, consulta preço e estoque. Para personalizados, calcula uma **estimativa condicionada** a requisitos suficientes e às regras de custo aprovadas.

Transferir para humano quando o cliente demonstrar intenção concreta, pedir negociação especial, houver personalização complexa, dúvida técnica/jurídica, risco de prazo, falta de custo confiável ou divergência cadastral. O bot não deve prometer estoque, prazo, resistência, vedação ou desempenho sem dados confirmados.

## 6\. Arquitetura recomendada

### Camadas

1. **Interface:** chat administrativo simples para falar com o gerente, revisar anúncios, aprovar mudanças e consultar relatórios; WhatsApp como canal comercial em uma fase posterior.
2. **Orquestração:** Hermes Agent como runtime/agente principal, com papéis especialistas/delegação e conexões MCP quando apropriado.
3. **Camada de serviços de negócio:** API própria em Python (FastAPI) contendo regras de preço, validações, aprovações, controle de versões, auditoria e chamadas a sistemas externos. O modelo não deve editar o banco ou chamar APIs críticas sem passar por essas regras.
4. **Conectores:** adaptadores separados para UpSeller, Shopee, TikTok Shop, WhatsApp, pesquisa web e serviço de imagem. Cada adaptador expõe funções estreitas, validadas e testáveis.
5. **Dados:** PostgreSQL para catálogo, custos, objetivos, histórico de anúncios, versões, leads, tarefas, aprovações e métricas; armazenamento compatível com S3 para fotos e artefatos. Uma fila como Redis pode ser acrescentada para tarefas demoradas/agendadas.
6. **Modelos:** OpenRouter como gateway; modelo econômico para tarefas simples e modelo mais capaz/visual quando a tarefa exigir análise complexa ou imagem. Selecionar modelos após testes de chamadas de ferramentas, qualidade em português, visão, latência e preço — não apenas pelo custo por token.
7. **Observabilidade:** logs por tarefa, origem dos dados, tokens/custo, falhas, tempo de execução, ação solicitada, autorização e resultado.

### Diagrama lógico

```text
Usuário / WhatsApp
        |
        v
Gerente (Hermes Agent)
        |
        +--> Copywriter ------+
        +--> Designer --------+--> Revisor --> Rascunho --> Aprovação humana
        +--> Analista --------+
        +--> Pesquisador -----+
        +--> Atendimento -----+
        |
        v
API de negócio (FastAPI): regras, permissões, preços, logs, auditoria
        |
        +--> UpSeller
        +--> Shopee API / painel autorizado
        +--> TikTok Shop API / painel autorizado
        +--> Pesquisa web / serviço de imagem
        |
        v
PostgreSQL + armazenamento de imagens + fila de tarefas
```

### Stack prática inicial

* **Python + FastAPI:** API, regras de negócio e conectores.
* **Hermes Agent:** interface agentiva, ferramentas e orquestração; manter a lógica crítica fora dos prompts.
* **OpenRouter:** acesso a modelos e roteamento por tarefa.
* **PostgreSQL:** dados estruturados e histórico auditável.
* **Docker Compose em VPS:** implantação inicial simples; segredos por variáveis de ambiente/secret manager, nunca no repositório.
* **Redis/fila de tarefas:** adicionar quando forem necessários jobs recorrentes, execução assíncrona ou reprocessamento confiável.
* **Armazenamento S3 compatível:** originais, versões de artes e imagens finais.

## 7\. Integrações: realidade e pontos de validação

### UpSeller

A documentação pública atual do UpSeller informa API aberta e MCP. Porém, os recursos MCP descritos explicitamente incluem **consultar armazéns e estoque por SKU**. A documentação consultada não comprova, por si só, operações de edição de anúncios, emissão fiscal, impressão de etiquetas ou publicação de produtos. Essas capacidades precisam ser confirmadas no painel/documentação do plano e com o suporte antes de definir o escopo do conector.

### Shopee e TikTok Shop

Priorizar APIs oficiais e permissões de parceiro/vendedor. A disponibilidade de criação/edição, upload de imagens, salvamento como rascunho e publicação precisa ser verificada separadamente em cada plataforma e para as credenciais aprovadas. Não depender da existência de uma integração do ERP para concluir que toda a operação está exposta por API.

### WhatsApp

Escolher depois se será WhatsApp Business Platform/API oficial ou outro provedor autorizado. Definir política de consentimento, janela de atendimento, transferência para humano, registro da conversa e proteção de dados.

### Imagens

Separar duas funções: (a) tratamento fiel de fotos reais — recorte, fundo, iluminação e enquadramento; (b) criação de peças gráficas complementares. Não permitir que a IA altere material, medidas, acessórios incluídos ou características funcionais do produto. Toda imagem final deve passar por verificação visual e aprovação humana no MVP.

## 8\. Dados que o sistema deve manter

* **Catálogo mestre:** SKU, marca, nome, variações, medidas, material, fotos, descrição factual e status.
* **Economia do produto:** filamento/material, tempo de máquina, mão de obra, embalagem, taxas, impostos, frete subsidiado, custo de anúncios e preço mínimo.
* **Canais:** ID do anúncio por plataforma, status, preço, estoque, conteúdo publicado e métricas disponíveis.
* **Objetivos:** metas e período, indicador, valor-alvo, fonte e responsável.
* **Memória operacional:** correções do usuário, estilo de comunicação, decisões aceitas/rejeitadas e motivos.
* **Experimentos:** versão do anúncio, hipótese, data da mudança, período de comparação e resultados.
* **Auditoria:** quem pediu, quem/qual agente executou, dados consultados, ferramenta chamada, aprovação, resposta do sistema e reversão, se houver.

“Aprender” deve significar principalmente **registrar feedback, regras, fatos verificados e resultados de experimentos**. Não deixar o modelo alterar sozinho suas próprias instruções ou aprender regras permanentes a partir de uma única observação. Usar revisão, versionamento e avaliações antes de mudar os procedimentos.

## 9\. Objetivos e métricas iniciais

Os PDFs fornecem um plano de lançamento e uma tabela comercial, mas **não definem metas numéricas de faturamento, lucro ou conversão**. O painel deve permitir preencher metas posteriormente, sem inventar valores.

Indicadores recomendados:

* vendas brutas e repasse líquido por canal e SKU;
* margem de contribuição estimada/confirmada;
* visualizações, cliques e conversão, se o marketplace disponibilizar;
* ticket médio, cancelamentos, devoluções e atraso;
* tempo gasto para criar/revisar um anúncio;
* proporção de sugestões aceitas pelo usuário;
* resultado dos anúncios antes/depois da atualização;
* leads recebidos, qualificados, orçados, transferidos e convertidos;
* oportunidades de produto pesquisadas, aprovadas, testadas e lançadas;
* custo de modelo por tarefa e custo total mensal da automação.

Todos os relatórios devem indicar período, origem dos dados e se os valores são confirmados ou estimados.

## 10\. Autonomia e segurança

**Fase inicial — sem ações externas automáticas:** consultar, analisar, redigir, gerar artes, preparar rascunhos e recomendar.

**Com aprovação humana:** salvar rascunhos nas plataformas, alterar anúncios, mexer em preço/estoque, responder casos sensíveis ou operar o painel por navegador.

**Somente após testes e política explícita:** automatizar ações repetitivas de baixo risco com limites definidos, logs e possibilidade de reversão.

Exigir aprovação para publicar anúncios, conceder descontos fora da regra, assumir compromissos com clientes, emitir/cancelar documentos fiscais, reembolsar, gastar em anúncios, comprar insumos ou alterar dados cadastrais. Usar menor privilégio, limites de operação, proteção contra duplicidade, idempotência, confirmação do estado final e alertas de falha. Nunca armazenar tokens ou senhas neste documento.

## 11\. Plano de desenvolvimento

### Etapa 0 — validação técnica

* Confirmar plano e permissões de API/MCP do UpSeller.
* Conferir acesso de desenvolvedor e permissões das APIs de Shopee e TikTok Shop.
* Testar consulta de estoque, leitura de produtos/anúncios e envio de alterações em ambiente seguro, quando disponível.
* Confirmar se cada canal permite draft real via API; caso não, usar rascunho interno.

### Etapa 1 — MVP do gerente

* VPS com Docker Compose, API FastAPI, PostgreSQL e Hermes.
* Cadastro mestre de produtos, preços, objetivos e regras.
* Interface simples para pedir análises, ver tarefas, aprovar rascunhos e consultar logs.
* Integrações em modo leitura sempre que possível.

### Etapa 2 — fábrica de anúncios

* Gerar título/descrição/atributos por canal.
* Pipeline de tratamento de imagem, validação e controle de versões.
* Revisor automático e fila de aprovação humana.
* Exportar rascunhos para publicação manual inicialmente, se API de escrita não estiver validada.

### Etapa 3 — análises e pesquisa

* Relatórios periódicos, alertas e ranking de oportunidades.
* Pesquisas de tendências com fontes e data de consulta.
* Hipóteses de otimização e comparação de resultados.

### Etapa 4 — atendimento

* Integrar canal de mensagens autorizado.
* Qualificar lead, consultar catálogo, elaborar pré-orçamento e encaminhar ao humano.
* Criar regras claras de transferência e revisão das respostas.

### Etapa 5 — automação controlada

* Liberar operações de escrita individualmente, com limites, aprovação adequada, logs e rollback.
* Automatizar rotinas apenas depois de demonstrar confiabilidade.

## 12\. Dados comerciais da Mocozim — fonte: “Planilha Produtos – Festival Jaguara – Preços.pdf”

Valores exatamente conforme a tabela fornecida. Confirmar antes de usar como preço vigente nos anúncios, pois preço/custo podem variar por canal e tarifa.

|Produto|Consumidor final|Revenda à vista|Revenda consignado|Revenda — 10 peças|
|-|-:|-:|-:|-:|
|Tubete Mocozim|R$ 15,00|R$ 9,50|R$ 12,00|R$ 95,00|
|Porta Bic|R$ 20,00|R$ 15,00|R$ 16,00|R$ 145,00|
|Banquinho|R$ 5,00|R$ 3,75|R$ 4,00|R$ 75,00|
|Potinho Dourado|R$ 20,00|R$ 15,00|R$ 16,00|R$ 145,00|
|Porta Incenso|R$ 25,00|R$ 18,75|R$ 20,00|R$ 180,00|
|Cinzeiro portátil|R$ 20,00|R$ 15,00|R$ 16,00|R$ 145,00|
|Porta Crema|R$ 15,00|R$ 11,50|R$ 12,00|R$ 110,00|
|Dichavador|R$ 20,00|R$ 15,00|R$ 16,00|R$ 145,00|
|Barril|R$ 50,00|R$ 37,50|R$ 40,00|R$ 365,00|
|Case 5x1|R$ 60,00|R$ 45,00|R$ 50,00|R$ 440,00|

**Regra do sistema:** manter estas quatro modalidades como listas comerciais distintas. Não misturar preço consumidor final, revenda à vista, consignação e pacote de 10 peças. Margem por canal só pode ser calculada depois que os custos por SKU e as taxas vigentes forem cadastrados.

## 13\. Plano de lançamento Mocozim — fonte: “Plano de Ação e Tarefas – Mocozim.pdf”

O documento registra **9 tarefas, 0 concluídas, 2 em andamento e 7 pendentes**, com investimento estimado total de **R$ 396,00**. Como este plano pode não refletir o estado de hoje e o responsável informa que já opera na Shopee e TikTok Shop, os status abaixo devem ser considerados o retrato do PDF e revalidados — não como o estado atual confirmado.

|Frente/tarefa do plano|Status registrado|Custo estimado|
|-|-|-:|
|Depósito do pedido de marca no INPI — classe 34, conforme plano|A fazer|R$ 166,00|
|Domínio `mocozim.com.br`|A fazer|R$ 40,00|
|Domínio internacional `mocozim.com`|A fazer|R$ 60,00|
|Padronização de perfis sociais e link para WhatsApp|A fazer|R$ 0,00|
|Estruturar tabela de preços e descontos por volume|Em andamento|R$ 0,00|
|Imprimir lote piloto dos produtos de maior giro|Em andamento|R$ 80,00|
|Catálogo digital e mostruário para B2B|A fazer|R$ 0,00|
|Cadastro de anúncios, títulos SEO, descrições e kits|Não iniciado|R$ 0,00|
|Estruturar e lançar loja, pagamentos e frete|Não iniciado|R$ 50,00|

O total de R$ 396,00 é a soma dos custos estimados listados no plano; não é confirmação de gastos já realizados. O registro de classe 34 e demais etapas de marca/domínio deve ser confirmado com orientação competente antes de executar pagamentos ou depósitos.

## 14\. Critérios de sucesso do MVP

O MVP é considerado útil quando conseguir:

1. Consultar os dados que realmente estão disponíveis no UpSeller e nos canais conectados, sem inventar dados faltantes.
2. Produzir anúncios completos e imagens revisáveis a partir de uma ficha confiável do produto.
3. Guardar rascunhos, versões, feedback e aprovações.
4. Gerar um relatório rastreável e sugerir ações explicando a evidência.
5. Qualificar uma conversa e transferir o lead com resumo, dados coletados e motivo do encaminhamento.
6. Medir custo por tarefa e permitir ao responsável controlar quais ações estão liberadas.

## Referências técnicas consultadas

* UpSeller — API aberta e MCP: https://www.upseller.com/pt/help-doc-article-3398
* UpSeller — configuração MCP e ferramentas documentadas: https://www.upseller.com/pt/help-doc-article-3400
* Hermes Agent — integração com MCP: https://github.com/hermes-agent-org/hermes/blob/main/website/docs/user-guide/features/mcp.md
* Hermes Agent — configuração e delegação: https://hermes-agent.nousresearch.com/docs/user-guide/configuration/
* OpenRouter — tool calling: https://openrouter.ai/docs/guides/features/tool-calling
* TikTok Shop Partner Center — exemplo de APIs de produto e edição: https://partner.tiktokshop.com/docv2/page/mdpqmff0

**Observação técnica:** documentação externa e permissões podem mudar. Antes de desenvolver conectores de escrita, validar endpoints, escopos, requisitos de aprovação do app, limites de uso e comportamento de publicação para a conta brasileira de cada marketplace.

