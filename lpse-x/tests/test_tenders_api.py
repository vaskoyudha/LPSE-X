"""
tests/test_tenders_api.py
==========================
Tests for GET /api/tenders and GET /api/tenders/{id} endpoints.

Strategy:
  - Uses httpx.AsyncClient with FastAPI ASGITransport (no server needed)
  - Patches DB_PATH constant in the tenders route module to a temp test DB
  - Tests: response shape, pagination, risk_level filter, 404, prediction nesting
  - No external API calls — fully offline
  - seed=42 data
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
import backend.api.routes.tenders as tenders_module


# ---------------------------------------------------------------------------
# Helpers: build a tiny test SQLite with the real schema
# ---------------------------------------------------------------------------

def _create_test_db(path: str) -> None:
    """Create a minimal test DB with 3 tenders, 3 features, 2 predictions."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tenders (
            tender_id TEXT PRIMARY KEY,
            title TEXT,
            buyer_name TEXT,
            buyer_id TEXT,
            value_amount REAL,
            value_currency TEXT,
            procurement_method TEXT,
            procurement_category TEXT,
            status TEXT,
            date_published TEXT,
            date_awarded TEXT,
            npwp_hash TEXT,
            npwp_last4 TEXT,
            total_score REAL,
            year INTEGER,
            source TEXT,
            ingested_at TEXT
        );
        CREATE TABLE IF NOT EXISTS features (
            tender_id TEXT PRIMARY KEY,
            temporal_split TEXT,
            icw_total_score REAL,
            feature_json TEXT,
            computed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS predictions (
            tender_id TEXT PRIMARY KEY,
            risk_score REAL,
            risk_level TEXT,
            model_version TEXT,
            predicted_at TEXT
        );
        """
    )
    features_data = {
        "R001": 0.8, "R002": 0.3, "n_bidders": 1.0, "price_ratio": 0.99,
    }
    conn.executemany(
        """
        INSERT INTO tenders (
            tender_id, title, buyer_name, buyer_id, value_amount, value_currency,
            procurement_method, procurement_category, status,
            date_published, date_awarded, npwp_hash, npwp_last4,
            total_score, year, source, ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "SYN-TEST-001", "Tender Satu", "Kota A", "B001",
                1_000_000.0, "IDR", "pengadaan_langsung", "konstruksi",
                "active", "2024-01-01", None, "abc123hash", "1234",
                0.75, 2024, "synthetic", "2024-01-01T00:00:00",
            ),
            (
                "SYN-TEST-002", "Tender Dua", "Kota B", "B002",
                2_000_000.0, "IDR", "lelang", "konsultansi",
                "complete", "2023-06-15", "2023-12-01", "def456hash", "5678",
                0.50, 2023, "synthetic", "2023-06-15T00:00:00",
            ),
            (
                "SYN-TEST-003", "Tender Tiga", "Kota C", "B003",
                500_000.0, "IDR", "pengadaan_langsung", "barang",
                "active", "2022-03-10", None, "ghi789hash", "9012",
                0.30, 2022, "synthetic", "2022-03-10T00:00:00",
            ),
        ],
    )
    conn.executemany(
        """
        INSERT INTO features (tender_id, temporal_split, icw_total_score, feature_json, computed_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            ("SYN-TEST-001", "train", 75.0, json.dumps(features_data), "2024-01-02T00:00:00"),
            ("SYN-TEST-002", "test", 50.0, json.dumps(features_data), "2023-07-01T00:00:00"),
            ("SYN-TEST-003", "train", 30.0, json.dumps(features_data), "2022-04-01T00:00:00"),
        ],
    )
    # 2 predictions — TEST-003 has none (tests null prediction)
    conn.executemany(
        """
        INSERT INTO predictions (tender_id, risk_score, risk_level, model_version, predicted_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            ("SYN-TEST-001", 0.87, "high", "v1.0", "2024-01-03T00:00:00"),
            ("SYN-TEST-002", 0.21, "low", "v1.0", "2023-07-02T00:00:00"),
        ],
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def test_db_path(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Create a reusable temp DB for the module."""
    db_dir = tmp_path_factory.mktemp("test_tenders_db")
    db_path = str(db_dir / "test.db")
    _create_test_db(db_path)
    return db_path


# ---------------------------------------------------------------------------
# Helper: async client with DB path patched
# ---------------------------------------------------------------------------

def _client(test_db_path: str) -> AsyncClient:
    """Return AsyncClient with DB_PATH constant patched to test DB."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _get(path: str, test_db_path: str, **params) -> Any:
    """Perform GET with DB path patched. Returns (status_code, json_body)."""
    url = path
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{path}?{qs}"
    with patch.object(tenders_module, "aiosqlite") as mock_aio:
        import aiosqlite as real_aiosqlite

        # Make aiosqlite.connect in the route use test_db_path
        mock_aio.connect = lambda _path, **kw: real_aiosqlite.connect(test_db_path)
        mock_aio.Row = real_aiosqlite.Row

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.get(url)
    return resp


# ---------------------------------------------------------------------------
# Tests: GET /api/tenders
# ---------------------------------------------------------------------------

class TestGetTenders:
    """Tests for GET /api/tenders."""

    @pytest.mark.asyncio
    async def test_returns_200(self, test_db_path: str) -> None:
        """Endpoint returns 200 OK."""
        resp = await _get("/api/tenders", test_db_path)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_shape(self, test_db_path: str) -> None:
        """Response has required top-level keys."""
        resp = await _get("/api/tenders", test_db_path)
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_returns_all_tenders(self, test_db_path: str) -> None:
        """Without filters, total == 3."""
        resp = await _get("/api/tenders", test_db_path, page_size=100)
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_pagination_page_size_1(self, test_db_path: str) -> None:
        """page_size=1 returns exactly 1 item, total still 3."""
        resp = await _get("/api/tenders", test_db_path, page=1, page_size=1)
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 1
        assert data["page"] == 1
        assert data["page_size"] == 1

    @pytest.mark.asyncio
    async def test_pagination_page_2(self, test_db_path: str) -> None:
        """page=2, page_size=2 returns 1 remaining item."""
        resp = await _get("/api/tenders", test_db_path, page=2, page_size=2)
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["page"] == 2

    @pytest.mark.asyncio
    async def test_filter_risk_level_high(self, test_db_path: str) -> None:
        """risk_level=high returns the 1 high-risk tender."""
        resp = await _get("/api/tenders", test_db_path, risk_level="high", page_size=100)
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["tender_id"] == "SYN-TEST-001"

    @pytest.mark.asyncio
    async def test_filter_risk_level_low(self, test_db_path: str) -> None:
        """risk_level=low returns the 1 low-risk tender."""
        resp = await _get("/api/tenders", test_db_path, risk_level="low", page_size=100)
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["tender_id"] == "SYN-TEST-002"

    @pytest.mark.asyncio
    async def test_prediction_nested(self, test_db_path: str) -> None:
        """Items with predictions have nested `prediction.risk_score` and `prediction.risk_level`."""
        resp = await _get("/api/tenders", test_db_path, risk_level="high", page_size=100)
        item = resp.json()["items"][0]
        assert "prediction" in item
        pred = item["prediction"]
        assert pred is not None
        assert "risk_score" in pred
        assert "risk_level" in pred
        assert pred["risk_score"] == pytest.approx(0.87, abs=0.01)
        assert pred["risk_level"] == "high"

    @pytest.mark.asyncio
    async def test_prediction_null_for_unpredicted(self, test_db_path: str) -> None:
        """SYN-TEST-003 has no prediction — prediction field is null."""
        resp = await _get("/api/tenders", test_db_path, page_size=100)
        items = resp.json()["items"]
        unpredicted = [i for i in items if i["tender_id"] == "SYN-TEST-003"]
        assert len(unpredicted) == 1
        assert unpredicted[0]["prediction"] is None

    @pytest.mark.asyncio
    async def test_item_fields_complete(self, test_db_path: str) -> None:
        """Each item contains all required fields."""
        required = [
            "tender_id", "title", "buyer_name", "buyer_id",
            "value_amount", "value_currency", "procurement_method",
            "procurement_category", "status", "date_published", "year",
        ]
        resp = await _get("/api/tenders", test_db_path, page_size=100)
        for item in resp.json()["items"]:
            for f in required:
                assert f in item, f"Missing field '{f}' in {item.get('tender_id')}"

    @pytest.mark.asyncio
    async def test_empty_filter_returns_empty(self, test_db_path: str) -> None:
        """risk_level=medium returns 0 items (not present in test data)."""
        resp = await _get("/api/tenders", test_db_path, risk_level="medium", page_size=100)
        data = resp.json()
        assert resp.status_code == 200
        assert data["total"] == 0
        assert data["items"] == []


# ---------------------------------------------------------------------------
# Tests: GET /api/tenders/{id}
# ---------------------------------------------------------------------------

class TestGetTenderById:
    """Tests for GET /api/tenders/{tender_id}."""

    @pytest.mark.asyncio
    async def test_existing_returns_200(self, test_db_path: str) -> None:
        """Known tender returns 200."""
        resp = await _get("/api/tenders/SYN-TEST-001", test_db_path)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_returns_404(self, test_db_path: str) -> None:
        """Unknown tender ID returns 404."""
        resp = await _get("/api/tenders/DOES-NOT-EXIST", test_db_path)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_features_present(self, test_db_path: str) -> None:
        """Detail response includes `features` dict."""
        resp = await _get("/api/tenders/SYN-TEST-001", test_db_path)
        data = resp.json()
        assert "features" in data
        assert isinstance(data["features"], dict)
        assert len(data["features"]) > 0

    @pytest.mark.asyncio
    async def test_features_correct_values(self, test_db_path: str) -> None:
        """Features dict contains the seeded keys with correct values."""
        resp = await _get("/api/tenders/SYN-TEST-001", test_db_path)
        features = resp.json()["features"]
        assert "n_bidders" in features
        assert "price_ratio" in features
        assert features["n_bidders"] == pytest.approx(1.0)
        assert features["price_ratio"] == pytest.approx(0.99)

    @pytest.mark.asyncio
    async def test_prediction_nested_on_detail(self, test_db_path: str) -> None:
        """Detail includes nested prediction for SYN-TEST-001."""
        resp = await _get("/api/tenders/SYN-TEST-001", test_db_path)
        data = resp.json()
        assert "prediction" in data
        pred = data["prediction"]
        assert pred is not None
        assert pred["risk_score"] == pytest.approx(0.87, abs=0.01)
        assert pred["risk_level"] == "high"

    @pytest.mark.asyncio
    async def test_prediction_null_when_missing(self, test_db_path: str) -> None:
        """SYN-TEST-003 has no prediction — detail returns prediction: null."""
        resp = await _get("/api/tenders/SYN-TEST-003", test_db_path)
        data = resp.json()
        assert resp.status_code == 200
        assert data["prediction"] is None

    @pytest.mark.asyncio
    async def test_all_required_fields_present(self, test_db_path: str) -> None:
        """Detail has all core tender fields."""
        required = [
            "tender_id", "title", "buyer_name", "value_amount",
            "procurement_method", "status", "year", "features", "prediction",
        ]
        resp = await _get("/api/tenders/SYN-TEST-002", test_db_path)
        data = resp.json()
        for f in required:
            assert f in data, f"Missing field: {f}"

    @pytest.mark.asyncio
    async def test_tender_id_matches_request(self, test_db_path: str) -> None:
        """Returned tender_id matches the requested ID."""
        resp = await _get("/api/tenders/SYN-TEST-002", test_db_path)
        assert resp.json()["tender_id"] == "SYN-TEST-002"

    @pytest.mark.asyncio
    async def test_timestamp_is_iso8601(self, test_db_path: str) -> None:
        """Detail response includes ISO 8601 timestamp."""
        resp = await _get("/api/tenders/SYN-TEST-001", test_db_path)
        data = resp.json()
        assert "timestamp" in data
        assert "T" in data["timestamp"]
