"""Converte o export "Todos pedido" da TikTok Shop (XLSX achatado) em CSV padrão.

O arquivo exportado veio com cada célula em uma linha/coluna deslocada
("triangular"). Este script reconstrói a tabela 60 colunas → linhas e gera um
CSV no formato canônico do mktagent.

Uso: python3 scripts/converter_tiktok_flat.py <arquivo.xlsx> <saida.csv>
"""

from __future__ import annotations

import csv
import datetime as dt
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
TOTAL_COLUNAS = 60


def celulas(caminho: Path) -> list[tuple[int, str]]:
    with zipfile.ZipFile(caminho) as z:
        compartilhadas: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            raiz = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in raiz.findall(f"{NS}si"):
                compartilhadas.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
        abas = [n for n in z.namelist() if n.startswith("xl/worksheets/") and n.endswith(".xml")]
        if not abas:
            raise SystemExit("XLSX sem abas")
        raiz = ET.fromstring(z.read(sorted(abas)[0]))
        saida: list[tuple[int, str]] = []
        for row in raiz.iter(f"{NS}row"):
            for c in row.findall(f"{NS}c"):
                ref = c.get("r") or ""
                letras = re.match(r"([A-Z]+)", ref)
                if not letras:
                    continue
                idx = 0
                for ch in letras.group(1):
                    idx = idx * 26 + (ord(ch) - 64)
                idx -= 1
                tipo = c.get("t")
                if tipo == "inlineStr":
                    valor = "".join(x.text or "" for x in c.iter(f"{NS}t"))
                else:
                    v = c.find(f"{NS}v")
                    if v is None or v.text is None:
                        continue
                    if tipo == "s":
                        try:
                            valor = compartilhadas[int(v.text)]
                        except (ValueError, IndexError):
                            valor = v.text
                    else:
                        valor = v.text
                if str(valor).strip():
                    saida.append((idx, str(valor)))
        return saida


def valor_brl(texto: str) -> float:
    texto = str(texto or "").replace("BRL", "").strip()
    if not texto:
        return 0.0
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return 0.0


def converter(origem: Path, destino: Path) -> dict:
    tokens = celulas(origem)
    if len(tokens) < 100:
        raise SystemExit("arquivo com poucas células; não parece ser o export achatado")
    inicio_dados = None
    for i, (_, valor) in enumerate(tokens):
        if i >= TOTAL_COLUNAS and re.fullmatch(r"\d{18,20}", valor):
            inicio_dados = i
            break
    if inicio_dados is None:
        raise SystemExit("nao encontrei o inicio dos dados")
    cabecalhos = [v for _, v in tokens[:TOTAL_COLUNAS]]
    indice = {nome: i for i, nome in enumerate(cabecalhos)}

    linhas: list[dict[str, str]] = []
    atual: dict[int, str] | None = None
    for coluna, valor in tokens[inicio_dados:]:
        if coluna == 0 or atual is None:
            if atual:
                linhas.append(atual)
            atual = {}
        atual[coluna] = valor
    if atual:
        linhas.append(atual)

    def pegar(linha: dict[int, str], nome: str, padrao: str = "") -> str:
        return linha.get(indice.get(nome, -1), padrao) if nome in indice else padrao

    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8-sig") as fh:
        escritor = csv.writer(fh, delimiter=";")
        escritor.writerow(
            [
                "pedido",
                "status",
                "data_pedido",
                "sku",
                "produto",
                "quantidade",
                "preco_unitario",
                "itens_total",
                "frete_pago",
                "cliente",
            ]
        )
        for linha in linhas:
            quantidade = pegar(linha, "Quantity") or "1"
            try:
                qtd = max(1, int(float(quantidade.replace(",", "."))))
            except ValueError:
                qtd = 1
            subtotal = valor_brl(pegar(linha, "SKU Subtotal After Discount"))
            if subtotal == 0:
                subtotal = valor_brl(pegar(linha, "Order Amount"))
            preco = subtotal / qtd if qtd else subtotal
            criado = pegar(linha, "Created Time")
            data_iso = ""
            for formato in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y"):
                try:
                    data_iso = dt.datetime.strptime(criado, formato).date().isoformat()
                    break
                except ValueError:
                    continue
            escritor.writerow(
                [
                    pegar(linha, "Order ID"),
                    pegar(linha, "Order Status"),
                    data_iso,
                    pegar(linha, "Seller SKU"),
                    pegar(linha, "Product Name"),
                    qtd,
                    f"{preco:.2f}".replace(".", ","),
                    f"{subtotal:.2f}".replace(".", ","),
                    f"{valor_brl(pegar(linha, 'Shipping Fee Seller Discount')):.2f}".replace(".", ","),
                    pegar(linha, "Buyer Username"),
                ]
            )

    status: dict[str, int] = {}
    for linha in linhas:
        status[pegar(linha, "Order Status")] = status.get(pegar(linha, "Order Status"), 0) + 1
    return {"linhas": len(linhas), "status": status, "destino": str(destino)}


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    resultado = converter(Path(sys.argv[1]).expanduser(), Path(sys.argv[2]).expanduser())
    print(resultado)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
