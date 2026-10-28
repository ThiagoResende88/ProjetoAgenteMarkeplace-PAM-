"""Escritor XLSX mínimo (sem dependências) para gerar planilhas do projeto.

Suporta múltiplas abas, cabeçalho em negrito, larguras de coluna, congelar
cabeçalho, auto-filtro e formatos simples (moeda, número, porcentagem).
"""

from __future__ import annotations

import datetime as dt
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

_FMT_MOEDA = 'R$ #,##0.00'
_FMT_NUMERO = '#,##0.00'
_FMT_PCT = '0.0%'
_FMT_INT = '0'

_ESTILOS = {
    "texto": 0,
    "cabecalho": 1,
    "moeda": 2,
    "numero": 3,
    "pct": 4,
    "inteiro": 5,
    "negrito": 6,
}


def _coluna(indice: int) -> str:
    nome = ""
    numero = indice + 1
    while numero:
        numero, resto = divmod(numero - 1, 26)
        nome = chr(ord("A") + resto) + nome
    return nome


def _celula(indice: int, linha: int, valor, estilo: int) -> str:
    ref = f"{_coluna(indice)}{linha}"
    if valor is None or valor == "":
        return ""
    if isinstance(valor, bool):
        return f'<c r="{ref}" t="b" s="{estilo}"><v>{1 if valor else 0}</v></c>'
    if isinstance(valor, (int, float)):
        if isinstance(valor, float) and (valor != valor):  # NaN
            return ""
        return f'<c r="{ref}" s="{estilo}"><v>{valor}</v></c>'
    texto = escape(str(valor))
    return f'<c r="{ref}" t="inlineStr" s="{estilo}"><is><t xml:space="preserve">{texto}</t></is></c>'


def _aba_xml(nome: str, linhas: list[list], larguras: list[float] | None, formatos: dict[int, str], congelar: bool = True) -> str:
    total_colunas = max((len(l) for l in linhas), default=0)
    cols = ""
    if larguras:
        cols = "<cols>" + "".join(
            f'<col min="{i+1}" max="{i+1}" width="{w}" customWidth="1"/>'
            for i, w in enumerate(larguras[:total_colunas])
        ) + "</cols>"
    views = ""
    if congelar and len(linhas) > 1:
        views = (
            '<sheetViews><sheetView workbookViewId="0">'
            '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
            "</sheetView></sheetViews>"
        )
    corpo = []
    for i, linha in enumerate(linhas, start=1):
        celulas = []
        for j, valor in enumerate(linha):
            if i == 1:
                estilo = _ESTILOS["cabecalho"]
            else:
                estilo = _ESTILOS[formatos.get(j, "texto")]
            celulas.append(_celula(j, i, valor, estilo))
        corpo.append(f'<row r="{i}">' + "".join(celulas) + "</row>")
    filtro = ""
    if len(linhas) > 1 and total_colunas:
        filtro = f'<autoFilter ref="A1:{_coluna(total_colunas-1)}{len(linhas)}"/>'
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        + views
        + cols
        + "<sheetData>"
        + "".join(corpo)
        + "</sheetData>"
        + filtro
        + "</worksheet>"
    )


def escrever_xlsx(
    caminho: str | Path,
    abas: list[dict],
    titulo: str = "Planilha",
) -> Path:
    """Grava um XLSX com várias abas.

    Cada aba: {"nome": str, "linhas": [[...]], "larguras": [..],
    "formatos": {indice_coluna: "moeda"|"numero"|"pct"|"inteiro"}}
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    nomes = [str(aba["nome"])[:31] for aba in abas]

    content_types = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
    ]
    for i in range(1, len(abas) + 1):
        content_types.append(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    content_types.append("</Types>")

    workbook = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        "<sheets>",
    ]
    for i, nome in enumerate(nomes, start=1):
        workbook.append(f'<sheet name="{escape(nome)}" sheetId="{i}" r:id="rId{i}"/>')
    workbook += ["</sheets>", "</workbook>"]

    rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    for i in range(1, len(abas) + 1):
        rels.append(
            f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{i}.xml"/>'
        )
    rels.append(
        f'<Relationship Id="rId{len(abas)+1}" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )
    rels.append("</Relationships>")

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<numFmts count="3"><numFmt numFmtId="164" formatCode="{escape(_FMT_MOEDA)}"/>'
        f'<numFmt numFmtId="165" formatCode="{escape(_FMT_NUMERO)}"/>'
        f'<numFmt numFmtId="166" formatCode="{escape(_FMT_PCT)}"/></numFmts>'
        '<fonts count="3">'
        '<font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font>'
        "</fonts>"
        '<fills count="3"><fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FF14213D"/><bgColor indexed="64"/></patternFill></fill>'
        "</fills>"
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="7">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'
        '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
        '<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
        '<xf numFmtId="166" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
        '<xf numFmtId="1" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
        '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
        "</cellXfs>"
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )

    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as pacote:
        pacote.writestr("[Content_Types].xml", "".join(content_types))
        pacote.writestr("_rels/.rels", root_rels)
        pacote.writestr("xl/workbook.xml", "".join(workbook))
        pacote.writestr("xl/_rels/workbook.xml.rels", "".join(rels))
        pacote.writestr("xl/styles.xml", styles)
        for i, aba in enumerate(abas, start=1):
            xml = _aba_xml(
                aba["nome"],
                aba["linhas"],
                aba.get("larguras"),
                aba.get("formatos", {}),
                aba.get("congelar", True),
            )
            pacote.writestr(f"xl/worksheets/sheet{i}.xml", xml)
    return caminho


__all__ = ["escrever_xlsx"]
