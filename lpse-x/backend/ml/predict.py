"""
LPSE-X Single-Tender Prediction
==================================
Loads pre-trained models and returns an EnsembleResult for one feature vector.
Called by the FastAPI inference endpoint (T14).

Models loaded lazily (once) from models/ directory.
NEVER retrain here -- inference-only.
"""
from __future__ import annotations

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

_iforest_model: IsolationForest | None = None
_xgboost_model: xgb.XGBClassifier | None = None

IFOREST_MODEL_PATH = Path("models") / "iforest.pkl"
XGBOOST_MODEL_PATH = Path("models") / "xgboost.ubj"


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


def _load_xgboost() -> xgb.XGBClassifier | None:
    global _xgboost_model
    if _xgboost_model is None:
        if XGBOOST_MODEL_PATH.exists():
            _xgboost_model = xgb.XGBClassifier()
            _xgboost_model.load_model(str(XGBOOST_MODEL_PATH))
            logger.info("XGBoost loaded from %s", XGBOOST_MODEL_PATH)
        else:
            logger.warning("XGBoost model not found at %s", XGBOOST_MODEL_PATH)
    return _xgboost_model


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

    # Build feature DataFrame (single row)
    row = {k: float(v) if isinstance(v, (int, float)) else 0.0
           for k, v in feature_vector.items()
           if k != "tender_id"}
    X_df = pd.DataFrame([row])

    # -- Isolation Forest score --
    iforest = _load_iforest()
    if iforest is not None:
        if_score = float(score_isolation_forest(iforest, X_df)[0])
    else:
        if_score = 0.5  # neutral fallback

    # -- XGBoost score --
    xgb_model = _load_xgboost()
    if xgb_model is not None:
        X_np = X_df.fillna(0.0).to_numpy(dtype=float)
        probs: np.ndarray = xgb_model.predict_proba(X_np)[0]
        # High-risk score = probability of class 2 (Risiko Tinggi) + class 3 (Risiko Kritis)
        xgb_score = float(probs[2] + probs[3])
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
