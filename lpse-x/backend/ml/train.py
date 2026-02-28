"""
LPSE-X Training Pipeline
==========================
Orchestrates full model training:
  1. Load features from SQLite (features table) or Parquet
  2. Apply temporal split (2018-2021 train / 2022 val / 2023-2024 test)
  3. Build ICW weak labels for supervision
  4. Fit Isolation Forest on train set
  5. Fit XGBoost with Optuna on train set, evaluate on val set
  6. Evaluate ensemble on test set, log metrics
  7. Save models to models/ directory

Run: python -m backend.ml.train
"""
from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score

from backend.config.runtime import get_config
from backend.ml.ensemble import batch_ensemble
from backend.ml.icw_weak_labels import build_weak_label_targets, extract_icw_weak_labels
from backend.ml.isolation_forest import fit_isolation_forest, score_isolation_forest
from backend.ml.temporal_split import temporal_split
from backend.ml.xgboost_model import RANDOM_SEED, fit_xgboost, predict_xgboost, score_to_label

logger = logging.getLogger(__name__)


def _detect_feature_cols(df: pd.DataFrame) -> list[str]:
    """Return numeric feature columns (exclude metadata columns)."""
    exclude = {
        "tender_id", "year", "temporal_split", "icw_total_score",
        "icw_normalized", "icw_label", "computed_at", "feature_json",
        "source", "date_published", "date_awarded",
    }
    return [
        c for c in df.columns
        if c not in exclude and pd.api.types.is_numeric_dtype(df[c])
    ]


def load_feature_dataframe(source: str | Path | None = None) -> pd.DataFrame:
    """Load feature DataFrame from SQLite or Parquet."""
    cfg = get_config()
    if source is None:
        db_path = Path(cfg.custom_params.get("database_path", "data/lpse_x.db"))
        source = db_path

    source_path = Path(source)
    if source_path.suffix == ".parquet":
        logger.info("Loading features from Parquet: %s", source_path)
        return pd.read_parquet(source_path)

    import sqlite3
    import json as json_lib
    logger.info("Loading features from SQLite: %s", source_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Database not found: {source_path}")

    conn = sqlite3.connect(str(source_path))
    rows = conn.execute(
        "SELECT tender_id, temporal_split, icw_total_score, feature_json FROM features"
    ).fetchall()
    conn.close()

    records: list[dict[str, Any]] = []
    for tender_id, split_tag, icw_score, feature_json_str in rows:
        try:
            feats: dict[str, Any] = json_lib.loads(feature_json_str)
        except Exception:
            feats = {}
        feats["tender_id"] = tender_id
        feats["temporal_split"] = split_tag
        feats["icw_total_score"] = icw_score
        records.append(feats)

    df = pd.DataFrame(records)
    logger.info("Loaded %d feature rows from SQLite", len(df))
    return df


def run_training_pipeline(
    source: str | Path | None = None,
    n_trials: int | None = None,
    models_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Full training pipeline. Returns metrics dict.

    Parameters
    ----------
    source:
        Feature data source (Parquet path or SQLite path).
    n_trials:
        Optuna trials for XGBoost (defaults to custom_params.xgb_n_trials=20).
    models_dir:
        Where to save trained models (default: models/).
    """
    if models_dir is None:
        models_dir = Path("models")
    models_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=== LPSE-X Training Pipeline START ===")
    logger.info("Seed=%d logged for reproducibility.", RANDOM_SEED)

    # Step 1: Load features
    df = load_feature_dataframe(source)
    if len(df) == 0:
        raise ValueError("Feature DataFrame is empty -- cannot train.")

    # Step 2: Temporal split
    if "temporal_split" in df.columns:
        train_df = df[df["temporal_split"] == "train"].copy()
        val_df = df[df["temporal_split"] == "val"].copy()
        test_df = df[df["temporal_split"] == "test"].copy()
    elif "year" in df.columns:
        train_df, val_df, test_df = temporal_split(df)
    else:
        logger.warning("No year or temporal_split column -- using all data as train.")
        train_df = df.copy()
        val_df = pd.DataFrame(columns=df.columns)
        test_df = pd.DataFrame(columns=df.columns)

    logger.info("Split: train=%d, val=%d, test=%d", len(train_df), len(val_df), len(test_df))

    # Step 3: Detect feature columns
    feature_cols = _detect_feature_cols(train_df)
    if not feature_cols:
        raise ValueError("No numeric feature columns detected.")
    logger.info("Feature columns: %d", len(feature_cols))

    X_train = train_df[feature_cols]
    X_test = test_df[feature_cols] if len(test_df) > 0 else pd.DataFrame(columns=feature_cols)

    # Step 4: Build weak labels from ICW
    y_train_icw = build_weak_label_targets(train_df)
    icw_test = extract_icw_weak_labels(test_df) if len(test_df) > 0 else pd.Series(dtype=float)

    # Step 5: Fit Isolation Forest
    logger.info("--- Fitting Isolation Forest ---")
    iforest = fit_isolation_forest(X_train)
    with open(models_dir / "iforest.pkl", "wb") as f:
        pickle.dump(iforest, f)
    logger.info("IsolationForest saved to %s/iforest.pkl", models_dir)

    # Step 6: Fit XGBoost with Optuna
    logger.info("--- Fitting XGBoost with Optuna ---")
    xgb_model, best_params = fit_xgboost(
        X_train=X_train,
        y_train=y_train_icw,
        n_trials=n_trials,
        best_params_path=models_dir / "xgb_best_params.json",
    )
    xgb_model.save_model(str(models_dir / "xgboost.ubj"))
    logger.info("XGBoost saved to %s/xgboost.ubj", models_dir)

    # Step 7: Evaluate ensemble on test set
    metrics: dict[str, Any] = {
        "train_size": len(train_df),
        "val_size": len(val_df),
        "test_size": len(test_df),
        "n_features": len(feature_cols),
        "xgb_best_params": best_params,
        "seed": RANDOM_SEED,
    }

    if len(X_test) > 0:
        if_scores_test = score_isolation_forest(iforest, X_test)
        _, xgb_probs_test = predict_xgboost(xgb_model, X_test)
        xgb_high_risk = xgb_probs_test[:, 2] + xgb_probs_test[:, 3]
        icw_arr = icw_test.to_numpy(dtype=float)

        results = batch_ensemble(
            tender_ids=[str(i) for i in range(len(X_test))],
            iforest_scores=if_scores_test,
            xgboost_scores=xgb_high_risk,
            icw_scores=icw_arr,
        )
        y_pred = [score_to_label(r.final_score) for r in results]
        y_true = build_weak_label_targets(test_df).tolist()

        if len(set(y_true)) > 1:
            f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
            prec = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
            rec = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
            metrics.update({
                "f1_macro": round(f1, 4),
                "precision_macro": round(prec, 4),
                "recall_macro": round(rec, 4),
            })
            logger.info("Test metrics: F1=%.4f Prec=%.4f Rec=%.4f", f1, prec, rec)
        else:
            metrics["f1_macro"] = 0.0
            logger.warning("Test set single-class -- F1 not meaningful.")
    else:
        metrics["f1_macro"] = 0.0

    with open(models_dir / "training_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    logger.info("Training metrics saved. Pipeline COMPLETE.")
    return metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    result = run_training_pipeline()
    print(json.dumps(result, indent=2))
