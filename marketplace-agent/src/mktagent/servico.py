"""Fachada de servico: uma API unica usada pela CLI e pelo servidor MCP.

Regra: toda leitura/escrita passa por aqui. A CLI e o agente (via MCP) nunca
falam direto com o banco.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from . import db
from .config import Config
from .datas import fmt_mes, mes_atual, normalizar_mes
from .dinheiro import fmt_brl
from .dominio import ResultadoImportacao
from .criativos import briefing_imagens as _briefing_imagens
from .criativos import gerar_criativo as _gerar_criativo
from .financeiro import (
    alertas as relatorio_alertas,
    cobertura_estoque,
    comparativo,
    criar_conta as _criar_conta,
    dados_disponiveis,
    dre as _dre,
    fluxo_caixa,
    insights as _insights,
    marcar_paga as _marcar_paga,
    margem_por_sku,
    resumo_contas as _resumo_contas,
)
from .ingestao import importar as _importar
from .operacao import (
    atualizar_status_pedido as _atualizar_status_pedido,
    criar_pedido as _criar_pedido,
    listar_pedidos,
    listar_produtos,
    registrar_custo as _registrar_custo,
)

EXTENSOES = {".csv", ".tsv", ".txt", ".xlsx", ".xls"}


class Servico:
    def __init__(self, config: Config | None = None):
        self.config = config or Config.carregar()
        self.config.garantir_pastas()

    # ── infraestrutura ─────────────────────────────────────────────────────

    @contextmanager
    def _conexao(self) -> Iterator[sqlite3.Connection]:
        with db.abrir(self.config) as conn:
            yield conn

    def resolver_caminho(self, caminho: str | Path) -> Path:
        candidato = Path(str(caminho)).expanduser()
        tentativas: list[Path] = []
        if candidato.is_absolute():
            tentativas.append(candidato)
        else:
            tentativas.extend(
                [
                    Path.cwd() / candidato,
                    self.config.entradas / candidato,
                    self.config.projeto / candidato,
                ]
            )
        for tentativa in tentativas:
            if tentativa.exists():
                return tentativa.resolve()
        listados = ", ".join(t.name for t in self.config.entradas.glob("*") if t.is_file())
        raise FileNotFoundError(
            f"arquivo nao encontrado: {caminho}. Procurei em: "
            + ", ".join(str(t) for t in tentativas)
            + (f". Arquivos em entradas/: {listados}" if listados else
               f". Coloque a planilha em {self.config.entradas}")
        )

    # ── panorama ───────────────────────────────────────────────────────────

    def resumo(self) -> dict:
        with self._conexao() as conn:
            dados = dados_disponiveis(conn)
            ultimo = dados["ultimo_mes"] or mes_atual()
            try:
                dre_mes = _dre(conn, ultimo, incluir_por_marketplace=False)
            except Exception as erro:
                dre_mes = {"aviso": f"nao foi possivel calcular o DRE: {erro}"}
            alertas_calc = relatorio_alertas(conn)
            contas = _resumo_contas(conn, "aberta")
            proximas = contas["contas"][:5]

        return {
            "banco": str(self.config.banco),
            "dados": dados,
            "ultimo_mes": {
                "mes": ultimo,
                "mes_extenso": fmt_mes(ultimo),
                "dre": dre_mes,
            },
            "alertas": {
                "total": alertas_calc["total"],
                "resumo": alertas_calc["resumo"],
                "titulos": [a["titulo"] for a in alertas_calc["alertas"][:5]],
            },
            "proximas_contas": [
                {
                    "descricao": c["descricao"],
                    "tipo": c["tipo"],
                    "valor": c["valor"],
                    "vencimento": c["vencimento_fmt"],
                }
                for c in proximas
            ],
            "integracoes": self.status_integracoes(),
            "modo_atual": "planilhas (importacao manual)",
            "como_usar": [
                "Coloque os relatorios exportados dos paineis em "
                f"{self.config.entradas} e peça para importar.",
                "Use as ferramentas mcp__marketplaces__* para consultar DRE, margem, "
                "caixa e alertas.",
                "Cadastre custo por SKU para a margem ficar confiavel.",
            ],
        }

    # ── importacao ─────────────────────────────────────────────────────────

    def importar(
        self,
        tipo: str,
        caminho: str | Path,
        marketplace: str | None = None,
        conta: str = "principal",
        dry_run: bool = False,
    ) -> dict:
        arquivo = self.resolver_caminho(caminho)
        if arquivo.suffix.lower() not in EXTENSOES:
            raise ValueError(
                f"extensao {arquivo.suffix!r} nao suportada. Use CSV ou XLSX."
            )
        with self._conexao() as conn:
            resultado: ResultadoImportacao = _importar(
                conn,
                tipo,
                arquivo,
                marketplace=marketplace,
                conta=conta,
                dry_run=dry_run,
            )
        dados = resultado.para_dict()
        dados["dry_run"] = dry_run
        dados["mensagem"] = _mensagem_importacao(resultado, dry_run)
        return dados

    def importar_pasta(
        self,
        tipo: str | None = None,
        marketplace: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Importa todos os arquivos suportados da pasta ``entradas/``."""
        arquivos = sorted(
            p for p in self.config.entradas.iterdir()
            if p.is_file() and p.suffix.lower() in EXTENSOES
        )
        if not arquivos:
            return {
                "mensagem": f"nenhuma planilha em {self.config.entradas}",
                "importados": [],
            }
        resultados = []
        for arquivo in arquivos:
            tipo_arquivo = tipo or _tipo_por_nome(arquivo.name)
            if tipo_arquivo is None:
                resultados.append(
                    {
                        "arquivo": arquivo.name,
                        "status": "ignorado",
                        "motivo": "nao consegui inferir o tipo pelo nome; "
                        "informe o tipo manualmente",
                    }
                )
                continue
            try:
                resultados.append(
                    self.importar(
                        tipo_arquivo,
                        arquivo,
                        marketplace=marketplace,
                        dry_run=dry_run,
                    )
                )
            except Exception as erro:
                resultados.append(
                    {"arquivo": arquivo.name, "status": "erro", "erro": str(erro)}
                )
        return {"pasta": str(self.config.entradas), "dry_run": dry_run, "importados": resultados}

    # ── relatorios ─────────────────────────────────────────────────────────

    def dre(self, mes: str | None = None, marketplace: str | None = None) -> dict:
        with self._conexao() as conn:
            return _dre(conn, mes, marketplace)

    def comparativo(self, mes: str | None = None) -> dict:
        with self._conexao() as conn:
            return comparativo(conn, mes)

    def margem(
        self,
        mes: str | None = None,
        dias: int | None = None,
        limite: int | None = None,
        marketplace: str | None = None,
        margem_alvo: float = 0.20,
    ) -> dict:
        from decimal import Decimal

        with self._conexao() as conn:
            return margem_por_sku(
                conn,
                mes=mes,
                dias=dias,
                limite=limite,
                marketplace=marketplace,
                margem_alvo=Decimal(str(margem_alvo)),
            )

    def caixa(self, dias: int = 30) -> dict:
        with self._conexao() as conn:
            return fluxo_caixa(conn, dias=dias)

    def alertas(self) -> dict:
        with self._conexao() as conn:
            return relatorio_alertas(conn)

    def estoque(self, dias: int = 30) -> dict:
        with self._conexao() as conn:
            return cobertura_estoque(conn, dias=dias)

    def insights(self, mes: str | None = None) -> dict:
        with self._conexao() as conn:
            return _insights(conn, mes)

    def desempenho(self, canal: str | None = None, dias: int = 30) -> dict:
        from .financeiro.desempenho import desempenho as _desempenho

        with self._conexao() as conn:
            return _desempenho(conn, canal=canal, dias=dias)

    def precificar_3d(self, **kwargs) -> dict:
        from .precificacao import precificar_3d

        return precificar_3d(**kwargs)

    # ── notificacoes ───────────────────────────────────────────────────────

    def notificacoes_status(self) -> dict:
        from . import notificacoes

        return {
            "telegram": {
                "configurado": notificacoes.telegram_configurado(self.config),
                "chat_id": self.config.telegram_chat_id or None,
                "como_configurar": [
                    "No celular, fale com @BotFather -> /newbot -> copie o token.",
                    "Fale com @userinfobot para descobrir seu chat_id.",
                    "Preencha TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env.",
                    "Teste: 'mkt telegram testar'.",
                ],
            },
            "whatsapp": {
                "configurado": notificacoes.whatsapp_configurado(self.config),
                "destino": self.config.whatsapp_destino or None,
                "como_configurar": [
                    "Exige WhatsApp Business Platform (Meta for Developers) com numero verificado.",
                    "Crie um app, ative WhatsApp, obtenha token e phone_number_id.",
                    "Preencha WHATSAPP_CLOUD_TOKEN, WHATSAPP_PHONE_NUMBER_ID e WHATSAPP_DESTINO.",
                    "Teste: 'mkt whatsapp testar'.",
                ],
            },
        }

    def enviar_telegram(self, texto: str | None = None, tipo: str = "texto") -> dict:
        from . import notificacoes

        if tipo == "digest" or not texto:
            return notificacoes.enviar_digest(self, "telegram")
        return notificacoes.enviar_telegram(self.config, texto)

    def enviar_whatsapp(self, texto: str | None = None, tipo: str = "texto") -> dict:
        from . import notificacoes

        if tipo == "digest" or not texto:
            return notificacoes.enviar_digest(self, "whatsapp")
        return notificacoes.enviar_whatsapp(self.config, texto)

    # ── criativos (texto e imagem) ─────────────────────────────────────────

    def gerar_criativo(
        self,
        sku: str,
        beneficios: list[str] | None = None,
        formato: str = "quadrado",
        tema: str = "claro",
        preco: object = None,
        titulo: str | None = None,
        selo: str | None = None,
        foto: str | None = None,
        modelo: str = "card",
        logo: str | None = None,
    ) -> dict:
        with self._conexao() as conn:
            return _gerar_criativo(
                conn,
                self.config,
                sku,
                beneficios=beneficios,
                formato=formato,
                tema=tema,
                preco=preco,
                titulo=titulo,
                selo=selo,
                foto=foto,
                modelo=modelo,
                logo=logo,
            )

    def briefing_imagens(
        self,
        sku: str,
        beneficios: list[str] | None = None,
        publico: str | None = None,
        tom: str = "clean e confiavel",
    ) -> dict:
        with self._conexao() as conn:
            return _briefing_imagens(
                conn,
                self.config,
                sku,
                beneficios=beneficios,
                publico=publico,
                tom=tom,
            )

    # ── UpSeller (ERP) ─────────────────────────────────────────────────────

    def upseller_status(self) -> dict:
        from .api import upseller

        return upseller.status(self.config)

    def upseller_sincronizar_estoque(self) -> dict:
        from .api import upseller

        with self._conexao() as conn:
            return upseller.sincronizar_estoque(conn, self.config)

    # ── contas a pagar / receber ───────────────────────────────────────────

    def contas(self, status: str | None = None) -> dict:
        with self._conexao() as conn:
            return _resumo_contas(conn, status)

    def criar_conta(
        self,
        tipo: str,
        descricao: str,
        valor: object,
        vencimento: object,
        categoria: str = "outros",
        marketplace: str | None = None,
        observacao: str | None = None,
    ) -> dict:
        with self._conexao() as conn:
            return _criar_conta(
                conn,
                tipo=tipo,
                descricao=descricao,
                valor=valor,
                vencimento=vencimento,
                categoria=categoria,
                marketplace=marketplace,
                observacao=observacao,
            )

    def marcar_paga(self, conta_id: int, pago_em: object = None) -> dict:
        with self._conexao() as conn:
            return _marcar_paga(conn, int(conta_id), pago_em=pago_em)

    # ── produtos e pedidos ─────────────────────────────────────────────────

    def produtos(self) -> dict:
        with self._conexao() as conn:
            return listar_produtos(conn)

    def registrar_custo(
        self,
        sku: str,
        custo: object,
        preco_venda: object = None,
        nome: str | None = None,
    ) -> dict:
        with self._conexao() as conn:
            return _registrar_custo(conn, sku, custo, preco_venda=preco_venda, nome=nome)

    def pedidos(
        self,
        mes: str | None = None,
        marketplace: str | None = None,
        situacao: str | None = None,
        limite: int = 30,
        cliente: str | None = None,
    ) -> dict:
        with self._conexao() as conn:
            return listar_pedidos(
                conn,
                mes=mes,
                marketplace=marketplace,
                situacao=situacao,
                limite=limite,
                cliente=cliente,
            )

    def criar_pedido(
        self,
        canal: str = "consignacao",
        cliente: str | None = None,
        data: object = None,
        itens: list[dict] | None = None,
        status: str = "Pendente",
        pedido_externo: str | None = None,
        observacao: str | None = None,
    ) -> dict:
        with self._conexao() as conn:
            return _criar_pedido(
                conn,
                canal=canal,
                cliente=cliente,
                data=data,
                itens=itens,
                status=status,
                pedido_externo=pedido_externo,
                observacao=observacao,
            )

    def atualizar_status_pedido(
        self, pedido_externo: str, status: str, canal: str | None = None
    ) -> dict:
        with self._conexao() as conn:
            return _atualizar_status_pedido(
                conn, pedido_externo=pedido_externo, status=status, canal=canal
            )

    # ── integracoes ────────────────────────────────────────────────────────

    def status_integracoes(self) -> dict:
        from .api import status_credenciais

        with self._conexao() as conn:
            importacoes = [
                dict(linha)
                for linha in conn.execute(
                    "SELECT tipo, marketplace, arquivo, inseridos, atualizados, criado_em "
                    "FROM importacoes ORDER BY id DESC LIMIT 8"
                )
            ]
        return {
            "modo": "planilhas (funciona agora, sem credenciais)",
            "shopee": status_credenciais("shopee", self.config),
            "tiktok": status_credenciais("tiktok", self.config),
            "upseller": status_credenciais("upseller", self.config),
            "ultimas_importacoes": importacoes,
            "proximo_passo": (
                "Para ligar a API oficial, siga GUIA_CREDENCIAIS.md e preencha o .env; "
                "o modo planilha continua funcionando em paralelo."
            ),
        }

    def limpar(self) -> dict:
        """Apaga os dados operacionais (mantem o esquema e as pastas)."""
        with self._conexao() as conn:
            db.limpar_dados(conn)
        return {
            "status": "limpo",
            "banco": str(self.config.banco),
            "mensagem": "dados operacionais apagados; use 'mkt demo' para recarregar o exemplo",
        }

    # ── dados de exemplo ───────────────────────────────────────────────────

    def demo(self, limpar: bool = False) -> dict:
        exemplos = self.config.projeto / "examples"
        if not exemplos.exists():
            raise FileNotFoundError(f"pasta de exemplos nao encontrada: {exemplos}")
        ordem = [
            ("custos", "custos_produtos.csv"),
            ("pedidos", "pedidos_shopee.csv"),
            ("pedidos", "pedidos_tiktok.csv"),
            ("repasses", "repasses_shopee.csv"),
            ("repasses", "repasses_tiktok.csv"),
            ("contas", "contas_a_pagar.csv"),
            ("estoque", "estoque.csv"),
        ]
        if limpar:
            with self._conexao() as conn:
                db.limpar_dados(conn)
        resultados = []
        for tipo, nome in ordem:
            arquivo = exemplos / nome
            if not arquivo.exists():
                continue
            marketplace = None
            if "shopee" in nome:
                marketplace = "shopee"
            elif "tiktok" in nome:
                marketplace = "tiktok"
            resultados.append(self.importar(tipo, arquivo, marketplace=marketplace))
        return {
            "modo": "dados de exemplo carregados",
            "limpo_antes": limpar,
            "importacoes": [
                {
                    "tipo": r["tipo"],
                    "arquivo": Path(r["arquivo"]).name,
                    "inseridos": r["inseridos"],
                    "atualizados": r["atualizados"],
                    "avisos": r["avisos"][:2],
                }
                for r in resultados
            ],
            "proximo_passo": "Peça o resumo ou o DRE do mes para ver os numeros.",
        }


def _mensagem_importacao(resultado: ResultadoImportacao, dry_run: bool) -> str:
    verbo = "seriam importados" if dry_run else "importados"
    return (
        f"{resultado.inseridos} registro(s) {verbo}, "
        f"{resultado.atualizados} atualizado(s), {resultado.ignorados} ignorado(s), "
        f"{resultado.linhas} linha(s) lida(s)."
    )


def _tipo_por_nome(nome: str) -> str | None:
    base = nome.lower()
    if any(p in base for p in ("pedido", "order", "venda")):
        return "pedidos"
    if any(p in base for p in ("repasse", "payout", "settlement", "extrato")):
        return "repasses"
    if any(p in base for p in ("conta", "despesa", "pagar", "receber", "financeiro")):
        return "contas"
    if any(p in base for p in ("custo", "produto", "sku", "cmv")):
        return "custos"
    if any(p in base for p in ("estoque", "inventario", "stock")):
        return "estoque"
    return None


__all__ = ["Servico"]
