"""
Tests for T12: DiCE Counterfactual Explainer + Template Cache
=============================================================
Tests verify:
  - CounterfactualResult structure has required keys
  - Synchronous generation returns correct number of CFs
  - Each CF has features, changes, risk_score
  - Each change has feature, from, to, direction keys
  - Async generation completes successfully
  - Async timeout triggers cache fallback (from_cache=True)
  - DiceCacheManager builds cache and writes JSON
  - find_nearest_template returns expected archetype
  - Cosine similarity selects the most similar template
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
import xgboost as xgb

# ---------------------------------------------------------------------------
# Feature contract (5 key LPSE-X features)
# ---------------------------------------------------------------------------

FEATURE_NAMES = [
    "n_bidders",
    "price_ratio",
    "winner_repeat_count",
    "same_city_pct",
    "benford_pvalue",
]
N_FEATURES = len(FEATURE_NAMES)
N_CLASSES = 4
RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_train_df(n: int = 200) -> pd.DataFrame:
    """Create synthetic training DataFrame with LPSE-X feature names."""
    data = {
        "n_bidders":           rng.integers(1, 10, size=n).astype(float),
        "price_ratio":         rng.uniform(0.4, 1.0, size=n),
        "winner_repeat_count": rng.integers(1, 20, size=n).astype(float),
        "same_city_pct":       rng.uniform(0.0, 1.0, size=n),
        "benford_pvalue":      rng.uniform(0.001, 0.5, size=n),
    }
    df = pd.DataFrame(data)
    # Ensure all 4 classes present
    labels = np.array([0, 1, 2, 3] * (n // 4), dtype=np.int32)
    df["risk_label"] = labels
    return df


@pytest.fixture(scope="module")
def trained_xgboost_and_df():
    """Train a minimal XGBoost model and return (model, train_df)."""
    train_df = _make_train_df(200)
    X = train_df[FEATURE_NAMES]
    y = train_df["risk_label"].values

    model = xgb.XGBClassifier(
        n_estimators=10,
        max_depth=3,
        objective="multi:softprob",
        num_class=N_CLASSES,
        random_state=RANDOM_SEED,
        verbosity=0,
        use_label_encoder=False,
        eval_metric="mlogloss",
    )
    model.fit(X, y)
    return model, train_df


@pytest.fixture(scope="module")
def saved_model_path(trained_xgboost_and_df, tmp_path_factory):
    """Save model to a temp directory in .ubj format and return path."""
    model, _ = trained_xgboost_and_df
    models_dir = tmp_path_factory.mktemp("models_dice")
    model_path = models_dir / "xgboost.ubj"
    model.save_model(str(model_path))
    return model_path


@pytest.fixture(scope="module")
def dice_explainer(trained_xgboost_and_df, saved_model_path, tmp_path_factory):
    """Build a DiceExplainer with known model + training data."""
    model, train_df = trained_xgboost_and_df
    cache_dir = tmp_path_factory.mktemp("dice_cache")
    cache_path = cache_dir / "dice_cache.json"

    from backend.xai.dice_explainer import DiceExplainer
    return DiceExplainer(
        model_path=saved_model_path,
        model=model,               # pass pre-loaded model to avoid sklearn 1.6 issue
        train_df=train_df,
        feature_names=FEATURE_NAMES,
        outcome_col="risk_label",
        cache_path=cache_path,
        method="random",           # faster for tests
        timeout_seconds=10.0,
    )


# ---------------------------------------------------------------------------
# High-risk sample query (single bidder, common manipulation signal)
# ---------------------------------------------------------------------------

SAMPLE_QUERY: dict[str, Any] = {
    "n_bidders": 1.0,
    "price_ratio": 0.98,
    "winner_repeat_count": 8.0,
    "same_city_pct": 0.9,
    "benford_pvalue": 0.02,
}


# ---------------------------------------------------------------------------
# T12.1 — CounterfactualResult structure
# ---------------------------------------------------------------------------

class TestCounterfactualResultStructure:
    """Verify the shape of CounterfactualResult returned by the explainer."""

    def test_result_has_required_top_level_keys(self, dice_explainer):
        result = dice_explainer.generate_counterfactuals(
            SAMPLE_QUERY, total_cfs=2, tender_id="test-001"
        )
        assert hasattr(result, "tender_id"),            "Missing: tender_id"
        assert hasattr(result, "original"),             "Missing: original"
        assert hasattr(result, "counterfactuals"),      "Missing: counterfactuals"
        assert hasattr(result, "generation_time_ms"),   "Missing: generation_time_ms"
        assert hasattr(result, "from_cache"),           "Missing: from_cache"

    def test_tender_id_preserved(self, dice_explainer):
        result = dice_explainer.generate_counterfactuals(
            SAMPLE_QUERY, total_cfs=1, tender_id="PKT-2024-0001"
        )
        assert result.tender_id == "PKT-2024-0001"

    def test_original_matches_input_features(self, dice_explainer):
        result = dice_explainer.generate_counterfactuals(
            SAMPLE_QUERY, total_cfs=1, tender_id="test-original"
        )
        for feat in FEATURE_NAMES:
            assert feat in result.original, f"Feature {feat} missing from original"

    def test_generation_time_ms_is_positive(self, dice_explainer):
        result = dice_explainer.generate_counterfactuals(
            SAMPLE_QUERY, total_cfs=1, tender_id="test-timing"
        )
        assert result.generation_time_ms >= 0.0

    def test_from_cache_is_false_for_sync(self, dice_explainer):
        result = dice_explainer.generate_counterfactuals(
            SAMPLE_QUERY, total_cfs=1, tender_id="test-cache-flag"
        )
        assert result.from_cache is False


# ---------------------------------------------------------------------------
# T12.2 — Synchronous generation
# ---------------------------------------------------------------------------

class TestSyncGeneration:
    """Verify synchronous counterfactual generation produces valid output."""

    def test_returns_requested_cfs_count(self, dice_explainer):
        result = dice_explainer.generate_counterfactuals(
            SAMPLE_QUERY, total_cfs=2, tender_id="test-count"
        )
        # DiCE may return up to total_cfs; must return at least 1
        assert len(result.counterfactuals) >= 1

    def test_cfs_count_does_not_exceed_max(self, dice_explainer):
        result = dice_explainer.generate_counterfactuals(
            SAMPLE_QUERY, total_cfs=5, tender_id="test-max"
        )
        from backend.xai.dice_explainer import MAX_COUNTERFACTUALS
        assert len(result.counterfactuals) <= MAX_COUNTERFACTUALS

    def test_error_is_none_on_success(self, dice_explainer):
        result = dice_explainer.generate_counterfactuals(
            SAMPLE_QUERY, total_cfs=1, tender_id="test-no-error"
        )
        assert result.error is None

    def test_graceful_degradation_on_bad_input(self, dice_explainer):
        """When all feature values are NaN/garbage, should return empty CFs, not crash."""
        bad_query = {k: float("nan") for k in FEATURE_NAMES}
        result = dice_explainer.generate_counterfactuals(
            bad_query, total_cfs=1, tender_id="test-bad"
        )
        # Must not raise — either empty CFs or error string
        assert result is not None
        assert isinstance(result.from_cache, bool)


# ---------------------------------------------------------------------------
# T12.3 — Counterfactual item structure
# ---------------------------------------------------------------------------

class TestCounterfactualItemStructure:
    """Each CF dict must have features, changes, and risk_score."""

    @pytest.fixture(scope="class")
    def single_cf_result(self, dice_explainer):
        return dice_explainer.generate_counterfactuals(
            SAMPLE_QUERY, total_cfs=2, tender_id="test-cf-items"
        )

    def test_each_cf_has_features_key(self, single_cf_result):
        assert len(single_cf_result.counterfactuals) >= 1
        for cf in single_cf_result.counterfactuals:
            assert "features" in cf, f"CF missing 'features' key: {cf}"

    def test_each_cf_has_changes_key(self, single_cf_result):
        for cf in single_cf_result.counterfactuals:
            assert "changes" in cf, f"CF missing 'changes' key: {cf}"

    def test_each_cf_has_risk_score_key(self, single_cf_result):
        for cf in single_cf_result.counterfactuals:
            assert "risk_score" in cf, f"CF missing 'risk_score' key: {cf}"

    def test_risk_score_is_integer(self, single_cf_result):
        for cf in single_cf_result.counterfactuals:
            assert isinstance(cf["risk_score"], int), \
                f"risk_score must be int, got {type(cf['risk_score'])}"

    def test_features_dict_is_non_empty(self, single_cf_result):
        for cf in single_cf_result.counterfactuals:
            assert len(cf["features"]) > 0, "features dict must be non-empty"

    def test_changes_is_list(self, single_cf_result):
        for cf in single_cf_result.counterfactuals:
            assert isinstance(cf["changes"], list), "changes must be a list"


# ---------------------------------------------------------------------------
# T12.4 — Individual change item structure
# ---------------------------------------------------------------------------

class TestChangeItemStructure:
    """Each change item must have feature, from, to, direction keys."""

    @pytest.fixture(scope="class")
    def cf_with_changes(self, dice_explainer):
        result = dice_explainer.generate_counterfactuals(
            SAMPLE_QUERY, total_cfs=3, tender_id="test-change-items"
        )
        # Collect all changes from all CFs
        all_changes = []
        for cf in result.counterfactuals:
            all_changes.extend(cf["changes"])
        return all_changes

    def test_changes_have_feature_key(self, cf_with_changes):
        if not cf_with_changes:
            pytest.skip("No changes generated (features may be identical)")
        for change in cf_with_changes:
            assert "feature" in change, f"change missing 'feature': {change}"

    def test_changes_have_from_key(self, cf_with_changes):
        if not cf_with_changes:
            pytest.skip("No changes generated")
        for change in cf_with_changes:
            assert "from" in change, f"change missing 'from': {change}"

    def test_changes_have_to_key(self, cf_with_changes):
        if not cf_with_changes:
            pytest.skip("No changes generated")
        for change in cf_with_changes:
            assert "to" in change, f"change missing 'to': {change}"

    def test_changes_have_direction_key(self, cf_with_changes):
        if not cf_with_changes:
            pytest.skip("No changes generated")
        for change in cf_with_changes:
            assert "direction" in change, f"change missing 'direction': {change}"

    def test_direction_is_valid_value(self, cf_with_changes):
        if not cf_with_changes:
            pytest.skip("No changes generated")
        valid = {"increase", "decrease", "change"}
        for change in cf_with_changes:
            assert change["direction"] in valid, \
                f"Invalid direction '{change['direction']}' — must be one of {valid}"


# ---------------------------------------------------------------------------
# T12.5 — Async generation
# ---------------------------------------------------------------------------

class TestAsyncGeneration:
    """Verify async variant completes and returns valid result."""

    def test_async_generate_returns_result(self, dice_explainer):
        async def _run():
            return await dice_explainer.async_generate_counterfactuals(
                SAMPLE_QUERY, total_cfs=2, tender_id="test-async"
            )

        result = asyncio.get_event_loop().run_until_complete(_run())
        assert result is not None
        assert hasattr(result, "counterfactuals")
        assert isinstance(result.from_cache, bool)

    def test_async_returns_counterfactual_result_type(self, dice_explainer):
        from backend.xai.dice_explainer import CounterfactualResult

        async def _run():
            return await dice_explainer.async_generate_counterfactuals(
                SAMPLE_QUERY, total_cfs=1, tender_id="test-async-type"
            )

        result = asyncio.get_event_loop().run_until_complete(_run())
        assert isinstance(result, CounterfactualResult)

    def test_async_timeout_triggers_cache_fallback(self, dice_explainer, tmp_path):
        """
        Mock _raw_generate to sleep 15s → async timeout → from_cache=True fallback.
        """
        import asyncio

        # First, pre-load cache with mock templates so fallback has data
        dice_explainer._cache_manager._templates = [
            {
                "seed_index": 0,
                "query": SAMPLE_QUERY,
                "counterfactuals": [
                    {
                        "features": {k: v * 0.8 for k, v in SAMPLE_QUERY.items()},
                        "changes": [
                            {"feature": "n_bidders", "from": 1.0, "to": 3.0,
                             "direction": "increase", "delta": 2.0}
                        ],
                        "risk_score": 0,
                    }
                ],
                "generation_ms": 0.0,
            }
        ]
        dice_explainer._cache_manager._feature_ranges = {
            k: (0.0, 20.0) for k in FEATURE_NAMES
        }
        dice_explainer._cache_manager._loaded = True

        def _slow_generate(*args, **kwargs):
            time.sleep(15)  # exceeds any reasonable timeout
            return []

        # Set very short timeout for the test
        original_timeout = dice_explainer._timeout_seconds
        dice_explainer._timeout_seconds = 0.5

        try:
            with patch.object(dice_explainer, "_raw_generate", side_effect=_slow_generate):
                async def _run():
                    return await dice_explainer.async_generate_counterfactuals(
                        SAMPLE_QUERY, total_cfs=1, tender_id="test-timeout"
                    )

                result = asyncio.get_event_loop().run_until_complete(_run())

            assert result.from_cache is True, \
                "Expected from_cache=True after timeout fallback"
        finally:
            dice_explainer._timeout_seconds = original_timeout


# ---------------------------------------------------------------------------
# T12.6 — DiceCacheManager
# ---------------------------------------------------------------------------

class TestDiceCacheManager:
    """Verify cache manager builds, persists, and retrieves templates."""

    @pytest.fixture(scope="class")
    def cache_manager_built(self, trained_xgboost_and_df, saved_model_path, tmp_path_factory):
        """Build a real cache and return (manager, cache_path)."""
        model, train_df = trained_xgboost_and_df
        cache_dir = tmp_path_factory.mktemp("cache_build")
        cache_path = cache_dir / "dice_cache.json"

        from backend.xai.dice_cache import DiceCacheManager
        mgr = DiceCacheManager(
            model_path=saved_model_path,
            cache_path=cache_path,
            feature_names=FEATURE_NAMES,
        )
        # Build with only 3 templates for speed
        mgr.build_cache(
            train_df=train_df,
            n_templates=3,
            method="random",
            desired_class=0,
            model=model,
            outcome_col="risk_label",
        )
        return mgr, cache_path

    def test_cache_json_file_created(self, cache_manager_built):
        _, cache_path = cache_manager_built
        assert cache_path.exists(), "Cache JSON file was not created"

    def test_cache_json_has_templates_key(self, cache_manager_built):
        _, cache_path = cache_manager_built
        with open(cache_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "templates" in data

    def test_cache_json_n_templates_matches(self, cache_manager_built):
        mgr, cache_path = cache_manager_built
        with open(cache_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["n_templates"] == 3

    def test_is_loaded_true_after_build(self, cache_manager_built):
        mgr, _ = cache_manager_built
        assert mgr.is_loaded() is True

    def test_templates_list_populated(self, cache_manager_built):
        mgr, _ = cache_manager_built
        assert len(mgr._templates) == 3

    def test_each_template_has_query(self, cache_manager_built):
        mgr, _ = cache_manager_built
        for t in mgr._templates:
            assert "query" in t, f"Template missing 'query': {t}"

    def test_each_template_has_seed_index(self, cache_manager_built):
        mgr, _ = cache_manager_built
        for t in mgr._templates:
            assert "seed_index" in t, f"Template missing 'seed_index': {t}"


# ---------------------------------------------------------------------------
# T12.7 — find_nearest_template
# ---------------------------------------------------------------------------

class TestFindNearestTemplate:
    """Verify cosine-similarity template lookup returns sensible results."""

    @pytest.fixture(scope="class")
    def seeded_cache(self, tmp_path_factory):
        """Create a cache with 3 known templates for deterministic testing."""
        from backend.xai.dice_cache import DiceCacheManager

        cache_dir = tmp_path_factory.mktemp("seeded_cache")
        cache_path = cache_dir / "seed_cache.json"

        templates = [
            {
                "seed_index": 0,
                # Single bidder — n_bidders=1
                "query": {"n_bidders": 1.0, "price_ratio": 0.98,
                          "winner_repeat_count": 5.0, "same_city_pct": 0.9, "benford_pvalue": 0.01},
                "counterfactuals": [{"features": {}, "changes": [], "risk_score": 0}],
                "generation_ms": 0.0,
            },
            {
                "seed_index": 1,
                # Many bidders — n_bidders=8
                "query": {"n_bidders": 8.0, "price_ratio": 0.70,
                          "winner_repeat_count": 1.0, "same_city_pct": 0.2, "benford_pvalue": 0.4},
                "counterfactuals": [{"features": {}, "changes": [], "risk_score": 0}],
                "generation_ms": 0.0,
            },
            {
                "seed_index": 2,
                # Geographic concentration
                "query": {"n_bidders": 3.0, "price_ratio": 0.85,
                          "winner_repeat_count": 3.0, "same_city_pct": 1.0, "benford_pvalue": 0.2},
                "counterfactuals": [{"features": {}, "changes": [], "risk_score": 0}],
                "generation_ms": 0.0,
            },
        ]
        feature_ranges = {
            "n_bidders": (1.0, 10.0),
            "price_ratio": (0.4, 1.0),
            "winner_repeat_count": (1.0, 20.0),
            "same_city_pct": (0.0, 1.0),
            "benford_pvalue": (0.001, 0.5),
        }

        mgr = DiceCacheManager(
            cache_path=cache_path,
            feature_names=FEATURE_NAMES,
        )
        mgr._templates = templates
        mgr._feature_ranges = feature_ranges
        mgr._loaded = True
        return mgr

    def test_find_nearest_returns_dict(self, seeded_cache):
        result = seeded_cache.find_nearest_template(SAMPLE_QUERY)
        assert isinstance(result, dict)

    def test_find_nearest_returns_not_none(self, seeded_cache):
        result = seeded_cache.find_nearest_template(SAMPLE_QUERY)
        assert result is not None

    def test_single_bidder_query_matches_single_bidder_template(self, seeded_cache):
        """Query with n_bidders=1 should match template[0] (single-bidder seed)."""
        query = {
            "n_bidders": 1.0,
            "price_ratio": 0.99,
            "winner_repeat_count": 6.0,
            "same_city_pct": 0.85,
            "benford_pvalue": 0.015,
        }
        result = seeded_cache.find_nearest_template(query)
        assert result is not None
        # Should be template 0 (n_bidders=1 is most similar)
        assert result.get("seed_index") == 0, \
            f"Expected seed_index=0 (single bidder), got {result.get('seed_index')}"

    def test_many_bidders_query_matches_many_bidders_template(self, seeded_cache):
        """Query with n_bidders=9 should match template[1] (many-bidder seed)."""
        query = {
            "n_bidders": 9.0,
            "price_ratio": 0.68,
            "winner_repeat_count": 1.0,
            "same_city_pct": 0.15,
            "benford_pvalue": 0.45,
        }
        result = seeded_cache.find_nearest_template(query)
        assert result is not None
        assert result.get("seed_index") == 1, \
            f"Expected seed_index=1 (many bidders), got {result.get('seed_index')}"

    def test_returns_none_when_no_templates(self):
        from backend.xai.dice_cache import DiceCacheManager
        empty_mgr = DiceCacheManager(feature_names=FEATURE_NAMES)
        empty_mgr._templates = []
        result = empty_mgr.find_nearest_template(SAMPLE_QUERY)
        assert result is None

    def test_nearest_template_has_counterfactuals_key(self, seeded_cache):
        result = seeded_cache.find_nearest_template(SAMPLE_QUERY)
        assert "counterfactuals" in result


# ---------------------------------------------------------------------------
# T12.8 — _build_changes helper unit tests
# ---------------------------------------------------------------------------

class TestBuildChangesHelper:
    """Unit tests for the internal _build_changes function."""

    def test_increase_direction_detected(self):
        from backend.xai.dice_explainer import _build_changes
        orig = {"n_bidders": 1.0}
        cf = {"n_bidders": 3.0}
        changes = _build_changes(orig, cf)
        assert len(changes) == 1
        assert changes[0]["direction"] == "increase"
        assert changes[0]["delta"] == pytest.approx(2.0)

    def test_decrease_direction_detected(self):
        from backend.xai.dice_explainer import _build_changes
        orig = {"price_ratio": 0.98}
        cf = {"price_ratio": 0.70}
        changes = _build_changes(orig, cf)
        assert len(changes) == 1
        assert changes[0]["direction"] == "decrease"
        assert changes[0]["delta"] == pytest.approx(-0.28, abs=1e-4)

    def test_no_change_returns_empty(self):
        from backend.xai.dice_explainer import _build_changes
        orig = {"n_bidders": 5.0}
        cf = {"n_bidders": 5.0}
        changes = _build_changes(orig, cf)
        assert len(changes) == 0

    def test_tiny_delta_filtered(self):
        from backend.xai.dice_explainer import _build_changes
        orig = {"price_ratio": 0.98}
        cf = {"price_ratio": 0.98 + 1e-8}  # below 1e-6 threshold
        changes = _build_changes(orig, cf)
        assert len(changes) == 0

    def test_multiple_feature_changes(self):
        from backend.xai.dice_explainer import _build_changes
        orig = {"n_bidders": 1.0, "price_ratio": 0.95, "same_city_pct": 0.9}
        cf   = {"n_bidders": 4.0, "price_ratio": 0.95, "same_city_pct": 0.3}
        changes = _build_changes(orig, cf)
        # Only 2 features changed
        assert len(changes) == 2
        feat_names = {c["feature"] for c in changes}
        assert feat_names == {"n_bidders", "same_city_pct"}

    def test_from_and_to_values_rounded(self):
        from backend.xai.dice_explainer import _build_changes
        orig = {"benford_pvalue": 0.011111111}
        cf   = {"benford_pvalue": 0.200000001}
        changes = _build_changes(orig, cf)
        assert len(changes) == 1
        # Values are rounded to 6 decimal places
        assert changes[0]["from"] == pytest.approx(0.011111, abs=1e-5)
        assert changes[0]["to"]   == pytest.approx(0.2, abs=1e-5)


# ---------------------------------------------------------------------------
# T12.9 — __init__.py exports
# ---------------------------------------------------------------------------

class TestPackageExports:
    """Verify all DiCE classes are exported from backend.xai."""

    def test_counterfactual_result_exported(self):
        from backend.xai import CounterfactualResult  # type: ignore[attr-defined]
        assert CounterfactualResult is not None

    def test_dice_explainer_exported(self):
        from backend.xai import DiceExplainer  # type: ignore[attr-defined]
        assert DiceExplainer is not None

    def test_dice_cache_manager_exported(self):
        from backend.xai import DiceCacheManager  # type: ignore[attr-defined]
        assert DiceCacheManager is not None
