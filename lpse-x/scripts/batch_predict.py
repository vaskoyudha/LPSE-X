"""
LPSE-X Batch Prediction Runner
================================
Loads pre-trained XGBoost + IsolationForest models and runs ensemble
inference on ALL tenders in the features table, then inserts results
into the predictions table.

Run from project root:
    .venv/Scripts/python.exe scripts/batch_predict.py
"""
from __future__ import annotations

import json
import pickle
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xgboost as xgb

# ── Constants ─────────────────────────────────────────────────────────────────
DB_PATH = "data/lpse_x.db"
XGBOOST_MODEL_PATH = Path("models") / "xgboost.ubj"
IFOREST_MODEL_PATH = Path("models") / "iforest.pkl"
IFOREST_META_PATH = Path("models") / "iforest.json"
MODEL_VERSION = "ensemble-v1"

# Ensemble weights (must sum to 1.0)
WEIGHT_IFOREST = 0.35
WEIGHT_XGBOOST = 0.40
WEIGHT_ICW = 0.25
ICW_NEUTRAL = 0.5  # No ICW score in batch — use neutral


# ── BoosterWrapper ─────────────────────────────────────────────────────────────
class BoosterWrapper:
    """Thin wrapper exposing predict_proba() on xgb.Booster."""

    def __init__(self, booster: xgb.Booster) -> None:
        self._booster = booster

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        dmatrix = xgb.DMatrix(X.astype(np.float32))
        probs = self._booster.predict(dmatrix)
        if probs.ndim == 1:
            probs = np.column_stack([1 - probs, probs])
        return probs

    def __getattr__(self, name: str):
        return getattr(self._booster, name)


# ── Risk classification ────────────────────────────────────────────────────────
def _score_to_risk_level(score: float) -> str:
    """Map ensemble score [0,1] to string risk level (plan thresholds)."""
    if score >= 0.65:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


# ── IForest score normalization ────────────────────────────────────────────────
def _normalize_iforest(raw_scores: np.ndarray) -> np.ndarray:
    """
    score_samples() returns negative values — more negative = more anomalous.
    Negate and min-max normalize to [0, 1].
    """
    neg = -raw_scores
    lo, hi = float(neg.min()), float(neg.max())
    if hi > lo:
        return ((neg - lo) / (hi - lo)).astype(float)
    return np.zeros_like(neg, dtype=float)


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    print("=== LPSE-X Batch Prediction Runner ===")

    # Load feature names
    with open(IFOREST_META_PATH, encoding="utf-8") as f:
        meta = json.load(f)
    feature_names: list[str] = meta["feature_names"]
    print(f"Feature names loaded: {len(feature_names)} features")

    # Load XGBoost model
    booster = xgb.Booster()
    booster.load_model(str(XGBOOST_MODEL_PATH))
    xgb_model = BoosterWrapper(booster)
    print(f"XGBoost model loaded from {XGBOOST_MODEL_PATH}")

    # Load IsolationForest model
    with open(IFOREST_MODEL_PATH, "rb") as f:
        iforest = pickle.load(f)
    print(f"IsolationForest loaded from {IFOREST_MODEL_PATH}")

    # Read all features from DB
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT tender_id, feature_json FROM features").fetchall()
    print(f"Loaded {len(rows)} feature rows from DB")

    # Build feature matrix
    tender_ids: list[str] = []
    X_list: list[list[float]] = []
    for row in rows:
        tid = row["tender_id"]
        raw = json.loads(row["feature_json"])
        vec = [float(raw.get(f) or 0.0) for f in feature_names]
        tender_ids.append(tid)
        X_list.append(vec)

    X_np = np.array(X_list, dtype=np.float32)
    print(f"Feature matrix shape: {X_np.shape}")

    # IForest scores (batch)
    raw_if_scores = iforest.score_samples(X_np)
    if_scores = _normalize_iforest(raw_if_scores)

    # XGBoost scores (batch)
    probs_all = xgb_model.predict_proba(X_np)  # (n, n_classes)
    if probs_all.shape[1] >= 4:
        xgb_scores = probs_all[:, 2] + probs_all[:, 3]  # P(Risiko Tinggi) + P(Risiko Kritis)
    else:
        xgb_scores = probs_all[:, -1]
    xgb_scores = np.clip(xgb_scores, 0.0, 1.0)

    # Ensemble
    final_scores = (
        WEIGHT_IFOREST * if_scores
        + WEIGHT_XGBOOST * xgb_scores
        + WEIGHT_ICW * ICW_NEUTRAL
    )
    final_scores = np.clip(final_scores, 0.0, 1.0)

    # Insert into predictions table
    predicted_at = datetime.now(timezone.utc).isoformat()
    records = [
        (
            tid,
            float(final_scores[i]),
            _score_to_risk_level(float(final_scores[i])),
            MODEL_VERSION,
            predicted_at,
        )
        for i, tid in enumerate(tender_ids)
    ]

    conn.execute("DELETE FROM predictions")
    conn.executemany(
        "INSERT INTO predictions (tender_id, risk_score, risk_level, model_version, predicted_at) "
        "VALUES (?, ?, ?, ?, ?)",
        records,
    )
    conn.commit()
    conn.close()

    # Summary
    risk_levels = [_score_to_risk_level(float(s)) for s in final_scores]
    high_count = risk_levels.count("high")
    medium_count = risk_levels.count("medium")
    low_count = risk_levels.count("low")
    print(f"\n=== Prediction Summary ===")
    print(f"Total predictions inserted: {len(records)}")
    print(f"  high    : {high_count} ({100*high_count/len(records):.1f}%)")
    print(f"  medium  : {medium_count} ({100*medium_count/len(records):.1f}%)")
    print(f"  low     : {low_count} ({100*low_count/len(records):.1f}%)")
    print(f"\nDone. predictions table now has {len(records)} rows.")


if __name__ == "__main__":
    main()
