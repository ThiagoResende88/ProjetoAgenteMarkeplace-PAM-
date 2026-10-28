"""Cliente do UpSeller (ERP): API aberta de estoque/armazens.

Verificado na documentacao oficial (Central de Ajuda UpSeller, 2026):
- recurso disponivel nos planos Profissional+ e Plano Kit;
- credenciais em Painel UpSeller -> Plataforma Aberta -> API Privada:
  User ID, API Token (API tradicional) e MCP Token (conexao MCP);
- API: POST https://openapi.upseller.com/erp/inventory/getWarehouseList/v1
       POST https://openapi.upseller.com/erp/inventory/pageWarehouseSku/v1
- headers: X-Upseller-Client-Id (User ID) e X-Upseller-Api-Token;
- MCP: https://openapi.upseller.com/mcp (Streamable HTTP), mesmos headers,
  usando o MCP Token como valor de X-Upseller-Api-Token.

ATENCAO: o corpo exato de `pageWarehouseSku` (nomes de campos/paginacao) nao foi
possivel confirmar na documentacao publica; o cliente usa PageNo/PageSize e
devolve o erro da API sem esconder. Valide com suas credenciais antes de confiar.
"""

from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.request

from .. import db
from ..config import Config

BASE = "https://openapi.upseller.com"
MCP_URL = f"{BASE}/mcp"
CAMINHO_ARMAZENS = "/erp/inventory/getWarehouseList/v1"
CAMINHO_ESTOQUE = "/erp/inventory/pageWarehouseSku/v1"

CAMPOS_SKU = ("sku", "sellerSku", "seller_sku", "productSku", "skuCode", "code")
CAMPOS_QTD = ("quantity", "qty", "stock", "availableQuantity", "availableStock", "inventoryQuantity")
CAMPOS_ARMAZEM = ("warehouseId", "warehouse_id", "id")
CAMPOS_NOME_ARMAZEM = ("warehouseName", "name", "warehouse_name")


def headers(config: Config, usar_mcp_token: bool = False) -> dict[str, str]:
    token = config.upseller.mcp_token if usar_mcp_token else config.upseller.app_secret
    return {
        "Content-Type": "application/json",
        "X-Upseller-Client-Id": config.upseller.app_id,
        "X-Upseller-Api-Token": token,
        "X-Upseller-Language": "pt",
    }


class UpSellerNaoConfigurado(ValueError):
    pass


def disponivel(config: Config) -> bool:
    return bool(config.upseller.app_id and config.upseller.app_secret)


def _post(config: Config, caminho: str, corpo: dict, timeout: int = 30) -> dict:
    if not disponivel(config):
        raise UpSellerNaoConfigurado(
            "UpSeller nao configurado. Preencha UPSELLER_CLIENT_ID e UPSELLER_API_TOKEN "
            "no .env (Painel UpSeller -> Plataforma Aberta -> API Privada) e rode "
            "'mkt upseller status'."
        )
    requisicao = urllib.request.Request(
        BASE + caminho,
        data=json.dumps(corpo).encode("utf-8"),
        headers=headers(config),
        method="POST",
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=timeout) as resposta:
            texto = resposta.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as erro:
        corpo_erro = erro.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"HTTP {erro.code} do UpSeller: {corpo_erro}") from erro
    except urllib.error.URLError as erro:
        raise RuntimeError(f"nao consegui falar com o UpSeller: {erro.reason}") from erro
    try:
        return json.loads(texto)
    except json.JSONDecodeError as erro:
        raise RuntimeError(f"resposta nao-JSON do UpSeller: {texto[:300]}") from erro


def _dados(resposta: dict) -> dict:
    """Extrai o objeto de dados de respostas com formatos variados."""
    if not isinstance(resposta, dict):
        return {}
    for chave in ("data", "result", "payload"):
        valor = resposta.get(chave)
        if isinstance(valor, dict):
            return valor
    return resposta


def _achar(objeto: dict, candidatos: tuple[str, ...]):
    if not isinstance(objeto, dict):
        return None
    baixo = {str(chave).lower(): valor for chave, valor in objeto.items()}
    for candidato in candidatos:
        if candidato.lower() in baixo:
            return baixo[candidato.lower()]
    return None


def listar_armazens(config: Config) -> dict:
    resposta = _post(config, CAMINHO_ARMAZENS, {})
    dados = _dados(resposta)
    lista = dados.get("list") or dados.get("warehouses") or dados.get("records") or []
    if not isinstance(lista, list):
        lista = []
    return {
        "bruto": resposta,
        "armazens": [
            {
                "id": _achar(item, CAMPOS_ARMAZEM),
                "nome": _achar(item, CAMPOS_NOME_ARMAZEM),
            }
            for item in lista
            if isinstance(item, dict)
        ],
    }


def listar_estoque(config: Config, pagina: int = 1, tamanho: int = 200) -> dict:
    corpo = {"PageNo": max(1, int(pagina)), "PageSize": max(1, min(500, int(tamanho)))}
    resposta = _post(config, CAMINHO_ESTOQUE, corpo)
    dados = _dados(resposta)
    lista = dados.get("list") or dados.get("records") or dados.get("skus") or []
    if not isinstance(lista, list):
        lista = []
    total = dados.get("total") or dados.get("totalCount") or dados.get("count")
    return {"bruto": resposta, "total": total, "itens": lista}


def sincronizar_estoque(conn: sqlite3.Connection, config: Config, max_paginas: int = 20) -> dict:
    """Baixa a posicao de estoque do UpSeller e atualiza a tabela ``estoque``.

    O SKU do marketplace e casado pelo campo de SKU do vendedor. Itens cujo SKU
    nao foi identificado aparecem em ``nao_mapeados`` (amostra) para diagnostico.
    """
    import datetime as dt

    if not disponivel(config):
        raise UpSellerNaoConfigurado(
            "UpSeller nao configurado: preencha UPSELLER_CLIENT_ID e UPSELLER_API_TOKEN no .env."
        )

    atualizados = 0
    nao_mapeados: list[dict] = []
    amostra_schema: dict | None = None
    paginas = 0
    total_declarado = None

    for pagina in range(1, max_paginas + 1):
        resultado = listar_estoque(config, pagina=pagina)
        itens = resultado["itens"]
        paginas += 1
        if total_declarado is None:
            total_declarado = resultado.get("total")
        if not itens:
            break
        if amostra_schema is None:
            amostra_schema = {chave: type(valor).__name__ for chave, valor in itens[0].items()}
        for item in itens:
            sku = _achar(item, CAMPOS_SKU)
            quantidade = _achar(item, CAMPOS_QTD)
            if not sku or quantidade is None:
                if len(nao_mapeados) < 10:
                    nao_mapeados.append(item)
                continue
            try:
                qtd = max(0, int(float(quantidade)))
            except (TypeError, ValueError):
                continue
            conn.execute(
                "INSERT INTO estoque (sku, quantidade, atualizado_em) VALUES (?,?,?) "
                "ON CONFLICT(sku) DO UPDATE SET quantidade=excluded.quantidade, "
                "atualizado_em=excluded.atualizado_em",
                (str(sku), qtd, dt.date.today().isoformat()),
            )
            atualizados += 1
        if len(itens) < 200:
            break

    db.registrar_importacao(
        conn,
        {
            "arquivo": "upseller:estoque",
            "tipo": "estoque",
            "linhas": atualizados + len(nao_mapeados),
            "inseridos": 0,
            "atualizados": atualizados,
            "ignorados": len(nao_mapeados),
            "avisos": "sincronizado via UpSeller API",
        },
    )
    return {
        "status": "ok",
        "origem": "upseller",
        "paginas": paginas,
        "total_declarado": total_declarado,
        "skus_atualizados": atualizados,
        "nao_mapeados_amostra": nao_mapeados,
        "schema_amostra": amostra_schema,
        "avisos": (
            ["Alguns itens nao tinham SKU/quantidade reconheciveis; veja nao_mapeados_amostra "
             "e confirme o schema no GUIA_UPSELER.md."]
            if nao_mapeados
            else []
        ),
    }


def status(config: Config) -> dict:
    dados = config.upseller.publica()
    dados["status"] = (
        "credenciais preenchidas — pode sincronizar estoque"
        if disponivel(config)
        else "nao configurado — exporte as planilhas do UpSeller manualmente"
    )
    dados["mcp_url"] = MCP_URL
    dados["mcp_token_configurado"] = "sim" if config.upseller.mcp_token else "nao"
    dados["passos"] = [
        "No UpSeller: Plataforma Aberta -> API Privada -> Gerar (somente planos Profissional/Empresarial; Inicial e Avancado nao tem API/MCP).",
        "Copie User ID, API Token e MCP Token.",
        "Preencha UPSELLER_CLIENT_ID e UPSELLER_API_TOKEN no .env do projeto.",
        "Rode 'mkt upseller status' e depois 'mkt upseller sincronizar-estoque'.",
        "Para conectar o MCP oficial do UpSeller direto no DSH, veja docs/GUIA_UPSELER.md.",
    ]
    return dados


__all__ = [
    "MCP_URL",
    "UpSellerNaoConfigurado",
    "disponivel",
    "headers",
    "listar_armazens",
    "listar_estoque",
    "sincronizar_estoque",
    "status",
]
