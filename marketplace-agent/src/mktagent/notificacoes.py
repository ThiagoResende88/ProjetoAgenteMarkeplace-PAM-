"""Notificacoes: Telegram (simples) e WhatsApp Cloud API (Meta).

Por que Telegram primeiro: criar um bot leva ~2 minutos no @BotFather, nao exige
aprovacao de empresa e funciona no celular. WhatsApp oficial exige conta
WhatsApp Business, verificacao na Meta, numero dedicado, token e webhook.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from .config import Config

LIMITE_TELEGRAM = 4000
LIMITE_WHATSAPP = 4000


def telegram_configurado(config: Config) -> bool:
    return bool(config.telegram_token and config.telegram_chat_id)


def whatsapp_configurado(config: Config) -> bool:
    return bool(config.whatsapp_token and config.whatsapp_phone_id and config.whatsapp_destino)


def _post_json(url: str, corpo: dict, cabecalhos: dict, timeout: int = 20) -> dict:
    requisicao = urllib.request.Request(
        url,
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json", **cabecalhos},
        method="POST",
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=timeout) as resposta:
            return json.loads(resposta.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode("utf-8", errors="replace")[:600]
        raise RuntimeError(f"HTTP {erro.code} ao enviar notificacao: {detalhe}") from erro
    except urllib.error.URLError as erro:
        raise RuntimeError(f"sem conexao para enviar notificacao: {erro.reason}") from erro


def enviar_telegram(
    config: Config,
    texto: str,
    token: str | None = None,
    chat_id: str | None = None,
) -> dict:
    token = token or config.telegram_token
    chat_id = chat_id or config.telegram_chat_id
    if not token or not chat_id:
        raise ValueError(
            "Telegram nao configurado. Crie um bot no @BotFather, pegue o token, "
            "descubra seu chat_id (@userinfobot) e preencha TELEGRAM_BOT_TOKEN e "
            "TELEGRAM_CHAT_ID no .env."
        )
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("mensagem vazia")
    resposta = _post_json(
        f"https://api.telegram.org/bot{token}/sendMessage",
        {"chat_id": chat_id, "text": texto[:LIMITE_TELEGRAM], "disable_web_page_preview": True},
        {},
    )
    if not resposta.get("ok"):
        raise RuntimeError(f"Telegram recusou a mensagem: {resposta}")
    return {
        "canal": "telegram",
        "status": "enviado",
        "caracteres": len(texto),
        "mensagem_id": resposta.get("result", {}).get("message_id"),
    }


def enviar_whatsapp(
    config: Config,
    texto: str,
    token: str | None = None,
    phone_id: str | None = None,
    destino: str | None = None,
) -> dict:
    token = token or config.whatsapp_token
    phone_id = phone_id or config.whatsapp_phone_id
    destino = destino or config.whatsapp_destino
    if not token or not phone_id or not destino:
        raise ValueError(
            "WhatsApp Cloud API nao configurado. Precisa de WHATSAPP_CLOUD_TOKEN, "
            "WHATSAPP_PHONE_NUMBER_ID e WHATSAPP_DESTINO (com DDI, ex.: 5516999999999)."
        )
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("mensagem vazia")
    resposta = _post_json(
        f"https://graph.facebook.com/v21.0/{phone_id}/messages",
        {
            "messaging_product": "whatsapp",
            "to": destino,
            "type": "text",
            "text": {"preview_url": False, "body": texto[:LIMITE_WHATSAPP]},
        },
        {"Authorization": f"Bearer {token}"},
    )
    return {
        "canal": "whatsapp",
        "status": "enviado",
        "caracteres": len(texto),
        "resposta": resposta,
    }


def montar_digest(servico) -> str:
    """Resumo do dia para enviar no celular (curto, sem tabela)."""
    resumo = servico.resumo()
    dre = resumo.get("ultimo_mes", {}).get("dre", {})
    dados = resumo.get("dados", {})
    alertas = servico.alertas()
    caixa = servico.caixa(30)
    linhas = [
        "*Gestor de Marketplaces — resumo*",
        f"Pedidos na base: {dados.get('pedidos', 0)} | mes: {resumo.get('ultimo_mes', {}).get('mes_extenso', '-')}",
    ]
    if dre.get("receita_bruta"):
        linhas += [
            f"Receita bruta: {dre.get('receita_bruta')}",
            f"Margem contrib.: {dre.get('margem_contribuicao')} ({dre.get('margem_contribuicao_pct')})",
            f"Lucro: {dre.get('lucro_liquido')} ({dre.get('lucro_liquido_pct')})",
        ]
    linhas += [
        f"Caixa 30d: {caixa.get('saldo_do_periodo')} | vencido a pagar: {caixa.get('vencido_a_pagar')}",
        f"Alertas: {alertas.get('total', 0)} "
        f"(alta {alertas.get('resumo', {}).get('alta', 0)}, "
        f"media {alertas.get('resumo', {}).get('media', 0)})",
    ]
    for alerta in alertas.get("alertas", [])[:4]:
        linhas.append(f"- [{alerta['severidade'].upper()}] {alerta['titulo']}")
    linhas.append("Detalhes: abra o agente e peça 'resumo do dia'.")
    return "\n".join(linhas)[:LIMITE_TELEGRAM]


def enviar_digest(servico, canal: str = "telegram") -> dict:
    texto = montar_digest(servico)
    config = servico.config
    if canal == "telegram":
        return enviar_telegram(config, texto)
    if canal == "whatsapp":
        return enviar_whatsapp(config, texto)
    raise ValueError("canal deve ser 'telegram' ou 'whatsapp'")


__all__ = [
    "enviar_digest",
    "enviar_telegram",
    "enviar_whatsapp",
    "montar_digest",
    "telegram_configurado",
    "whatsapp_configurado",
]
