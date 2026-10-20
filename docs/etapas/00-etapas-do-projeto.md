# Etapas do projeto — Agente Gerente de E-commerce

**Marcas:** 3D Print Franca e Mocozim  
**Fonte:** [abertura de projeto](../abertura_de_projeto.md)  
**Versão:** 1.0 — 20/10/2026  
**Objetivo deste documento:** ordenar o desenvolvimento, fixar o que cada etapa entrega e apontar os requisitos que valem para todas elas.

A arquitetura de componentes, o modelo físico de dados e a escolha de runtime ficam para um documento próprio. Estes textos descrevem comportamento, limites e qualidade. Onde a abertura recomenda uma stack, isso aparece como premissa de trabalho, sujeita à discussão de arquitetura.

## 1. O que o projeto entrega

Um assistente de operação de e-commerce, hospedado em VPS, que concentra catálogo, anúncios, estoque, resultados, leads e pendências. O operador define regras e objetivos. O sistema acompanha resultados, prepara ações e registra o que foi aprovado ou rejeitado.

O primeiro uso é Shopee e TikTok Shop, com o UpSeller como ERP/hub. Publicação e qualquer ação com efeito financeiro ou compromisso com cliente permanecem sob aprovação humana até a política da etapa 5 liberar uma operação específica.

## 2. Como ler os documentos de etapa

Cada etapa tem código (`E0` a `E5`) e título. Cada requisito tem código, título, prioridade e descrição. O título é o nome curto da obrigação; a descrição diz como ela se verifica.

Cada etapa tem um documento com:

- objetivo, dependências e fora de escopo;
- requisitos funcionais (`RF-<etapa>-<nn>`);
- requisitos não funcionais (`RNF-<etapa>-<nn>`);
- critérios de aceite;
- pontos que a etapa precisa deixar decididos antes de seguir.

Identificadores transversais usam o prefixo `T` e valem em todas as etapas.

| Código | Título | Documento |
|---|---|---|
| T | Requisitos transversais | Este documento |
| E0 | Validação técnica | [Etapa 0 — Validação técnica](etapa-0-validacao-tecnica.md) |
| E1 | MVP do gerente | [Etapa 1 — MVP do gerente](etapa-1-mvp-do-gerente.md) |
| E2 | Fábrica de anúncios | [Etapa 2 — Fábrica de anúncios](etapa-2-fabrica-de-anuncios.md) |
| E3 | Análises e pesquisa | [Etapa 3 — Análises e pesquisa](etapa-3-analises-e-pesquisa.md) |
| E4 | Atendimento e qualificação | [Etapa 4 — Atendimento e qualificação](etapa-4-atendimento.md) |
| E5 | Automação controlada | [Etapa 5 — Automação controlada](etapa-5-automacao-controlada.md) |

Prioridade dentro da etapa:

- **Obrigatório:** a etapa não fecha sem isso.
- **Desejável:** entra se não atrasar o obrigatório.

## 3. Mapa das etapas

```text
Etapa 0  Validação técnica
   |
   v
Etapa 1  MVP do gerente  (cadastro, leitura, tarefas, auditoria, autonomia)
   |
   +------------------+------------------+
   v                  v                  v
Etapa 2            Etapa 3            Etapa 4
Fábrica de         Análises e         Atendimento
anúncios           pesquisa
   |                  |                  |
   +------------------+------------------+
                      v
                 Etapa 5
            Automação controlada
```

| Código | Título | Objetivo | Depende de | Entrega que desbloqueia a seguinte |
|---|---|---|---|---|
| E0 | Validação técnica | Saber o que UpSeller, Shopee e TikTok Shop realmente permitem nesta conta | Acesso do responsável às contas e às documentações | Matriz de capacidades e decisão de rascunho por canal |
| E1 | MVP do gerente | Operar cadastro, consulta, tarefas e aprovação num ambiente único | Decisão de leitura da E0 para cada conector ligado | Base de produtos, regras, logs e controle do que está liberado |
| E2 | Fábrica de anúncios | Produzir anúncio revisável e guardá-lo como rascunho versionado | E1; decisão de rascunho da E0 | Fila de aprovação e pacote pronto para publicação manual ou API |
| E3 | Análises e pesquisa | Explicar resultado e sugerir oportunidade com evidência | E1; métricas que a E0 tiver confirmado como legíveis | Relatório rastreável, alerta e registro de experimento |
| E4 | Atendimento e qualificação | Qualificar contato e entregar o lead ao humano | E1 (catálogo, custo e regras); escolha do canal de mensagem | Conversa registrada, pré-orçamento condicionado e handoff |
| E5 | Automação controlada | Ligar escrita externa operação por operação | Confiabilidade demonstrada na operação correspondente (E2 e/ou E4) | Política de limite, aprovação, log e rollback por operação |

A etapa 0 e a preparação de ambiente da etapa 1 podem andar em paralelo. Conector de leitura só entra no produto depois do veredito da etapa 0 para aquela capacidade. Conector de escrita só entra na etapa 5, e somente para a operação cujo veredito tenha sido “confirmada”.

As etapas 2, 3 e 4 podem avançar em paralelo depois da etapa 1. A etapa 3 fica mais útil quando a etapa 2 já grava versões de anúncio, porque a comparação antes/depois precisa dessa versão. A etapa 4 precisa de preço e custo cadastrados; precisa da fábrica de anúncios só quando a resposta citar conteúdo de anúncio ainda não publicado.

O sucesso do MVP descrito na abertura corresponde às etapas 0 a 4. A etapa 5 começa depois desse MVP.

## 4. Atores

| Ator | Onde atua |
|---|---|
| Operador | Dono da operação. Cadastra, pede trabalho ao gerente, revisa, aprova e desliga ações. |
| Cliente ou lead | Só na etapa 4, pelo canal de mensagem autorizado. |
| Gerente | Orquestra a solicitação, junta resultados e devolve plano, recomendação e pendências. |
| Papéis especialistas | Copywriter, designer, analista, pesquisador, atendimento e revisor. Na etapa 1 são contratos de entrada e saída sob o gerente, com processo separado apenas quando houver benefício claro. |

## 5. Requisitos transversais

Estes requisitos aparecem de novo só quando a etapa acrescenta detalhe. Uma etapa não os relaxa.

### 5.1 Funcionais

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-T-01 | Natureza do dado | Obrigatório | Todo valor exibido ou gravado carrega a natureza **confirmado**, **estimado** ou **ausente**. Valor ausente permanece ausente. O texto gerado declara a lacuna em vez de completar com suposição. |
| RF-T-02 | Efeito externo autorizado | Obrigatório | Efeito fora do sistema — publicar ou alterar anúncio, preço, estoque ou cadastro; responder cliente; assumir prazo ou estoque; conceder desconto fora da regra; emitir ou cancelar documento fiscal; reembolsar; gastar em anúncio; comprar insumo — só ocorre na etapa que o prevê e com a autorização exigida por essa etapa. |
| RF-T-03 | Trilha da execução | Obrigatório | Cada execução guarda: solicitante, papel que executou, dados consultados, ferramenta chamada, autorização, resultado e, quando houver, reversão. |
| RF-T-04 | Mudança por versão | Obrigatório | Regra permanente, preço vigente e procedimento mudam por nova versão revisada. Um feedback ou um resultado isolado fica registrado e aguarda promoção explícita. |
| RF-T-05 | Listas de preço separadas | Obrigatório | As modalidades **consumidor final**, **revenda à vista**, **revenda consignado** e **revenda — 10 peças** permanecem listas distintas. Cálculo de margem de canal usa a lista indicada para aquele canal e os custos vigentes daquele SKU. |
| RF-T-06 | Origem do número | Obrigatório | Relatório, recomendação e pré-orçamento informam período, origem de cada número e se o número é confirmado ou estimado. |
| RF-T-07 | Classes de ação | Obrigatório | O operador vê e altera o conjunto de classes de ação liberadas. Classe desligada recusa a execução e registra a recusa. |

### 5.2 Não funcionais

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RNF-T-01 | Segredos fora do repositório | Obrigatório | Token, senha e chave ficam em variável de ambiente ou cofre de segredo. Repositório, documentos e logs de auditoria exibidos ao operador recebem esses valores mascarados. |
| RNF-T-02 | Regras no caminho crítico | Obrigatório | Leitura e escrita de dados persistidos e chamada a API externa passam por regras de negócio versionadas. Prompt de papel especialista não é caminho de atualização de cadastro nem de API crítica. |
| RNF-T-03 | Escrita confirmada | Obrigatório | Escrita externa, quando existir, é idempotente, confirma o estado final na origem e emite alerta quando o estado final divergir do pedido. |
| RNF-T-04 | Privilégio mínimo | Obrigatório | Cada conector e cada papel recebem só as operações necessárias à etapa vigente. |
| RNF-T-05 | Auditoria acrescentada | Obrigatório | O registro de auditoria é acrescentado, com retenção definida pelo operador antes de dados reais de cliente ou de preço vigente entrarem no ambiente. |
| RNF-T-06 | Português e estilo | Obrigatório | Texto de anúncio, relatório ao operador e mensagem ao cliente sai em português. O registro de comunicação segue o estilo que o operador tiver aceito na memória operacional. |

## 6. Premissas herdadas da abertura

- Há um operador principal. O sistema atende duas marcas no mesmo ambiente: 3D Print Franca e Mocozim.
- UpSeller, Shopee e TikTok Shop são integrações a confirmar na etapa 0. A abertura já registra que o MCP público do UpSeller descreve consulta de armazém e estoque por SKU, e que edição de anúncio, fiscal, etiqueta e publicação precisam de confirmação na conta.
- A tabela comercial do PDF do Festival Jaguara e o plano de lançamento da Mocozim são fontes históricas. Preço vigente e status daquelas tarefas comerciais são confirmados pelo operador antes de uso.
- Metas numéricas de faturamento, lucro ou conversão entram quando o operador as cadastrar.
- WhatsApp é canal de uma fase posterior (etapa 4), depois de escolhida a plataforma e a política de dados.

## 7. Fora do escopo de todas as etapas de software

- Depósito de marca no INPI, compra de domínio, padronização de redes, impressão de lote piloto e demais itens do plano de lançamento da Mocozim. O sistema pode guardá-los depois como tarefas do operador; executá-los está fora do produto.
- Emissão fiscal, reembolso, mídia paga e compra de insumo como rotinas autônomas.
- Treinar ou alterar pesos de modelo a cada interação. Aprendizado operacional é registro de feedback, regra, fato verificado e resultado de experimento (RF-T-04).

## 8. Critério de sucesso do MVP, por etapa

| Critério da abertura | Etapa que o torna verdadeiro |
|---|---|
| Consultar só o que a fonte devolve, com lacuna explícita | E0 Validação técnica e E1 MVP do gerente |
| Produzir anúncio completo e imagens revisáveis a partir de ficha confiável | E2 Fábrica de anúncios |
| Guardar rascunho, versão, feedback e aprovação | E1 MVP do gerente (estrutura) e E2 Fábrica de anúncios (uso) |
| Gerar relatório rastreável e ação com evidência | E3 Análises e pesquisa |
| Qualificar conversa e transferir lead com resumo, dados e motivo | E4 Atendimento e qualificação |
| Medir custo por tarefa e deixar o responsável ligar ou desligar ações | E1 MVP do gerente, reforçado na E5 Automação controlada |

## 9. O que a discussão de arquitetura ainda precisa fechar

Estes documentos fixam obrigações. A arquitetura precisa responder, sem reabrir o comportamento:

1. Onde roda o gerente e como um papel especialista é invocado (mesmo processo, ferramenta ou agente separado).
2. Fronteira entre orquestração e API de regras de negócio.
3. Contratos mínimos de cada conector a partir da matriz da etapa 0.
4. Modelo de persistência de catálogo, versão de anúncio, lead, aprovação e auditoria.
5. O que é síncrono na interface e o que vai para fila.
6. Roteamento de modelo por tipo de tarefa, com critério de ferramenta, português, visão, latência e custo.
7. Como a aprovação humana entra no fluxo sem que o papel especialista publique por conta própria.
