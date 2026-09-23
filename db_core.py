"""
ស្នូល Database (Database Core)
================================
គាំទ្រ Database ២ ប្រភេទដោយប្រើកូដ SQL តែមួយ៖

  • SQLite   (លំនាំដើម) — ឯកសារ inventory.db ក្នុងម៉ាស៊ីន
  • Postgres (Supabase) — ពេលកំណត់ environment variable `DATABASE_URL`

កូដក្នុង database.py សរសេរជាស្ទីល SQLite (`?` placeholder, DATE(), strftime()...)
ហើយ module នេះបកប្រែវាទៅជា Postgres ដោយស្វ័យប្រវត្តិ ពេលភ្ជាប់ទៅ Supabase។
"""
import os
import re
import datetime
from typing import Any, Dict, List, Optional, Sequence

from config import DATABASE_PATH, DATABASE_URL, APP_TZ, DB_SCHEMA

IS_PG = bool(DATABASE_URL)

# ពេលប្រើ Postgres ទើប import psycopg (មិនបង្ខំឱ្យដំឡើងសម្រាប់អ្នកប្រើ SQLite)
if IS_PG:
    import psycopg
    from psycopg.rows import dict_row
    IntegrityError = psycopg.errors.IntegrityError
else:
    import sqlite3
    IntegrityError = sqlite3.IntegrityError


# ==========================================
# ការបកប្រែ SQL ពី SQLite -> Postgres
# ==========================================

# កន្សោមម៉ោងក្នុងតំបន់ (Local time) ជាអក្សរ 'YYYY-MM-DD HH:MM:SS'
PG_NOW_LOCAL = f"to_char(now() AT TIME ZONE '{APP_TZ}', 'YYYY-MM-DD HH24:MI:SS')"

_RE_STRFTIME = re.compile(r"strftime\(\s*'%([YmdHMS])'\s*,\s*([^()]+?)\s*\)")
_RE_DATE_FN = re.compile(r"\bDATE\(\s*([^()]+?)\s*\)", re.I)
_RE_GROUP_CONCAT = re.compile(r"\bGROUP_CONCAT\(", re.I)
_RE_MAX2 = re.compile(r"\bMAX\(\s*0\s*,", re.I)

_STRFTIME_FMT = {"Y": "YYYY", "m": "MM", "d": "DD", "H": "HH24", "M": "MI", "S": "SS"}

# តារាងដែលមាន column `id` ជា Primary Key (សម្រាប់ស្វែងរក lastrowid)
_ID_TABLES = ("products", "product_batches", "transactions")
_RE_INSERT_TABLE = re.compile(r"^\s*INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)


def translate_sql(query: str) -> str:
    """បកប្រែ SQL ស្ទីល SQLite ទៅជា Postgres"""
    q = query

    # 1. ម៉ោងបច្ចុប្បន្នក្នុងតំបន់
    q = q.replace("datetime('now','localtime')", PG_NOW_LOCAL)
    q = q.replace("datetime('now', 'localtime')", PG_NOW_LOCAL)
    q = re.sub(r"\bCURRENT_TIMESTAMP\b", PG_NOW_LOCAL, q)

    # 2. strftime('%Y', x) -> to_char(x::timestamp, 'YYYY')
    q = _RE_STRFTIME.sub(
        lambda m: f"to_char(({m.group(2)})::timestamp, '{_STRFTIME_FMT[m.group(1)]}')",
        q,
    )

    # 3. DATE(x) -> (x)::date   (រំលង DATE ដែលជាប្រភេទ column ក្នុង DDL)
    q = _RE_DATE_FN.sub(lambda m: f"({m.group(1)})::date", q)

    # 4. មុខងារផ្សេងៗ
    q = _RE_GROUP_CONCAT.sub("string_agg(", q)
    q = _RE_MAX2.sub("GREATEST(0,", q)

    # 5. Placeholder ? -> %s (SQL របស់យើងគ្មាន ? ក្នុង string literal ទេ)
    q = q.replace("?", "%s")

    return q


class _PGCursor:
    """រុំ psycopg cursor ឱ្យប្រើដូច sqlite3 cursor (placeholder `?` និង lastrowid)"""

    def __init__(self, cur):
        self._cur = cur
        self.lastrowid: Optional[int] = None

    def execute(self, query: str, params: Sequence[Any] = ()):
        q = translate_sql(query)

        # ធ្វើត្រាប់តាម cursor.lastrowid របស់ SQLite ដោយបន្ថែម RETURNING id
        want_id = False
        m = _RE_INSERT_TABLE.match(query)
        if m and m.group(1).lower() in _ID_TABLES and "RETURNING" not in q.upper():
            q = q.rstrip().rstrip(";") + " RETURNING id"
            want_id = True

        self._cur.execute(q, tuple(params))

        if want_id:
            row = self._cur.fetchone()
            self.lastrowid = row["id"] if row else None
        else:
            self.lastrowid = None
        return self

    def executemany(self, query: str, seq):
        self._cur.executemany(translate_sql(query), [tuple(p) for p in seq])
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def close(self):
        self._cur.close()

    @property
    def rowcount(self):
        return self._cur.rowcount


class _PGConnection:
    """រុំ psycopg connection ឱ្យប្រើដូច sqlite3 connection"""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self) -> _PGCursor:
        return _PGCursor(self._conn.cursor())

    def execute(self, query: str, params: Sequence[Any] = ()) -> _PGCursor:
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # ដូច sqlite3៖ commit ពេលជោគជ័យ, rollback ពេលមាន error — តែបិទ connection ផងដែរ
        try:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        finally:
            self.close()
        return False


def get_connection():
    """បើក Connection ថ្មី (Postgres បើមាន DATABASE_URL, បើមិនដូច្នេះ SQLite)"""
    if IS_PG:
        # search_path កំណត់តាម connection option (គង់វង្សទោះប្រើ Transaction Pooler)
        # prepare_threshold=None ព្រោះ Supabase Transaction Pooler មិនគាំទ្រ prepared statements
        conn = psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row,
            prepare_threshold=None,
            connect_timeout=15,
            options=f"-c search_path={DB_SCHEMA},public",
        )
        return _PGConnection(conn)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def now_local_str() -> str:
    """ម៉ោងបច្ចុប្បន្នក្នុងតំបន់ជាអក្សរ 'YYYY-MM-DD HH:MM:SS'"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def backend_name() -> str:
    return "Supabase (PostgreSQL)" if IS_PG else f"SQLite ({DATABASE_PATH})"


# ==========================================
# Schema សម្រាប់ Postgres
# ==========================================

PG_SCHEMA = f"""
CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}";
CREATE TABLE IF NOT EXISTS users (
    user_id       BIGINT PRIMARY KEY,
    username      TEXT,
    full_name     TEXT,
    role          TEXT NOT NULL DEFAULT 'staff',
    is_active     INTEGER NOT NULL DEFAULT 1,
    password_hash TEXT DEFAULT '',
    created_at    TEXT NOT NULL DEFAULT {PG_NOW_LOCAL}
);

CREATE TABLE IF NOT EXISTS products (
    id           BIGSERIAL PRIMARY KEY,
    code         TEXT UNIQUE NOT NULL,
    name         TEXT NOT NULL,
    category     TEXT DEFAULT 'ទូទៅ',
    unit         TEXT DEFAULT 'ឯកតា',
    cost_price   DOUBLE PRECISION DEFAULT 0.0,
    sell_price   DOUBLE PRECISION DEFAULT 0.0,
    quantity     INTEGER NOT NULL DEFAULT 0,
    min_quantity INTEGER NOT NULL DEFAULT 5,
    location     TEXT DEFAULT 'ឃ្លាំងធំ',
    created_at   TEXT NOT NULL DEFAULT {PG_NOW_LOCAL},
    updated_at   TEXT NOT NULL DEFAULT {PG_NOW_LOCAL}
);
CREATE INDEX IF NOT EXISTS idx_products_code ON products(code);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);

CREATE TABLE IF NOT EXISTS product_batches (
    id          BIGSERIAL PRIMARY KEY,
    product_id  BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    batch_no    TEXT NOT NULL DEFAULT '',
    expiry_date TEXT NOT NULL,
    quantity    INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
    created_at  TEXT NOT NULL DEFAULT {PG_NOW_LOCAL},
    updated_at  TEXT NOT NULL DEFAULT {PG_NOW_LOCAL},
    UNIQUE(product_id, batch_no, expiry_date)
);
CREATE INDEX IF NOT EXISTS idx_batches_product ON product_batches(product_id);
CREATE INDEX IF NOT EXISTS idx_batches_expiry ON product_batches(expiry_date);

CREATE TABLE IF NOT EXISTS transactions (
    id           BIGSERIAL PRIMARY KEY,
    product_id   BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    type         TEXT NOT NULL CHECK(type IN ('IN', 'OUT')),
    quantity     INTEGER NOT NULL CHECK(quantity > 0),
    unit_price   DOUBLE PRECISION DEFAULT 0.0,
    total_price  DOUBLE PRECISION DEFAULT 0.0,
    reference    TEXT,
    performed_by BIGINT NOT NULL,
    batch_id     BIGINT,
    expiry_date  TEXT,
    batch_no     TEXT,
    created_at   TEXT NOT NULL DEFAULT {PG_NOW_LOCAL}
);
CREATE INDEX IF NOT EXISTS idx_tx_created ON transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_tx_product ON transactions(product_id);

-- Session សម្រាប់ Web Login (ត្រូវរក្សាក្នុង DB ព្រោះ Vercel ជា serverless)
CREATE TABLE IF NOT EXISTS web_sessions (
    token      TEXT PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    username   TEXT,
    full_name  TEXT,
    role       TEXT,
    expires_at DOUBLE PRECISION NOT NULL,
    created_at TEXT NOT NULL DEFAULT {PG_NOW_LOCAL}
);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON web_sessions(expires_at);

-- ការកំណត់ផ្សេងៗ (ឧ. Google Sheets Webhook URL)
CREATE TABLE IF NOT EXISTS app_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TEXT NOT NULL DEFAULT {PG_NOW_LOCAL}
);

-- ទិន្នន័យ Telegram Bot (conversation state) សម្រាប់ដំណើរការលើ serverless
CREATE TABLE IF NOT EXISTS bot_state (
    scope      TEXT NOT NULL,
    key        TEXT NOT NULL,
    value      TEXT,
    updated_at TEXT NOT NULL DEFAULT {PG_NOW_LOCAL},
    PRIMARY KEY (scope, key)
);
"""

SQLITE_EXTRA_SCHEMA = """
CREATE TABLE IF NOT EXISTS web_sessions (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    username   TEXT,
    full_name  TEXT,
    role       TEXT,
    expires_at REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot_state (
    scope      TEXT NOT NULL,
    key        TEXT NOT NULL,
    value      TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (scope, key)
);
"""


def init_pg_schema(cursor) -> None:
    """បង្កើតតារាងទាំងអស់លើ Postgres"""
    for stmt in [s.strip() for s in PG_SCHEMA.split(";") if s.strip()]:
        cursor.execute(stmt + ";")


# ==========================================
# ការកំណត់ (Settings) រក្សាក្នុង Database
# ==========================================

def get_setting(key: str, default: str = "") -> str:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cur.fetchone()
            return (row["value"] if row and row["value"] is not None else default)
    except Exception:
        return default


def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at;
        """, (key, value))
        conn.commit()
