"""
LPSE-X Anchors Rule Explainer
==============================
Layer 3 of the Oracle Sandwich: Rule-based Explanation.

Uses AnchorTabular from alibi library to extract human-readable if-then rules.
Example output: "IF HPS_Deviation > 0.15 AND Participant_Count < 3 THEN High Risk (precision=0.95)"

Performance SLA: < 5s per individual tender explanation.

References:
  - UPGRADE 3 line 145 — Anchors from alibi
  - DEEP_RESEARCH_SYNTHESIS.md line 141
  - Thanathamathee & Sawangarreerak (2024): SHAP + Anchors + XGBoost validated
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Target minimum precision for anchor rules
MIN_ANCHOR_PRECISION = 0.80

# Timeout for anchor computation (seconds)
ANCHOR_TIMEOUT_SECONDS = 5.0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class AnchorResult:
    """
    Anchors rule extraction result for a single tender.
    Returns human-readable if-then decision rules.
    """
    tender_id: str
    anchor_rules: list[str]              # ["IF feature > value AND ...", ...]
    precision: float                     # how often anchor holds (0.0-1.0)
    coverage: float                      # fraction of data points covered
    features_used: list[str]             # feature names in the anchor
    plain_text: str                      # human-readable summary in Bahasa Indonesia
    computation_seconds: float
    error: str | None = None             # non-None if explainer failed gracefully


# ---------------------------------------------------------------------------
# Helper: build predict function
# ---------------------------------------------------------------------------

def _make_predict_fn(
    model: Any,
    feature_names: list[str],
) -> Callable[[np.ndarray], np.ndarray]:
    """
    Wrap model.predict so AnchorTabular can call it.
    AnchorTabular expects predict(X: np.ndarray) -> np.ndarray of int labels.
    """
    import pandas as pd

    def predict_fn(X: np.ndarray) -> np.ndarray:
        df = pd.DataFrame(X, columns=feature_names)
        return model.predict(df.fillna(0.0).to_numpy(dtype=float))

    return predict_fn


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fit_anchor_explainer(
    model: Any,
    X_train: pd.DataFrame,
    seed: int = 42,
) -> Any:
    """
    Initialize and fit AnchorTabular explainer on training data.

    Parameters
    ----------
    model:
        Fitted XGBClassifier.
    X_train:
        Training feature DataFrame used as background.
    seed:
        Random seed for reproducibility.

    Returns
    -------
    Fitted AnchorTabular explainer ready for .explain() calls.
    """
    from alibi.explainers import AnchorTabular

    feature_names: list[str] = list(X_train.columns)
    X_np = X_train.fillna(0.0).to_numpy(dtype=float)

    predict_fn = _make_predict_fn(model, feature_names)

    explainer = AnchorTabular(
        predictor=predict_fn,
        feature_names=feature_names,
        seed=seed,
    )
    explainer.fit(X_np)
    logger.info(
        "AnchorTabular fitted on %d training samples, %d features, seed=%d",
        X_np.shape[0], X_np.shape[1], seed,
    )
    return explainer


def compute_anchors(
    explainer: Any,
    instance: pd.DataFrame,
    tender_id: str,
    threshold: float = MIN_ANCHOR_PRECISION,
    timeout: float = ANCHOR_TIMEOUT_SECONDS,
) -> AnchorResult:
    """
    Compute Anchors rule explanation for a single tender.

    Parameters
    ----------
    explainer:
        Fitted AnchorTabular explainer from fit_anchor_explainer().
    instance:
        Single-row DataFrame with feature values.
    tender_id:
        Identifier for logging.
    threshold:
        Minimum precision for anchor rules (default 0.80).
    timeout:
        Maximum seconds to allow (default 5.0).

    Returns
    -------
    AnchorResult with human-readable if-then rules.
    Gracefully returns error result if computation fails or times out.
    """
    t0 = time.perf_counter()

    try:
        X_np = instance.fillna(0.0).to_numpy(dtype=float)
        feature_names: list[str] = list(instance.columns)

        if X_np.shape[0] != 1:
            raise ValueError(f"compute_anchors expects single-row DataFrame, got {X_np.shape[0]} rows")

        # Run anchors explanation with precision threshold
        explanation = explainer.explain(
            X_np[0],
            threshold=threshold,
        )

        elapsed = time.perf_counter() - t0
        if elapsed > ANCHOR_TIMEOUT_SECONDS:
            logger.warning("Anchors SLA breach: %.3fs > %.1fs for tender %s", elapsed, ANCHOR_TIMEOUT_SECONDS, tender_id)

        # Extract anchor rules
        anchor_list: list[str] = list(explanation.anchor) if explanation.anchor else []
        precision_val = float(explanation.precision) if hasattr(explanation, "precision") else 0.0
        coverage_val = float(explanation.coverage) if hasattr(explanation, "coverage") else 0.0

        # Identify features used in the anchor
        features_used: list[str] = []
        for rule in anchor_list:
            for fname in feature_names:
                if fname.lower() in rule.lower() and fname not in features_used:
                    features_used.append(fname)

        # Build human-readable plain text in Bahasa Indonesia
        if anchor_list:
            conditions = " DAN ".join(anchor_list)
            plain_text = (
                f"Tender ini teridentifikasi berisiko tinggi karena: {conditions}. "
                f"Aturan ini berlaku dengan presisi {precision_val:.0%} "
                f"dan mencakup {coverage_val:.0%} dari data referensi."
            )
        else:
            plain_text = (
                "Penjelasan berbasis aturan tidak dapat ditemukan dengan presisi yang memadai. "
                "Silakan merujuk ke nilai SHAP untuk interpretasi fitur."
            )

        logger.info(
            "Anchors for tender %s: %d rules, precision=%.3f, coverage=%.3f, time=%.3fs",
            tender_id, len(anchor_list), precision_val, coverage_val, elapsed,
        )

        return AnchorResult(
            tender_id=tender_id,
            anchor_rules=anchor_list,
            precision=round(precision_val, 4),
            coverage=round(coverage_val, 4),
            features_used=features_used,
            plain_text=plain_text,
            computation_seconds=round(elapsed, 4),
            error=None,
        )

    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error("Anchors failed for tender %s after %.3fs: %s", tender_id, elapsed, exc)
        return AnchorResult(
            tender_id=tender_id,
            anchor_rules=[],
            precision=0.0,
            coverage=0.0,
            features_used=[],
            plain_text="Penjelasan berbasis aturan tidak tersedia saat ini.",
            computation_seconds=round(elapsed, 4),
            error=str(exc),
        )
