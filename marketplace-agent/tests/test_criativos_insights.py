"""Testes de insights, criativos (imagem) e integracao UpSeller."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from mktagent.api.upseller import MCP_URL, UpSellerNaoConfigurado, headers
from mktagent.config import Credenciais
from mktagent.datas import mes_atual
from tests.apoio import BIN, CasoBase

try:  # Pillow e opcional
    from PIL import Image

    TEM_PILLOW = True
except Exception:  # pragma: no cover
    TEM_PILLOW = False


class TestInsights(CasoBase):
    def test_insights_mes_fechado(self):
        self.carregar_demo()
        dados = self.servico.insights("2026-09")
        self.assertEqual(dados["mes"], "2026-09")
        self.assertTrue(dados["insights"])
        self.assertLessEqual(len(dados["acoes_prioritarias"]), 5)
        self.assertIn("receita_bruta", dados["numeros"])
        self.assertEqual(dados["numeros"]["comparacao"], "mes fechado vs mes fechado")
        for acao in dados["acoes_prioritarias"]:
            self.assertIn(acao["prioridade"], (1, 2, 3))

    def test_insights_mes_em_andamento_usa_mtd(self):
        self.carregar_demo()
        dados = self.servico.insights(mes_atual())
        self.assertEqual(dados["numeros"]["comparacao"], "MTD (mesmo numero de dias nos dois meses)")
        self.assertTrue(any("Mes em andamento" in item for item in dados["insights"]))

    def test_comparativo_parcial(self):
        self.carregar_demo()
        comp = self.servico.comparativo(mes_atual())
        self.assertTrue(comp["parcial"])
        self.assertIn("MTD", comp["comparacao"])
        fechado = self.servico.comparativo("2026-09")
        self.assertFalse(fechado["parcial"])

    def test_matriz_sku_classifica(self):
        self.carregar_demo()
        dados = self.servico.insights("2026-09")
        classes = {item["classe"] for item in dados["matriz_sku"]}
        self.assertTrue(classes.issubset({"motor", "oportunidade", "volume_que_segura", "revisar"}))


class TestCriativos(CasoBase):
    def setUp(self):
        super().setUp()
        self.servico.registrar_custo(
            "CRI-001", "12,50", preco_venda="49,90", nome="Organizador Teste"
        )

    def test_gerar_criativo_quadrado(self):
        resultado = self.servico.gerar_criativo(
            "CRI-001",
            beneficios=["Material resistente", "Fácil de limpar"],
            formato="quadrado",
            selo="FRETE GRÁTIS",
        )
        self.assertEqual(resultado["preco"], "R$ 49,90")
        svg = resultado["arquivos"]["svg"]
        self.assertTrue(os.path.exists(svg))
        conteudo = Path(svg).read_text(encoding="utf-8")
        self.assertIn("Organizador Teste", conteudo)
        self.assertIn("Material resistente", conteudo)
        self.assertIn("FRETE GRÁTIS", conteudo)
        if TEM_PILLOW and resultado["arquivos"]["png"]:
            self.assertTrue(os.path.exists(resultado["arquivos"]["png"]))
            with Image.open(resultado["arquivos"]["png"]) as imagem:
                self.assertEqual(imagem.size, (1080, 1080))

    def test_gerar_criativo_vertical_escuro(self):
        resultado = self.servico.gerar_criativo(
            "CRI-001", beneficios=["Benefício 1"], formato="vertical", tema="escuro"
        )
        self.assertEqual(resultado["formato"], "vertical")
        if TEM_PILLOW and resultado["arquivos"]["png"]:
            with Image.open(resultado["arquivos"]["png"]) as imagem:
                self.assertEqual(imagem.size, (1080, 1350))

    def test_sku_inexistente_erro_claro(self):
        with self.assertRaises(ValueError) as contexto:
            self.servico.gerar_criativo("NAO-EXISTE")
        self.assertIn("SKU", str(contexto.exception))

    def test_modelo_limpo_com_foto_e_logo(self):
        from PIL import Image, ImageDraw

        self.servico.registrar_custo("LIMPO-1", "1,56", preco_venda="15,00", nome="Tubete Limpo")
        foto = self._tmp / "lifestyle.png"
        imagem = Image.new("RGB", (900, 900), "#f2f2f2")
        desenho = ImageDraw.Draw(imagem)
        desenho.rectangle((300, 250, 600, 700), fill="#e75480")
        imagem.save(foto)

        logo = self._tmp / "logo.png"
        marca = Image.new("RGBA", (300, 120), (0, 0, 0, 0))
        desenho_logo = ImageDraw.Draw(marca)
        desenho_logo.rectangle((10, 10, 290, 110), fill=(0, 200, 220, 255))
        marca.save(logo)

        resultado = self.servico.gerar_criativo(
            "LIMPO-1", modelo="limpo", foto=str(foto), logo=str(logo)
        )
        self.assertEqual(resultado["modelo"], "limpo")
        self.assertIsNotNone(resultado["logo_usada"])
        self.assertTrue(Path(resultado["arquivos"]["svg"]).exists())
        self.assertIn(
            "<image", Path(resultado["arquivos"]["svg"]).read_text(encoding="utf-8")
        )
        if resultado["arquivos"]["png"]:
            with Image.open(resultado["arquivos"]["png"]) as imagem_final:
                self.assertEqual(imagem_final.size, (1080, 1080))

    def test_modelo_limpo_sem_foto_erro(self):
        self.servico.registrar_custo("LIMPO-2", "1,56", preco_venda="15,00")
        with self.assertRaises(ValueError):
            self.servico.gerar_criativo("LIMPO-2", modelo="limpo")

    def test_briefing_imagens(self):
        resultado = self.servico.briefing_imagens(
            "CRI-001", beneficios=["Cabe em qualquer gaveta"], publico="quem organiza a casa"
        )
        self.assertEqual(resultado["total_prompts"], 6)
        caminho = resultado["arquivo"]
        texto = Path(caminho).read_text(encoding="utf-8")
        self.assertIn("Organizador Teste", texto)
        self.assertIn("Imagem principal", texto)
        self.assertIn("negative prompt", texto)
        self.assertIn("quem organiza a casa", texto)
        self.assertIn("Checklist antes de publicar", texto)

    def test_ferramentas_mcp_incluem_criativos_e_insights(self):
        env = dict(os.environ)
        env["MKT_HOME"] = str(self._tmp)
        env["MKT_DB"] = str(self._tmp / "mkt.db")
        processo = subprocess.run(
            [sys.executable, str(BIN / "mkt-mcp"), "--listar-ferramentas"],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )
        self.assertEqual(processo.returncode, 0, processo.stderr)
        nomes = {ferramenta["name"] for ferramenta in json.loads(processo.stdout)["ferramentas"]}
        for esperada in {
            "insights",
            "gerar_criativo",
            "briefing_imagens",
            "upseller_status",
            "upseller_sincronizar_estoque",
        }:
            self.assertIn(esperada, nomes)


class TestUpSeller(CasoBase):
    def test_status_default_nao_configurado(self):
        dados = self.servico.upseller_status()
        self.assertEqual(dados["status"], "nao configurado — exporte as planilhas do UpSeller manualmente")
        self.assertEqual(dados["mcp_url"], MCP_URL)
        self.assertTrue(dados["passos"])

    def test_sincronizar_sem_credenciais_falha_claro(self):
        with self.assertRaises(UpSellerNaoConfigurado) as contexto:
            self.servico.upseller_sincronizar_estoque()
        self.assertIn("UPSELLER_CLIENT_ID", str(contexto.exception))

    def test_headers_usam_client_id_e_token(self):
        credenciais = Credenciais(app_id="user-123", app_secret="api-token", mcp_token="mcp-token")
        config = replace(self.config, upseller=credenciais)
        cabecalhos = headers(config)
        self.assertEqual(cabecalhos["X-Upseller-Client-Id"], "user-123")
        self.assertEqual(cabecalhos["X-Upseller-Api-Token"], "api-token")
        self.assertEqual(cabecalhos["X-Upseller-Language"], "pt")
        cabecalhos_mcp = headers(config, usar_mcp_token=True)
        self.assertEqual(cabecalhos_mcp["X-Upseller-Api-Token"], "mcp-token")

    def test_status_configurado(self):
        credenciais = Credenciais(app_id="user-123", app_secret="api-token", mcp_token="mcp-token")
        config = replace(self.config, upseller=credenciais)
        from mktagent.api.upseller import status

        dados = status(config)
        self.assertIn("pode sincronizar", dados["status"])
        self.assertEqual(dados["mcp_token_configurado"], "sim")
