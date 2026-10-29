"""Leitura de planilhas: CSV (com deteccao de encoding/delimitador) e XLSX.

Sem dependencias externas. O XLSX e lido como ZIP + XML (apenas valores,
primeira aba) — suficiente para os relatorios exportados pelos paineis.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_RE_REF = re.compile(r"^([A-Z]+)")
_FORMATOS = (".csv", ".tsv", ".txt", ".xlsx", ".xls")


@dataclass
class Tabela:
    colunas: list[str]
    linhas: list[dict[str, str]]
    avisos: list[str] = field(default_factory=list)


def ler_tabela(caminho: str | Path) -> Tabela:
    """Le CSV/TSV/XLSX e devolve colunas + linhas (valores como texto)."""
    caminho = Path(caminho).expanduser()
    if not caminho.exists():
        raise FileNotFoundError(f"arquivo nao encontrado: {caminho}")
    if caminho.is_dir():
        raise IsADirectoryError(f"esperava um arquivo, recebi um diretorio: {caminho}")

    if caminho.suffix.lower() == ".xlsx" or _eh_zip(caminho):
        return _ler_xlsx(caminho)
    if caminho.suffix.lower() == ".xls":
        raise ValueError(
            "formato .xls (Excel antigo) nao suportado. Abra no Excel/LibreOffice "
            "e salve como .xlsx ou .csv."
        )
    return _ler_csv(caminho)


def _eh_zip(caminho: Path) -> bool:
    try:
        with open(caminho, "rb") as fh:
            return fh.read(2) == b"PK"
    except OSError:
        return False


# ── CSV ─────────────────────────────────────────────────────────────────────


def _decodificar(bruto: bytes) -> tuple[str, str]:
    for codificacao in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return bruto.decode(codificacao), codificacao
        except UnicodeDecodeError:
            continue
    return bruto.decode("utf-8", errors="replace"), "utf-8 (com falhas)"


def _detectar_delimitador(texto: str) -> str:
    amostra = texto[:16384]
    tentativas = [";", ",", "\t", "|"]
    try:
        dialeto = csv.Sniffer().sniff(amostra, delimiters=";,\t|")
        return dialeto.delimiter
    except csv.Error:
        pass
    # fallback: o delimitador que aparece mais na primeira linha
    primeira = amostra.splitlines()[0] if amostra.splitlines() else ""
    contagens = {d: primeira.count(d) for d in tentativas}
    melhor = max(contagens, key=contagens.get)
    return melhor if contagens[melhor] else ";"


def _ler_csv(caminho: Path) -> Tabela:
    bruto = caminho.read_bytes()
    texto, codificacao = _decodificar(bruto)
    if not texto.strip():
        raise ValueError(f"arquivo vazio: {caminho.name}")
    delimitador = _detectar_delimitador(texto)
    leitor = csv.reader(io.StringIO(texto), delimiter=delimitador)
    linhas_brutas = [linha for linha in leitor]
    avisos = [f"CSV lido como {codificacao}, delimitador {delimitador!r}"]
    return _montar_tabela(linhas_brutas, avisos, origem="CSV")


# ── XLSX ────────────────────────────────────────────────────────────────────


def _indice_coluna(ref: str) -> int:
    match = _RE_REF.match(ref or "")
    if not match:
        return -1
    indice = 0
    for letra in match.group(1):
        indice = indice * 26 + (ord(letra) - ord("A") + 1)
    return indice - 1


def _texto_celula(celula: ET.Element, compartilhadas: list[str]) -> str | None:
    tipo = celula.get("t")
    if tipo == "inlineStr":
        return "".join(t.text or "" for t in celula.iter(f"{_NS}t"))
    valor = celula.find(f"{_NS}v")
    if valor is None or valor.text is None:
        return None
    bruto = valor.text
    if tipo == "s":
        try:
            return compartilhadas[int(bruto)]
        except (ValueError, IndexError):
            return None
    if tipo == "b":
        return "1" if bruto.strip() == "1" else "0"
    if tipo == "e":
        return None
    return bruto


def _ler_xlsx(caminho: Path) -> Tabela:
    with zipfile.ZipFile(caminho) as pacote:
        nomes = set(pacote.namelist())
        compartilhadas: list[str] = []
        if "xl/sharedStrings.xml" in nomes:
            raiz = ET.fromstring(pacote.read("xl/sharedStrings.xml"))
            for si in raiz.findall(f"{_NS}si"):
                compartilhadas.append("".join(t.text or "" for t in si.iter(f"{_NS}t")))

        planilhas = sorted(
            n
            for n in nomes
            if n.startswith("xl/worksheets/") and n.endswith(".xml")
        )
        if not planilhas:
            raise ValueError(f"nenhuma aba encontrada no XLSX: {caminho.name}")
        raiz = ET.fromstring(pacote.read(planilhas[0]))

        linhas_brutas: list[list[str]] = []
        for linha in raiz.iter(f"{_NS}row"):
            celulas: dict[int, str] = {}
            for celula in linha.findall(f"{_NS}c"):
                indice = _indice_coluna(celula.get("r", ""))
                if indice < 0:
                    continue
                texto = _texto_celula(celula, compartilhadas)
                if texto is not None:
                    celulas[indice] = texto
            if not celulas:
                continue
            largura = max(celulas) + 1
            linhas_brutas.append([celulas.get(i, "") for i in range(largura)])

    avisos = [f"XLSX lido: aba {planilhas[0].split('/')[-1]}"]
    if len(planilhas) > 1:
        avisos.append(
            f"o arquivo tem {len(planilhas)} abas; usei a primeira. "
            "Se precisar de outra, exporte-a como CSV."
        )
    return _montar_tabela(linhas_brutas, avisos, origem="XLSX")


# ── comum ───────────────────────────────────────────────────────────────────


def _montar_tabela(
    linhas_brutas: list[list[str]], avisos: list[str], origem: str
) -> Tabela:
    linhas_limpas = [
        [str(c).strip() for c in linha]
        for linha in linhas_brutas
        if any(str(c).strip() for c in linha)
    ]
    if not linhas_limpas:
        raise ValueError(f"{origem} sem linhas de dados")

    indice_cabecalho = 0
    for i, linha in enumerate(linhas_limpas[:10]):
        if sum(1 for c in linha if c) >= 2:
            indice_cabecalho = i
            break
    if indice_cabecalho:
        avisos.append(
            f"ignorei {indice_cabecalho} linha(s) antes do cabecalho "
            "(titulo/relatorio do painel)"
        )

    cabecalho = linhas_limpas[indice_cabecalho]
    while cabecalho and not cabecalho[-1]:
        cabecalho = cabecalho[:-1]
    colunas = _deduplicar(cabecalho)

    linhas: list[dict[str, str]] = []
    for linha in linhas_limpas[indice_cabecalho + 1 :]:
        valores = linha[: len(colunas)] + [""] * max(0, len(colunas) - len(linha))
        if not any(valores):
            continue
        linhas.append({coluna: valores[i] for i, coluna in enumerate(colunas)})

    if not linhas:
        raise ValueError(f"{origem} tem cabecalho mas nenhuma linha de dados")
    return Tabela(colunas=colunas, linhas=linhas, avisos=avisos)


def _deduplicar(cabecalho: list[str]) -> list[str]:
    vistos: dict[str, int] = {}
    resultado = []
    for i, nome in enumerate(cabecalho):
        nome = nome or f"coluna_{i + 1}"
        if nome in vistos:
            vistos[nome] += 1
            nome = f"{nome}_{vistos[nome]}"
        else:
            vistos[nome] = 0
        resultado.append(nome)
    return resultado
