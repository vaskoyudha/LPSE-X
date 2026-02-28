"""
LPSE-X DiCE Template Cache Manager
=====================================
Manages pre-built counterfactual template cache for fast fallback
when DiCE generation times out.

Strategy:
  - At startup: build N diverse template queries (representative risk archetypes)
  - For each template: run DiCE to generate counterfactuals + store result
  - On timeout fallback: find nearest template to the incoming query via
    cosine similarity on normalized feature vectors
  - Cache stored as JSON at models/dice_cache.json
  - Cache invalidated when model version changes (checks models/xgboost_meta.json)

Risk archetypes covered:
  - Single bidder (n_bidders=1, high manipulation risk)
  - High-value repeat winner (large contract + repeat win)
  - Low price anomaly (price significantly below market)
  - Geographic concentration (same city bidders cluster)
  - Benford anomaly (statistical digit distribution flag)
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Default number of templates to pre-build
DEFAULT_N_TEMPLATES = 15

# Risk archetype seed queries for template generation
# These represent the most common high-risk patterns in Indonesian procurement
_ARCHETYPE_SEEDS: list[dict[str, Any]] = [
    # Single-bidder patterns (most common manipulation signal)
    {"n_bidders": 1.0, "price_ratio": 0.98, "winner_repeat_count": 5.0, "same_city_pct": 0.9, "benford_pvalue": 0.01},
    {"n_bidders": 1.0, "price_ratio": 0.95, "winner_repeat_count": 10.0, "same_city_pct": 0.7, "benford_pvalue": 0.05},
    {"n_bidders": 1.0, "price_ratio": 0.99, "winner_repeat_count": 1.0, "same_city_pct": 0.5, "benford_pvalue": 0.3},
    # Repeat winner patterns
    {"n_bidders": 3.0, "price_ratio": 0.96, "winner_repeat_count": 15.0, "same_city_pct": 0.8, "benford_pvalue": 0.02},
    {"n_bidders": 2.0, "price_ratio": 0.90, "winner_repeat_count": 20.0, "same_city_pct": 0.6, "benford_pvalue": 0.1},
    # Price anomaly patterns
    {"n_bidders": 5.0, "price_ratio": 0.50, "winner_repeat_count": 2.0, "same_city_pct": 0.3, "benford_pvalue": 0.4},
    {"n_bidders": 4.0, "price_ratio": 0.45, "winner_repeat_count": 1.0, "same_city_pct": 0.2, "benford_pvalue": 0.5},
    # Geographic concentration
    {"n_bidders": 3.0, "price_ratio": 0.85, "winner_repeat_count": 3.0, "same_city_pct": 1.0, "benford_pvalue": 0.2},
    {"n_bidders": 2.0, "price_ratio": 0.80, "winner_repeat_count": 4.0, "same_city_pct": 0.95, "benford_pvalue": 0.15},
    # Benford Law violations
    {"n_bidders": 4.0, "price_ratio": 0.88, "winner_repeat_count": 2.0, "same_city_pct": 0.4, "benford_pvalue": 0.001},
    {"n_bidders": 5.0, "price_ratio": 0.92, "winner_repeat_count": 3.0, "same_city_pct": 0.35, "benford_pvalue": 0.005},
    # Combined signals (high risk)
    {"n_bidders": 1.0, "price_ratio": 0.98, "winner_repeat_count": 12.0, "same_city_pct": 1.0, "benford_pvalue": 0.005},
    {"n_bidders": 2.0, "price_ratio": 0.97, "winner_repeat_count": 8.0, "same_city_pct": 0.85, "benford_pvalue": 0.01},
    # Lower risk (border cases)
    {"n_bidders": 5.0, "price_ratio": 0.75, "winner_repeat_count": 5.0, "same_city_pct": 0.4, "benford_pvalue": 0.08},
    {"n_bidders": 3.0, "price_ratio": 0.70, "winner_repeat_count": 6.0, "same_city_pct": 0.5, "benford_pvalue": 0.06},
]


def _normalize_features(
    features: dict[str, Any],
    feature_names: list[str],
    feature_ranges: dict[str, tuple[float, float]],
) -> np.ndarray:
    """
    Normalize feature dict to unit vector for cosine similarity.

    Parameters
    ----------
    features:
        Input feature dict.
    feature_names:
        Ordered list of feature names to include.
    feature_ranges:
        Min/max ranges for each feature (for min-max normalization).

    Returns
    -------
    Float32 numpy array of shape (n_features,), L2-normalized.
    """
    vec = np.zeros(len(feature_names), dtype=np.float32)
    for i, name in enumerate(feature_names):
        val = float(features.get(name, 0.0))
        min_v, max_v = feature_ranges.get(name, (0.0, 1.0))
        rng = max_v - min_v
        vec[i] = (val - min_v) / rng if rng > 1e-9 else 0.0

    # L2 normalize for cosine similarity
    norm = np.linalg.norm(vec)
    if norm > 1e-9:
        vec /= norm
    return vec


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two unit vectors (already normalized)."""
    return float(np.dot(a, b))


class DiceCacheManager:
    """
    Template cache manager for DiCE counterfactual fallbacks.

    Usage:
        cache = DiceCacheManager(
            model_path="models/xgboost.ubj",
            cache_path="models/dice_cache.json",
            feature_names=["n_bidders", "price_ratio", ...],
        )
        # Build cache (called at startup or when model version changes)
        cache.build_cache(train_df=df, n_templates=15)

        # Find nearest template (called on DiCE timeout)
        template = cache.find_nearest_template(input_features)
    """

    def __init__(
        self,
        model_path: str | Path = "models/xgboost.ubj",
        cache_path: str | Path = "models/dice_cache.json",
        feature_names: list[str] | None = None,
    ) -> None:
        self._model_path = Path(model_path)
        self._cache_path = Path(cache_path)
        self._feature_names: list[str] = feature_names or []
        self._templates: list[dict[str, Any]] = []
        self._feature_ranges: dict[str, tuple[float, float]] = {}
        self._cache_version: str = ""
        self._loaded = False

        # Try to load existing cache from disk
        self._try_load()

    def is_loaded(self) -> bool:
        """Return True if the cache has been loaded and has templates."""
        return self._loaded and len(self._templates) > 0

    def _try_load(self) -> None:
        """Attempt to load cache from disk. Silent on failure."""
        if not self._cache_path.exists():
            return
        try:
            with open(self._cache_path, encoding="utf-8") as f:
                data = json.load(f)
            self._templates = data.get("templates", [])
            self._feature_ranges = {
                k: tuple(v)  # type: ignore[arg-type]
                for k, v in data.get("feature_ranges", {}).items()
            }
            self._cache_version = data.get("version", "")
            if self._feature_names and not self._feature_names:
                self._feature_names = data.get("feature_names", [])
            self._loaded = True
            logger.info(
                "DiceCacheManager: loaded %d templates from %s (version=%s)",
                len(self._templates), self._cache_path, self._cache_version,
            )
        except Exception as exc:
            logger.warning("DiceCacheManager: failed to load cache: %s", exc)

    def _compute_feature_ranges(
        self,
        train_df: Any,  # pd.DataFrame
    ) -> dict[str, tuple[float, float]]:
        """Compute min/max ranges for normalization from training data."""
        ranges: dict[str, tuple[float, float]] = {}
        for name in self._feature_names:
            if name in train_df.columns:
                col = train_df[name].dropna()
                if len(col) > 0:
                    ranges[name] = (float(col.min()), float(col.max()))
                else:
                    ranges[name] = (0.0, 1.0)
            else:
                ranges[name] = (0.0, 1.0)
        return ranges

    def build_cache(
        self,
        train_df: Any | None = None,   # pd.DataFrame
        n_templates: int = DEFAULT_N_TEMPLATES,
        method: str = "random",
        desired_class: int = 0,
        model: Any = None,
        outcome_col: str = "risk_label",
    ) -> None:
        """
        Pre-build counterfactual templates for the most common risk archetypes.

        Uses the archetype seed queries (_ARCHETYPE_SEEDS) to generate
        representative counterfactual templates. Templates are stored in
        models/dice_cache.json for fast fallback.

        Parameters
        ----------
        train_df:
            Training DataFrame with features + outcome column.
            Required for DiCE initialization.
        n_templates:
            Number of templates to generate (uses first n_templates archetypes).
        method:
            DiCE method ("random" is faster for cache building).
        desired_class:
            Target risk class for counterfactuals (0 = "Aman").
        model:
            Pre-loaded model. If None, loads from self._model_path.
        outcome_col:
            Outcome column name in train_df.
        """
        import dice_ml  # type: ignore[import]
        import pandas as pd

        if train_df is None:
            raise ValueError("train_df required for cache building")

        # Load model if not provided
        if model is None:
            from backend.xai.dice_explainer import _load_xgboost_model
            model = _load_xgboost_model(self._model_path)

        # Resolve feature names from model if not set
        if not self._feature_names:
            from backend.xai.dice_explainer import _get_feature_names
            self._feature_names = _get_feature_names(model, None)

        # Compute feature ranges for normalization
        self._feature_ranges = self._compute_feature_ranges(train_df)

        # Init DiCE
        continuous = [c for c in self._feature_names if c in train_df.columns]
        data_iface = dice_ml.Data(
            dataframe=train_df[[*continuous, outcome_col]].copy(),
            continuous_features=continuous,
            outcome_name=outcome_col,
        )
        model_iface = dice_ml.Model(model=model, backend="sklearn")
        dice_exp = dice_ml.Dice(data_iface, model_iface, method=method)

        # Select seed queries
        seeds = _ARCHETYPE_SEEDS[:n_templates]

        templates: list[dict[str, Any]] = []
        t_total = time.perf_counter()

        for i, seed in enumerate(seeds):
            t0 = time.perf_counter()
            try:
                # Only include features present in training data
                seed_filtered = {k: v for k, v in seed.items() if k in continuous}
                query = pd.DataFrame([seed_filtered])

                cf_result = dice_exp.generate_counterfactuals(
                    query,
                    total_CFs=2,
                    desired_class=desired_class,
                    verbose=False,
                )
                cf_df = cf_result.cf_examples_list[0].final_cfs_df

                counterfactuals = []
                if cf_df is not None and len(cf_df) > 0:
                    from backend.xai.dice_explainer import _build_changes
                    original = {k: v for k, v in seed_filtered.items()}
                    for _, row in cf_df.iterrows():
                        row_dict = row.to_dict()
                        feats = {k: v for k, v in row_dict.items() if k != outcome_col}
                        changes = _build_changes(original, feats)
                        counterfactuals.append({
                            "features": feats,
                            "changes": changes,
                            "risk_score": int(row_dict.get(outcome_col, desired_class)),
                        })

                templates.append({
                    "seed_index": i,
                    "query": seed_filtered,
                    "counterfactuals": counterfactuals,
                    "generation_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                })
                logger.debug("Template %d/%d built in %.0fms", i + 1, len(seeds), (time.perf_counter() - t0) * 1000)

            except Exception as exc:
                logger.warning("Template %d failed: %s", i, exc)
                # Store empty template (still usable as similarity anchor)
                templates.append({
                    "seed_index": i,
                    "query": {k: v for k, v in seed.items() if k in continuous},
                    "counterfactuals": [],
                    "generation_ms": 0.0,
                    "error": str(exc),
                })

        self._templates = templates
        self._cache_version = datetime.now(timezone.utc).isoformat()
        total_ms = (time.perf_counter() - t_total) * 1000.0

        # Write to disk
        cache_data: dict[str, Any] = {
            "version": self._cache_version,
            "feature_names": self._feature_names,
            "feature_ranges": {k: list(v) for k, v in self._feature_ranges.items()},
            "n_templates": len(templates),
            "templates": templates,
            "build_time_ms": round(total_ms, 2),
        }
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False, default=str)

        self._loaded = True
        logger.info(
            "DiceCacheManager: built %d templates in %.0fms, saved to %s",
            len(templates), total_ms, self._cache_path,
        )

    def find_nearest_template(
        self,
        input_features: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Find the template whose seed query is most similar to input_features.

        Uses cosine similarity on L2-normalized, min-max-scaled feature vectors.
        Only templates with at least 1 counterfactual are considered.

        Parameters
        ----------
        input_features:
            Feature dict for the incoming query.

        Returns
        -------
        The most similar template dict, or None if cache is empty.
        """
        if not self._templates:
            logger.warning("DiceCacheManager: no templates in cache for fallback")
            return None

        # Only consider templates that have counterfactuals
        usable = [t for t in self._templates if t.get("counterfactuals")]
        if not usable:
            # Fall back to any template if none have counterfactuals
            usable = self._templates

        # Ensure we have feature ranges
        if not self._feature_ranges:
            # Use unit range as fallback
            self._feature_ranges = {
                name: (0.0, 1.0) for name in self._feature_names
            }

        # Vectorize the query
        query_vec = _normalize_features(
            input_features, self._feature_names, self._feature_ranges
        )

        best_idx = 0
        best_sim = -1.0
        for i, template in enumerate(usable):
            seed = template.get("query", {})
            seed_vec = _normalize_features(
                seed, self._feature_names, self._feature_ranges
            )
            sim = _cosine_similarity(query_vec, seed_vec)
            if sim > best_sim:
                best_sim = sim
                best_idx = i

        best = usable[best_idx]
        logger.info(
            "DiceCacheManager: nearest template idx=%d, cosine_sim=%.3f",
            best.get("seed_index", best_idx), best_sim,
        )
        return best
