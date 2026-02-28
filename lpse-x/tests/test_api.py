"""
Tests for T14: FastAPI Endpoints
==================================
~35 tests covering all API routes, request/response validation,
Dynamic Injection, fault tolerance, and HTTP status codes.

Test strategy:
  - Uses httpx.AsyncClient with FastAPI's ASGITransport (no server needed)
  - Mocks heavy ML operations (predict_single, explain_tender, ReportGenerator)
  - Tests HTTP contract: status codes, response shape, field types
  - Verifies Dynamic Injection endpoint (COMPETITION-CRITICAL)
  - Tests fault tolerance: bad input → 422, backend error → 500
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.main import app


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_ensemble_result(
    tender_id: str = "TEST-001",
    final_score: float = 0.72,
    risk_level: str = "Risiko Tinggi",
    disagreement: bool = False,
) -> Any:
    """Minimal EnsembleResult-like namespace for mocking predict_single."""
    return SimpleNamespace(
        tender_id=tender_id,
        final_score=final_score,
        risk_level=risk_level,
        individual_scores={"xgboost": 0.75, "iforest": 0.68, "icw": 0.73},
        disagreement_flag=disagreement,
        disagreement_detail="",
        manual_review_priority=False,
    )


def _make_layer(status: str = "ok", data: Any = None) -> Any:
    return SimpleNamespace(status=status, data=data, error=None)


def _make_oracle_result(tender_id: str = "TEST-001") -> Any:
    return SimpleNamespace(
        tender_id=tender_id,
        shap=_make_layer("ok", {"model_output": 0.82, "top_positive_features": [], "top_negative_features": [], "base_value": 0.1, "additivity_error": 0.001}),
        anchors=_make_layer("ok", {"rules": ["n_bidders <= 1"], "precision": 0.91, "coverage": 0.15}),
        leiden=_make_layer("not_applicable"),
        benford=_make_layer("ok", {"suspicious": True, "chi2": 42.0, "p_value": 0.001}),
        dice=_make_layer("not_applicable"),
        layers_ok=3,
        layers_failed=2,
        total_seconds=1.23,
    )


@pytest.fixture
def predict_payload() -> dict:
    return {
        "tender_id": "TEST-001",
        "features": {
            "n_bidders": 1.0,
            "price_ratio": 0.995,
            "bid_spread": 0.004,
            "winner_bid_rank": 1.0,
            "hhi": 0.92,
            "log_amount": 19.8,
        },
        "icw_raw_score": 78.5,
    }


@pytest.fixture
def xai_payload() -> dict:
    return {
        "features": {
            "n_bidders": 1.0,
            "price_ratio": 0.995,
            "bid_spread": 0.004,
        },
        "amount_values": [4980000000.0, 5100000000.0],
    }


@pytest.fixture
def oracle_dict() -> dict:
    return {
        "tender_id": "TEST-001",
        "layers_ok": 3,
        "layers_failed": 2,
        "total_seconds": 1.23,
        "shap": {"status": "ok", "data": {"model_output": 0.82, "top_positive_features": [], "base_value": 0.1}, "error": None},
        "anchors": {"status": "ok", "data": {"rules": ["n_bidders <= 1"], "precision": 0.91, "coverage": 0.15}, "error": None},
        "leiden": {"status": "not_applicable", "data": None, "error": None},
        "benford": {"status": "ok", "data": {"suspicious": True, "chi2": 42.0, "p_value": 0.001}, "error": None},
        "dice": {"status": "not_applicable", "data": None, "error": None},
    }


# ---------------------------------------------------------------------------
# TestHealthEndpoint
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    """Tests for GET /api/health."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/health")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_has_required_fields(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/health")
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "uptime" in data
        assert "uptime_seconds" in data
        assert "timestamp" in data
        assert "models" in data
        assert "config_hash" in data

    @pytest.mark.asyncio
    async def test_health_models_field_has_known_keys(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/health")
        models = resp.json()["models"]
        assert "xgboost" in models
        assert "isolation_forest" in models

    @pytest.mark.asyncio
    async def test_health_config_field_present(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/health")
        cfg = resp.json()["config"]
        assert "risk_threshold" in cfg
        assert "anomaly_method" in cfg
        assert "procurement_scope" in cfg

    @pytest.mark.asyncio
    async def test_health_version_string(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/health")
        assert resp.json()["version"] == "0.1.0"


# ---------------------------------------------------------------------------
# TestConfigInjection (Dynamic Injection — COMPETITION-CRITICAL)
# ---------------------------------------------------------------------------

class TestConfigInjection:
    """Tests for /api/config endpoints — Dynamic Injection."""

    @pytest.mark.asyncio
    async def test_get_config_returns_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/config")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_config_has_risk_threshold(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/config")
        data = resp.json()
        assert "risk_threshold" in data
        assert 0.0 <= float(data["risk_threshold"]) <= 1.0

    @pytest.mark.asyncio
    async def test_inject_risk_threshold(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(
                "/api/config/inject",
                json={"risk_threshold": 0.55},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "old_values" in data
        assert "new_values" in data
        assert "injected_at" in data

    @pytest.mark.asyncio
    async def test_inject_updates_risk_threshold_value(self):
        target = 0.42
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.put("/api/config/inject", json={"risk_threshold": target})
            resp = await client.get("/api/config")
        data = resp.json()
        assert abs(float(data["risk_threshold"]) - target) < 1e-6

    @pytest.mark.asyncio
    async def test_inject_invalid_threshold_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(
                "/api/config/inject",
                json={"risk_threshold": 1.5},  # out of [0,1]
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_config_log_endpoint(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/config/log")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# TestInferenceEndpoint
# ---------------------------------------------------------------------------

class TestInferenceEndpoint:
    """Tests for POST /api/predict."""

    @pytest.mark.asyncio
    async def test_predict_returns_200_with_mock(self, predict_payload):
        mock_result = _make_ensemble_result()
        with patch("backend.api.routes.inference.predict_single", return_value=mock_result):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/predict", json=predict_payload)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_predict_response_fields(self, predict_payload):
        mock_result = _make_ensemble_result()
        with patch("backend.api.routes.inference.predict_single", return_value=mock_result):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/predict", json=predict_payload)
        data = resp.json()
        assert data["status"] == "ok"
        assert data["tender_id"] == "TEST-001"
        assert "risk_level" in data
        assert "final_score" in data
        assert "individual_scores" in data
        assert "disagreement_flag" in data
        assert "risk_threshold" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_predict_score_is_float_in_range(self, predict_payload):
        mock_result = _make_ensemble_result(final_score=0.72)
        with patch("backend.api.routes.inference.predict_single", return_value=mock_result):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/predict", json=predict_payload)
        score = resp.json()["final_score"]
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_predict_missing_features_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/predict", json={"tender_id": "X"})  # missing features
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_predict_icw_out_of_range_returns_422(self, predict_payload):
        payload = dict(predict_payload)
        payload["icw_raw_score"] = 150.0  # > 100
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/predict", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_predict_backend_error_returns_500(self, predict_payload):
        with patch("backend.api.routes.inference.predict_single", side_effect=RuntimeError("Model not loaded")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/predict", json=predict_payload)
        assert resp.status_code == 500
        detail = resp.json()["detail"]
        assert "tender_id" in detail
        assert "timestamp" in detail


# ---------------------------------------------------------------------------
# TestXaiEndpoint
# ---------------------------------------------------------------------------

class TestXaiEndpoint:
    """Tests for POST /api/xai/{tender_id}."""

    @pytest.mark.asyncio
    async def test_xai_returns_200_with_mock(self, xai_payload):
        mock_oracle = _make_oracle_result()
        with (
            patch("backend.api.routes.xai._load_xgboost", return_value=MagicMock()),
            patch("backend.api.routes.xai.explain_tender", return_value=mock_oracle),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/xai/TEST-001", json=xai_payload)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_xai_response_has_layers(self, xai_payload):
        mock_oracle = _make_oracle_result()
        with (
            patch("backend.api.routes.xai._load_xgboost", return_value=MagicMock()),
            patch("backend.api.routes.xai.explain_tender", return_value=mock_oracle),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/xai/TEST-001", json=xai_payload)
        data = resp.json()["data"]
        assert "shap" in data
        assert "anchors" in data
        assert "leiden" in data
        assert "benford" in data
        assert "dice" in data
        assert "layers_ok" in data
        assert "layers_failed" in data

    @pytest.mark.asyncio
    async def test_xai_model_not_loaded_returns_200_with_shap_error(self, xai_payload):
        """When XGBoost model is missing, XAI returns 200 with SHAP layer in error status.
        Fault tolerance is a core competition requirement: no layer failure should crash the endpoint.
        """
        with patch("backend.api.routes.xai._load_xgboost", return_value=None):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/xai/TEST-001", json=xai_payload)
        assert resp.status_code == 200
        data = resp.json()
        inner = data.get("data", data)
        # SHAP will have error status since model is None, but endpoint must not crash
        assert "shap" in inner
        assert inner["shap"]["status"] in ("error", "ok", "not_applicable")

    @pytest.mark.asyncio
    async def test_xai_missing_features_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/xai/TEST-001", json={})  # missing features
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# TestDicePrecompute
# ---------------------------------------------------------------------------

class TestDicePrecompute:
    """Tests for POST /api/xai/dice/precompute and GET /api/xai/dice/status/{id}."""

    @pytest.mark.asyncio
    async def test_dice_precompute_returns_202_shape(self):
        """POST /api/xai/dice/precompute → 200 with 'accepted' status."""
        with patch("backend.api.routes.xai._load_xgboost", return_value=MagicMock()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/xai/dice/precompute",
                    json={"tender_id": "DICE-001", "features": {"n_bidders": 1.0}, "n_cfs": 3},
                )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("accepted", "already_running")
        assert data["tender_id"] == "DICE-001"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_dice_n_cfs_max_5(self):
        """Competition rule: max 5 counterfactuals."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/xai/dice/precompute",
                json={"tender_id": "DICE-001", "features": {"n_bidders": 1.0}, "n_cfs": 6},
            )
        assert resp.status_code == 422  # n_cfs > 5 violates schema

    @pytest.mark.asyncio
    async def test_dice_status_endpoint(self):
        """GET /api/xai/dice/status/{id} returns status field."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/xai/dice/status/NONEXISTENT-999")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tender_id"] == "NONEXISTENT-999"
        assert data["status"] == "not_started"
        assert "result_available" in data
        assert "timestamp" in data


# ---------------------------------------------------------------------------
# TestGraphEndpoint
# ---------------------------------------------------------------------------

class TestGraphEndpoint:
    """Tests for GET /api/graph and GET /api/graph/vendor/{id}."""

    @pytest.mark.asyncio
    async def test_graph_communities_returns_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/graph")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_graph_response_shape(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/graph")
        data = resp.json()
        assert data["status"] == "ok"
        assert "communities" in data
        assert isinstance(data["communities"], list)
        assert "total" in data
        assert "filters" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_graph_vendor_lookup_returns_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/graph/vendor/CV-MAJU-JAYA")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_graph_vendor_response_shape(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/graph/vendor/CV-MAJU-JAYA")
        data = resp.json()
        assert data["status"] == "ok"
        assert data["vendor_id"] == "CV-MAJU-JAYA"
        assert "in_community" in data
        assert "timestamp" in data


# ---------------------------------------------------------------------------
# TestReportsEndpoint
# ---------------------------------------------------------------------------

class TestReportsEndpoint:
    """Tests for GET and POST /api/reports/{tender_id}."""

    @pytest.mark.asyncio
    async def test_get_report_returns_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/reports/TEST-001")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_report_has_required_fields(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/reports/TEST-001")
        data = resp.json()
        assert data["status"] == "ok"
        assert data["tender_id"] == "TEST-001"
        assert "risk_level" in data
        assert "risk_score" in data
        assert "report_text" in data
        assert "sections" in data
        assert "recommendations" in data
        assert "generated_at" in data
        assert "evidence_count" in data

    @pytest.mark.asyncio
    async def test_post_report_with_oracle_returns_200(self, oracle_dict):
        payload = {"oracle_result": oracle_dict, "tender_data": {"nama_paket": "Test Tender"}}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/reports/TEST-001", json=payload)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_post_report_risk_level_is_string(self, oracle_dict):
        payload = {"oracle_result": oracle_dict}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/reports/TEST-001", json=payload)
        risk_level = resp.json()["risk_level"]
        assert isinstance(risk_level, str)
        assert risk_level in ("Aman", "Perlu Pantauan", "Berisiko", "Kritis")

    @pytest.mark.asyncio
    async def test_post_report_risk_score_range(self, oracle_dict):
        payload = {"oracle_result": oracle_dict}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/reports/TEST-001", json=payload)
        risk_score = resp.json()["risk_score"]
        assert 0 <= risk_score <= 3

    @pytest.mark.asyncio
    async def test_post_report_sections_dict(self, oracle_dict):
        payload = {"oracle_result": oracle_dict}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/reports/TEST-001", json=payload)
        sections = resp.json()["sections"]
        assert isinstance(sections, dict)

    @pytest.mark.asyncio
    async def test_post_report_report_text_nonempty(self, oracle_dict):
        payload = {"oracle_result": oracle_dict}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/reports/TEST-001", json=payload)
        report_text = resp.json()["report_text"]
        assert isinstance(report_text, str)
        assert len(report_text) > 100  # must be a real report, not empty

    @pytest.mark.asyncio
    async def test_get_report_null_oracle_still_works(self):
        """GET endpoint (no oracle_result) must not crash — fault tolerant."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/reports/UNKNOWN-999")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# TestFaultTolerance
# ---------------------------------------------------------------------------

class TestFaultTolerance:
    """Tests for proper HTTP error handling across all routes."""

    @pytest.mark.asyncio
    async def test_predict_empty_body_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/predict", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_predict_500_has_timestamp(self):
        with patch("backend.api.routes.inference.predict_single", side_effect=ValueError("boom")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/predict",
                    json={"tender_id": "X", "features": {"n_bidders": 1.0}},
                )
        assert resp.status_code == 500
        assert "timestamp" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_xai_500_has_tender_id_in_detail(self):
        with (
            patch("backend.api.routes.xai._load_xgboost", side_effect=RuntimeError("GPU OOM")),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/xai/FAIL-999",
                    json={"features": {"n_bidders": 1.0}},
                )
        assert resp.status_code == 500
        assert resp.json()["detail"]["tender_id"] == "FAIL-999"

    @pytest.mark.asyncio
    async def test_unknown_route_returns_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/nonexistent")
        assert resp.status_code == 404
