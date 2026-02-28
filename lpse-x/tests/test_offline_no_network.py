"""
T21 Offline enforcement tests.

Verifies that the entire inference pipeline makes zero outbound network
connections.  LPSE-X is designed to run 100% air-gapped / offline — this
is a hard competition requirement.

Uses socket-level patching so the test is independent of OS firewall rules.
"""
from __future__ import annotations

import socket
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "", "0.0.0.0"})


def _make_blocking_patch():
    """Return a patched socket.connect that blocks all outbound connections."""
    original_connect = socket.socket.connect
    blocked: list = []

    def patched_connect(self, address):
        host = address[0] if isinstance(address, tuple) else str(address)
        if host not in ALLOWED_HOSTS:
            blocked.append(address)
            raise ConnectionError(f"OFFLINE TEST: blocked outbound connection to {address}")
        return original_connect(self, address)

    return patched_connect, blocked


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_predict_no_outbound_connections(app_client: TestClient) -> None:
    """
    POST /api/predict must make zero outbound TCP connections.
    All model inference must be fully local.
    """
    patched_connect, blocked = _make_blocking_patch()

    with patch.object(socket.socket, "connect", patched_connect):
        resp = app_client.post("/api/predict", json={
            "tender_id": "OFFLINE-PREDICT-001",
            "features": {
                "n_bidders": 1.0,
                "price_ratio": 0.99,
                "bid_spread": 0.001,
                "winner_bid_rank": 1.0,
                "hhi": 0.98,
                "log_amount": 20.5,
            },
        })

    assert len(blocked) == 0, (
        f"Outbound TCP connections were attempted during /api/predict: {blocked}"
    )
    assert resp.status_code == 200, f"Predict failed: {resp.text}"


def test_xai_no_outbound_connections(app_client: TestClient) -> None:
    """
    POST /api/xai/{id} must make zero outbound TCP connections.
    XAI layers (SHAP, Anchors, Benford) must run fully locally.
    """
    patched_connect, blocked = _make_blocking_patch()

    with patch.object(socket.socket, "connect", patched_connect):
        resp = app_client.post("/api/xai/OFFLINE-XAI-001", json={
            "features": {
                "n_bidders": 1.0,
                "price_ratio": 0.99,
                "bid_spread": 0.001,
                "winner_bid_rank": 1.0,
                "hhi": 0.95,
                "log_amount": 19.8,
            },
            "amount_values": [float(i * 1_000_000) for i in range(1, 21)],
        })

    assert len(blocked) == 0, (
        f"Outbound TCP connections were attempted during /api/xai: {blocked}"
    )
    assert resp.status_code == 200, f"XAI failed: {resp.text}"


def test_config_inject_no_outbound_connections(app_client: TestClient) -> None:
    """
    PUT /api/config/inject must work completely offline — no external calls.
    """
    patched_connect, blocked = _make_blocking_patch()

    with patch.object(socket.socket, "connect", patched_connect):
        resp = app_client.put("/api/config/inject", json={
            "risk_threshold": 0.6,
            "procurement_scope": "konstruksi",
        })

    assert len(blocked) == 0, (
        f"Outbound TCP connections were attempted during /api/config/inject: {blocked}"
    )
    assert resp.status_code == 200, f"Config inject failed: {resp.text}"


def test_report_no_outbound_connections(app_client: TestClient) -> None:
    """
    POST /api/reports/{id} report generation must be fully offline.
    No external NLP or cloud APIs should be called.
    """
    patched_connect, blocked = _make_blocking_patch()

    with patch.object(socket.socket, "connect", patched_connect):
        resp = app_client.post("/api/reports/OFFLINE-REPORT-001", json={})

    assert len(blocked) == 0, (
        f"Outbound TCP connections were attempted during /api/reports: {blocked}"
    )
    assert resp.status_code == 200, f"Report failed: {resp.text}"


def test_health_no_outbound_connections(app_client: TestClient) -> None:
    """
    GET /api/health must work offline — no external health-check pings.
    """
    patched_connect, blocked = _make_blocking_patch()

    with patch.object(socket.socket, "connect", patched_connect):
        resp = app_client.get("/api/health")

    assert len(blocked) == 0, (
        f"Outbound TCP connections were attempted during /api/health: {blocked}"
    )
    assert resp.status_code == 200


def test_graph_no_outbound_connections(app_client: TestClient) -> None:
    """
    GET /api/graph must work offline — Leiden community detection is local.
    """
    patched_connect, blocked = _make_blocking_patch()

    with patch.object(socket.socket, "connect", patched_connect):
        resp = app_client.get("/api/graph")

    assert len(blocked) == 0, (
        f"Outbound TCP connections were attempted during /api/graph: {blocked}"
    )
    assert resp.status_code == 200


def test_full_pipeline_no_outbound_connections(app_client: TestClient) -> None:
    """
    Full pipeline (predict → xai → report) in sequence: zero outbound connections.
    Simulates a complete hackathon demo flow, all offline.
    """
    patched_connect, blocked = _make_blocking_patch()
    tender_id = "OFFLINE-FULL-PIPELINE-001"
    features = {
        "n_bidders": 1.0,
        "price_ratio": 0.995,
        "bid_spread": 0.005,
        "winner_bid_rank": 1.0,
        "hhi": 0.97,
        "log_amount": 21.0,
    }

    with patch.object(socket.socket, "connect", patched_connect):
        # Step 1: predict
        r1 = app_client.post("/api/predict", json={
            "tender_id": tender_id,
            "features": features,
        })
        # Step 2: XAI
        r2 = app_client.post(f"/api/xai/{tender_id}", json={"features": features})
        # Step 3: Report
        r3 = app_client.post(f"/api/reports/{tender_id}", json={})

    assert len(blocked) == 0, (
        f"Outbound TCP connections in full pipeline: {blocked}"
    )
    assert r1.status_code == 200, f"Predict: {r1.text}"
    assert r2.status_code == 200, f"XAI: {r2.text}"
    assert r3.status_code == 200, f"Report: {r3.text}"
