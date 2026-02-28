"""Pytest configuration for LPSE-X tests."""
from __future__ import annotations

import json
import pathlib
import sqlite3
import tempfile
from typing import Generator

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Existing fixture (preserved)
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_config() -> dict[str, object]:
    """Sample runtime config for tests."""
    return {
        "procurement_scope": "konstruksi",
        "institution_filter": [],
        "risk_threshold": 0.65,
        "year_range": {"start": 2022, "end": 2024},
        "anomaly_method": "ensemble",
        "output_format": "dashboard",
        "custom_params": {},
    }


# ---------------------------------------------------------------------------
# T21 integration fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mini_tenders() -> list[dict]:
    """Load the 50-record OCDS mini dataset for integration tests."""
    with open(FIXTURES_DIR / "mini_tenders.json", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 50, f"Expected 50 records, got {len(data)}"
    return data


@pytest.fixture(scope="session")
def mini_db(mini_tenders: list[dict], tmp_path_factory: pytest.TempPathFactory) -> str:
    """
    Create a temporary SQLite DB loaded with the mini dataset.

    Returns the path to the DB file (string) so backend modules can use it.
    The DB is reused across all session-scoped tests for performance.
    """
    db_dir = tmp_path_factory.mktemp("db")
    db_path = str(db_dir / "mini.db")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tenders (
            tender_id       TEXT PRIMARY KEY,
            ocid            TEXT,
            title           TEXT,
            amount          REAL,
            n_bidders       INTEGER,
            winner_id       TEXT,
            year            INTEGER,
            institution_id  TEXT,
            province        TEXT,
            procurement_type TEXT,
            bid_prices      TEXT,
            winner_bid      REAL,
            hps             REAL,
            total_score     REAL,
            items           TEXT
        )
        """
    )

    for t in mini_tenders:
        conn.execute(
            """
            INSERT OR REPLACE INTO tenders
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                t["tender_id"],
                t.get("ocid", ""),
                t.get("title", ""),
                float(t.get("amount", 0)),
                int(t.get("n_bidders", 1)),
                t.get("winner_id", ""),
                int(t.get("year", 2023)),
                t.get("institution_id", ""),
                t.get("province", ""),
                t.get("procurement_type", "konstruksi"),
                json.dumps(t.get("bid_prices", [])),
                float(t.get("winner_bid", 0)),
                float(t.get("hps", 0)),
                float(t.get("total_score", 0)),
                json.dumps(t.get("items", [])),
            ),
        )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture(scope="session")
def app_client() -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient — no real server process needed.
    Reused across all session-scoped integration tests.
    """
    from backend.main import app

    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


@pytest.fixture(scope="session")
def runtime_config() -> dict:
    """Default RuntimeConfig as a plain dict for integration tests."""
    from backend.config.runtime import get_config

    return get_config().model_dump()
