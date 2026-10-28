"""Banco de dados SQLite do mktagent.

Sem ORM e sem dependencia externa: schema versionado por ``PRAGMA user_version``.
Valores monetarios sempre em centavos (INTEGER).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import Config

VERSAO_ESQUEMA = 3

ESQUEMA = """
CREATE TABLE IF NOT EXISTS meta (
    chave TEXT PRIMARY KEY,
    valor TEXT
);

CREATE TABLE IF NOT EXISTS contas_loja (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    marketplace TEXT NOT NULL,
    apelido TEXT NOT NULL,
    loja_id TEXT,
    moeda TEXT NOT NULL DEFAULT 'BRL',
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (marketplace, apelido)
);

CREATE TABLE IF NOT EXISTS produtos (
    sku TEXT PRIMARY KEY,
    nome TEXT,
    custo_unitario_centavos INTEGER,
    preco_venda_centavos INTEGER,
    categoria TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    atualizado_em TEXT
);

CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conta_id INTEGER NOT NULL REFERENCES contas_loja(id),
    marketplace TEXT NOT NULL,
    pedido_externo TEXT NOT NULL,
    cliente TEXT,
    status TEXT,
    situacao TEXT NOT NULL DEFAULT 'desconhecido',
    data_pedido TEXT NOT NULL,
    data_entrega TEXT,
    itens_total_centavos INTEGER NOT NULL DEFAULT 0,
    desconto_centavos INTEGER NOT NULL DEFAULT 0,
    frete_cobrado_centavos INTEGER NOT NULL DEFAULT 0,
    frete_pago_centavos INTEGER NOT NULL DEFAULT 0,
    comissao_centavos INTEGER NOT NULL DEFAULT 0,
    taxa_servico_centavos INTEGER NOT NULL DEFAULT 0,
    cupom_centavos INTEGER NOT NULL DEFAULT 0,
    imposto_centavos INTEGER NOT NULL DEFAULT 0,
    repasse_centavos INTEGER,
    moeda TEXT NOT NULL DEFAULT 'BRL',
    origem_importacao TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (marketplace, pedido_externo)
);

CREATE INDEX IF NOT EXISTS idx_pedidos_data ON pedidos (data_pedido);
CREATE INDEX IF NOT EXISTS idx_pedidos_situacao ON pedidos (situacao);
CREATE INDEX IF NOT EXISTS idx_pedidos_marketplace ON pedidos (marketplace);

CREATE TABLE IF NOT EXISTS itens_pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    sku TEXT NOT NULL,
    nome_produto TEXT,
    quantidade INTEGER NOT NULL DEFAULT 1,
    preco_unitario_centavos INTEGER NOT NULL DEFAULT 0,
    custo_unitario_centavos INTEGER,
    UNIQUE (pedido_id, sku)
);

CREATE INDEX IF NOT EXISTS idx_itens_sku ON itens_pedido (sku);

CREATE TABLE IF NOT EXISTS repasses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conta_id INTEGER NOT NULL REFERENCES contas_loja(id),
    data TEXT NOT NULL,
    valor_centavos INTEGER NOT NULL,
    referencia TEXT,
    pedido_externo TEXT,
    origem TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (conta_id, data, valor_centavos, referencia)
);

CREATE INDEX IF NOT EXISTS idx_repasses_data ON repasses (data);

CREATE TABLE IF NOT EXISTS contas_financeiras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL CHECK (tipo IN ('pagar', 'receber')),
    descricao TEXT NOT NULL,
    categoria TEXT NOT NULL DEFAULT 'outros',
    marketplace TEXT,
    valor_centavos INTEGER NOT NULL,
    vencimento TEXT NOT NULL,
    pago_em TEXT,
    status TEXT NOT NULL DEFAULT 'aberta',
    recorrente INTEGER NOT NULL DEFAULT 0,
    observacao TEXT,
    origem TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (tipo, descricao, valor_centavos, vencimento)
);

CREATE INDEX IF NOT EXISTS idx_contas_vencimento ON contas_financeiras (vencimento);
CREATE INDEX IF NOT EXISTS idx_contas_status ON contas_financeiras (status);

CREATE TABLE IF NOT EXISTS estoque (
    sku TEXT PRIMARY KEY,
    quantidade INTEGER NOT NULL DEFAULT 0,
    atualizado_em TEXT
);

CREATE TABLE IF NOT EXISTS desempenho_diario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canal TEXT NOT NULL DEFAULT 'consolidado',
    data TEXT NOT NULL,
    pedidos INTEGER NOT NULL DEFAULT 0,
    pedidos_validos INTEGER NOT NULL DEFAULT 0,
    pedidos_cancelados INTEGER NOT NULL DEFAULT 0,
    clientes INTEGER NOT NULL DEFAULT 0,
    receita_total_centavos INTEGER NOT NULL DEFAULT 0,
    receita_valida_centavos INTEGER NOT NULL DEFAULT 0,
    origem TEXT,
    UNIQUE (canal, data)
);

CREATE INDEX IF NOT EXISTS idx_desempenho_data ON desempenho_diario (data);

CREATE TABLE IF NOT EXISTS importacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arquivo TEXT,
    hash TEXT,
    tipo TEXT,
    marketplace TEXT,
    conta TEXT,
    linhas INTEGER NOT NULL DEFAULT 0,
    inseridos INTEGER NOT NULL DEFAULT 0,
    atualizados INTEGER NOT NULL DEFAULT 0,
    ignorados INTEGER NOT NULL DEFAULT 0,
    avisos TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def conectar(caminho: Path) -> sqlite3.Connection:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(caminho))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.DatabaseError:
        pass
    return conn


def garantir_esquema(conn: sqlite3.Connection) -> None:
    conn.executescript(ESQUEMA)
    _migrar(conn)
    versao = conn.execute("PRAGMA user_version").fetchone()[0]
    if versao < VERSAO_ESQUEMA:
        conn.execute(f"PRAGMA user_version = {VERSAO_ESQUEMA}")
    conn.commit()


def _migrar(conn: sqlite3.Connection) -> None:
    """Migracoes idempotentes para bancos criados em versoes anteriores."""
    colunas = {linha["name"] for linha in conn.execute("PRAGMA table_info(pedidos)")}
    if "cliente" not in colunas:
        conn.execute("ALTER TABLE pedidos ADD COLUMN cliente TEXT")


@contextmanager
def abrir(config: Config | None = None) -> Iterator[sqlite3.Connection]:
    """Abre o banco do projeto, garante o esquema e faz commit/rollback."""
    cfg = config or Config.carregar()
    cfg.garantir_pastas()
    conn = conectar(cfg.banco)
    try:
        garantir_esquema(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── consultas auxiliares ────────────────────────────────────────────────────


def obter_conta(conn: sqlite3.Connection, marketplace: str, apelido: str = "principal") -> int:
    """Devolve o id da conta da loja, criando-a se necessario."""
    marketplace = marketplace.strip().lower()
    apelido = (apelido or "principal").strip()
    linha = conn.execute(
        "SELECT id FROM contas_loja WHERE marketplace = ? AND apelido = ?",
        (marketplace, apelido),
    ).fetchone()
    if linha:
        return int(linha["id"])
    cursor = conn.execute(
        "INSERT INTO contas_loja (marketplace, apelido) VALUES (?, ?)",
        (marketplace, apelido),
    )
    return int(cursor.lastrowid)


def listar_contas(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT c.*, "
            "(SELECT COUNT(*) FROM pedidos p WHERE p.conta_id = c.id) AS pedidos "
            "FROM contas_loja c ORDER BY c.marketplace, c.apelido"
        )
    )


def meses_com_dados(conn: sqlite3.Connection) -> list[str]:
    linhas = conn.execute(
        "SELECT DISTINCT substr(data_pedido, 1, 7) AS mes FROM pedidos "
        "UNION SELECT DISTINCT substr(data, 1, 7) FROM repasses "
        "UNION SELECT DISTINCT substr(vencimento, 1, 7) FROM contas_financeiras "
        "ORDER BY mes"
    ).fetchall()
    return [linha["mes"] for linha in linhas if linha["mes"]]


def ultimo_mes_com_pedidos(conn: sqlite3.Connection) -> str | None:
    linha = conn.execute(
        "SELECT substr(data_pedido, 1, 7) AS mes FROM pedidos ORDER BY data_pedido DESC LIMIT 1"
    ).fetchone()
    return linha["mes"] if linha else None


def registrar_importacao(conn: sqlite3.Connection, dados: dict) -> int:
    cursor = conn.execute(
        "INSERT INTO importacoes "
        "(arquivo, hash, tipo, marketplace, conta, linhas, inseridos, atualizados, "
        " ignorados, avisos) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            dados.get("arquivo"),
            dados.get("hash"),
            dados.get("tipo"),
            dados.get("marketplace"),
            dados.get("conta"),
            dados.get("linhas", 0),
            dados.get("inseridos", 0),
            dados.get("atualizados", 0),
            dados.get("ignorados", 0),
            dados.get("avisos"),
        ),
    )
    return int(cursor.lastrowid)


def limpar_dados(conn: sqlite3.Connection) -> None:
    """Apaga dados operacionais (mantem o esquema)."""
    for tabela in (
        "itens_pedido",
        "pedidos",
        "repasses",
        "contas_financeiras",
        "estoque",
        "desempenho_diario",
        "produtos",
        "importacoes",
        "contas_loja",
    ):
        conn.execute(f"DELETE FROM {tabela}")
    conn.execute("DELETE FROM sqlite_sequence WHERE name IN "
                 "('itens_pedido','pedidos','repasses','contas_financeiras','produtos',"
                 "'importacoes','contas_loja')")
