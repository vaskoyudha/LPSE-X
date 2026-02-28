"""
T21 — End-to-End Integration Tests for LPSE-X.

Tests the FULL API pipeline through FastAPI TestClient (no real server needed):
  - Health check
  - Prediction (POST /api/predict)
  - XAI explanation (POST /api/xai/{id})
  - Graph communities (GET /api/graph)
  - Report generation (POST /api/reports/{id})
  - Config injection: valid and invalid

Design rules:
  - NO mocks for ML models — real ONNX/PKL models used
  - NO hardcoded expected score values — test shapes, types, and ranges
  - NO running server — all via FastAPI TestClient
  - Mini dataset only — 50 records, never the full 1.1M
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Minimal feature vector fixture (re-used across tests)
# ---------------------------------------------------------------------------

HIGH_RISK_FEATURES = {
    "n_bidders": 1.0,
    "price_ratio": 0.997,
    "bid_spread": 0.002,
    "winner_bid_rank": 1.0,
    "hhi": 1.0,
    "log_amount": 20.1,
    "hps_ratio": 0.945,
    "winner_repeat_count": 5.0,
}

CLEAN_FEATURES = {
    "n_bidders": 4.0,
    "price_ratio": 0.82,
    "bid_spread": 0.12,
    "winner_bid_rank": 2.0,
    "hhi": 0.31,
    "log_amount": 18.5,
    "hps_ratio": 0.72,
    "winner_repeat_count": 1.0,
}

VALID_RISK_LEVELS = {
    "Aman",
    "Perlu Pantauan",
    "Risiko Tinggi",
    "Risiko Kritis",
    # lower-case variants (defensive)
    "aman",
    "perlu_pantauan",
    "perlu pantauan",
    "risiko_tinggi",
    "risiko tinggi",
    "risiko_kritis",
    "risiko kritis",
}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_api_health(app_client: TestClient) -> None:
    """GET /api/health → 200 with status field."""
    resp = app_client.get("/api/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    data = resp.json()
    assert "status" in data, f"Missing 'status' in health response: {data}"
    assert data["status"] == "ok", f"Unexpected status: {data['status']}"


def test_api_health_has_version(app_client: TestClient) -> None:
    """Health response must include version field."""
    resp = app_client.get("/api/health")
    data = resp.json()
    assert "version" in data, f"Missing 'version' in health response: {data}"


def test_api_health_has_config(app_client: TestClient) -> None:
    """Health response must include config section."""
    resp = app_client.get("/api/health")
    data = resp.json()
    assert "config" in data or "config_hash" in data, (
        f"Missing config info in health response: {data}"
    )


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------


def test_api_predict_high_risk(app_client: TestClient) -> None:
    """POST /api/predict with single-bidder tender → 200 + valid risk_level."""
    payload = {
        "tender_id": "IT-TEST-0001",
        "features": HIGH_RISK_FEATURES,
        "icw_raw_score": 22.0,
    }
    resp = app_client.post("/api/predict", json=payload)
    assert resp.status_code == 200, f"Predict failed: {resp.text}"
    data = resp.json()

    assert "risk_level" in data, f"Missing 'risk_level': {data}"
    risk = data["risk_level"].lower().replace(" ", "_")
    assert risk in {
        "aman", "perlu_pantauan", "risiko_tinggi", "risiko_kritis"
    }, f"Unexpected risk_level: {data['risk_level']}"


def test_api_predict_returns_score(app_client: TestClient) -> None:
    """Prediction response must have final_score in [0, 1]."""
    payload = {
        "tender_id": "IT-TEST-0002",
        "features": HIGH_RISK_FEATURES,
    }
    resp = app_client.post("/api/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "final_score" in data, f"Missing 'final_score': {data}"
    score = data["final_score"]
    assert isinstance(score, (int, float)), f"final_score not numeric: {score}"
    assert 0.0 <= float(score) <= 1.0, f"final_score out of range: {score}"


def test_api_predict_clean_tender(app_client: TestClient) -> None:
    """Prediction for clean tender → 200, no crash."""
    payload = {
        "tender_id": "IT-TEST-0003",
        "features": CLEAN_FEATURES,
        "icw_raw_score": 75.0,
    }
    resp = app_client.post("/api/predict", json=payload)
    assert resp.status_code == 200, f"Clean tender predict failed: {resp.text}"
    data = resp.json()
    assert "risk_level" in data


def test_api_predict_minimal_features(app_client: TestClient) -> None:
    """Prediction with near-empty features dict → 200, no crash (graceful defaults)."""
    payload = {
        "tender_id": "IT-TEST-0004",
        "features": {"n_bidders": 2.0},
    }
    resp = app_client.post("/api/predict", json=payload)
    assert resp.status_code == 200, f"Minimal features predict failed: {resp.text}"


def test_api_predict_has_disagreement_flag(app_client: TestClient) -> None:
    """Prediction response must include disagreement_flag boolean."""
    payload = {
        "tender_id": "IT-TEST-0005",
        "features": HIGH_RISK_FEATURES,
    }
    resp = app_client.post("/api/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "disagreement_flag" in data, f"Missing 'disagreement_flag': {data}"
    assert isinstance(data["disagreement_flag"], bool)


def test_api_predict_individual_scores(app_client: TestClient) -> None:
    """Prediction response must include per-model scores dict."""
    payload = {
        "tender_id": "IT-TEST-0006",
        "features": HIGH_RISK_FEATURES,
        "icw_raw_score": 30.0,
    }
    resp = app_client.post("/api/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "individual_scores" in data, f"Missing 'individual_scores': {data}"
    scores = data["individual_scores"]
    assert isinstance(scores, dict), f"individual_scores must be dict: {scores}"
    # At least one model score must be present
    assert len(scores) >= 1, f"individual_scores empty: {scores}"
    for k, v in scores.items():
        assert isinstance(v, (int, float)), f"Score {k}={v} not numeric"
        assert 0.0 <= float(v) <= 1.0, f"Score {k}={v} out of [0,1]"


# ---------------------------------------------------------------------------
# XAI
# ---------------------------------------------------------------------------


def test_api_xai_returns_200(app_client: TestClient) -> None:
    """POST /api/xai/{id} → 200."""
    payload = {"features": HIGH_RISK_FEATURES}
    resp = app_client.post("/api/xai/IT-TEST-XAI-001", json=payload)
    assert resp.status_code == 200, f"XAI failed: {resp.text}"


def test_api_xai_has_all_five_layers(app_client: TestClient) -> None:
    """Oracle Sandwich response must contain all 5 XAI layer keys."""
    payload = {"features": HIGH_RISK_FEATURES, "amount_values": [4_500_000_000.0] * 20}
    resp = app_client.post("/api/xai/IT-TEST-XAI-002", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    # Response is wrapped in {"status": "ok", "data": {...}}
    inner = data.get("data", data)

    for layer in ("shap", "anchors", "leiden", "benford", "dice"):
        assert layer in inner, f"XAI layer '{layer}' missing from response: {list(inner.keys())}"


def test_api_xai_layers_have_status(app_client: TestClient) -> None:
    """Each XAI layer must have a 'status' key."""
    payload = {"features": HIGH_RISK_FEATURES}
    resp = app_client.post("/api/xai/IT-TEST-XAI-003", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    inner = data.get("data", data)

    for layer in ("shap", "anchors", "leiden", "benford", "dice"):
        layer_data = inner.get(layer, {})
        assert "status" in layer_data, (
            f"Layer '{layer}' missing 'status' key: {layer_data}"
        )
        valid_statuses = {"ok", "error", "not_applicable", "timeout", "skipped"}
        assert layer_data["status"] in valid_statuses, (
            f"Layer '{layer}' has unexpected status: {layer_data['status']}"
        )


def test_api_xai_partial_failure_still_returns_200(app_client: TestClient) -> None:
    """
    Oracle Sandwich must return 200 even when some layers fail.
    Fault tolerance is a core competition requirement.
    """
    # Use an empty feature dict — some layers may fail gracefully
    payload = {"features": {}}
    resp = app_client.post("/api/xai/IT-TEST-XAI-FAULT", json=payload)
    # Must NOT return 500 — fault tolerance means 200 with partial results
    assert resp.status_code in (200, 422), (
        f"XAI should not crash with empty features: status={resp.status_code} body={resp.text}"
    )


def test_api_xai_with_amount_values_for_benford(app_client: TestClient) -> None:
    """Benford layer receives amount_values and returns a result (any valid status)."""
    # 30+ amount values spanning different orders of magnitude
    amounts = [
        1_000_000.0, 5_000_000.0, 12_000_000.0, 50_000_000.0,
        120_000_000.0, 500_000_000.0, 1_200_000_000.0, 5_000_000_000.0,
        980_000.0, 4_200_000.0, 11_000_000.0, 48_000_000.0,
        115_000_000.0, 480_000_000.0, 1_100_000_000.0, 4_800_000_000.0,
        1_050_000.0, 5_100_000.0, 12_500_000.0, 51_000_000.0,
        125_000_000.0, 510_000_000.0, 1_250_000_000.0, 5_100_000_000.0,
        990_000.0, 4_500_000.0, 11_500_000.0, 49_000_000.0,
        118_000_000.0, 490_000_000.0,
    ]
    payload = {"features": HIGH_RISK_FEATURES, "amount_values": amounts}
    resp = app_client.post("/api/xai/IT-TEST-XAI-BENFORD", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    inner = data.get("data", data)
    benford = inner.get("benford", {})
    assert "status" in benford, f"Benford layer missing 'status': {benford}"


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


def test_api_graph_returns_200(app_client: TestClient) -> None:
    """GET /api/graph → 200."""
    resp = app_client.get("/api/graph")
    assert resp.status_code == 200, f"Graph endpoint failed: {resp.text}"


def test_api_graph_has_communities_key(app_client: TestClient) -> None:
    """Graph response must contain 'communities' list."""
    resp = app_client.get("/api/graph")
    data = resp.json()
    assert "communities" in data, f"Missing 'communities' key: {data}"
    assert isinstance(data["communities"], list), (
        f"'communities' must be a list: {type(data['communities'])}"
    )


def test_api_graph_has_status(app_client: TestClient) -> None:
    """Graph response must have 'status' field."""
    resp = app_client.get("/api/graph")
    data = resp.json()
    assert "status" in data, f"Missing 'status': {data}"


def test_api_graph_accepts_filters(app_client: TestClient) -> None:
    """Graph endpoint accepts query params without crashing."""
    resp = app_client.get("/api/graph?min_community_size=3&top_n=5")
    assert resp.status_code == 200, f"Filtered graph failed: {resp.text}"


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def test_api_report_get_returns_200(app_client: TestClient) -> None:
    """GET /api/reports/{id} → 200."""
    resp = app_client.get("/api/reports/IT-TEST-RPT-001")
    assert resp.status_code == 200, f"Report GET failed: {resp.text}"


def test_api_report_post_returns_200(app_client: TestClient) -> None:
    """POST /api/reports/{id} → 200."""
    payload: dict = {"oracle_result": None, "tender_data": None}
    resp = app_client.post("/api/reports/IT-TEST-RPT-002", json=payload)
    assert resp.status_code == 200, f"Report POST failed: {resp.text}"


def test_api_report_has_report_text(app_client: TestClient) -> None:
    """Report response must include non-empty report_text."""
    resp = app_client.post(
        "/api/reports/IT-TEST-RPT-003",
        json={"oracle_result": None, "tender_data": None},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "report_text" in data, f"Missing 'report_text': {data}"
    assert isinstance(data["report_text"], str), "report_text must be string"
    assert len(data["report_text"]) > 20, "report_text is suspiciously short"


def test_api_report_with_oracle_result(app_client: TestClient) -> None:
    """POST /api/reports/{id} with full oracle_result dict → 200 + richer report."""
    oracle_result = {
        "tender_id": "IT-TEST-RPT-004",
        "layers_ok": 3,
        "layers_failed": 2,
        "total_seconds": 1.24,
        "shap": {
            "status": "ok",
            "data": {"model_output": 0.87, "top_features": [{"name": "n_bidders", "value": -0.42}]},
            "error": None,
        },
        "anchors": {
            "status": "ok",
            "data": {"rules": ["IF n_bidders <= 1 THEN Risiko Tinggi"]},
            "error": None,
        },
        "leiden": {"status": "not_applicable", "data": None, "error": None},
        "benford": {
            "status": "ok",
            "data": {"suspicious": True, "chi2": 42.3, "p_value": 0.001},
            "error": None,
        },
        "dice": {"status": "not_applicable", "data": None, "error": None},
    }
    tender_data = {
        "nama_paket": "Konstruksi Gedung Kantor",
        "satuan_kerja": "Dinas PUPR",
        "nilai_hps": 5_000_000_000,
    }
    payload = {"oracle_result": oracle_result, "tender_data": tender_data}
    resp = app_client.post("/api/reports/IT-TEST-RPT-004", json=payload)
    assert resp.status_code == 200, f"Report with oracle failed: {resp.text}"
    data = resp.json()
    assert "report_text" in data
    assert len(data["report_text"]) > 50


def test_api_report_has_risk_level(app_client: TestClient) -> None:
    """Report response must include risk_level field."""
    resp = app_client.get("/api/reports/IT-TEST-RPT-005")
    assert resp.status_code == 200
    data = resp.json()
    assert "risk_level" in data, f"Missing 'risk_level': {data}"


# ---------------------------------------------------------------------------
# Config injection
# ---------------------------------------------------------------------------


def test_api_inject_valid(app_client: TestClient) -> None:
    """PUT /api/config/inject with valid params → 200 + success=True."""
    payload = {"risk_threshold": 0.75, "procurement_scope": "konstruksi"}
    resp = app_client.put("/api/config/inject", json=payload)
    assert resp.status_code == 200, f"Valid inject failed: {resp.text}"
    data = resp.json()
    assert data.get("success") is True, f"Inject did not return success=True: {data}"


def test_api_inject_invalid_threshold(app_client: TestClient) -> None:
    """PUT /api/config/inject with risk_threshold > 1.0 → 422."""
    payload = {"risk_threshold": 999.0}
    resp = app_client.put("/api/config/inject", json=payload)
    assert resp.status_code == 422, (
        f"Expected 422 for invalid threshold, got {resp.status_code}: {resp.text}"
    )


def test_api_inject_invalid_negative_threshold(app_client: TestClient) -> None:
    """PUT /api/config/inject with risk_threshold < 0 → 422."""
    payload = {"risk_threshold": -0.1}
    resp = app_client.put("/api/config/inject", json=payload)
    assert resp.status_code == 422, (
        f"Expected 422 for negative threshold, got {resp.status_code}: {resp.text}"
    )


def test_api_inject_custom_params_accepted(app_client: TestClient) -> None:
    """PUT /api/config/inject with custom_params wildcard → 200."""
    payload = {
        "custom_params": {
            "secret_judge_param": 42,
            "extra_province_filter": "DKI Jakarta",
            "enable_debug_mode": True,
        }
    }
    resp = app_client.put("/api/config/inject", json=payload)
    assert resp.status_code == 200, f"custom_params injection failed: {resp.text}"
    data = resp.json()
    assert data.get("success") is True


def test_api_inject_persists_in_config(app_client: TestClient) -> None:
    """Injected risk_threshold must be reflected in GET /api/config."""
    new_threshold = 0.88
    app_client.put("/api/config/inject", json={"risk_threshold": new_threshold})

    resp = app_client.get("/api/config")
    assert resp.status_code == 200
    cfg = resp.json()
    assert "risk_threshold" in cfg, f"Missing risk_threshold in config: {cfg}"
    assert abs(float(cfg["risk_threshold"]) - new_threshold) < 1e-6, (
        f"Config not updated: expected {new_threshold}, got {cfg['risk_threshold']}"
    )


def test_api_inject_old_and_new_values_returned(app_client: TestClient) -> None:
    """Inject response must include old_values and new_values for audit trail."""
    payload = {"risk_threshold": 0.70}
    resp = app_client.put("/api/config/inject", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "old_values" in data, f"Missing old_values: {data}"
    assert "new_values" in data, f"Missing new_values: {data}"


def test_api_get_config_returns_all_fields(app_client: TestClient) -> None:
    """GET /api/config → all 7 injectable fields present."""
    resp = app_client.get("/api/config")
    assert resp.status_code == 200
    cfg = resp.json()
    required = {
        "procurement_scope",
        "institution_filter",
        "risk_threshold",
        "year_range",
        "anomaly_method",
        "output_format",
        "custom_params",
    }
    missing = required - set(cfg.keys())
    assert not missing, f"Config missing fields: {missing}"


# ---------------------------------------------------------------------------
# Mini dataset validity
# ---------------------------------------------------------------------------


def test_mini_dataset_has_50_records(mini_tenders: list[dict]) -> None:
    """Fixture: mini_tenders.json must contain exactly 50 records."""
    assert len(mini_tenders) == 50, f"Expected 50 tenders, got {len(mini_tenders)}"


def test_mini_dataset_has_ocid(mini_tenders: list[dict]) -> None:
    """Fixture: all records must have OCDS 'ocid' field."""
    for t in mini_tenders:
        assert "ocid" in t, f"Record missing 'ocid': {t.get('tender_id', '?')}"


def test_mini_dataset_has_required_fields(mini_tenders: list[dict]) -> None:
    """Fixture: all records have the core fields needed by feature pipeline."""
    required = {"tender_id", "amount", "n_bidders", "winner_id", "year", "total_score"}
    for t in mini_tenders:
        missing = required - set(t.keys())
        assert not missing, (
            f"Record {t.get('tender_id', '?')} missing fields: {missing}"
        )


def test_mini_dataset_has_risk_distribution(mini_tenders: list[dict]) -> None:
    """Fixture: dataset should include both high-risk (n_bidders=1) and clean (n_bidders>=3) records."""
    single_bidder = sum(1 for t in mini_tenders if t.get("n_bidders", 0) == 1)
    multi_bidder = sum(1 for t in mini_tenders if t.get("n_bidders", 0) >= 3)
    assert single_bidder >= 5, f"Too few high-risk records (n_bidders=1): {single_bidder}"
    assert multi_bidder >= 10, f"Too few clean records (n_bidders>=3): {multi_bidder}"


# ---------------------------------------------------------------------------
# Mini DB fixture
# ---------------------------------------------------------------------------


def test_mini_db_has_50_rows(mini_db: str) -> None:
    """mini_db fixture: SQLite DB must have 50 rows in tenders table."""
    import sqlite3

    conn = sqlite3.connect(mini_db)
    count = conn.execute("SELECT COUNT(*) FROM tenders").fetchone()[0]
    conn.close()
    assert count == 50, f"Expected 50 rows in mini_db, got {count}"


def test_mini_db_has_required_columns(mini_db: str) -> None:
    """mini_db fixture: tenders table must have all required columns."""
    import sqlite3

    conn = sqlite3.connect(mini_db)
    cursor = conn.execute("PRAGMA table_info(tenders)")
    columns = {row[1] for row in cursor.fetchall()}
    conn.close()

    required = {"tender_id", "amount", "n_bidders", "year", "total_score", "hps"}
    missing = required - columns
    assert not missing, f"mini_db tenders table missing columns: {missing}"
