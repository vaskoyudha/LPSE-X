"""
LPSE-X Isolation Forest Wrapper
=================================
Unsupervised anomaly detection — no labels needed.
Decision: anomaly_score normalized to [0, 1] (higher = more suspicious).

Contamination and n_estimators are read from runtime_config (never hardcoded).
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from backend.config.runtime import get_config

logger = logging.getLogger(__name__)

RANDOM_SEED: int = 42


def _get_contamination() -> Any:
    """Read contamination from runtime config custom_params, default 'auto'."""
    cfg = get_config()
    return cfg.custom_params.get("iforest_contamination", "auto")


def _get_n_estimators() -> int:
    return int(get_config().custom_params.get("iforest_n_estimators", 200))


def fit_isolation_forest(
    X_train: pd.DataFrame,
) -> IsolationForest:
    """
    Fit an Isolation Forest on the training feature matrix.

    Parameters
    ----------
    X_train:
        Feature DataFrame (numeric columns only; NaNs will be filled with 0).

    Returns
    -------
    Fitted IsolationForest model.
    """
    contamination = _get_contamination()
    n_estimators = _get_n_estimators()

    logger.info(
        "Fitting IsolationForest: n_rows=%d, n_features=%d, contamination=%s, n_estimators=%d, seed=%d",
        len(X_train), X_train.shape[1], contamination, n_estimators, RANDOM_SEED,
    )

    X_np = X_train.fillna(0.0).to_numpy(dtype=float)

    model = IsolationForest(
        contamination=contamination,
        n_estimators=n_estimators,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    model.fit(X_np)

    logger.info("IsolationForest fitted. Seed=%d logged for reproducibility.", RANDOM_SEED)
    return model


def score_isolation_forest(
    model: IsolationForest,
    X: pd.DataFrame,
) -> np.ndarray:
    """
    Predict anomaly scores for feature matrix X.

    Returns scores in [0, 1] where 1 = most anomalous.
    IsolationForest.score_samples() returns negative values (more negative = more anomalous).
    We negate and normalize to [0, 1].

    Parameters
    ----------
    model:
        Fitted IsolationForest.
    X:
        Feature DataFrame.

    Returns
    -------
    1-D numpy array of anomaly scores in [0, 1].
    """
    X_np = X.fillna(0.0).to_numpy(dtype=float)
    raw_scores = model.score_samples(X_np)  # range: (-inf, 0], more negative = anomaly

    # Negate so higher = more anomalous, then min-max normalize to [0, 1]
    neg_scores = -raw_scores  # now (0, inf], higher = anomaly
    min_s, max_s = float(neg_scores.min()), float(neg_scores.max())
    if max_s > min_s:
        normalized: np.ndarray = (neg_scores - min_s) / (max_s - min_s)
    else:
        normalized = np.zeros_like(neg_scores)

    logger.debug(
        "IF scores: min=%.4f max=%.4f mean=%.4f",
        float(normalized.min()), float(normalized.max()), float(normalized.mean()),
    )
    return normalized.astype(float)
