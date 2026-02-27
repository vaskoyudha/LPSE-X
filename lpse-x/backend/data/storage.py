"""
LPSE-X Data Storage — Async SQLite with aiosqlite.

Provides idempotent init_db() and async connection helper.
ALL database operations use raw SQL (no ORM).
"""

import logging
from pathlib import Path
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQL DDL — 5 required tables
# ---------------------------------------------------------------------------

_TENDERS_DDL = """
CREATE TABLE IF NOT EXISTS tenders (
    tender_id TEXT PRIMARY KEY,
    title TEXT,
    buyer_name TEXT,
    buyer_id TEXT,
    value_amount REAL,
    value_currency TEXT DEFAULT 'IDR',
    procurement_method TEXT,
    procurement_category TEXT,
    status TEXT,
    date_published TEXT,
    date_awarded TEXT,
    npwp_hash TEXT,
    npwp_last4 TEXT,
    total_score REAL,
    year INTEGER,
    source TEXT DEFAULT 'opentender',
    ingested_at TEXT DEFAULT (datetime('now'))
)
"""

_FEATURES_DDL = """
CREATE TABLE IF NOT EXISTS features (
    tender_id TEXT PRIMARY KEY,
    feature_vector BLOB,
    computed_at TEXT DEFAULT (datetime('now'))
)
"""

_PREDICTIONS_DDL = """
CREATE TABLE IF NOT EXISTS predictions (
    tender_id TEXT PRIMARY KEY,
    risk_score REAL,
    risk_level TEXT,
    model_version TEXT,
    predicted_at TEXT DEFAULT (datetime('now'))
)
"""

_COMMUNITIES_DDL = """
CREATE TABLE IF NOT EXISTS communities (
    community_id TEXT PRIMARY KEY,
    member_ids TEXT,
    risk_score REAL,
    detected_at TEXT DEFAULT (datetime('now'))
)
"""

_REPORTS_DDL = """
CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    tender_id TEXT,
    report_type TEXT,
    content TEXT,
    generated_at TEXT DEFAULT (datetime('now'))
)
"""

_ALL_DDL = [_TENDERS_DDL, _FEATURES_DDL, _PREDICTIONS_DDL, _COMMUNITIES_DDL, _REPORTS_DDL]

# ---------------------------------------------------------------------------
# Index definitions for query performance
# ---------------------------------------------------------------------------

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_tenders_year ON tenders(year)",
    "CREATE INDEX IF NOT EXISTS idx_tenders_category ON tenders(procurement_category)",
    "CREATE INDEX IF NOT EXISTS idx_tenders_buyer ON tenders(buyer_name)",
    "CREATE INDEX IF NOT EXISTS idx_tenders_source ON tenders(source)",
    "CREATE INDEX IF NOT EXISTS idx_predictions_risk ON predictions(risk_level)",
    "CREATE INDEX IF NOT EXISTS idx_reports_tender ON reports(tender_id)",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def init_db(db_path: str) -> None:
    """
    Initialize SQLite database with all 5 required tables.
    Idempotent — safe to call multiple times (CREATE TABLE IF NOT EXISTS).

    Args:
        db_path: Path to SQLite database file (relative or absolute).
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Initializing database at %s", path)

    async with aiosqlite.connect(str(path)) as db:
        # Enable WAL mode for concurrent read performance
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")

        for ddl in _ALL_DDL:
            await db.execute(ddl)

        for idx in _INDEXES:
            await db.execute(idx)

        await db.commit()

    logger.info("Database initialized successfully: 5 tables, %d indexes", len(_INDEXES))


async def get_connection(db_path: str) -> aiosqlite.Connection:
    """
    Open an async SQLite connection.
    Caller is responsible for closing via `async with` or `.close()`.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        aiosqlite.Connection instance.
    """
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    return conn


async def upsert_tender(db: aiosqlite.Connection, tender: dict[str, object]) -> None:
    """
    Insert or replace a tender record.

    Args:
        db: Active aiosqlite connection.
        tender: Dict with keys matching tenders table columns.
    """
    await db.execute(
        """
        INSERT OR REPLACE INTO tenders (
            tender_id, title, buyer_name, buyer_id, value_amount,
            value_currency, procurement_method, procurement_category,
            status, date_published, date_awarded, npwp_hash, npwp_last4,
            total_score, year, source, ingested_at
        ) VALUES (
            :tender_id, :title, :buyer_name, :buyer_id, :value_amount,
            :value_currency, :procurement_method, :procurement_category,
            :status, :date_published, :date_awarded, :npwp_hash, :npwp_last4,
            :total_score, :year, :source, datetime('now')
        )
        """,
        {
            "tender_id": tender.get("tender_id"),
            "title": tender.get("title"),
            "buyer_name": tender.get("buyer_name"),
            "buyer_id": tender.get("buyer_id"),
            "value_amount": tender.get("value_amount"),
            "value_currency": tender.get("value_currency", "IDR"),
            "procurement_method": tender.get("procurement_method"),
            "procurement_category": tender.get("procurement_category"),
            "status": tender.get("status"),
            "date_published": tender.get("date_published"),
            "date_awarded": tender.get("date_awarded"),
            "npwp_hash": tender.get("npwp_hash"),
            "npwp_last4": tender.get("npwp_last4"),
            "total_score": tender.get("total_score"),
            "year": tender.get("year"),
            "source": tender.get("source", "opentender"),
        },
    )


async def count_tenders(db: aiosqlite.Connection) -> int:
    """Return total number of tenders in database."""
    async with db.execute("SELECT COUNT(*) FROM tenders") as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0
