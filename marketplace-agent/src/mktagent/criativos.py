"""Criativos: card de anuncio (SVG/PNG) e briefing de imagens para IA.

- ``gerar_criativo``: monta uma arte 1080x1080 (ou 1080x1350) com nome, beneficios
  e preco do produto — PNG via Pillow (se instalado) e SVG sempre, para editar.
- ``briefing_imagens``: gera um pacote de prompts (PT/EN) para ferramentas de IA
  (Midjourney, DALL-E, Canva AI, Photoshop Firefly) + checklist de regras.
"""

from __future__ import annotations

import datetime as dt
import html
import sqlite3
import textwrap
from pathlib import Path

from .datas import hoje
from .dinheiro import fmt_brl

LARGURA = 1080
ALTURAS = {"quadrado": 1080, "vertical": 1350}

TEMAS = {
    "claro": {
        "fundo": "#F7F3EA",
        "fundo2": "#EFE6D6",
        "tinta": "#14213D",
        "destaque": "#E76F51",
        "secundario": "#2A9D8F",
        "branco": "#FFFFFF",
    },
    "escuro": {
        "fundo": "#14213D",
        "fundo2": "#0B1428",
        "tinta": "#FFFFFF",
        "destaque": "#FCA311",
        "secundario": "#2A9D8F",
        "branco": "#FFFFFF",
    },
}

FONTES = {
    "negrito": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ],
    "normal": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ],
}

BENEFICIOS_PADRAO = ["Material resistente", "Pratico no dia a dia", "Pronto para presente"]


def _fonte(tamanho: int, estilo: str = "normal"):
    from PIL import ImageFont  # import local: Pillow e opcional

    for caminho in FONTES.get(estilo, FONTES["normal"]):
        if Path(caminho).exists():
            try:
                return ImageFont.truetype(caminho, tamanho)
            except OSError:
                continue
    return ImageFont.load_default()


def _quebrar(texto: str, largura_px: int, fonte) -> list[str]:
    if not texto:
        return []
    palavras = str(texto).split()
    linhas: list[str] = []
    atual = ""
    for palavra in palavras:
        teste = (atual + " " + palavra).strip()
        if fonte.getlength(teste) <= largura_px or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def _dados_produto(conn: sqlite3.Connection, sku: str) -> dict:
    linha = conn.execute("SELECT * FROM produtos WHERE sku = ?", (sku,)).fetchone()
    if not linha:
        raise ValueError(
            f"SKU {sku} nao encontrado. Cadastre com 'registrar_custo' "
            "(ou importe a planilha de custos) para gerar o criativo."
        )
    return {
        "sku": linha["sku"],
        "nome": linha["nome"] or linha["sku"],
        "categoria": linha["categoria"],
        "preco_centavos": linha["preco_venda_centavos"],
        "custo_centavos": linha["custo_unitario_centavos"],
    }


def _resolver_foto(foto: str | None) -> Path | None:
    if not foto:
        return None
    caminho = Path(str(foto)).expanduser()
    return caminho.resolve() if caminho.is_file() else None


def _resolver_destino(config, subpasta: str) -> Path:
    destino = Path(config.saidas) / subpasta
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def gerar_criativo(
    conn: sqlite3.Connection,
    config,
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
    from .dinheiro import para_centavos, parse_valor

    formato = (formato or "quadrado").strip().lower()
    if formato not in ALTURAS:
        raise ValueError("formato deve ser 'quadrado' ou 'vertical'")
    modelo = (modelo or "card").strip().lower()
    if modelo not in {"card", "limpo"}:
        raise ValueError("modelo deve ser 'card' (promocional) ou 'limpo' (foto estilo anuncio)")
    tema = (tema or "claro").strip().lower()
    if tema not in TEMAS:
        raise ValueError("tema deve ser 'claro' ou 'escuro'")
    dados = _dados_produto(conn, sku)
    beneficios = [b.strip() for b in (beneficios or []) if b and b.strip()][:4] or BENEFICIOS_PADRAO
    nome = titulo or dados["nome"]
    preco_centavos = para_centavos(parse_valor(preco)) if preco not in (None, "") else dados["preco_centavos"]
    selo = (selo or "").strip() or None

    caminho_foto = _resolver_foto(foto)
    caminho_logo = _resolver_foto(logo)
    base = _resolver_destino(config, "criativos")
    nome_arquivo = _slug(sku) + "-" + formato + ("-limpo" if modelo == "limpo" else "")
    avisos_foto: list[str] = []
    if foto and not caminho_foto:
        avisos_foto.append(
            f"foto nao encontrada: {foto}. Gerei com o espaco reservado; "
            "coloque a imagem numa pasta local (ex.: Google Drive sincronizado) e informe o caminho."
        )
    if modelo == "limpo" and caminho_foto is None:
        raise ValueError(
            "o modelo 'limpo' precisa de uma foto real (--foto) do produto. "
            "Informe o caminho da foto que voce quer usar no anuncio."
        )
    svg_path = base / f"{nome_arquivo}.svg"
    if modelo == "limpo":
        svg_path.write_text(
            _svg_limpo(nome, formato, caminho_foto, caminho_logo, selo), encoding="utf-8"
        )
    else:
        svg_path.write_text(
            _svg_card(nome, beneficios, preco_centavos, tema, formato, selo, caminho_foto),
            encoding="utf-8",
        )

    png_path = None
    avisos = []
    try:
        png_path = base / f"{nome_arquivo}.png"
        if modelo == "limpo":
            _png_limpo(png_path, formato, caminho_foto, caminho_logo, selo)
        else:
            _png_card(
                png_path,
                nome,
                beneficios,
                preco_centavos,
                tema,
                formato,
                selo,
                dados["sku"],
                caminho_foto,
            )
    except ImportError:
        avisos.append(
            "Pillow nao instalado: gerei apenas o SVG. "
            "Instale com 'pip install pillow' para PNG."
        )
    except Exception as erro:  # nao falhar a ferramenta por detalhe de fonte/render
        avisos.append(f"nao consegui gerar o PNG ({erro}); o SVG foi gerado.")
        png_path = None

    return {
        "sku": sku,
        "produto": nome,
        "formato": formato,
        "modelo": modelo,
        "tema": tema,
        "preco": fmt_brl(preco_centavos) if preco_centavos else None,
        "beneficios": beneficios,
        "foto_usada": str(caminho_foto) if caminho_foto else None,
        "logo_usada": str(caminho_logo) if caminho_logo else None,
        "arquivos": {
            "svg": str(svg_path),
            "png": str(png_path) if png_path and png_path.exists() else None,
        },
        "avisos": avisos + avisos_foto,
        "proximo_passo": (
            "O PNG pode ser publicado direto no marketplace; o SVG permite editar textos "
            "no Inkscape/Illustrator. Para fotos de produto use o briefing de imagens."
        ),
    }


def briefing_imagens(
    conn: sqlite3.Connection,
    config,
    sku: str,
    beneficios: list[str] | None = None,
    publico: str | None = None,
    tom: str = "clean e confiavel",
) -> dict:
    dados = _dados_produto(conn, sku)
    beneficios = [b.strip() for b in (beneficios or []) if b and b.strip()] or BENEFICIOS_PADRAO
    publico = (publico or "consumidor brasileiro que compra por conveniencia").strip()
    nome = dados["nome"]
    categoria = dados["categoria"] or "produto"
    preco = fmt_brl(dados["preco_centavos"]) if dados["preco_centavos"] else "preco a definir"

    prompts = _prompts(nome, categoria, beneficios, publico, tom)
    destino = _resolver_destino(config, "briefings")
    arquivo = destino / f"{_slug(sku)}-briefing-imagens.md"
    conteudo = _markdown_briefing(dados, beneficios, publico, tom, prompts, preco)
    arquivo.write_text(conteudo, encoding="utf-8")

    return {
        "sku": sku,
        "produto": nome,
        "arquivo": str(arquivo),
        "total_prompts": len(prompts),
        "prompts": [
            {"uso": p["uso"], "proporcao": p["proporcao"], "prompt_en": p["prompt_en"]}
            for p in prompts
        ],
        "checklist": _checklist(),
        "proximo_passo": (
            "Cole os prompts na ferramenta de imagem que voce usa (Midjourney, DALL-E, "
            "Canva AI, Firefly) e use o checklist antes de publicar."
        ),
    }


# ── prompts ─────────────────────────────────────────────────────────────────


def _prompts(nome: str, categoria: str, beneficios: list[str], publico: str, tom: str) -> list[dict]:
    beneficio_txt = ", ".join(beneficios)
    base = (
        f"professional e-commerce product photography of a {nome} ({categoria}), "
        f"{beneficio_txt}, for {publico}, {tom} aesthetic"
    )
    return [
        {
            "uso": "1. Imagem principal (fundo limpo)",
            "proporcao": "1:1",
            "prompt_en": (
                f"{base}, centered on a seamless soft white background, studio softbox lighting, "
                "subtle shadow, product occupying 85% of the frame, ultra sharp focus, "
                "no text, no logo, no watermark, high resolution"
            ),
            "dica": "A primeira imagem deve vender sozinha e seguir a regra do marketplace "
            "(geralmente fundo branco/limpo). Confirme no painel.",
        },
        {
            "uso": "2. Lifestyle (contexto de uso)",
            "proporcao": "1:1",
            "prompt_en": (
                f"{base}, in a realistic Brazilian home environment, naturally being used, "
                "warm morning light, shallow depth of field, aspirational but believable, "
                "no text, no logo"
            ),
            "dica": "Mostre a pessoa usando; evita cara de foto de catalogo generica.",
        },
        {
            "uso": "3. Detalhe/macro (material e acabamento)",
            "proporcao": "1:1",
            "prompt_en": (
                f"extreme macro detail shot of the {nome}, showing texture, finish and build quality, "
                "dark neutral background, dramatic side lighting, high contrast, no text"
            ),
            "dica": "Bom para responder objecao sobre material/durabilidade.",
        },
        {
            "uso": "4. Escala e medidas",
            "proporcao": "1:1",
            "prompt_en": (
                f"clean infographic-style product photo of the {nome} next to a common household object "
                "for scale, flat design, minimal background, space for measurement labels, no text"
            ),
            "dica": "Adicione as medidas reais depois na arte (nao peca medidas a IA).",
        },
        {
            "uso": "5. Antes/depois ou problema/solucao",
            "proporcao": "4:5",
            "prompt_en": (
                f"split composition showing the problem and the solution using the {nome}, "
                "left side organized chaos, right side tidy result, consistent lighting, no text"
            ),
            "dica": "Funciona bem para organizacao, limpeza, beleza e utilidades.",
        },
        {
            "uso": "6. Embalagem / unboxing",
            "proporcao": "1:1",
            "prompt_en": (
                f"unboxing scene with the {nome} and simple recyclable packaging on a clean table, "
                "hands opening the box, warm light, trustworthy feeling, no text, no brand logo"
            ),
            "dica": "Reduz medo de compra e ajuda na expectativa de entrega.",
        },
    ]


def _checklist() -> list[str]:
    return [
        "Formato e tamanho: 1:1 com pelo menos 1000x1000 px (a maioria dos marketplaces "
        "recomenda 1200+; confirme no painel).",
        "Primeira imagem: produto claro, fundo limpo, sem texto excessivo nem selo inventado.",
        "Nada de marca de terceiros, personagem, celebridade ou promessa de resultado.",
        "Medidas reais vao na arte/descricao — nunca deixe a IA inventar numeros.",
        "Nao use 'antes e depois' de saude/estetica; foque em organizacao/uso.",
        "Mantenha as cores reais do produto: arte enganosa gera devolucao.",
        "Inclua o produto em uso e em escala para reduzir duvida e devolucao.",
        "Alt text (acessibilidade): descricao curta do que aparece na imagem.",
    ]


def _markdown_briefing(dados, beneficios, publico, tom, prompts, preco) -> str:
    linhas = [
        f"# Briefing de imagens — {dados['nome']}",
        "",
        f"- **SKU:** {dados['sku']}",
        f"- **Categoria:** {dados['categoria'] or 'nao informada'}",
        f"- **Preco de venda:** {preco}",
        f"- **Publico:** {publico}",
        f"- **Tom visual:** {tom}",
        f"- **Beneficios:** {', '.join(beneficios)}",
        f"- **Gerado em:** {dt.datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "## Prompts (use um por imagem, 1024 px ou mais)",
        "",
    ]
    for p in prompts:
        linhas += [
            f"### {p['uso']} (proporcao {p['proporcao']})",
            "",
            "```text",
            p["prompt_en"],
            "```",
            "",
            f"_{p['dica']}_",
            "",
        ]
    linhas += [
        "## Prompt negativo (cole no campo 'negative prompt' quando existir)",
        "",
        "```text",
        "text, watermark, logo, distorted proportions, extra fingers, blurry, low resolution, "
        "fake brand, unrealistic size, cluttered background",
        "```",
        "",
        "## Checklist antes de publicar",
        "",
    ]
    linhas += [f"- [ ] {item}" for item in _checklist()]
    linhas += [
        "",
        "## Observacao",
        "",
        "Nao e obrigatorio gerar todas com IA: a foto principal e o lifestyle costumam valer "
        "mais que 6 imagens medianas. Se tiver foto real do produto, use como base (img2img) "
        "para manter o produto fiel.",
        "",
    ]
    return "\n".join(linhas)


# ── render ──────────────────────────────────────────────────────────────────


def _slug(texto: str) -> str:
    import re
    import unicodedata

    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-") or "sku"


def _png_card(
    caminho: Path,
    nome: str,
    beneficios: list[str],
    preco_centavos: int | None,
    tema: str,
    formato: str,
    selo: str | None,
    sku: str,
    foto: Path | None = None,
) -> None:
    from PIL import Image, ImageDraw, ImageOps

    cores = TEMAS[tema]
    largura = LARGURA
    altura = ALTURAS[formato]
    imagem = Image.new("RGB", (largura, altura), cores["fundo"])
    desenho = ImageDraw.Draw(imagem)
    _gradiente(imagem, desenho, cores["fundo"], cores["fundo2"])

    margem = 80
    y = 70

    # faixa do topo: SKU + selo opcional
    fonte_pequena = _fonte(28, "negrito")
    desenho.text((margem, y), sku.upper(), font=fonte_pequena, fill=cores["secundario"])
    if selo:
        selo_fonte = _fonte(28, "negrito")
        largura_selo = int(selo_fonte.getlength(selo) + 48)
        desenho.rounded_rectangle(
            (largura - margem - largura_selo, y - 8, largura - margem, y + 44),
            radius=26,
            fill=cores["destaque"],
        )
        desenho.text(
            (largura - margem - largura_selo + 24, y),
            selo,
            font=selo_fonte,
            fill=TEMAS[tema]["branco"],
        )
    y += 110

    # titulo
    fonte_titulo = _fonte(64, "negrito")
    linhas_titulo = _quebrar(nome, largura - 2 * margem, fonte_titulo)[:2]
    for linha in linhas_titulo:
        desenho.text((margem, y), linha, font=fonte_titulo, fill=cores["tinta"])
        y += 76
    y += 18

    # beneficios (max 3 para garantir a area da foto)
    fonte_beneficio = _fonte(36, "normal")
    for beneficio in beneficios[:3]:
        desenho.ellipse((margem, y + 8, margem + 20, y + 28), fill=cores["secundario"])
        linhas_beneficio = _quebrar(beneficio, largura - 2 * margem - 60, fonte_beneficio)[:2]
        for i, linha in enumerate(linhas_beneficio):
            desenho.text(
                (margem + 40, y + (i * 44) - 4),
                linha,
                font=fonte_beneficio,
                fill=cores["tinta"],
            )
        y += 44 * max(1, len(linhas_beneficio)) + 16
        if y > altura - 360:
            break

    # area reservada para a foto do produto (ou foto real, se informada)
    area_topo = y + 12
    area_base = altura - 300 - 24
    if area_base - area_topo > 160:
        caixa = (margem, area_topo, largura - margem, area_base)
        if foto is not None:
            _colar_foto(imagem, foto, caixa, raio=32)
        else:
            desenho.rounded_rectangle(
                caixa,
                radius=32,
                outline=cores["secundario"],
                width=3,
            )
            dica = "ESPACO PARA A FOTO DO PRODUTO"
            fonte_dica = _fonte(30, "normal")
            desenho.text(
                (
                    (largura - fonte_dica.getlength(dica)) / 2,
                    (area_topo + area_base) / 2 - 20,
                ),
                dica,
                font=fonte_dica,
                fill=cores["secundario"],
            )

    # caixa de preco
    caixa_altura = 190
    topo = altura - caixa_altura - 110
    desenho.rounded_rectangle(
        (margem, topo, largura - margem, topo + caixa_altura), radius=36, fill=cores["tinta"]
    )
    if preco_centavos:
        fonte_preco = _fonte(96, "negrito")
        texto_preco = fmt_brl(preco_centavos)
        desenho.text((margem + 50, topo + 28), texto_preco, font=fonte_preco, fill=cores["fundo"])
        desenho.text(
            (margem + 54, topo + 132),
            "a vista no anuncio",
            font=_fonte(28, "normal"),
            fill=cores["fundo2"],
        )
    else:
        desenho.text(
            (margem + 50, topo + 60),
            "Preco no anuncio",
            font=_fonte(64, "negrito"),
            fill=cores["fundo"],
        )

    rodape = "Confira medidas, cores e prazo no anuncio"
    fonte_rodape = _fonte(26, "normal")
    desenho.text(
        ((largura - fonte_rodape.getlength(rodape)) / 2, altura - 66),
        rodape,
        font=fonte_rodape,
        fill=cores["tinta"],
    )
    imagem.save(caminho, "PNG", optimize=True)


def _colar_foto(imagem, foto: Path, caixa: tuple[int, int, int, int], raio: int = 32) -> None:
    """Cola a foto real na area: fundo desfocado (cover) + produto inteiro (contain)."""
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

    largura_area = caixa[2] - caixa[0]
    altura_area = caixa[3] - caixa[1]
    foto_aberta = Image.open(foto).convert("RGB")

    fundo = ImageOps.fit(foto_aberta, (largura_area, altura_area), method=Image.LANCZOS)
    fundo = fundo.filter(ImageFilter.GaussianBlur(16))
    fundo = ImageEnhance.Brightness(fundo).enhance(0.72)

    frente = ImageOps.contain(
        foto_aberta, (int(largura_area * 0.94), int(altura_area * 0.94)), method=Image.LANCZOS
    )
    fundo.paste(frente, ((largura_area - frente.width) // 2, (altura_area - frente.height) // 2))

    mascara = Image.new("L", (largura_area, altura_area), 0)
    desenho_mascara = ImageDraw.Draw(mascara)
    desenho_mascara.rounded_rectangle((0, 0, largura_area, altura_area), radius=raio, fill=255)
    imagem.paste(fundo, (caixa[0], caixa[1]), mascara)




def _recortar_bordas_brancas(imagem, tolerancia: int = 245):
    """Remove faixas uniformes claras nas bordas (fotos exportadas com moldura)."""
    from PIL import Image

    foto = imagem.convert("RGB")
    largura, altura = foto.size
    pixels = foto.load()

    def linha_branca(y: int) -> bool:
        brancos = sum(
            1 for x in range(largura)
            if min(pixels[x, y]) >= tolerancia
        )
        return brancos >= largura * 0.98

    def coluna_branca(x: int) -> bool:
        brancos = sum(
            1 for y in range(altura)
            if min(pixels[x, y]) >= tolerancia
        )
        return brancos >= altura * 0.98

    topo, base, esquerda, direita = 0, altura - 1, 0, largura - 1
    while topo < base and linha_branca(topo):
        topo += 1
    while base > topo and linha_branca(base):
        base -= 1
    while esquerda < direita and coluna_branca(esquerda):
        esquerda += 1
    while direita > esquerda and coluna_branca(direita):
        direita -= 1
    if (topo, base, esquerda, direita) != (0, altura - 1, 0, largura - 1):
        return foto.crop((esquerda, topo, direita + 1, base + 1))
    return foto


def _preparar_logo(caminho: Path, largura_alvo: int):
    """Carrega a logo, remove fundo claro/chapado quando necessario e corta sobras."""
    from PIL import Image

    marca = Image.open(caminho).convert("RGBA")
    if marca.getchannel("A").getextrema()[0] == 255:
        cor = marca.convert("RGB").getpixel((1, 1))
        if min(cor) >= 225:  # fundo claro: vira transparente
            dados = []
            for r, g, b, a in marca.getdata():
                if r >= 225 and g >= 225 and b >= 225:
                    dados.append((r, g, b, 0))
                else:
                    dados.append((r, g, b, a))
            marca.putdata(dados)
    caixa = marca.getchannel("A").getbbox()
    if caixa:
        marca = marca.crop(caixa)
    proporcao = largura_alvo / marca.width
    return marca.resize((largura_alvo, max(1, int(marca.height * proporcao))), Image.LANCZOS)


def _png_limpo(
    caminho: Path,
    formato: str,
    foto: Path,
    logo: Path | None = None,
    selo: str | None = None,
) -> None:
    """Foto estilo anuncio: imagem cheia, sem texto de preco, logo discreta."""
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

    largura = LARGURA
    altura = ALTURAS[formato]
    base = Image.new("RGB", (largura, altura), "#FAFAF8")
    foto_aberta = _recortar_bordas_brancas(Image.open(foto).convert("RGB"))
    recortada = ImageOps.fit(foto_aberta, (largura, altura), method=Image.LANCZOS)
    base.paste(recortada, (0, 0))

    # leve escurecida no rodape para a logo ficar legivel
    rodape = Image.new("L", (largura, 260), 0)
    desenho_rodape = ImageDraw.Draw(rodape)
    for i in range(260):
        valor = int(110 * (i / 260) ** 1.4)
        desenho_rodape.line([(0, i), (largura, i)], fill=valor)
    escuro = Image.new("RGB", (largura, 260), (0, 0, 0))
    base.paste(escuro, (0, altura - 260), rodape)

    if logo is not None:
        try:
            marca = _preparar_logo(logo, int(largura * 0.22))
            margem = int(largura * 0.045)
            base.paste(
                marca,
                (largura - marca.width - margem, altura - marca.height - margem),
                marca,
            )
        except OSError:
            pass

    if selo:
        desenho = ImageDraw.Draw(base)
        fonte = _fonte(30, "negrito")
        largura_selo = int(fonte.getlength(selo) + 52)
        desenho.rounded_rectangle(
            (int(largura * 0.045), int(largura * 0.045),
             int(largura * 0.045) + largura_selo, int(largura * 0.045) + 58),
            radius=29,
            fill=TEMAS["claro"]["destaque"],
        )
        desenho.text(
            (int(largura * 0.045) + 26, int(largura * 0.045) + 12),
            selo,
            font=fonte,
            fill="#FFFFFF",
        )
    base.save(caminho, "PNG", optimize=True)


def _svg_limpo(
    nome: str,
    formato: str,
    foto: Path,
    logo: Path | None = None,
    selo: str | None = None,
) -> str:
    largura = LARGURA
    altura = ALTURAS[formato]
    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{altura}" '
        f'viewBox="0 0 {largura} {altura}">',
        f'<rect width="{largura}" height="{altura}" fill="#FAFAF8"/>',
        f'<image href="{html.escape(foto.as_uri())}" x="0" y="0" width="{largura}" '
        f'height="{altura}" preserveAspectRatio="xMidYMid slice"/>',
        '<defs><linearGradient id="sombra" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#000" stop-opacity="0.45"/></linearGradient></defs>',
        f'<rect x="0" y="{altura - 260}" width="{largura}" height="260" fill="url(#sombra)"/>',
    ]
    if logo is not None:
        partes.append(
            f'<image href="{html.escape(logo.as_uri())}" x="{largura - 300}" '
            f'y="{altura - 160}" width="250" height="110" preserveAspectRatio="xMidYMid meet"/>'
        )
    if selo:
        partes.append(
            f'<rect x="{int(largura * 0.045)}" y="{int(largura * 0.045)}" width="{len(selo) * 20 + 40}" '
            f'height="58" rx="29" fill="{TEMAS["claro"]["destaque"]}"/>'
            f'<text x="{int(largura * 0.045) + 20}" y="{int(largura * 0.045) + 38}" '
            f'font-family="DejaVu Sans, Arial" font-size="30" font-weight="bold" '
            f'fill="#FFFFFF">{html.escape(selo)}</text>'
        )
    partes.append("</svg>")
    return "\n".join(partes)


def _gradiente(imagem, desenho, cor1: str, cor2: str) -> None:
    largura, altura = imagem.size
    r1, g1, b1 = _rgb(cor1)
    r2, g2, b2 = _rgb(cor2)
    for y in range(altura):
        t = y / max(1, altura - 1)
        desenho.line(
            [(0, y), (largura, y)],
            fill=(int(r1 + (r2 - r1) * t), int(g1 + (g2 - g1) * t), int(b1 + (b2 - b1) * t)),
        )
    # volta o fundo do desenho para as cores solidas usadas depois
    return None


def _rgb(hexadecimal: str) -> tuple[int, int, int]:
    hexadecimal = hexadecimal.lstrip("#")
    return tuple(int(hexadecimal[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _svg_card(
    nome: str,
    beneficios: list[str],
    preco_centavos: int | None,
    tema: str,
    formato: str,
    selo: str | None,
    foto: Path | None = None,
) -> str:
    cores = TEMAS[tema]
    largura, altura = LARGURA, ALTURAS[formato]
    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{altura}" '
        f'viewBox="0 0 {largura} {altura}">',
        "<defs>",
        f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{cores["fundo"]}"/>'
        f'<stop offset="1" stop-color="{cores["fundo2"]}"/></linearGradient>',
        "</defs>",
        f'<rect width="{largura}" height="{altura}" fill="url(#bg)"/>',
    ]
    margem = 80
    y = 100
    partes.append(
        f'<text x="{margem}" y="{y}" font-family="DejaVu Sans, Arial" font-size="28" '
        f'font-weight="bold" fill="{cores["secundario"]}">SKU</text>'
    )
    if selo:
        largura_selo = max(160, len(selo) * 18)
        partes.append(
            f'<rect x="{largura - margem - largura_selo}" y="{y - 36}" width="{largura_selo}" '
            f'height="52" rx="26" fill="{cores["destaque"]}"/>'
            f'<text x="{largura - margem - largura_selo + 24}" y="{y}" font-family="DejaVu Sans, Arial" '
            f'font-size="28" font-weight="bold" fill="{cores["branco"]}">{html.escape(selo)}</text>'
        )
    y += 100
    linhas = textwrap.wrap(nome, width=26)[:2] or [nome]
    for linha in linhas:
        partes.append(
            f'<text x="{margem}" y="{y}" font-family="DejaVu Sans, Arial" font-size="64" '
            f'font-weight="bold" fill="{cores["tinta"]}">{html.escape(linha)}</text>'
        )
        y += 76
    y += 18
    for beneficio in beneficios[:3]:
        partes.append(f'<circle cx="{margem + 10}" cy="{y - 10}" r="10" fill="{cores["secundario"]}"/>')
        partes.append(
            f'<text x="{margem + 40}" y="{y}" font-family="DejaVu Sans, Arial" font-size="36" '
            f'fill="{cores["tinta"]}">{html.escape(beneficio)}</text>'
        )
        y += 60
    area_topo = y + 12
    area_base = altura - 300 - 24
    if area_base - area_topo > 160:
        if foto is not None:
            partes.append(
                f'<image href="{html.escape(foto.as_uri())}" x="{margem}" y="{area_topo}" '
                f'width="{largura - 2 * margem}" height="{area_base - area_topo}" '
                f'preserveAspectRatio="xMidYMid slice"/>'
            )
        else:
            meio_x = largura / 2
            meio_y = (area_topo + area_base) / 2
            partes.append(
                f'<rect x="{margem}" y="{area_topo}" width="{largura - 2 * margem}" '
                f'height="{area_base - area_topo}" rx="32" fill="none" '
                f'stroke="{cores["secundario"]}" stroke-width="3" stroke-dasharray="18 14"/>'
                f'<text x="{meio_x}" y="{meio_y}" text-anchor="middle" font-family="DejaVu Sans, Arial" '
                f'font-size="30" fill="{cores["secundario"]}">ESPACO PARA A FOTO DO PRODUTO</text>'
            )
    topo = altura - 300
    partes.append(
        f'<rect x="{margem}" y="{topo}" width="{largura - 2 * margem}" height="190" rx="36" '
        f'fill="{cores["tinta"]}"/>'
    )
    if preco_centavos:
        partes.append(
            f'<text x="{margem + 50}" y="{topo + 100}" font-family="DejaVu Sans, Arial" '
            f'font-size="92" font-weight="bold" fill="{cores["fundo"]}">{html.escape(fmt_brl(preco_centavos))}</text>'
            f'<text x="{margem + 54}" y="{topo + 158}" font-family="DejaVu Sans, Arial" '
            f'font-size="28" fill="{cores["fundo2"]}">a vista no anuncio</text>'
        )
    else:
        partes.append(
            f'<text x="{margem + 50}" y="{topo + 120}" font-family="DejaVu Sans, Arial" '
            f'font-size="64" font-weight="bold" fill="{cores["fundo"]}">Preco no anuncio</text>'
        )
    rodape = "Confira medidas, cores e prazo no anuncio"
    partes.append(
        f'<text x="{largura / 2}" y="{altura - 55}" text-anchor="middle" '
        f'font-family="DejaVu Sans, Arial" font-size="26" fill="{cores["tinta"]}">{rodape}</text>'
    )
    partes.append("</svg>")
    return "\n".join(partes)


__all__ = ["gerar_criativo", "briefing_imagens", "TEMAS", "ALTURAS"]
