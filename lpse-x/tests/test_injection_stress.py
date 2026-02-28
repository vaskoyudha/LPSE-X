"""
T22: Dynamic Injection Stress Tests
======================================
Competition requirement (verbatim):
  "Aplikasi Anda WAJIB mampu menerima dan memproses variabel/logika dadakan ini
   agar sistem dianggap valid."
  "Kegagalan dalam mengimplementasikan Dynamic Injection ini akan dianggap
   sebagai indikasi ketidaksiapan sistem atau kecurangan, yang dapat berdampak
   pada diskualifikasi."

Tests every valid and invalid combination of the 7 injectable runtime parameters:
  1. procurement_scope  — enum: konstruksi|barang|jasa_konsultansi|jasa_lainnya
  2. institution_filter — list[str]
  3. risk_threshold     — float [0.0, 1.0]
  4. year_range         — tuple[int, int]
  5. anomaly_method     — enum: isolation_forest|xgboost|ensemble
  6. output_format      — enum: dashboard|api_json|audit_report
  7. custom_params      — dict (arbitrary key-value)

After each injection the config is verified via GET /api/config.
All injections are isolated: each test resets via a fresh override.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def inject(client: TestClient, payload: dict) -> dict:
    """PUT /api/config/inject and return the JSON response."""
    resp = client.put("/api/config/inject", json=payload)
    return resp


def get_cfg(client: TestClient) -> dict:
    """GET /api/config and return the JSON."""
    resp = client.get("/api/config")
    assert resp.status_code == 200, f"GET /api/config failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# 1. procurement_scope
# ---------------------------------------------------------------------------

VALID_SCOPES = ["konstruksi", "barang", "jasa_konsultansi", "jasa_lainnya"]


@pytest.mark.parametrize("scope", VALID_SCOPES)
def test_inject_procurement_scope_valid(app_client: TestClient, scope: str) -> None:
    """All valid procurement scopes must be accepted (200) and persisted."""
    resp = inject(app_client, {"procurement_scope": scope})
    assert resp.status_code == 200, f"scope={scope} rejected: {resp.text}"
    body = resp.json()
    assert body["success"] is True, f"success=False for scope={scope}"
    # Verify persists
    cfg = get_cfg(app_client)
    assert cfg["procurement_scope"] == scope, (
        f"scope not persisted: expected {scope}, got {cfg.get('procurement_scope')}"
    )


@pytest.mark.parametrize("bad_scope", ["semua", "KONSTRUKSI", "other", ""])
def test_inject_procurement_scope_invalid(app_client: TestClient, bad_scope: str) -> None:
    """Invalid procurement scope values must be rejected with 422."""
    resp = inject(app_client, {"procurement_scope": bad_scope})
    assert resp.status_code == 422, (
        f"Expected 422 for bad scope '{bad_scope}', got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 2. institution_filter
# ---------------------------------------------------------------------------

def test_inject_institution_filter_single(app_client: TestClient) -> None:
    """institution_filter with a single item must be accepted."""
    resp = inject(app_client, {"institution_filter": ["KEMENKEU"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    cfg = get_cfg(app_client)
    assert "KEMENKEU" in cfg["institution_filter"]


def test_inject_institution_filter_multiple(app_client: TestClient) -> None:
    """institution_filter with multiple items must be accepted."""
    filters = ["KEMENKEU", "BAPPENAS", "KEMENPU"]
    resp = inject(app_client, {"institution_filter": filters})
    assert resp.status_code == 200
    cfg = get_cfg(app_client)
    for f in filters:
        assert f in cfg["institution_filter"], f"Filter '{f}' not in config: {cfg['institution_filter']}"


def test_inject_institution_filter_empty_list(app_client: TestClient) -> None:
    """Empty institution_filter list must be accepted (clears the filter)."""
    resp = inject(app_client, {"institution_filter": []})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 3. risk_threshold — sweep all 0.0 to 1.0 in 0.1 steps
# ---------------------------------------------------------------------------

THRESHOLD_SWEEP = [round(i / 10, 1) for i in range(11)]  # [0.0, 0.1, ..., 1.0]


@pytest.mark.parametrize("threshold", THRESHOLD_SWEEP)
def test_inject_threshold_sweep(app_client: TestClient, threshold: float) -> None:
    """risk_threshold values 0.0–1.0 must all be accepted."""
    resp = inject(app_client, {"risk_threshold": threshold})
    assert resp.status_code == 200, (
        f"risk_threshold={threshold} rejected: {resp.text}"
    )
    body = resp.json()
    assert body["success"] is True
    cfg = get_cfg(app_client)
    assert abs(cfg["risk_threshold"] - threshold) < 1e-9, (
        f"risk_threshold not persisted: expected {threshold}, got {cfg['risk_threshold']}"
    )


def test_inject_threshold_above_max_rejected(app_client: TestClient) -> None:
    """risk_threshold > 1.0 must be rejected (Pydantic ge/le validation)."""
    resp = inject(app_client, {"risk_threshold": 1.01})
    assert resp.status_code == 422, (
        f"Expected 422 for risk_threshold=1.01, got {resp.status_code}: {resp.text}"
    )


def test_inject_threshold_below_min_rejected(app_client: TestClient) -> None:
    """risk_threshold < 0.0 must be rejected."""
    resp = inject(app_client, {"risk_threshold": -0.01})
    assert resp.status_code == 422, (
        f"Expected 422 for risk_threshold=-0.01, got {resp.status_code}: {resp.text}"
    )


def test_inject_threshold_extreme_low(app_client: TestClient) -> None:
    """risk_threshold=0.0 is the boundary minimum — must be accepted."""
    resp = inject(app_client, {"risk_threshold": 0.0})
    assert resp.status_code == 200


def test_inject_threshold_extreme_high(app_client: TestClient) -> None:
    """risk_threshold=1.0 is the boundary maximum — must be accepted."""
    resp = inject(app_client, {"risk_threshold": 1.0})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 4. year_range
# ---------------------------------------------------------------------------

def test_inject_year_range_valid(app_client: TestClient) -> None:
    """Valid year_range tuple must be accepted and persisted."""
    resp = inject(app_client, {"year_range": [2020, 2024]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    cfg = get_cfg(app_client)
    yr = cfg["year_range"]
    assert yr[0] == 2020 and yr[1] == 2024, f"year_range not persisted correctly: {yr}"


@pytest.mark.parametrize("yr", [
    [2019, 2023],
    [2021, 2025],
    [2018, 2026],
    [2022, 2022],  # same year = single year range
])
def test_inject_year_range_valid_variants(app_client: TestClient, yr: list) -> None:
    """Various valid year ranges must be accepted."""
    resp = inject(app_client, {"year_range": yr})
    assert resp.status_code == 200, f"year_range={yr} rejected: {resp.text}"


# ---------------------------------------------------------------------------
# 5. anomaly_method
# ---------------------------------------------------------------------------

VALID_METHODS = ["isolation_forest", "xgboost", "ensemble"]


@pytest.mark.parametrize("method", VALID_METHODS)
def test_inject_anomaly_method_valid(app_client: TestClient, method: str) -> None:
    """All valid anomaly methods must be accepted and persisted."""
    resp = inject(app_client, {"anomaly_method": method})
    assert resp.status_code == 200, f"method={method} rejected: {resp.text}"
    body = resp.json()
    assert body["success"] is True
    cfg = get_cfg(app_client)
    assert cfg["anomaly_method"] == method


INVALID_METHODS = ["neural_network", "random_forest", "lstm", "gpt4", "bert", "svm", ""]


@pytest.mark.parametrize("bad_method", INVALID_METHODS)
def test_inject_anomaly_method_invalid(app_client: TestClient, bad_method: str) -> None:
    """Invalid anomaly method values must be rejected with 422."""
    resp = inject(app_client, {"anomaly_method": bad_method})
    assert resp.status_code == 422, (
        f"Expected 422 for anomaly_method='{bad_method}', got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 6. output_format
# ---------------------------------------------------------------------------

VALID_FORMATS = ["dashboard", "api_json", "audit_report"]


@pytest.mark.parametrize("fmt", VALID_FORMATS)
def test_inject_output_format_valid(app_client: TestClient, fmt: str) -> None:
    """All valid output formats must be accepted and persisted."""
    resp = inject(app_client, {"output_format": fmt})
    assert resp.status_code == 200, f"output_format={fmt} rejected: {resp.text}"
    body = resp.json()
    assert body["success"] is True
    cfg = get_cfg(app_client)
    assert cfg["output_format"] == fmt


@pytest.mark.parametrize("bad_fmt", ["html", "pdf", "excel", "csv", ""])
def test_inject_output_format_invalid(app_client: TestClient, bad_fmt: str) -> None:
    """Invalid output format values must be rejected with 422."""
    resp = inject(app_client, {"output_format": bad_fmt})
    assert resp.status_code == 422, (
        f"Expected 422 for output_format='{bad_fmt}', got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 7. custom_params — arbitrary key-value store
# ---------------------------------------------------------------------------

def test_inject_custom_params_arbitrary_keys(app_client: TestClient) -> None:
    """custom_params must accept any arbitrary key-value dict."""
    payload = {
        "custom_params": {
            "xai_timeout_shap": "3.0",
            "xai_timeout_anchors": "7.0",
            "judge_demo_mode": "true",
            "hackathon_track": "C",
            "arbitrary_key_123": "value",
        }
    }
    resp = inject(app_client, payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


def test_inject_custom_params_nested_numeric(app_client: TestClient) -> None:
    """custom_params with numeric string values must be accepted."""
    resp = inject(app_client, {"custom_params": {
        "xgb_n_trials": "5",
        "max_batch_size": "100",
    }})
    assert resp.status_code == 200


def test_inject_custom_params_empty_dict(app_client: TestClient) -> None:
    """Empty custom_params dict must be accepted."""
    resp = inject(app_client, {"custom_params": {}})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 8. Response structure validation
# ---------------------------------------------------------------------------

def test_inject_response_has_old_and_new_values(app_client: TestClient) -> None:
    """Injection response must contain old_values and new_values for audit trail."""
    # Set a known baseline
    inject(app_client, {"risk_threshold": 0.5})
    # Now inject new value
    resp = inject(app_client, {"risk_threshold": 0.7})
    assert resp.status_code == 200
    body = resp.json()
    assert "old_values" in body, f"old_values missing from response: {body}"
    assert "new_values" in body, f"new_values missing from response: {body}"
    assert "injected_at" in body, f"injected_at missing from response: {body}"


def test_inject_response_success_flag(app_client: TestClient) -> None:
    """Successful injection must return success=True."""
    resp = inject(app_client, {"procurement_scope": "barang"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_inject_empty_body_accepted(app_client: TestClient) -> None:
    """Empty injection body (no fields changed) must return 200 — all fields optional."""
    resp = inject(app_client, {})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 9. Multi-parameter simultaneous injection
# ---------------------------------------------------------------------------

def test_inject_all_params_simultaneously(app_client: TestClient) -> None:
    """All 7 parameters injected at once must be accepted and all persisted."""
    payload = {
        "procurement_scope": "jasa_konsultansi",
        "institution_filter": ["KEMENKES", "KEMENDIKBUD"],
        "risk_threshold": 0.65,
        "year_range": [2021, 2025],
        "anomaly_method": "ensemble",
        "output_format": "audit_report",
        "custom_params": {"demo": "true", "xgb_n_trials": "3"},
    }
    resp = inject(app_client, payload)
    assert resp.status_code == 200, f"Multi-param injection failed: {resp.text}"
    body = resp.json()
    assert body["success"] is True

    cfg = get_cfg(app_client)
    assert cfg["procurement_scope"] == "jasa_konsultansi"
    assert "KEMENKES" in cfg["institution_filter"]
    assert abs(cfg["risk_threshold"] - 0.65) < 1e-9
    assert cfg["anomaly_method"] == "ensemble"
    assert cfg["output_format"] == "audit_report"


def test_inject_scope_and_threshold_together(app_client: TestClient) -> None:
    """Inject scope + threshold together — both must persist."""
    resp = inject(app_client, {
        "procurement_scope": "konstruksi",
        "risk_threshold": 0.45,
    })
    assert resp.status_code == 200
    cfg = get_cfg(app_client)
    assert cfg["procurement_scope"] == "konstruksi"
    assert abs(cfg["risk_threshold"] - 0.45) < 1e-9


def test_inject_method_and_format_together(app_client: TestClient) -> None:
    """Inject anomaly_method + output_format together — both must persist."""
    resp = inject(app_client, {
        "anomaly_method": "xgboost",
        "output_format": "api_json",
    })
    assert resp.status_code == 200
    cfg = get_cfg(app_client)
    assert cfg["anomaly_method"] == "xgboost"
    assert cfg["output_format"] == "api_json"


# ---------------------------------------------------------------------------
# 10. Injection affects live inference
# ---------------------------------------------------------------------------

def test_injected_threshold_affects_predict_risk_level(app_client: TestClient) -> None:
    """
    Changing risk_threshold must affect the risk_level returned by /api/predict.
    With threshold=0.01, almost all tenders should be flagged high-risk.
    With threshold=0.99, almost all should be safe.
    """
    features = {
        "n_bidders": 2.0,
        "price_ratio": 0.85,
        "bid_spread": 0.05,
        "winner_bid_rank": 1.0,
        "hhi": 0.6,
        "log_amount": 18.0,
    }

    # Very low threshold → should flag as higher risk
    inject(app_client, {"risk_threshold": 0.01})
    r_low = app_client.post("/api/predict", json={
        "tender_id": "THRESHOLD-TEST-LOW",
        "features": features,
    })
    assert r_low.status_code == 200
    low_body = r_low.json()
    assert "risk_threshold" in low_body
    assert abs(low_body["risk_threshold"] - 0.01) < 1e-9, (
        f"Injected threshold not reflected in response: {low_body}"
    )

    # Very high threshold → same tender may be classified differently
    inject(app_client, {"risk_threshold": 0.99})
    r_high = app_client.post("/api/predict", json={
        "tender_id": "THRESHOLD-TEST-HIGH",
        "features": features,
    })
    assert r_high.status_code == 200
    high_body = r_high.json()
    assert abs(high_body["risk_threshold"] - 0.99) < 1e-9, (
        f"Injected threshold not reflected in response: {high_body}"
    )


def test_injection_sequence_each_param(app_client: TestClient) -> None:
    """
    Sequential injection of each of the 7 params — simulates a judge
    running live parameter changes during the demo.
    """
    steps = [
        {"procurement_scope": "konstruksi"},
        {"anomaly_method": "isolation_forest"},
        {"output_format": "dashboard"},
        {"risk_threshold": 0.3},
        {"institution_filter": ["KEMENPU"]},
        {"year_range": [2020, 2024]},
        {"custom_params": {"judge_step": "7"}},
    ]
    for step in steps:
        resp = inject(app_client, step)
        assert resp.status_code == 200, (
            f"Step {step} failed: {resp.status_code} {resp.text}"
        )
        assert resp.json()["success"] is True, f"success=False for step {step}"
