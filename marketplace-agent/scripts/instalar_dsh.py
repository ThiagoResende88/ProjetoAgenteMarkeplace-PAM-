#!/usr/bin/env python3
"""Instala o agente de marketplaces no DSH (perfil web).

O que faz:
  1. copia o skill para <workspace>/.dsh/skills/gestor-marketplaces/SKILL.md;
  2. injeta o bloco do dsh/patch-marketplaces.yml em
     $DSH_HOME/profiles/<perfil>/cordis.patch.yml, trocando os caminhos;
  3. valida o YAML resultante com ``dsh --profile <perfil> --dump-config``
     (se o binario dsh estiver no PATH) e reverte em caso de erro.

Rodar de novo e seguro: o bloco fica entre marcadores e e substituido.

Uso:
    python3 scripts/instalar_dsh.py [--dry-run] [--perfil web] [--remover]
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJETO = Path(__file__).resolve().parents[1]
TEMPLATE = PROJETO / "dsh" / "patch-marketplaces.yml"
TEMPLATE_UPSELER = PROJETO / "dsh" / "patch-upseller-mcp.yml"
SKILLS_ORIGEM = PROJETO / "skills"
MARCA_INICIO = "# >>> mktagent"
MARCA_FIM = "# <<< mktagent"
MARCA_UPS_INICIO = "# >>> mktagent-upseller"
MARCA_UPS_FIM = "# <<< mktagent-upseller"

_RE_INICIO = re.compile(r"^# >>> mktagent[ \t]*$", re.MULTILINE)
_RE_FIM = re.compile(r"^# <<< mktagent[ \t]*$", re.MULTILINE)
_RE_BLOCO = re.compile(
    r"^# >>> mktagent[ \t]*$.*?^# <<< mktagent[ \t]*$",
    re.MULTILINE | re.DOTALL,
)


def aplicar_upseller_texto(texto: str, bloco: str) -> str:
    padrao = re.compile(
        re.escape(MARCA_UPS_INICIO) + r".*?" + re.escape(MARCA_UPS_FIM), re.DOTALL
    )
    if padrao.search(texto):
        return padrao.sub(lambda _m: bloco, texto, count=1)
    return texto.rstrip("\n") + "\n\n" + bloco.strip("\n") + "\n"


def remover_upseller_texto(texto: str) -> str:
    padrao = re.compile(
        re.escape(MARCA_UPS_INICIO) + r".*?" + re.escape(MARCA_UPS_FIM) + r"[ \t]*\n?",
        re.DOTALL,
    )
    novo = padrao.sub("", texto)
    while "\n\n\n" in novo:
        novo = novo.replace("\n\n\n", "\n\n")
    return novo


def _limites_ups(texto: str) -> tuple[int, int] | None:
    inicio = re.search(re.escape(MARCA_UPS_INICIO) + r"[ \t]*$", texto, re.MULTILINE)
    if not inicio:
        return None
    fim = re.search(re.escape(MARCA_UPS_FIM) + r"[ \t]*$", texto[inicio.end():], re.MULTILINE)
    if not fim:
        return None
    return inicio.start(), inicio.end() + fim.end()


def ler_env(arquivo: Path) -> dict[str, str]:
    valores: dict[str, str] = {}
    if not arquivo.exists():
        return valores
    for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valores[chave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def bloco_upseller() -> str | None:
    """Monta o bloco do MCP do UpSeller se as credenciais existirem."""
    credenciais = {**ler_env(PROJETO / ".env")}
    cliente = (os.environ.get("UPSELLER_CLIENT_ID") or credenciais.get("UPSELLER_CLIENT_ID") or "").strip()
    token = (os.environ.get("UPSELLER_MCP_TOKEN") or credenciais.get("UPSELLER_MCP_TOKEN") or "").strip()
    if not cliente or not token:
        return None
    if not TEMPLATE_UPSELER.exists():
        raise SystemExit(f"modelo nao encontrado: {TEMPLATE_UPSELER}")
    texto = TEMPLATE_UPSELER.read_text(encoding="utf-8")
    limites = _limites_ups(texto)
    if limites is None:
        raise SystemExit(f"modelo do UpSeller sem marcadores: {TEMPLATE_UPSELER}")
    bloco = texto[limites[0] : limites[1]]
    bloco = bloco.replace("{{UPSELLER_CLIENT_ID}}", cliente).replace(
        "{{UPSELLER_MCP_TOKEN}}", token
    )
    return bloco




def _limites(texto: str) -> tuple[int, int] | None:
    """Posicao (inicio, fim) do bloco marcado, se existir."""
    inicio = _RE_INICIO.search(texto)
    if not inicio:
        return None
    fim = _RE_FIM.search(texto, inicio.end())
    if not fim:
        return None
    return inicio.start(), fim.end()


def dsh_home() -> Path:
    return Path(os.environ.get("DSH_HOME") or (Path.home() / ".dsh")).expanduser()


def caminho_perfil(perfil: str) -> Path:
    return dsh_home() / "profiles" / perfil / "cordis.patch.yml"


def python_do_projeto() -> str:
    return sys.executable or shutil.which("python3") or "/usr/bin/python3"


def workspace(padrao: Path | None = None) -> Path:
    if padrao:
        return padrao.resolve()
    return PROJETO.parent


def bloco_novo() -> str:
    texto = TEMPLATE.read_text(encoding="utf-8")
    limites = _limites(texto)
    if limites is None:
        raise SystemExit(f"modelo sem os marcadores esperados: {TEMPLATE}")
    bloco = texto[limites[0] : limites[1]]
    bloco = bloco.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
    substituicoes = {
        "{{PROJETO}}": str(PROJETO),
        "{{PYTHON}}": python_do_projeto(),
        "{{DSH_HOME}}": str(dsh_home()),
    }
    for chave, valor in substituicoes.items():
        bloco = bloco.replace(chave, valor)
    if "{{" in bloco:
        raise SystemExit("modelo de patch com marcador nao substituido: " + bloco[:200])
    return f"{MARCA_INICIO}\n{bloco}\n{MARCA_FIM}\n"


def aplicar_no_patch(caminho: Path, bloco: str) -> str:
    """Insere/substitui o bloco e devolve o texto novo (sem gravar)."""
    atual = caminho.read_text(encoding="utf-8") if caminho.exists() else ""
    bloco = bloco.strip("\n")
    if _RE_BLOCO.search(atual):
        novo = _RE_BLOCO.sub(lambda _m: bloco, atual, count=1)
    elif atual.strip():
        novo = atual.rstrip("\n") + "\n\n" + bloco + "\n"
    else:
        novo = bloco + "\n"
    if not novo.endswith("\n"):
        novo += "\n"
    return novo


def remover_do_patch(caminho: Path) -> str:
    atual = caminho.read_text(encoding="utf-8")
    if not _RE_BLOCO.search(atual):
        return atual
    novo = _RE_BLOCO.sub("", atual, count=1)
    while "\n\n\n" in novo:
        novo = novo.replace("\n\n\n", "\n\n")
    return novo.strip("\n") + ("\n" if novo.strip() else "")


def copiar_skills(destino_workspace: Path, dry_run: bool) -> list[Path]:
    """Copia todas as skills do projeto para <workspace>/.dsh/skills/."""
    resultados: list[Path] = []
    if not SKILLS_ORIGEM.exists():
        return resultados
    for origem in sorted(SKILLS_ORIGEM.iterdir()):
        if not origem.is_dir():
            continue
        destino = destino_workspace / ".dsh" / "skills" / origem.name
        resultados.append(destino / "SKILL.md")
        if dry_run:
            continue
        for arquivo in origem.rglob("*"):
            if arquivo.is_file():
                relativo = arquivo.relative_to(origem)
                alvo = destino / relativo
                alvo.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(arquivo, alvo)
    return resultados


def validar_com_dsh(perfil: str) -> tuple[bool, str]:
    dsh = shutil.which("dsh")
    if not dsh:
        return True, "dsh nao encontrado no PATH; validacao pulada (reinicie o DSH depois)"
    try:
        resultado = subprocess.run(
            [dsh, "--profile", perfil, "--dump-config"],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (subprocess.TimeoutExpired, OSError) as erro:
        return False, f"nao consegui validar a configuracao: {erro}"
    if resultado.returncode != 0:
        detalhe = (resultado.stderr or resultado.stdout or "").strip()[-1500:]
        return False, "dsh --dump-config falhou:\n" + detalhe
    saida = resultado.stdout
    esperados = ["mcp-marketplaces", "preset-marketplaces"]
    if "--com-upseller" in sys.argv:
        esperados.append("mcp-upseller")
    faltando = [nome for nome in esperados if nome not in saida]
    if faltando:
        return False, "configuracao valida, mas nao encontrei: " + ", ".join(faltando)
    return True, "configuracao validada com dsh --dump-config"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--perfil", default="web", help="perfil do DSH (padrao: web)")
    parser.add_argument("--dry-run", action="store_true", help="mostra o que seria feito")
    parser.add_argument("--remover", action="store_true", help="remove a integracao do perfil")
    parser.add_argument("--workspace", default=None, help="workspace onde colocar o skill")
    parser.add_argument("--sem-validar", action="store_true", help="pula o dsh --dump-config")
    parser.add_argument(
        "--com-upseller",
        action="store_true",
        help="adiciona o MCP oficial do UpSeller (le UPSELLER_CLIENT_ID/MCP_TOKEN do .env)",
    )
    parser.add_argument(
        "--remover-upseller", action="store_true", help="remove o MCP do UpSeller do perfil"
    )
    args = parser.parse_args(argv)

    if not TEMPLATE.exists():
        raise SystemExit(f"modelo nao encontrado: {TEMPLATE}")
    patch = caminho_perfil(args.perfil)
    if not patch.exists():
        raise SystemExit(
            f"perfil do DSH nao encontrado: {patch}\n"
            "Abra o DSH Web ('dsh web') uma vez para criar o perfil, ou informe --perfil."
        )

    alvo_skills = copiar_skills(
        workspace(Path(args.workspace) if args.workspace else None), args.dry_run
    )
    novo = remover_do_patch(patch) if args.remover else aplicar_no_patch(patch, bloco_novo())

    bloco_ups = None
    if args.com_upseller:
        bloco_ups = bloco_upseller()
        if not bloco_ups:
            raise SystemExit(
                "--com-upseller: preencha UPSELLER_CLIENT_ID e UPSELLER_MCP_TOKEN no .env "
                "(Painel UpSeller -> Plataforma Aberta -> API Privada -> Gerar)."
            )
        novo = aplicar_upseller_texto(novo, bloco_ups)
    elif args.remover_upseller:
        novo = remover_upseller_texto(novo)

    print(f"perfil:   {patch}")
    for skill in alvo_skills:
        print(f"skill:    {skill}")
    print(f"projeto:  {PROJETO}")
    if args.dry_run:
        print("\n--- conteudo que seria gravado no patch ---")
        print(novo)
        print("--- fim (nada foi gravado) ---")
        return 0

    backup = patch.with_name(patch.name + time.strftime(".bak-%Y%m%d-%H%M%S"))
    shutil.copy2(patch, backup)
    patch.write_text(novo, encoding="utf-8")
    print(f"backup:   {backup}")

    if args.remover:
        print("\nIntegracao removida do perfil. Reinicie o DSH se o agente ainda aparecer.")
        return 0

    if not args.sem_validar:
        ok, mensagem = validar_com_dsh(args.perfil)
        if not ok:
            shutil.copy2(backup, patch)
            print("\nERRO: configuracao invalida, restaurei o backup.")
            print(mensagem)
            return 1
        print(f"validacao: {mensagem}")

    print(
        "\nPronto. Abra uma NOVA conversa no DSH Web e escolha o agente "
        "'Gestor de Marketplaces' no seletor. As ferramentas aparecem como "
        "mcp__marketplaces__*."
    )
    print(
        "Se o DSH nao tiver recarregado sozinho (HMR), feche e abra o DSH Web."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
