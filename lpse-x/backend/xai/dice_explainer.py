"""
LPSE-X DiCE Counterfactual Explainer
======================================
Layer 2 of the Oracle Sandwich: What-If Scenarios.

Uses dice-ml to generate counterfactual explanations — showing which features
a vendor/tender would need to change to move from high-risk to low-risk.

Design:
  - Synchronous `generate_counterfactuals()` for direct use
  - Async `async_generate_counterfactuals()` with hard 10-second timeout
  - On timeout → falls back to nearest cached template (cosine similarity)
  - Template cache pre-built at startup via DiceCacheManager

Feature contract:
  - Works with any subset of continuous features from the trained model
  - Feature names read from the XGBoost model's feature_names_in_ attribute
    or passed explicitly — never hardcoded

Performance SLA:
  - Timeout: 10s (overridable via runtime_config.yaml custom_params xai_timeout_dice)
  - Cache fallback: < 50ms

References:
  - UPGRADE 3 lines 137-148 — Oracle Sandwich Layer 2
  - DEEP_RESEARCH_SYNTHESIS.md lines 86-127 — DiCE positioning
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Default timeout for DiCE generation (seconds) — overridable via runtime config
DEFAULT_DICE_TIMEOUT = 10.0

# Number of counterfactuals per request (max)
MAX_COUNTERFACTUALS = 5

# Default desired class (integer label for "Aman" / lowest risk)
DEFAULT_DESIRED_CLASS = 0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CounterfactualResult:
    """
    DiCE counterfactual explanation result for a single tender.

    Returns actionable recommendations: which features to change
    to move from high-risk to low-risk.
    """
    tender_id: str
    original: dict[str, Any]                      # original feature values
    counterfactuals: list[dict[str, Any]]          # list of CF dicts, each with:
                                                    #   features: dict[str, float]
                                                    #   changes:  list[{feature, from, to, direction}]
                                                    #   risk_score: int (predicted class)
    generation_time_ms: float
    from_cache: bool = False                       # True if result came from template cache
    error: str | None = None                       # non-None if explainer failed gracefully


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_changes(
    original: dict[str, Any],
    counterfactual_row: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Compute the feature changes between original and counterfactual row.

    Returns list of dicts with keys: feature, from, to, direction, delta.
    Only features that actually changed (|delta| > 1e-6) are included.
    """
    changes: list[dict[str, Any]] = []
    for feat, orig_val in original.items():
        cf_val = counterfactual_row.get(feat, orig_val)
        try:
            orig_f = float(orig_val)
            cf_f = float(cf_val)
            delta = cf_f - orig_f
            if abs(delta) > 1e-6:
                changes.append({
                    "feature": feat,
                    "from": round(orig_f, 6),
                    "to": round(cf_f, 6),
                    "direction": "increase" if delta > 0 else "decrease",
                    "delta": round(delta, 6),
                })
        except (TypeError, ValueError):
            # categorical / non-numeric — include if different
            if str(orig_val) != str(cf_val):
                changes.append({
                    "feature": feat,
                    "from": orig_val,
                    "to": cf_val,
                    "direction": "change",
                    "delta": None,
                })
    return changes


def _load_xgboost_model(model_path: str | Path) -> Any:
    """Load XGBoost model from .ubj (native) or .pkl (pickle) path.
    NOTE: XGBoost 2.1.3 + sklearn 1.6 makes bare XGBClassifier() risky
    (property 'classes_' has no setter on unfitted estimator).
    Prefer passing ``model=`` directly to DiceExplainer.__init__ instead.
    This function is kept for production path where models are pre-trained.
    """
    import xgboost as xgb
    path = Path(model_path)
    if path.suffix in {".ubj", ".json", ".model"}:
        # Safe path: load into a properly fitted XGBClassifier skeleton
        # by using object.__new__ to bypass __init__ (avoids sklearn 1.6 issue)
        booster = xgb.Booster()
        booster.load_model(str(path))
        clf = object.__new__(xgb.XGBClassifier)
        clf.__dict__["_Booster"] = booster
        n_classes = int(booster.attr("n_classes") or 4)
        clf.__dict__["classes_"] = list(range(n_classes))
        clf.__dict__["n_classes_"] = n_classes
        if booster.feature_names:
            clf.__dict__["feature_names_in_"] = np.array(booster.feature_names)
        return clf
    else:
        import pickle
        with open(path, "rb") as f:
            return pickle.load(f)


def _get_feature_names(model: Any, explicit_names: list[str] | None) -> list[str]:
    """Return feature names: prefer explicit_names, then model attribute."""
    if explicit_names:
        return explicit_names
    if hasattr(model, "feature_names_in_"):
        return list(model.feature_names_in_)
    if hasattr(model, "get_booster"):
        booster = model.get_booster()
        if booster.feature_names:
            return list(booster.feature_names)
    raise ValueError(
        "Cannot determine feature names — pass feature_names explicitly "
        "or use a model trained with named DataFrame input."
    )


# ---------------------------------------------------------------------------
# Main explainer class
# ---------------------------------------------------------------------------

class DiceExplainer:
    """
    DiCE counterfactual explanation wrapper for LPSE-X.

    Usage:
        explainer = DiceExplainer(
            model_path="models/xgboost.ubj",
            train_df=train_data,          # DataFrame with features + outcome_col
        )
        result = explainer.generate_counterfactuals(
            input_features={"n_bidders": 1, "price_ratio": 0.98, ...},
            total_cfs=3,
            desired_class=0,              # 0 = "Aman" (lowest risk)
        )

    The async variant has a hard 10s timeout and falls back to the cache:
        result = await explainer.async_generate_counterfactuals({...})
    """

    def __init__(
        self,
        model_path: str | Path = "models/xgboost.ubj",
        model: Any = None,
        train_df: pd.DataFrame | None = None,
        feature_names: list[str] | None = None,
        outcome_col: str = "risk_label",
        cache_path: str | Path = "models/dice_cache.json",
        method: str = "genetic",
        timeout_seconds: float = DEFAULT_DICE_TIMEOUT,
    ) -> None:
        """
        Parameters
        ----------
        model_path:
            Path to the trained XGBoost model (.ubj native or .pkl).
        train_df:
            Training DataFrame used to initialize DiCE's data interface.
            Must include the outcome column.  If None, DiCE is initialized
            lazily on first call (requires train_df then).
        feature_names:
            Explicit list of continuous feature names.
            If None, inferred from model.feature_names_in_.
        outcome_col:
            Name of the outcome/label column in train_df (default: "risk_label").
        cache_path:
            Path to the template cache JSON file.
        method:
            DiCE generation method: "genetic" (default) or "random".
            Genetic produces higher-quality counterfactuals but is slightly slower.
        timeout_seconds:
            Hard timeout for async generation before falling back to cache.
        """
        import dice_ml  # type: ignore[import]

        self._model_path = Path(model_path)
        self._outcome_col = outcome_col
        self._cache_path = Path(cache_path)
        self._method = method
        self._timeout_seconds = timeout_seconds

        # Load the XGBoost model — use pre-loaded object when provided
        if model is not None:
            self._model = model
        else:
            self._model = _load_xgboost_model(model_path)

        # Resolve feature names
        self._feature_names = _get_feature_names(self._model, feature_names)

        # DiCE interfaces — initialized lazily if train_df not provided
        self._dice_exp: Any = None
        self._data_interface: Any = None

        if train_df is not None:
            self._init_dice(train_df, dice_ml)

        # Load or build template cache
        from backend.xai.dice_cache import DiceCacheManager
        self._cache_manager = DiceCacheManager(
            model_path=model_path,
            cache_path=cache_path,
            feature_names=self._feature_names,
        )
        if not self._cache_manager.is_loaded():
            logger.info("DiceExplainer: no cache found at %s — cache will be built on demand", cache_path)

    def _init_dice(self, train_df: pd.DataFrame, dice_ml: Any) -> None:
        """Initialize DiCE data + model interfaces from training DataFrame."""
        continuous = [c for c in self._feature_names if c in train_df.columns]
        self._data_interface = dice_ml.Data(
            dataframe=train_df[[*continuous, self._outcome_col]].copy(),
            continuous_features=continuous,
            outcome_name=self._outcome_col,
        )
        model_interface = dice_ml.Model(model=self._model, backend="sklearn")
        self._dice_exp = dice_ml.Dice(
            self._data_interface,
            model_interface,
            method=self._method,
        )
        logger.info(
            "DiceExplainer: initialized with %d features, method=%s",
            len(continuous), self._method,
        )

    def _ensure_initialized(self, train_df: pd.DataFrame | None = None) -> None:
        """Lazy init: build DiCE interfaces on first use if not already done."""
        if self._dice_exp is not None:
            return
        if train_df is None:
            raise RuntimeError(
                "DiceExplainer not initialized — pass train_df to __init__ "
                "or to generate_counterfactuals()."
            )
        import dice_ml  # type: ignore[import]
        self._init_dice(train_df, dice_ml)

    def _raw_generate(
        self,
        input_features: dict[str, Any],
        total_cfs: int,
        desired_class: int,
        train_df: pd.DataFrame | None = None,
    ) -> list[dict[str, Any]]:
        """
        Synchronous DiCE generation (no timeout guard).
        Returns list of counterfactual feature dicts (including outcome column).
        """
        self._ensure_initialized(train_df)

        # Build query DataFrame
        query = pd.DataFrame([input_features])
        # Keep only features known to the data interface
        available = [c for c in self._feature_names if c in query.columns]
        query = query[available]

        cf_result = self._dice_exp.generate_counterfactuals(
            query,
            total_CFs=min(total_cfs, MAX_COUNTERFACTUALS),
            desired_class=desired_class,
            verbose=False,
        )

        cf_df = cf_result.cf_examples_list[0].final_cfs_df
        if cf_df is None or len(cf_df) == 0:
            return []

        rows: list[dict[str, Any]] = []
        for _, row in cf_df.iterrows():
            rows.append(row.to_dict())
        return rows

    def generate_counterfactuals(
        self,
        input_features: dict[str, Any],
        total_cfs: int = 3,
        desired_class: int = DEFAULT_DESIRED_CLASS,
        tender_id: str = "unknown",
        train_df: pd.DataFrame | None = None,
    ) -> CounterfactualResult:
        """
        Generate counterfactual explanations synchronously (blocking).

        Parameters
        ----------
        input_features:
            Dict of feature_name → value for the tender to explain.
        total_cfs:
            Number of counterfactuals to generate (1-5).
        desired_class:
            Target risk class (0="Aman", 1="Perlu Pantauan", etc.).
        tender_id:
            Identifier for logging.
        train_df:
            Training DataFrame required if not passed at init time.

        Returns
        -------
        CounterfactualResult with original features, counterfactuals list,
        and generation timing.
        """
        t0 = time.perf_counter()
        original = {k: v for k, v in input_features.items() if k in self._feature_names}

        try:
            cf_rows = self._raw_generate(input_features, total_cfs, desired_class, train_df)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            counterfactuals = []
            for row in cf_rows:
                features = {k: v for k, v in row.items() if k != self._outcome_col}
                changes = _build_changes(original, features)
                risk_score = int(row.get(self._outcome_col, desired_class))
                counterfactuals.append({
                    "features": features,
                    "changes": changes,
                    "risk_score": risk_score,
                })

            logger.info(
                "DiCE generated %d CFs for tender %s in %.1fms",
                len(counterfactuals), tender_id, elapsed_ms,
            )
            return CounterfactualResult(
                tender_id=tender_id,
                original=original,
                counterfactuals=counterfactuals,
                generation_time_ms=round(elapsed_ms, 2),
                from_cache=False,
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            logger.error("DiCE generation failed for %s: %s", tender_id, exc)
            return CounterfactualResult(
                tender_id=tender_id,
                original=original,
                counterfactuals=[],
                generation_time_ms=round(elapsed_ms, 2),
                from_cache=False,
                error=str(exc),
            )

    async def async_generate_counterfactuals(
        self,
        input_features: dict[str, Any],
        total_cfs: int = 3,
        desired_class: int = DEFAULT_DESIRED_CLASS,
        tender_id: str = "unknown",
        train_df: pd.DataFrame | None = None,
    ) -> CounterfactualResult:
        """
        Async counterfactual generation with hard timeout.

        Runs DiCE in a thread via asyncio.to_thread() with a
        ``self._timeout_seconds`` hard timeout.

        On timeout → returns nearest cached template via DiceCacheManager.
        On cache miss → returns empty counterfactuals with error message.

        This MUST be used from the API layer to avoid blocking the event loop.
        """
        t0 = time.perf_counter()
        original = {k: v for k, v in input_features.items() if k in self._feature_names}

        try:
            cf_result = await asyncio.wait_for(
                asyncio.to_thread(
                    self._raw_generate,
                    input_features,
                    total_cfs,
                    desired_class,
                    train_df,
                ),
                timeout=self._timeout_seconds,
            )

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            counterfactuals = []
            for row in cf_result:
                features = {k: v for k, v in row.items() if k != self._outcome_col}
                changes = _build_changes(original, features)
                risk_score = int(row.get(self._outcome_col, desired_class))
                counterfactuals.append({
                    "features": features,
                    "changes": changes,
                    "risk_score": risk_score,
                })

            logger.info(
                "DiCE async: %d CFs for tender %s in %.1fms",
                len(counterfactuals), tender_id, elapsed_ms,
            )
            return CounterfactualResult(
                tender_id=tender_id,
                original=original,
                counterfactuals=counterfactuals,
                generation_time_ms=round(elapsed_ms, 2),
                from_cache=False,
            )

        except asyncio.TimeoutError:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            logger.warning(
                "DiCE timeout (%.0fs) for tender %s — falling back to cache",
                self._timeout_seconds, tender_id,
            )
            # Fallback: nearest cached template
            template = self._cache_manager.find_nearest_template(input_features)
            if template is not None:
                return CounterfactualResult(
                    tender_id=tender_id,
                    original=original,
                    counterfactuals=template.get("counterfactuals", []),
                    generation_time_ms=round(elapsed_ms, 2),
                    from_cache=True,
                )
            else:
                return CounterfactualResult(
                    tender_id=tender_id,
                    original=original,
                    counterfactuals=[],
                    generation_time_ms=round(elapsed_ms, 2),
                    from_cache=True,
                    error="DiCE timeout and no cache template available.",
                )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            logger.error("DiCE async error for %s: %s", tender_id, exc)
            return CounterfactualResult(
                tender_id=tender_id,
                original=original,
                counterfactuals=[],
                generation_time_ms=round(elapsed_ms, 2),
                from_cache=False,
                error=str(exc),
            )
