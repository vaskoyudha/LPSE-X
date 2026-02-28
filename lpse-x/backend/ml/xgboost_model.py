"""
LPSE-X XGBoost Classifier
===========================
Supervised 4-class risk classifier with:
  - SMOTE oversampling for class imbalance
  - Optuna hyperparameter tuning (fast mode: n_trials=20 for demo speed)
  - Macro F1 objective
  - Temporal cross-validation

Risk level integer encoding (must match PROPOSAL exactly):
  0 = Aman             (score 0.00-0.24)
  1 = Perlu Pantauan   (score 0.25-0.49)
  2 = Risiko Tinggi    (score 0.50-0.79)
  3 = Risiko Kritis    (score 0.80-1.00)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import optuna
import xgboost as xgb
from imblearn.over_sampling import SMOTE
from sklearn.metrics import f1_score
from sklearn.model_selection import TimeSeriesSplit

from backend.config.runtime import get_config

logger = logging.getLogger(__name__)

RANDOM_SEED: int = 42
# Suppress optuna verbosity
optuna.logging.set_verbosity(optuna.logging.WARNING)

# ---------------------------------------------------------------------------
# Label mapping
# ---------------------------------------------------------------------------
RISK_SCORE_THRESHOLDS: tuple[float, float, float] = (0.25, 0.50, 0.80)

def score_to_label(score: float) -> int:
    """Convert continuous score [0,1] to 4-class label (0-3)."""
    if score < RISK_SCORE_THRESHOLDS[0]:
        return 0
    if score < RISK_SCORE_THRESHOLDS[1]:
        return 1
    if score < RISK_SCORE_THRESHOLDS[2]:
        return 2
    return 3


def label_to_risk_name(label: int) -> str:
    mapping = {0: "Aman", 1: "Perlu Pantauan", 2: "Risiko Tinggi", 3: "Risiko Kritis"}
    return mapping.get(label, "Aman")


# ---------------------------------------------------------------------------
# SMOTE
# ---------------------------------------------------------------------------
def apply_smote(
    X: np.ndarray,
    y: np.ndarray,
    seed: int = RANDOM_SEED,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Apply SMOTE oversampling. SMOTE requires >= 2 samples per class.
    If a class has < 2 samples it is left as-is.
    """
    from collections import Counter
    class_counts = Counter(y)
    min_count = min(class_counts.values())
    if min_count < 2:
        logger.warning(
            "SMOTE skipped: some class has <2 samples. Class distribution: %s",
            dict(class_counts),
        )
        return X, y

    # k_neighbors must be <= min(class_count) - 1
    k = min(5, min_count - 1)
    sm = SMOTE(random_state=seed, k_neighbors=k)
    try:
        X_res, y_res = sm.fit_resample(X, y)
        logger.info(
            "SMOTE: %d -> %d samples. New distribution: %s",
            len(y), len(y_res), dict(Counter(y_res)),
        )
        return X_res, y_res
    except Exception as exc:
        logger.warning("SMOTE failed (%s), proceeding without it.", exc)
        return X, y


# ---------------------------------------------------------------------------
# Optuna objective
# ---------------------------------------------------------------------------
def _optuna_objective(
    trial: optuna.Trial,
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_cv_splits: int = 3,
) -> float:
    """Optuna objective: maximize macro F1 via 3-fold TimeSeriesSplit."""
    params: dict[str, Any] = {
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "n_estimators": trial.suggest_int("n_estimators", 100, 500),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "use_label_encoder": False,
        "eval_metric": "mlogloss",
        "objective": "multi:softprob",
        "num_class": 4,
        "random_state": RANDOM_SEED,
        "n_jobs": -1,
        "verbosity": 0,
    }

    tscv = TimeSeriesSplit(n_splits=n_cv_splits)
    f1_scores: list[float] = []
    for tr_idx, vl_idx in tscv.split(X_train):
        X_tr, X_vl = X_train[tr_idx], X_train[vl_idx]
        y_tr, y_vl = y_train[tr_idx], y_train[vl_idx]
        X_tr_sm, y_tr_sm = apply_smote(X_tr, y_tr, seed=RANDOM_SEED)
        clf = xgb.XGBClassifier(**params)
        clf.fit(X_tr_sm, y_tr_sm, verbose=False)
        y_pred = clf.predict(X_vl)
        f1_scores.append(float(f1_score(y_vl, y_pred, average="macro", zero_division=0)))

    return float(np.mean(f1_scores))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def fit_xgboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    n_trials: int | None = None,
    best_params_path: Path | None = None,
) -> tuple[xgb.XGBClassifier, dict[str, Any]]:
    """
    Fit XGBoost with Optuna hyperparameter search + SMOTE.

    Parameters
    ----------
    X_train:
        Feature DataFrame (train split only).
    y_train:
        Integer labels 0-3.
    n_trials:
        Optuna trials. Defaults to custom_params.xgb_n_trials (20 for demo speed).
    best_params_path:
        Where to save best params JSON. Defaults to models/xgb_best_params.json.

    Returns
    -------
    (fitted XGBClassifier, best_params dict)
    """
    cfg = get_config()
    if n_trials is None:
        n_trials = int(cfg.custom_params.get("xgb_n_trials", 20))

    logger.info(
        "XGBoost Optuna tuning: n_trials=%d, seed=%d",
        n_trials, RANDOM_SEED,
    )

    X_np = X_train.fillna(0.0).to_numpy(dtype=float)
    y_np = y_train.to_numpy(dtype=int)

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=RANDOM_SEED),
    )
    study.optimize(
        lambda trial: _optuna_objective(trial, X_np, y_np),
        n_trials=n_trials,
        show_progress_bar=False,
    )

    best = study.best_params
    logger.info("Best XGBoost params (F1=%.4f): %s", study.best_value, best)

    # Retrain on full training set with SMOTE using best params
    best_full: dict[str, Any] = {
        **best,
        "use_label_encoder": False,
        "eval_metric": "mlogloss",
        "objective": "multi:softprob",
        "num_class": 4,
        "random_state": RANDOM_SEED,
        "n_jobs": -1,
        "verbosity": 0,
    }
    X_sm, y_sm = apply_smote(X_np, y_np)
    final_model = xgb.XGBClassifier(**best_full)
    final_model.fit(X_sm, y_sm, verbose=False)

    # Persist best params
    if best_params_path is None:
        best_params_path = Path("models") / "xgb_best_params.json"
    best_params_path.parent.mkdir(parents=True, exist_ok=True)
    with open(best_params_path, "w", encoding="utf-8") as f:
        json.dump(best, f, indent=2)
    logger.info("Best params saved to %s", best_params_path)

    return final_model, best


def predict_xgboost(
    model: xgb.XGBClassifier,
    X: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Predict risk labels and probabilities.

    Returns
    -------
    (predicted_labels, predicted_probabilities)
    predicted_labels: int array shape (n,) with values 0-3
    predicted_probabilities: float array shape (n, 4) softmax probs per class
    """
    X_np = X.fillna(0.0).to_numpy(dtype=float)
    labels: np.ndarray = model.predict(X_np)
    probs: np.ndarray = model.predict_proba(X_np)
    return labels, probs
