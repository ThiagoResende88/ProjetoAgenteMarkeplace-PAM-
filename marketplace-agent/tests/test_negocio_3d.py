"""Testes do incremento de negocio 3D: desempenho, precificacao, foto e notificacoes."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from mktagent import notificacoes
from mktagent.precificacao import precificar_3d
from tests.apoio import BIN, CasoBase


class TestDesempenho(CasoBase):
    def _csv(self):
        return self.planilha(
            "desempenho.csv",
            [
                "Data",
                "Total de Pedidos",
                "Pedidos Válidos",
                "Valor de Vendas Válidas",
                "Pedidos Cancelados",
                "Clientes",
            ],
            [
                ["23/09/2026", "5", "5", "100,00", "0", "5"],
                ["24/09/2026", "3", "2", "60,00", "1", "2"],
                ["25/09/2026", "6", "6", "150,00", "0", "6"],
            ],
        )

    def test_importa_e_relata(self):
        arquivo = self._csv()
        resultado = self.importar("desempenho", arquivo, marketplace="shopee")
        self.assertEqual(resultado["inseridos"], 3)
        self.assertEqual(resultado["marketplace"], "shopee")
        self.importar("desempenho", arquivo, marketplace="shopee")  # idempotente
        self.assertEqual(
            self.consultar("SELECT COUNT(*) AS n FROM desempenho_diario")[0]["n"], 3
        )
        dados = self.servico.desempenho("shopee", 30)
        self.assertEqual(dados["pedidos_validos"], 13)
        self.assertEqual(dados["receita_valida_centavos"], 31000)
        self.assertEqual(dados["taxa_cancelamento"], "7,1%")
        self.assertTrue(dados["semanas"])
        self.assertEqual(dados["por_canal"][0]["canal"], "shopee")

    def test_data_serial_e_canal_consolidado(self):
        serial = (dt.date(2026, 10, 1) - dt.date(1899, 12, 30)).days
        arquivo = self.planilha(
            "serial.csv",
            ["Data", "Total de Pedidos", "Valor Total de Vendas"],
            [[str(serial), "2", "40,00"]],
        )
        resultado = self.importar("desempenho", arquivo)
        self.assertEqual(resultado["marketplace"], "consolidado")
        linhas = self.consultar("SELECT data FROM desempenho_diario")
        self.assertEqual(linhas[0]["data"], "2026-10-01")

    def test_sem_dados(self):
        dados = self.servico.desempenho()
        self.assertIn("mensagem", dados)


class TestPrecificacao3D(CasoBase):
    def test_mocozim_instagram(self):
        resultado = precificar_3d(
            peso_g=10,
            custo_filamento_kg=120,
            horas_impressao=0.83,
            custo_maquina_hora=2.5,
            taxa_falha_pct=0.05,
            acabamento=0.3,
            embalagem=0.8,
            canal="instagram",
            preco_venda=15,
            margem_alvo_pct=0.30,
        )
        self.assertEqual(resultado["custo"]["material"], "R$ 1,20")
        self.assertEqual(resultado["custo"]["maquina"], "R$ 2,08")
        self.assertEqual(resultado["precos"]["empate"], "R$ 4,69")
        self.assertEqual(resultado["precos"]["para_margem_alvo"], "R$ 6,76")
        self.assertEqual(resultado["precos"]["sugerido"], "R$ 6,90")
        margem_15 = [c for c in resultado["cenarios"] if c["rotulo"] == "preco informado"][0]
        self.assertEqual(margem_15["margem"], "67,4%")

    def test_shopee_com_frete_gera_prejuizo_e_aviso(self):
        resultado = precificar_3d(
            peso_g=10,
            custo_filamento_kg=120,
            horas_impressao=0.83,
            custo_maquina_hora=2.5,
            acabamento=0.3,
            embalagem=0.8,
            canal="shopee",
            frete_pago_pelo_vendedor=20,
            preco_venda=9.90,
        )
        self.assertEqual(resultado["canal"], "shopee")
        self.assertTrue(any("frete" in aviso.lower() for aviso in resultado["avisos"]))
        cenario = [c for c in resultado["cenarios"] if c["rotulo"] == "preco informado"][0]
        self.assertLess(cenario["lucro_centavos"], 0)

    def test_unidades_kit_multiplica_material(self):
        unitario = precificar_3d(peso_g=10, custo_filamento_kg=120, canal="direto")
        kit = precificar_3d(peso_g=10, custo_filamento_kg=120, canal="direto", unidades=10)
        self.assertEqual(kit["custo"]["material"], "R$ 12,00")
        self.assertEqual(kit["unidades"], 10)
        self.assertGreater(
            kit["custo"]["custo_total_centavos"], unitario["custo"]["custo_total_centavos"]
        )

    def test_sem_horas_avisa(self):
        resultado = precificar_3d(peso_g=20, custo_filamento_kg=100)
        self.assertTrue(any("tempo de impressao" in aviso for aviso in resultado["avisos"]))

    def test_canal_desconhecido_vira_outros(self):
        resultado = precificar_3d(peso_g=10, custo_filamento_kg=100, canal="loja-fisica")
        self.assertEqual(resultado["canal"], "outros")


class TestFotoNoCriativo(CasoBase):
    def test_cola_foto_real(self):
        from PIL import Image, ImageDraw

        self.servico.registrar_custo(
            "FOTO-1", "10,00", preco_venda="59,90", nome="Produto com Foto"
        )
        foto = self._tmp / "foto.png"
        imagem = Image.new("RGB", (800, 600), "#c9a227")
        desenho = ImageDraw.Draw(imagem)
        desenho.ellipse((200, 150, 600, 450), fill="#1d3557")
        imagem.save(foto)

        resultado = self.servico.gerar_criativo(
            "FOTO-1", beneficios=["Acabamento premium"], foto=str(foto)
        )
        self.assertEqual(Path(resultado["foto_usada"]).name, "foto.png")
        self.assertIn(
            "<image", Path(resultado["arquivos"]["svg"]).read_text(encoding="utf-8")
        )
        if resultado["arquivos"]["png"]:
            with Image.open(resultado["arquivos"]["png"]) as imagem_criativo:
                cor = imagem_criativo.getpixel((540, 560))
                self.assertIsInstance(cor, tuple)

    def test_foto_inexistente_avisa_e_nao_quebra(self):
        self.servico.registrar_custo("FOTO-2", "10,00", preco_venda="59,90")
        resultado = self.servico.gerar_criativo("FOTO-2", foto="/caminho/que/nao/existe.png")
        self.assertIsNone(resultado["foto_usada"])
        self.assertTrue(
            any("foto nao encontrada" in aviso for aviso in resultado["avisos"])
        )


class TestNotificacoes(CasoBase):
    def test_nao_configurado(self):
        self.assertFalse(notificacoes.telegram_configurado(self.config))
        with self.assertRaises(ValueError):
            notificacoes.enviar_telegram(self.config, "oi")

    def test_status(self):
        dados = self.servico.notificacoes_status()
        self.assertFalse(dados["telegram"]["configurado"])
        self.assertIn("como_configurar", dados["telegram"])
        self.assertIn("WhatsApp", " ".join(dados["whatsapp"]["como_configurar"]))

    def test_digest(self):
        self.carregar_demo()
        texto = notificacoes.montar_digest(self.servico)
        self.assertIn("Gestor de Marketplaces", texto)
        self.assertIn("Receita bruta", texto)
        self.assertIn("Alertas", texto)
        self.assertLess(len(texto), notificacoes.LIMITE_TELEGRAM)

    def test_configurado_detecta(self):
        config = replace(self.config, telegram_token="123", telegram_chat_id="456")
        self.assertTrue(notificacoes.telegram_configurado(config))


class TestMultiCanal(CasoBase):
    def test_importa_mercadolivre(self):
        arquivo = self.planilha(
            "ml.csv",
            ["pedido", "status", "data_pedido", "sku", "quantidade", "preco_unitario"],
            [["ML-1", "Entregue", "2026-09-05", "CUBO", "1", "59,90"]],
        )
        resultado = self.importar("pedidos", arquivo, marketplace="mercadolivre")
        self.assertEqual(resultado["marketplace"], "mercadolivre")
        pedido = self.consultar("SELECT marketplace FROM pedidos")[0]
        self.assertEqual(pedido["marketplace"], "mercadolivre")

    def test_importa_canal_com_espaco(self):
        arquivo = self.planilha(
            "direto.csv",
            ["pedido", "status", "data_pedido", "sku", "quantidade", "preco_unitario"],
            [["D-1", "Pago", "2026-09-05", "TUBETE", "1", "15,00"]],
        )
        resultado = self.importar("pedidos", arquivo, marketplace="Instagram")
        self.assertEqual(resultado["marketplace"], "instagram")


class TestFerramentasMCPNovas(CasoBase):
    def test_lista_ferramentas_do_negocio(self):
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
        nomes = {f["name"] for f in json.loads(processo.stdout)["ferramentas"]}
        for esperada in {
            "desempenho",
            "precificar_3d",
            "status_notificacoes",
            "enviar_telegram",
        }:
            self.assertIn(esperada, nomes)
