"""
LPSE-X Single-Tender Prediction
==================================
Loads pre-trained models and returns an EnsembleResult for one feature vector.
Called by the FastAPI inference endpoint (T14).

Models loaded lazily (once) from models/ directory.
NEVER retrain here -- inference-only.
"""
from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import IsolationForest

from backend.config.runtime import get_config
from backend.ml.ensemble import EnsembleResult, compute_ensemble
from backend.ml.icw_weak_labels import normalize_icw_score
from backend.ml.isolation_forest import score_isolation_forest

logger = logging.getLogger(__name__)


class BoosterWrapper:
    """
    Thin wrapper around xgb.Booster that exposes predict_proba()
    for compatibility with SHAP explainer and other sklearn-style callers.
    """
    def __init__(self, booster: xgb.Booster) -> None:
        self._booster = booster

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return class probabilities, shape (n, n_classes)."""
        dmatrix = xgb.DMatrix(X.astype(np.float32))
        probs = self._booster.predict(dmatrix)
        if probs.ndim == 1:
            # Binary classification — wrap as 2-class
            probs = np.column_stack([1 - probs, probs])
        return probs

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return class labels."""
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)

    # Delegate everything else to Booster
    def __getattr__(self, name: str):
        return getattr(self._booster, name)


_iforest_model: IsolationForest | None = None
_xgboost_booster: xgb.Booster | None = None
_model_feature_names: list[str] | None = None

IFOREST_MODEL_PATH = Path("models") / "iforest.pkl"
XGBOOST_MODEL_PATH = Path("models") / "xgboost.ubj"
IFOREST_META_PATH = Path("models") / "iforest.json"


def _load_feature_names() -> list[str]:
    """Load the 21 training feature names from IForest sidecar JSON."""
    global _model_feature_names
    if _model_feature_names is None:
        if IFOREST_META_PATH.exists():
            with open(IFOREST_META_PATH, encoding="utf-8") as f:
                meta = json.load(f)
            _model_feature_names = meta["feature_names"]
            logger.info("Loaded %d training feature names from %s", len(_model_feature_names), IFOREST_META_PATH)
        else:
            logger.warning("IForest metadata not found at %s -- feature filtering disabled", IFOREST_META_PATH)
            _model_feature_names = []
    return _model_feature_names


def _filter_features(X_df: pd.DataFrame) -> pd.DataFrame:
    """Select only the 21 training features. Missing columns filled with 0.0."""
    feat_names = _load_feature_names()
    if not feat_names:
        return X_df
    result = pd.DataFrame(index=X_df.index)
    for col in feat_names:
        result[col] = X_df[col].fillna(0.0) if col in X_df.columns else 0.0
    return result


def _load_iforest() -> IsolationForest | None:
    global _iforest_model
    if _iforest_model is None:
        if IFOREST_MODEL_PATH.exists():
            with open(IFOREST_MODEL_PATH, "rb") as f:
                _iforest_model = pickle.load(f)
            logger.info("IsolationForest loaded from %s", IFOREST_MODEL_PATH)
        else:
            logger.warning("IsolationForest model not found at %s", IFOREST_MODEL_PATH)
    return _iforest_model


def _load_xgboost() -> "BoosterWrapper | None":
    """Load XGBoost model wrapped for sklearn-style API compatibility."""
    global _xgboost_booster
    if _xgboost_booster is None:
        if XGBOOST_MODEL_PATH.exists():
            booster = xgb.Booster()
            booster.load_model(str(XGBOOST_MODEL_PATH))
            _xgboost_booster = BoosterWrapper(booster)
            logger.info("XGBoost Booster loaded from %s", XGBOOST_MODEL_PATH)
        else:
            logger.warning("XGBoost model not found at %s", XGBOOST_MODEL_PATH)
    return _xgboost_booster


def predict_single(
    feature_vector: dict[str, Any],
    icw_raw_score: float | None = None,
) -> EnsembleResult:
    """
    Predict risk for a single tender.

    Parameters
    ----------
    feature_vector:
        Dict of feature_name -> float. Missing features filled with 0.0.
    icw_raw_score:
        Raw ICW total_score from opentender.net (0-100). Optional.

    Returns
    -------
    EnsembleResult with final_score, risk_level, individual_scores, disagreement_flag.
    """
    tender_id: str = str(feature_vector.get("tender_id", "unknown"))
    cfg = get_config()

    # Build feature DataFrame (single row) from all incoming features
    row = {k: float(v) if isinstance(v, (int, float)) else 0.0
           for k, v in feature_vector.items()
           if k != "tender_id"}
    X_df_full = pd.DataFrame([row])

    # Filter to only the 21 training features
    X_df = _filter_features(X_df_full)

    # -- Isolation Forest score --
    iforest = _load_iforest()
    if iforest is not None:
        if_score = float(score_isolation_forest(iforest, X_df)[0])
    else:
        if_score = 0.5  # neutral fallback

    # -- XGBoost score (via BoosterWrapper for sklearn API compat) --
    booster = _load_xgboost()
    if booster is not None:
        X_np = X_df.fillna(0.0).to_numpy(dtype=np.float32)
        probs = booster.predict_proba(X_np)[0]  # (n_classes,)
        # High-risk score = P(class 2: Risiko Tinggi) + P(class 3: Risiko Kritis)
        xgb_score = float(probs[2] + probs[3]) if len(probs) >= 4 else float(probs[-1])
    else:
        xgb_score = 0.5  # neutral fallback

    # -- ICW weak label score --
    icw_norm = normalize_icw_score(icw_raw_score)

    # -- Ensemble --
    result = compute_ensemble(
        tender_id=tender_id,
        iforest_score=if_score,
        xgboost_score=xgb_score,
        icw_score=icw_norm,
    )

    logger.debug(
        "predict_single: tender=%s score=%.4f risk=%s disagreement=%s",
        tender_id, result.final_score, result.risk_level, result.disagreement_flag,
    )
    return result
