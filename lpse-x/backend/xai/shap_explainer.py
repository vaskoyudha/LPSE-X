"""
LPSE-X SHAP Explainer
======================
Layer 1 of the Oracle Sandwich: Global Feature Importance + Local Explanation.

Uses TreeSHAP for XGBoost (fast exact SHAP for tree models).

IMPORTANT — Encoding Sensitivity (Hwang et al., 2025):
  SHAP values are sensitive to One-Hot vs Target Encoding on categorical features.
  We use Target Encoding for procurement categoricals (institution, category) to
  avoid SHAP fragmentation across many binary columns. This is set in the feature
  pipeline (T6) and respected here.
  Reference: DEEP_RESEARCH_SYNTHESIS.md lines 122-126.

Performance SLAs:
  Global SHAP (batch 100 tenders): < 2s
  Local SHAP (single tender): < 0.5s
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import shap
import xgboost as xgb

logger = logging.getLogger(__name__)

GLOBAL_SHAP_CACHE: dict[str, "ShapGlobalResult"] = {}


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ShapGlobalResult:
    """
    Global SHAP feature importance for a trained XGBoost model.
    Returned as JSON-serializable data — frontend renders the chart.
    """
    feature_names: list[str]
    mean_abs_shap: list[float]           # |E[|SHAP|]| per feature, sorted desc
    shap_matrix: list[list[float]]       # [n_samples x n_features] raw SHAP values
    base_value: float                    # model.predict(X).mean() background
    top_k_features: list[str]            # top-5 features by mean |SHAP|
    computation_seconds: float           # wall time for SLA tracking


@dataclass
class ShapLocalResult:
    """
    Local SHAP explanation for a single tender prediction.
    SHAP additivity: sum(shap_values) + base_value ≈ model_output.
    """
    tender_id: str
    feature_names: list[str]
    shap_values: list[float]             # per-feature SHAP contribution
    base_value: float                    # SHAP background value
    model_output: float                  # actual model prediction
    top_positive_features: list[dict[str, Any]]   # [{name, shap, value}] top risk drivers
    top_negative_features: list[dict[str, Any]]   # [{name, shap, value}] top risk reducers
    additivity_error: float              # |sum(shap) + base - output| — should be < 0.01
    computation_seconds: float


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_shap_global(
    model: xgb.XGBClassifier,
    X_train: pd.DataFrame,
    top_k: int = 5,
    cache_key: str = "default",
    force_recompute: bool = False,
) -> ShapGlobalResult:
    """
    Compute global SHAP feature importance for a trained XGBoost model.

    Parameters
    ----------
    model:
        Fitted XGBClassifier.
    X_train:
        Training feature DataFrame (used as background for SHAP).
    top_k:
        Number of top features to return in top_k_features.
    cache_key:
        Cache identifier — reuse results between API calls without recomputing.
    force_recompute:
        If True, ignore cache and recompute.

    Returns
    -------
    ShapGlobalResult with feature importances sorted by mean |SHAP|.

    Notes
    -----
    Uses TreeExplainer (fast exact SHAP for tree models).
    For multiclass XGBoost: shap_values is a 3D array [n_samples, n_features, n_classes].
    We average |SHAP| across all classes to get a single importance per feature.
    """
    global GLOBAL_SHAP_CACHE

    if not force_recompute and cache_key in GLOBAL_SHAP_CACHE:
        logger.debug("SHAP global: returning cached result for key=%s", cache_key)
        return GLOBAL_SHAP_CACHE[cache_key]

    t0 = time.perf_counter()
    X_np = X_train.fillna(0.0).to_numpy(dtype=float)
    feature_names: list[str] = list(X_train.columns)

    # Unwrap BoosterWrapper to get raw xgb.Booster for SHAP
    _shap_model = getattr(model, '_booster', model)
    explainer = shap.TreeExplainer(_shap_model)

    # shap_values: for multi-class XGBoost, shape = (n_samples, n_features, n_classes)
    # or list of [n_samples x n_features] arrays — depends on shap version.
    raw_shap = explainer.shap_values(X_np)

    if isinstance(raw_shap, list):
        # Old API: list of [n_samples x n_features] arrays, one per class
        shap_3d = np.stack(raw_shap, axis=2)  # (n_samples, n_features, n_classes)
    elif isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 3:
        shap_3d = raw_shap
    elif isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 2:
        # Binary or single output — treat as single class
        shap_3d = raw_shap[:, :, np.newaxis]
    else:
        shap_3d = np.array(raw_shap)

    # Mean |SHAP| across all samples AND all classes → shape (n_features,)
    mean_abs = np.mean(np.abs(shap_3d), axis=(0, 2))  # (n_features,)

    # Sort by importance descending
    sorted_idx = np.argsort(mean_abs)[::-1]
    sorted_features = [feature_names[i] for i in sorted_idx]
    sorted_mean_abs = [float(mean_abs[i]) for i in sorted_idx]

    # Reorder shap_matrix columns to sorted order
    # For storage: store mean across classes per sample, sorted
    shap_2d_mean = np.mean(shap_3d, axis=2)  # (n_samples, n_features)
    shap_sorted = shap_2d_mean[:, sorted_idx]

    # Base value: mean of training data predictions
    try:
        base_val = float(explainer.expected_value)
    except (TypeError, AttributeError):
        # Multi-class: list of base values — take mean
        ev = explainer.expected_value
        base_val = float(np.mean(ev)) if hasattr(ev, '__iter__') else float(ev)

    elapsed = time.perf_counter() - t0
    logger.info(
        "SHAP global computed in %.3fs for %d samples x %d features",
        elapsed, X_np.shape[0], len(feature_names),
    )
    if elapsed > 2.0:
        logger.warning("SHAP global SLA breach: %.3fs > 2.0s", elapsed)

    result = ShapGlobalResult(
        feature_names=sorted_features,
        mean_abs_shap=sorted_mean_abs,
        shap_matrix=shap_sorted.tolist(),
        base_value=base_val,
        top_k_features=sorted_features[:top_k],
        computation_seconds=round(elapsed, 4),
    )
    GLOBAL_SHAP_CACHE[cache_key] = result
    return result


def compute_shap_local(
    model: xgb.XGBClassifier,
    instance: pd.DataFrame,
    tender_id: str,
    top_k: int = 5,
) -> ShapLocalResult:
    """
    Compute local SHAP explanation for a single tender.

    Parameters
    ----------
    model:
        Fitted XGBClassifier.
    instance:
        Single-row DataFrame with feature values (same schema as training data).
    tender_id:
        Identifier for logging and output.
    top_k:
        Number of top positive and negative features to surface.

    Returns
    -------
    ShapLocalResult with per-feature SHAP values.

    Notes
    -----
    Additivity check: sum(shap_values) + base_value ≈ model output (should be < 0.01 error).
    """
    t0 = time.perf_counter()
    X_np = instance.fillna(0.0).to_numpy(dtype=float)
    feature_names: list[str] = list(instance.columns)

    if X_np.shape[0] != 1:
        raise ValueError(f"compute_shap_local expects a single-row DataFrame, got {X_np.shape[0]} rows")

    # Unwrap BoosterWrapper to get raw xgb.Booster for SHAP
    _shap_model = getattr(model, '_booster', model)
    explainer = shap.TreeExplainer(_shap_model)
    raw_shap = explainer.shap_values(X_np)

    # For multiclass: average SHAP values across classes for interpretability
    if isinstance(raw_shap, list):
        shap_3d = np.stack(raw_shap, axis=2)   # (1, n_features, n_classes)
    elif isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 3:
        shap_3d = raw_shap
    elif isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 2:
        shap_3d = raw_shap[:, :, np.newaxis]
    else:
        shap_3d = np.array(raw_shap)

    # Use the highest-risk class (class 3 = Risiko Kritis) for local explanation
    # This gives the most interpretable "why is this risky?" explanation
    n_classes = shap_3d.shape[2]
    risk_class_idx = min(3, n_classes - 1)
    shap_for_risk = shap_3d[0, :, risk_class_idx]  # (n_features,)

    # Base value for the risk class
    try:
        ev = explainer.expected_value
        if hasattr(ev, '__iter__'):
            ev_list = list(ev)
            base_val = float(ev_list[risk_class_idx]) if risk_class_idx < len(ev_list) else float(np.mean(ev_list))
        else:
            base_val = float(ev)
    except (TypeError, AttributeError):
        base_val = 0.0

    # Model output for this instance (probability of highest risk class)
    proba = model.predict_proba(X_np)  # (1, n_classes)
    model_output = float(proba[0, risk_class_idx])

    # Additivity check
    additivity_error = abs(float(np.sum(shap_for_risk)) + base_val - model_output)
    if additivity_error > 0.01:
        logger.warning(
            "SHAP additivity error %.4f > 0.01 for tender %s (expected < 0.01)",
            additivity_error, tender_id,
        )

    # Top positive (risk drivers) and negative (risk reducers) features
    feature_shap_pairs = [
        {"name": feature_names[i], "shap": float(shap_for_risk[i]), "value": float(X_np[0, i])}
        for i in range(len(feature_names))
    ]
    sorted_by_shap = sorted(feature_shap_pairs, key=lambda x: x["shap"], reverse=True)
    top_positive = [x for x in sorted_by_shap if x["shap"] > 0][:top_k]
    top_negative = [x for x in sorted_by_shap if x["shap"] < 0][-top_k:]

    elapsed = time.perf_counter() - t0
    logger.debug("SHAP local for tender %s computed in %.3fs", tender_id, elapsed)

    return ShapLocalResult(
        tender_id=tender_id,
        feature_names=feature_names,
        shap_values=shap_for_risk.tolist(),
        base_value=base_val,
        model_output=model_output,
        top_positive_features=top_positive,
        top_negative_features=top_negative,
        additivity_error=round(additivity_error, 6),
        computation_seconds=round(elapsed, 4),
    )
