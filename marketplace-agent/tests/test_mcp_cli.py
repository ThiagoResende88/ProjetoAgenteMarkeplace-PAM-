"""Testes do servidor MCP (protocolo JSON-RPC sobre stdio) e da CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from tests.apoio import BIN, CasoBase


def _rodar_mcp(mensagens: list[dict], env: dict, timeout: int = 60) -> list[dict]:
    processo = subprocess.Popen(
        [sys.executable, str(BIN / "mkt-mcp")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    entrada = "\n".join(json.dumps(mensagem) for mensagem in mensagens) + "\n"
    saida, erro = processo.communicate(entrada, timeout=timeout)
    respostas = []
    for linha in saida.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        respostas.append(json.loads(linha))
    return respostas, erro


class TestServidorMCP(CasoBase):
    def _env(self) -> dict:
        env = dict(os.environ)
        env["MKT_HOME"] = str(self._tmp)
        env["MKT_DB"] = str(self._tmp / "mkt.db")
        return env

    def test_handshake_e_ferramentas(self):
        respostas, erro = _rodar_mcp(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2026-07-28",
                        "capabilities": {},
                        "clientInfo": {"name": "teste", "version": "1"},
                    },
                },
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "ping"},
            ],
            self._env(),
        )
        self.assertEqual(len(respostas), 3, erro)
        inicial = respostas[0]
        self.assertEqual(inicial["id"], 1)
        self.assertEqual(inicial["result"]["protocolVersion"], "2026-07-28")
        self.assertIn("tools", inicial["result"]["capabilities"])
        self.assertEqual(inicial["result"]["serverInfo"]["name"], "marketplaces")
        self.assertIn("NUNCA invente", inicial["result"]["instructions"])

        ferramentas = respostas[1]["result"]["tools"]
        nomes = {ferramenta["name"] for ferramenta in ferramentas}
        for esperada in {"resumo", "dre", "margem_sku", "fluxo_caixa", "alertas", "criar_conta", "importar_arquivo"}:
            self.assertIn(esperada, nomes)
        for ferramenta in ferramentas:
            self.assertEqual(ferramenta["inputSchema"]["type"], "object")
            self.assertIn("description", ferramenta)
        self.assertIn("result", respostas[2])

    def test_chamada_de_ferramenta_e_erro_controlado(self):
        respostas, _ = _rodar_mcp(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "resumo", "arguments": {}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "nao_existe", "arguments": {}},
                },
            ],
            self._env(),
        )
        self.assertEqual(len(respostas), 3)
        resultado = respostas[1]["result"]
        self.assertFalse(resultado.get("isError"))
        self.assertEqual(resultado["content"][0]["type"], "text")
        carga = json.loads(resultado["content"][0]["text"])
        self.assertIn("banco", carga)
        self.assertIn("integracoes", carga)

        desconhecida = respostas[2]["result"]
        self.assertTrue(desconhecida["isError"])

    def test_erro_de_ferramenta_nao_derruba_servidor(self):
        respostas, _ = _rodar_mcp(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "dre", "arguments": {"mes": "mes-invalido"}},
                },
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "alertas", "arguments": {}}},
            ],
            self._env(),
        )
        self.assertEqual(len(respostas), 3)
        self.assertFalse(respostas[2]["result"].get("isError"))

    def test_listar_ferramentas_cli(self):
        processo = subprocess.run(
            [sys.executable, str(BIN / "mkt-mcp"), "--listar-ferramentas"],
            capture_output=True,
            text=True,
            env=self._env(),
            timeout=60,
        )
        self.assertEqual(processo.returncode, 0, processo.stderr)
        dados = json.loads(processo.stdout)
        self.assertGreaterEqual(len(dados["ferramentas"]), 15)


class TestCLI(CasoBase):
    def _rodar(self, *argumentos: str) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["MKT_HOME"] = str(self._tmp)
        env["MKT_DB"] = str(self._tmp / "mkt.db")
        return subprocess.run(
            [sys.executable, str(BIN / "mkt"), *argumentos],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )

    def test_demo_e_relatorios_json(self):
        demo = self._rodar("demo", "--limpar", "--json")
        self.assertEqual(demo.returncode, 0, demo.stderr)
        self.assertIn("importacoes", json.loads(demo.stdout))

        dre = self._rodar("dre", "--mes", "2026-09", "--json")
        self.assertEqual(dre.returncode, 0, dre.stderr)
        dados = json.loads(dre.stdout)
        self.assertGreater(dados["receita_bruta_centavos"], 0)
        self.assertEqual(
            dados["receita_liquida_centavos"],
            dados["receita_bruta_centavos"]
            - dados["descontos_centavos"]
            + dados["frete_cobrado_centavos"]
            - dados["frete_pago_centavos"]
            - dados["comissao_centavos"]
            - dados["taxa_servico_centavos"]
            - dados["cupom_centavos"]
            - dados["imposto_centavos"],
        )
        self.assertIn("shopee", dados["por_marketplace"])
        self.assertIn("tiktok", dados["por_marketplace"])

        margem = self._rodar("margem", "--dias", "90", "--json")
        self.assertEqual(margem.returncode, 0, margem.stderr)
        self.assertGreater(len(json.loads(margem.stdout)["skus"]), 0)

        caixa = self._rodar("caixa", "--dias", "30", "--json")
        self.assertEqual(caixa.returncode, 0, caixa.stderr)

        alertas = self._rodar("alertas", "--json")
        self.assertEqual(alertas.returncode, 0, alertas.stderr)
        self.assertGreaterEqual(json.loads(alertas.stdout)["total"], 1)

    def test_erro_amigavel(self):
        resultado = self._rodar("importar", "pedidos", "nao_existe.csv", "--json")
        self.assertEqual(resultado.returncode, 1)
        self.assertIn("erro", json.loads(resultado.stdout).keys() if resultado.stdout else {})
        resultado = self._rodar("importar", "pedidos", "nao_existe.csv")
        self.assertEqual(resultado.returncode, 1)
        self.assertIn("nao encontrado", resultado.stderr)

    def test_modelo_impresso(self):
        resultado = self._rodar("modelo", "pedidos")
        self.assertEqual(resultado.returncode, 0)
        self.assertIn("pedido;status;data_pedido", resultado.stdout)


if __name__ == "__main__":
    unittest.main()
