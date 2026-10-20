# Etapa 0 — Validação técnica

**Código:** E0  
**Título:** Validação técnica  
**Projeto:** Agente Gerente de E-commerce  
**Fonte:** [abertura de projeto](../abertura_de_projeto.md), seções 7 e 11  
**Versão:** 1.0 — 20/10/2026  
**Depende de:** acesso do operador às contas UpSeller, Shopee e TikTok Shop e à documentação vigente de cada uma.  
**Desbloqueia:** conectores de leitura da etapa 1 e a forma de rascunho da etapa 2.

## 1. Objetivo

Produzir uma matriz do que a conta realmente permite em UpSeller, Shopee e TikTok Shop, com evidência e data. A etapa entrega decisão, não funcionalidade de produto.

## 2. Fora de escopo

- Implementar o conector definitivo.
- Alterar anúncio, preço, estoque ou cadastro em produção.
- Escolher fornecedor de WhatsApp (isso abre a etapa 4).
- Tratar a existência de uma tela no ERP como prova de que a mesma operação existe em API.

## 3. Resultado obrigatório

Um relatório versionado, sem segredos, com uma linha por capacidade e uma decisão de rascunho por canal. Cada linha usa um destes vereditos:

| Veredito | Significado |
|---|---|
| Confirmada | Chamada ou procedimento autorizado funcionou no ambiente combinado, com evidência anexada. |
| Indisponível | Documentação da conta, escopo do app ou resposta do suporte exclui a capacidade. |
| Não verificada | Faltou acesso, sandbox ou resposta. A etapa seguinte trata a capacidade como ausente. |

## 4. Requisitos funcionais

### 4.1 UpSeller

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-0-01 | Plano e MCP do UpSeller | Obrigatório | O relatório registra plano contratado, se a API aberta está habilitada e quais ferramentas MCP aparecem para esta conta. |
| RF-0-02 | Matriz de capacidades do UpSeller | Obrigatório | Cada capacidade abaixo recebe veredito próprio: consultar armazéns; consultar estoque por SKU; ler produto; ler anúncio; editar anúncio; salvar rascunho; publicar; emitir ou consultar documento fiscal; imprimir etiqueta. |
| RF-0-03 | Prova de estoque do UpSeller | Obrigatório | Consulta de armazém e estoque por SKU, descritas na documentação pública, são provadas com chamada real quando o plano permitir. O resultado de exemplo entra no relatório com identificadores mascarados. |

### 4.2 Shopee e TikTok Shop

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-0-04 | Acesso de desenvolvedor nos marketplaces | Obrigatório | Para cada marketplace, o relatório registra app de desenvolvedor, tipo de autorização (vendedor ou parceiro), escopos concedidos e se a conta é a conta brasileira da operação. |
| RF-0-05 | Matriz de capacidades dos marketplaces | Obrigatório | Cada capacidade abaixo recebe veredito próprio, separado por canal: ler produto; ler anúncio; ler métricas de resultado (visualização, clique, conversão, pedido, cancelamento, devolução); enviar imagem; salvar rascunho não publicado; criar anúncio; editar anúncio; publicar. |
| RF-0-06 | Limites e restrições do app | Obrigatório | Limite de uso, pré-requisito de revisão do app e qualquer restrição de publicação constam na mesma linha da capacidade. |

### 4.3 Provas

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-0-07 | Prova de leitura com SKU real | Obrigatório | Prova de leitura, quando a permissão existir, cobre ao menos um SKU real de cada marca que já esteja no canal: identificador, estoque e campos de anúncio disponíveis. |
| RF-0-08 | Prova de escrita em ambiente seguro | Obrigatório | Prova de escrita só ocorre em ambiente seguro indicado pelo operador, com autorização registrada antes da chamada. O relatório guarda estado anterior, pedido e estado posterior. |
| RF-0-09 | Escrita sem sandbox | Obrigatório | Se não houver ambiente seguro, o veredito de escrita permanece **não verificada**. A etapa 2 usa rascunho interno e exportação manual para esse canal. |
| RF-0-10 | Decisão de rascunho por canal | Obrigatório | Ao final, cada canal recebe uma decisão única: **rascunho na plataforma**, **rascunho interno** ou **exportação para lançamento manual**. A decisão cita os vereditos que a sustentam. |
| RF-0-11 | Catálogo de leitura para a E1 | Desejável | O relatório lista endpoints ou ferramentas que a etapa 1 pode chamar em modo leitura, com o nome estável usado na documentação consultada. |

### 4.4 Rastreio da consulta

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RF-0-12 | Fonte e data da conclusão | Obrigatório | Cada conclusão cita a origem: documentação (URL e data de leitura), painel da conta ou resultado de chamada. |
| RF-0-13 | Veredito independente do ERP | Obrigatório | Uma integração visível no ERP gera veredito próprio. Ela não herda veredito de outra integração. |

## 5. Requisitos não funcionais

| ID | Título | Prioridade | Requisito |
|---|---|---|---|
| RNF-0-01 | Prova sem efeito em produção | Obrigatório | Nenhuma prova grava em anúncio, preço, estoque ou cadastro de produção. |
| RNF-0-02 | Relatório sem credencial | Obrigatório | O relatório versionado contém zero credencial, token, cookie ou senha. Evidência de chamada mostra cabeçalhos sensíveis mascarados. |
| RNF-0-03 | Validade de 90 dias | Obrigatório | A data da verificação fica em cada linha. Veredito com mais de 90 dias é revalidado antes de a etapa 2 ou a etapa 5 depender dele. |
| RNF-0-04 | Relatório implementável | Obrigatório | O relatório é legível por quem for implementar o conector sem precisar repetir a descoberta: capacidade, veredito, evidência, limite e decisão de rascunho. |
| RNF-0-05 | Roteiro repetível de leitura | Desejável | As provas de leitura são repetíveis com um roteiro curto (conta, escopo, chamada, resultado esperado). |

## 6. Critérios de aceite

1. UpSeller, Shopee e TikTok Shop têm matriz completa, inclusive linhas **não verificada**.
2. Existe decisão de rascunho para Shopee e para TikTok Shop.
3. Provas que rodaram têm evidência; provas que não rodaram têm o motivo.
4. O relatório passou por leitura do operador e está referenciado como insumo da etapa 1.

## 7. Pontos que permanecem abertos até o relatório existir

- Se o UpSeller desta conta edita anúncio, publica, emite fiscal ou imprime etiqueta.
- Se Shopee e TikTok Shop, com as credenciais aprovadas, salvam rascunho real via API.
- Quais métricas cada canal devolve para a etapa 3.

Enquanto um item estiver aberto, as etapas seguintes usam o comportamento de **não verificada**: leitura ausente, escrita desligada, rascunho interno.
