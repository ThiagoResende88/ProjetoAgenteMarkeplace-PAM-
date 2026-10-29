"""Integracoes com as APIs oficiais (fase 2).

O modo principal do projeto hoje e importacao de planilhas, que nao exige
credenciais. Este pacote deixa o caminho da API pronto:

- URLs de producao e sandbox;
- fluxo OAuth (autorizacao + troca de code + refresh);
- assinatura HMAC-SHA256 de cada request;
- status do que falta configurar.

Nada aqui e chamado automaticamente: o agente so usa a API quando as
credenciais existem e o usuario pede para sincronizar.
"""

from __future__ import annotations

from ..config import Config

PASSOS_SITE = {
    "upseller": [
        "No UpSeller: Plataforma Aberta -> API Privada -> Gerar (planos Profissional+ ou Kit).",
        "Copie User ID, API Token e MCP Token.",
        "Preencha UPSELLER_CLIENT_ID e UPSELLER_API_TOKEN no .env do projeto.",
        "Rode 'mkt upseller status' e depois 'mkt upseller sincronizar-estoque'.",
        "Para ligar o MCP oficial do UpSeller no DSH, veja docs/GUIA_UPSELER.md.",
    ],
}

PASSOS = {
    "shopee": [
        "Crie uma conta de desenvolvedor em https://open.shopee.com e registre um app.",
        "Copie o Partner ID e a Partner Key para o .env (SHOPEE_PARTNER_ID / SHOPEE_PARTNER_KEY).",
        "Cadastre a Redirect URL do app (ex.: http://localhost:8765/shopee/callback).",
        "Comece no sandbox: SHOPEE_ENV=sandbox e use uma loja de teste.",
        "Rode 'mkt status' para conferir o que falta.",
    ],
    "tiktok": [
        "Crie um app no TikTok Shop Partner Center (https://partner.tiktokshop.com).",
        "Copie App Key e App Secret para o .env (TIKTOK_APP_KEY / TIKTOK_APP_SECRET).",
        "Cadastre a Redirect URL autorizada no painel do app.",
        "Use o ambiente sandbox primeiro (TIKTOK_ENV=sandbox).",
        "Rode 'mkt status' para conferir o que falta.",
    ],
}


def status_credenciais(marketplace: str, config: Config) -> dict:
    if marketplace == "upseller":
        from . import upseller

        dados = upseller.status(config)
        dados["guia"] = "docs/GUIA_UPSELER.md"
        return dados
    credenciais = config.shopee if marketplace == "shopee" else config.tiktok
    dados = credenciais.publica()
    dados["status"] = (
        "credenciais preenchidas — pronto para testar a API"
        if credenciais.configurada
        else "nao configurada — usando importacao de planilhas"
    )
    dados["passos"] = PASSOS.get(marketplace, [])
    dados["guia"] = "GUIA_CREDENCIAIS.md"
    return dados


def sincronizar(
    marketplace: str,
    desde: str | None = None,
    ate: str | None = None,
    config: Config | None = None,
) -> dict:
    """Ponto de entrada da sincronizacao via API (fase 2)."""
    config = config or Config.carregar()
    credenciais = config.shopee if marketplace == "shopee" else config.tiktok
    if marketplace not in {"shopee", "tiktok"}:
        raise ValueError("marketplace deve ser 'shopee' ou 'tiktok'")
    if not credenciais.configurada:
        return {
            "status": "nao_configurado",
            "marketplace": marketplace,
            "mensagem": (
                "A API ainda nao esta configurada. O modo planilha continua "
                "funcionando normalmente."
            ),
            "passos": PASSOS.get(marketplace, []),
            "guia": "GUIA_CREDENCIAIS.md",
        }
    return {
        "status": "api_em_implantacao",
        "marketplace": marketplace,
        "desde": desde,
        "ate": ate,
        "mensagem": (
            "Credenciais encontradas, mas a sincronizacao automatica ainda nao "
            "foi validada contra o sandbox. Enquanto isso, importe o relatorio "
            "exportado do painel com 'mkt importar pedidos'."
        ),
        "proximo_passo": (
            "Preencha o CLIENTE/API conforme o GUIA_CREDENCIAIS.md e rode "
            "'mkt sincronizar --teste' (a ser implementado na fase 2)."
        ),
    }


__all__ = ["PASSOS", "sincronizar", "status_credenciais"]
