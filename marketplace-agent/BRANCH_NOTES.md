# Branch `feature/marketplace-agent`

Esta branch isola o **código do agente de marketplaces** para revisão, sem alterar a
`main` do projeto PAM.

## O que está aqui

- `src/mktagent/` — biblioteca, importadores, financeiro, operação, API Shopee/TikTok.
- `tests/` — suíte unittest.
- `scripts/` — geradores/utilitários e instalador do DSH.
- `bin/mkt`, `bin/mkt-mcp` — launchers.
- `skills/`, `dsh/` — skills e patch do agente no DSH.
- `examples/` — planilhas fictícias (sem dados reais).
- `docs/` — arquitetura, pesquisa das APIs e guias genéricos.

## O que ficou de fora (de propósito)

- `.env`, banco SQLite, tokens e credenciais.
- `dados/`, `saidas/`, `entradas/` e `todo/` (dados operacionais e entregáveis locais).
- Documentos com dados financeiros/do negócio (custos, pedidos, B2B, plano, EasyPU).
- A demo pública fica na branch `gh-pages` (GitHub Pages), não aqui.

## Como rodar

```sh
python3 -m unittest discover -s tests -t .   # testes
./bin/mkt demo --limpar                      # cenário fictício
./bin/mkt resumo
```

O modo planilha funciona sem credenciais. A integração Shopee/TikTok é fase 2 e
depende de app aprovado + credenciais locais (não versionadas).
