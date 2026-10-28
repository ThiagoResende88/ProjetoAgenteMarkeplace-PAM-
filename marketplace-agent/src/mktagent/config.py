"""Configuracao central: caminhos, banco e credenciais.

Tudo que e ambiente vem de variaveis de ambiente ou do arquivo ``.env``
na raiz do projeto (nao versionado).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# marketplace-agent/src/mktagent/config.py -> marketplace-agent/
PROJETO = Path(__file__).resolve().parents[2]

MOEDA_PADRAO = "BRL"

# Canais de venda do negocio (marketplaces + canais proprios/B2B)
MARKETPLACES = (
    "shopee",
    "tiktok",
    "mercadolivre",
    "instagram",
    "consignacao",
    "direto",
    "outros",
)

NOMES_MARKETPLACE = {
    "shopee": "Shopee",
    "tiktok": "TikTok Shop",
    "mercadolivre": "Mercado Livre",
    "instagram": "Instagram (direto)",
    "consignacao": "Consignacao",
    "direto": "Venda direta",
    "outros": "Outros",
}

# Taxa total tipica por canal (comissao + taxa de pagamento), como Fracao.
# Servem de PADRAO para a calculadora; ajuste conforme seu plano real.
# Tarifas observadas na tela de liquidacao do TikTok Shop (27/10/2026):
# 10% de comissao + 6% de SFP + R$ 4,00 por item vendido.
TAXA_TIKTOK_COMISSAO = 0.10
TAXA_TIKTOK_SFP = 0.06
TAXA_TIKTOK_FIXO_CENTAVOS = 400

TAXAS_CANAL = {
    "shopee": "0.16",
    "tiktok": "0.10",
    "mercadolivre": "0.14",
    "instagram": "0.02",
    "consignacao": "0.00",
    "direto": "0.02",
    "outros": "0.10",
}

ALIASES_CANAL = {
    "shopee": "shopee",
    "tiktok": "tiktok",
    "tiktok shop": "tiktok",
    "tik tok": "tiktok",
    "mercado livre": "mercadolivre",
    "mercadolivre": "mercadolivre",
    "mercadolibre": "mercadolivre",
    "ml": "mercadolivre",
    "instagram": "instagram",
    "insta": "instagram",
    "direto": "direto",
    "consignacao": "consignacao",
    "consignado": "consignacao",
    "outros": "outros",
}


def normalizar_canal(valor: str | None, padrao: str = "outros") -> str:
    """Normaliza nome de canal/marketplace para uma chave de MARKETPLACES."""
    if not valor:
        return padrao
    chave = str(valor).strip().lower().replace("_", " ").replace("-", " ")
    return ALIASES_CANAL.get(chave, padrao)


def carregar_env(arquivo: Path | None = None) -> None:
    """Le um .env simples (KEY=VALOR) sem sobrescrever o ambiente atual."""
    arquivo = arquivo or PROJETO / ".env"
    if not arquivo.exists():
        return
    try:
        texto = arquivo.read_text(encoding="utf-8")
    except OSError:
        return
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave = chave.strip()
        valor = valor.strip().strip('"').strip("'")
        if chave and chave not in os.environ:
            os.environ[chave] = valor


def _bool(valor: str | None, padrao: bool = False) -> bool:
    if valor is None:
        return padrao
    return valor.strip().lower() in {"1", "true", "sim", "yes", "on"}


@dataclass(frozen=True)
class Credenciais:
    """Credenciais de uma integracao (vazias quando ainda nao configurada)."""

    app_id: str = ""
    app_secret: str = ""
    redirect_url: str = ""
    ambiente: str = "producao"
    regiao: str = "global"
    service_id: str = ""
    mcp_token: str = ""

    @property
    def configurada(self) -> bool:
        return bool(self.app_id and self.app_secret)

    def publica(self) -> dict[str, str]:
        """Versao segura para exibir (nunca expoe o segredo)."""
        return {
            "app_id": self.app_id,
            "app_secret_configurado": "sim" if self.app_secret else "nao",
            "redirect_url": self.redirect_url,
            "ambiente": self.ambiente,
            "regiao": self.regiao,
            "service_id": self.service_id,
            "mcp_token_configurado": "sim" if self.mcp_token else "nao",
        }


@dataclass(frozen=True)
class Config:
    projeto: Path
    dados: Path
    entradas: Path
    saidas: Path
    banco: Path
    moeda: str = MOEDA_PADRAO
    timezone: str = "America/Sao_Paulo"
    shopee: Credenciais = field(default_factory=Credenciais)
    tiktok: Credenciais = field(default_factory=Credenciais)
    upseller: Credenciais = field(default_factory=Credenciais)
    telegram_token: str = ""
    telegram_chat_id: str = ""
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_destino: str = ""

    def caminho_banco(self) -> Path:
        return self.banco

    @classmethod
    def carregar(cls, base: Path | None = None) -> "Config":
        carregar_env()
        projeto = (base or PROJETO).resolve()
        casa = Path(os.environ.get("MKT_HOME") or (projeto / "dados")).expanduser()
        banco_env = os.environ.get("MKT_DB")
        banco = Path(banco_env).expanduser() if banco_env else casa / "mkt.db"

        shopee = Credenciais(
            app_id=(os.environ.get("SHOPEE_PARTNER_ID") or "").strip(),
            app_secret=(os.environ.get("SHOPEE_PARTNER_KEY") or "").strip(),
            redirect_url=(os.environ.get("SHOPEE_REDIRECT_URL") or "").strip(),
            ambiente=(os.environ.get("SHOPEE_ENV") or "producao").strip().lower(),
            regiao=(os.environ.get("SHOPEE_REGIAO") or "br").strip().lower(),
        )
        tiktok = Credenciais(
            app_id=(os.environ.get("TIKTOK_APP_KEY") or "").strip(),
            app_secret=(os.environ.get("TIKTOK_APP_SECRET") or "").strip(),
            redirect_url=(os.environ.get("TIKTOK_REDIRECT_URL") or "").strip(),
            ambiente=(os.environ.get("TIKTOK_ENV") or "producao").strip().lower(),
            regiao=(os.environ.get("TIKTOK_REGIAO") or "row").strip().lower(),
            service_id=(os.environ.get("TIKTOK_SERVICE_ID") or "").strip(),
        )

        upseller = Credenciais(
            app_id=(os.environ.get("UPSELLER_CLIENT_ID") or "").strip(),
            app_secret=(os.environ.get("UPSELLER_API_TOKEN") or "").strip(),
            redirect_url="",
            ambiente="producao",
            regiao="br",
            mcp_token=(os.environ.get("UPSELLER_MCP_TOKEN") or "").strip(),
        )

        return cls(
            projeto=projeto,
            dados=casa,
            entradas=projeto / "entradas",
            saidas=Path(os.environ.get("MKT_SAIDAS") or (projeto / "saidas")).expanduser(),
            banco=banco,
            moeda=MOEDA_PADRAO,
            telegram_token=(os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip(),
            telegram_chat_id=(os.environ.get("TELEGRAM_CHAT_ID") or "").strip(),
            whatsapp_token=(os.environ.get("WHATSAPP_CLOUD_TOKEN") or "").strip(),
            whatsapp_phone_id=(os.environ.get("WHATSAPP_PHONE_NUMBER_ID") or "").strip(),
            whatsapp_destino=(os.environ.get("WHATSAPP_DESTINO") or "").strip(),
            shopee=shopee,
            tiktok=tiktok,
            upseller=upseller,
        )

    def garantir_pastas(self) -> None:
        for pasta in (self.dados, self.entradas, self.saidas):
            pasta.mkdir(parents=True, exist_ok=True)

    def nome_marketplace(self, chave: str) -> str:
        return NOMES_MARKETPLACE.get(chave.strip().lower(), chave)
