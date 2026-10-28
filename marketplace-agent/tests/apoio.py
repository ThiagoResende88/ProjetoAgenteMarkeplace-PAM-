"""Apoio comum aos testes: banco temporario e helpers de planilha."""

from __future__ import annotations

import csv
import io
import os
import tempfile
import unittest
from pathlib import Path

from mktagent.config import Config
from mktagent.servico import Servico

RAIZ = Path(__file__).resolve().parents[1]
EXEMPLOS = RAIZ / "examples"
BIN = RAIZ / "bin"


class CasoBase(unittest.TestCase):
    """Cria um banco isolado por teste (MKT_HOME/MKT_DB em diretorio temporario)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self._tmp = Path(self.tmp.name)
        self._env_original = {
            k: os.environ.get(k) for k in ("MKT_HOME", "MKT_DB", "MKT_SAIDAS")
        }
        os.environ["MKT_HOME"] = str(self._tmp)
        os.environ["MKT_DB"] = str(self._tmp / "mkt.db")
        os.environ["MKT_SAIDAS"] = str(self._tmp / "saidas")
        self.config = Config.carregar()
        self.servico = Servico(self.config)
        with self.servico._conexao():  # noqa: SLF001 - inicializa o esquema
            pass

    def tearDown(self) -> None:
        for chave, valor in self._env_original.items():
            if valor is None:
                os.environ.pop(chave, None)
            else:
                os.environ[chave] = valor
        self.tmp.cleanup()

    # helpers ---------------------------------------------------------------

    def planilha(self, nome: str, cabecalho: list[str], linhas: list[list], delimitador: str = ";") -> Path:
        destino = self._tmp / nome
        with destino.open("w", newline="", encoding="utf-8-sig") as fh:
            escritor = csv.writer(fh, delimiter=delimitador)
            escritor.writerow(cabecalho)
            escritor.writerows(linhas)
        return destino

    def importar(self, tipo: str, arquivo: Path, **kwargs) -> dict:
        return self.servico.importar(tipo, arquivo, **kwargs)

    def consultar(self, sql: str, parametros: tuple = ()) -> list:
        with self.servico._conexao() as conn:  # noqa: SLF001
            return [dict(linha) for linha in conn.execute(sql, parametros)]

    def carregar_demo(self) -> None:
        self.servico.demo(limpar=True)


def csv_bytes(cabecalho: list[str], linhas: list[list], delimitador: str = ";") -> bytes:
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=delimitador)
    escritor.writerow(cabecalho)
    escritor.writerows(linhas)
    return buffer.getvalue().encode("utf-8-sig")
