"""
LPSE-X Tri-Method AI Test Suite
=================================
Tests for:
  - temporal_split.py       (train/val/test partitioning)
  - isolation_forest.py     (unsupervised anomaly detection)
  - icw_weak_labels.py      (ICW score normalization + labelling)
  - ensemble.py             (weighted ensemble + disagreement protocol)
  - xgboost_model.py        (score_to_label, label_to_risk_name, apply_smote)

All stochastic tests use seed=42 for reproducibility.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_year_df(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """Feature DataFrame spanning 2019-2024 with numeric features."""
    rng = np.random.default_rng(seed)
    n_features = 10
    data = rng.random((n, n_features))
    df = pd.DataFrame(data, columns=[f"f{i}" for i in range(n_features)])
    # Spread years so every partition (train<=2021, val==2022, test>=2023) gets rows
    years_pool = [2019, 2020, 2021, 2022, 2023, 2024]
    df["year"] = [years_pool[i % len(years_pool)] for i in range(n)]
    return df


def _make_feature_matrix(n: int = 50, n_features: int = 5, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.random((n, n_features)), columns=[f"f{i}" for i in range(n_features)])


def _make_imbalanced_labels(n: int = 80, seed: int = 42) -> np.ndarray:
    """85% class 0, ~5% each class 1/2/3 -- typical procurement fraud imbalance."""
    rng = np.random.default_rng(seed)
    labels = np.zeros(n, dtype=int)
    for cls in [1, 2, 3]:
        idx = rng.choice(n, size=max(2, n // 20), replace=False)
        labels[idx] = cls
    return labels


# ===========================================================================
# 1. Temporal Split
# ===========================================================================

class TestTemporalSplit:
    """temporal_split() must produce non-overlapping, year-correct partitions."""

    def test_returns_three_dataframes(self) -> None:
        from backend.ml.temporal_split import temporal_split
        df = _make_year_df(120)
        result = temporal_split(df)
        assert len(result) == 3
        train, val, test = result
        assert isinstance(train, pd.DataFrame)
        assert isinstance(val, pd.DataFrame)
        assert isinstance(test, pd.DataFrame)

    def test_train_years_lte_2021(self) -> None:
        from backend.ml.temporal_split import temporal_split, TRAIN_END_YEAR
        df = _make_year_df(120)
        train, _, _ = temporal_split(df)
        assert len(train) > 0
        assert (train["year"] <= TRAIN_END_YEAR).all()

    def test_val_year_eq_2022(self) -> None:
        from backend.ml.temporal_split import temporal_split, VAL_YEAR
        df = _make_year_df(120)
        _, val, _ = temporal_split(df)
        assert len(val) > 0
        assert (val["year"] == VAL_YEAR).all()

    def test_test_years_gte_2023(self) -> None:
        from backend.ml.temporal_split import temporal_split, TEST_START_YEAR
        df = _make_year_df(120)
        _, _, test = temporal_split(df)
        assert len(test) > 0
        assert (test["year"] >= TEST_START_YEAR).all()

    def test_no_row_in_multiple_partitions(self) -> None:
        from backend.ml.temporal_split import temporal_split
        df = _make_year_df(120)
        train, val, test = temporal_split(df)
        all_idx = set(train.index) | set(val.index) | set(test.index)
        assert len(all_idx) == len(train) + len(val) + len(test), "Rows appear in multiple partitions"

    def test_total_rows_preserved(self) -> None:
        from backend.ml.temporal_split import temporal_split
        df = _make_year_df(120)
        train, val, test = temporal_split(df)
        # Only rows with years 2019-2024 should be present; all are here
        assert len(train) + len(val) + len(test) == len(df)

    def test_missing_year_col_raises(self) -> None:
        from backend.ml.temporal_split import temporal_split
        df = pd.DataFrame({"a": [1, 2, 3]})
        with pytest.raises(ValueError, match="year"):
            temporal_split(df, year_col="year")

    def test_custom_year_col(self) -> None:
        from backend.ml.temporal_split import temporal_split, TRAIN_END_YEAR
        df = _make_year_df(60)
        df = df.rename(columns={"year": "tahun"})
        train, val, test = temporal_split(df, year_col="tahun")
        assert len(train) > 0

    def test_returns_copies_not_views(self) -> None:
        from backend.ml.temporal_split import temporal_split
        df = _make_year_df(60)
        train, val, test = temporal_split(df)
        # Modifying a partition should NOT change the original
        train.iloc[0, 0] = 9999.0
        assert df.iloc[0, 0] != 9999.0


class TestTimeSeriesCV:
    """get_timeseries_cv() must return N_SPLITS folds in temporal order."""

    def test_returns_correct_n_splits(self) -> None:
        from backend.ml.temporal_split import temporal_split, get_timeseries_cv, N_SPLITS
        df = _make_year_df(200)
        train, _, _ = temporal_split(df)
        splits = get_timeseries_cv(train)
        assert len(splits) == N_SPLITS

    def test_each_split_is_tuple_of_arrays(self) -> None:
        from backend.ml.temporal_split import temporal_split, get_timeseries_cv
        df = _make_year_df(200)
        train, _, _ = temporal_split(df)
        for tr_idx, vl_idx in get_timeseries_cv(train):
            assert len(tr_idx) > 0
            assert len(vl_idx) > 0

    def test_val_indices_come_after_train_indices(self) -> None:
        """TimeSeriesSplit must never have val indices before train indices."""
        from backend.ml.temporal_split import temporal_split, get_timeseries_cv
        df = _make_year_df(200)
        train, _, _ = temporal_split(df)
        for tr_idx, vl_idx in get_timeseries_cv(train):
            assert int(tr_idx.max()) < int(vl_idx.min()), "Val indices before train indices (temporal leakage!)"


# ===========================================================================
# 2. Isolation Forest
# ===========================================================================

class TestIsolationForest:
    """fit_isolation_forest + score_isolation_forest must produce valid [0,1] scores."""

    def test_fit_returns_isolation_forest(self) -> None:
        from sklearn.ensemble import IsolationForest
        from backend.ml.isolation_forest import fit_isolation_forest
        X = _make_feature_matrix(60)
        model = fit_isolation_forest(X)
        assert isinstance(model, IsolationForest)

    def test_scores_in_zero_one(self) -> None:
        from backend.ml.isolation_forest import fit_isolation_forest, score_isolation_forest
        X = _make_feature_matrix(80)
        model = fit_isolation_forest(X)
        scores = score_isolation_forest(model, X)
        assert scores.min() >= 0.0 - 1e-9
        assert scores.max() <= 1.0 + 1e-9

    def test_score_shape_matches_input(self) -> None:
        from backend.ml.isolation_forest import fit_isolation_forest, score_isolation_forest
        X = _make_feature_matrix(50)
        model = fit_isolation_forest(X)
        scores = score_isolation_forest(model, X)
        assert scores.shape == (50,)

    def test_same_seed_same_scores(self) -> None:
        """Reproducibility: same data + seed=42 must yield identical scores."""
        from backend.ml.isolation_forest import fit_isolation_forest, score_isolation_forest
        X = _make_feature_matrix(60)
        model1 = fit_isolation_forest(X)
        model2 = fit_isolation_forest(X)
        s1 = score_isolation_forest(model1, X)
        s2 = score_isolation_forest(model2, X)
        np.testing.assert_allclose(s1, s2, rtol=1e-5)

    def test_handles_nan_values(self) -> None:
        from backend.ml.isolation_forest import fit_isolation_forest, score_isolation_forest
        X = _make_feature_matrix(50)
        model = fit_isolation_forest(X)
        X_nan = X.copy()
        X_nan.iloc[0, 0] = np.nan
        scores = score_isolation_forest(model, X_nan)
        assert scores.shape == (50,)
        assert not np.isnan(scores).any()

    def test_single_row_scoring(self) -> None:
        from backend.ml.isolation_forest import fit_isolation_forest, score_isolation_forest
        X_train = _make_feature_matrix(80)
        model = fit_isolation_forest(X_train)
        X_single = X_train.iloc[:1]
        scores = score_isolation_forest(model, X_single)
        # Single row -> min==max -> normalized to 0.0
        assert scores.shape == (1,)
        assert float(scores[0]) == pytest.approx(0.0, abs=1e-9)

    def test_returns_ndarray(self) -> None:
        from backend.ml.isolation_forest import fit_isolation_forest, score_isolation_forest
        X = _make_feature_matrix(40)
        model = fit_isolation_forest(X)
        scores = score_isolation_forest(model, X)
        assert isinstance(scores, np.ndarray)


# ===========================================================================
# 3. ICW Weak Labels
# ===========================================================================

class TestNormalizeICWScore:
    """normalize_icw_score: 0-100 -> 0.0-1.0, edge cases handled."""

    def test_none_returns_zero(self) -> None:
        from backend.ml.icw_weak_labels import normalize_icw_score
        assert normalize_icw_score(None) == 0.0

    def test_nan_returns_zero(self) -> None:
        from backend.ml.icw_weak_labels import normalize_icw_score
        assert normalize_icw_score(float("nan")) == 0.0

    def test_zero_returns_zero(self) -> None:
        from backend.ml.icw_weak_labels import normalize_icw_score
        assert normalize_icw_score(0.0) == pytest.approx(0.0)

    def test_100_returns_one(self) -> None:
        from backend.ml.icw_weak_labels import normalize_icw_score
        assert normalize_icw_score(100.0) == pytest.approx(1.0)

    def test_50_returns_half(self) -> None:
        from backend.ml.icw_weak_labels import normalize_icw_score
        assert normalize_icw_score(50.0) == pytest.approx(0.5)

    def test_clamps_above_100(self) -> None:
        from backend.ml.icw_weak_labels import normalize_icw_score
        assert normalize_icw_score(150.0) == pytest.approx(1.0)

    def test_clamps_below_zero(self) -> None:
        from backend.ml.icw_weak_labels import normalize_icw_score
        assert normalize_icw_score(-10.0) == pytest.approx(0.0)

    def test_band_low_40(self) -> None:
        from backend.ml.icw_weak_labels import normalize_icw_score
        # raw 40 -> 0.40
        assert normalize_icw_score(40.0) == pytest.approx(0.40)

    def test_band_medium_70(self) -> None:
        from backend.ml.icw_weak_labels import normalize_icw_score
        # raw 70 -> 0.70
        assert normalize_icw_score(70.0) == pytest.approx(0.70)


class TestICWScoreToLabel:
    """icw_score_to_label: 4-class bucketing at 0.25, 0.50, 0.80."""

    def test_zero_is_aman(self) -> None:
        from backend.ml.icw_weak_labels import icw_score_to_label
        assert icw_score_to_label(0.0) == 0

    def test_below_025_is_aman(self) -> None:
        from backend.ml.icw_weak_labels import icw_score_to_label
        assert icw_score_to_label(0.24) == 0

    def test_at_025_is_perlu_pantauan(self) -> None:
        from backend.ml.icw_weak_labels import icw_score_to_label
        assert icw_score_to_label(0.25) == 1

    def test_at_049_is_perlu_pantauan(self) -> None:
        from backend.ml.icw_weak_labels import icw_score_to_label
        assert icw_score_to_label(0.49) == 1

    def test_at_050_is_risiko_tinggi(self) -> None:
        from backend.ml.icw_weak_labels import icw_score_to_label
        assert icw_score_to_label(0.50) == 2

    def test_at_079_is_risiko_tinggi(self) -> None:
        from backend.ml.icw_weak_labels import icw_score_to_label
        assert icw_score_to_label(0.79) == 2

    def test_at_080_is_risiko_kritis(self) -> None:
        from backend.ml.icw_weak_labels import icw_score_to_label
        assert icw_score_to_label(0.80) == 3

    def test_one_is_risiko_kritis(self) -> None:
        from backend.ml.icw_weak_labels import icw_score_to_label
        assert icw_score_to_label(1.0) == 3


class TestBuildWeakLabelTargets:
    """build_weak_label_targets must produce integer 0-3 labels."""

    def test_returns_series(self) -> None:
        from backend.ml.icw_weak_labels import build_weak_label_targets
        df = pd.DataFrame({"icw_total_score": [0, 25, 50, 80, 100]})
        labels = build_weak_label_targets(df)
        assert isinstance(labels, pd.Series)

    def test_labels_in_range_0_3(self) -> None:
        from backend.ml.icw_weak_labels import build_weak_label_targets
        df = pd.DataFrame({"icw_total_score": list(range(0, 101, 10))})
        labels = build_weak_label_targets(df)
        assert labels.min() >= 0
        assert labels.max() <= 3

    def test_missing_col_returns_zeros(self) -> None:
        from backend.ml.icw_weak_labels import build_weak_label_targets
        df = pd.DataFrame({"other_col": [1, 2, 3]})
        labels = build_weak_label_targets(df)
        assert (labels == 0).all()

    def test_nan_scores_become_aman(self) -> None:
        from backend.ml.icw_weak_labels import build_weak_label_targets
        df = pd.DataFrame({"icw_total_score": [np.nan, np.nan]})
        labels = build_weak_label_targets(df)
        assert (labels == 0).all()

    def test_index_alignment(self) -> None:
        from backend.ml.icw_weak_labels import build_weak_label_targets
        df = pd.DataFrame({"icw_total_score": [0, 50, 100]}, index=[10, 20, 30])
        labels = build_weak_label_targets(df)
        assert list(labels.index) == [10, 20, 30]


# ===========================================================================
# 4. Ensemble
# ===========================================================================

class TestEnsembleWeightedAverage:
    """compute_ensemble: verify weighted average math."""

    def test_all_zero_scores_give_aman(self) -> None:
        from backend.ml.ensemble import compute_ensemble
        result = compute_ensemble("T001", 0.0, 0.0, 0.0)
        assert result.final_score == pytest.approx(0.0)
        assert result.risk_level == "Aman"

    def test_all_one_scores_give_kritis(self) -> None:
        from backend.ml.ensemble import compute_ensemble
        result = compute_ensemble("T002", 1.0, 1.0, 1.0)
        assert result.final_score == pytest.approx(1.0)
        assert result.risk_level == "Risiko Kritis"

    def test_weighted_average_math(self) -> None:
        """Default weights: IF=0.35, XGB=0.40, ICW=0.25. Verify math."""
        from backend.ml.ensemble import compute_ensemble
        # Choose scores so math is easy: IF=1.0, XGB=0.0, ICW=0.0
        # Expected: 1.0*0.35 + 0.0*0.40 + 0.0*0.25 = 0.35
        result = compute_ensemble("T003", 1.0, 0.0, 0.0)
        assert result.final_score == pytest.approx(0.35, abs=0.01)

    def test_final_score_in_zero_one(self) -> None:
        from backend.ml.ensemble import compute_ensemble
        result = compute_ensemble("T004", 0.6, 0.4, 0.8)
        assert 0.0 <= result.final_score <= 1.0

    def test_result_has_correct_fields(self) -> None:
        from backend.ml.ensemble import compute_ensemble, EnsembleResult
        result = compute_ensemble("T005", 0.3, 0.3, 0.3)
        assert isinstance(result, EnsembleResult)
        assert result.tender_id == "T005"
        assert "isolation_forest" in result.individual_scores
        assert "xgboost" in result.individual_scores
        assert "icw" in result.individual_scores

    def test_individual_scores_clamped_to_zero_one(self) -> None:
        """Out-of-range inputs must be clamped."""
        from backend.ml.ensemble import compute_ensemble
        result = compute_ensemble("T006", -0.5, 1.5, 0.5)
        assert result.individual_scores["isolation_forest"] == pytest.approx(0.0)
        assert result.individual_scores["xgboost"] == pytest.approx(1.0)


class TestRiskLevelMapping:
    """_score_to_risk_level boundaries must match proposal exactly."""

    def test_aman_boundary(self) -> None:
        from backend.ml.ensemble import compute_ensemble
        # score < 0.25 -> Aman
        r = compute_ensemble("X", 0.24, 0.24, 0.0)
        # weighted: 0.24*0.35 + 0.24*0.40 + 0.0*0.25 = 0.084+0.096 = 0.18
        assert r.risk_level == "Aman"

    def test_perlu_pantauan_boundary(self) -> None:
        from backend.ml.ensemble import compute_ensemble
        # All at 0.30 -> final=0.30 -> Perlu Pantauan
        r = compute_ensemble("X", 0.30, 0.30, 0.30)
        assert r.risk_level == "Perlu Pantauan"

    def test_risiko_tinggi_boundary(self) -> None:
        from backend.ml.ensemble import compute_ensemble
        # All at 0.60 -> Risiko Tinggi
        r = compute_ensemble("X", 0.60, 0.60, 0.60)
        assert r.risk_level == "Risiko Tinggi"

    def test_risiko_kritis_boundary(self) -> None:
        from backend.ml.ensemble import compute_ensemble
        # All at 0.90 -> Risiko Kritis
        r = compute_ensemble("X", 0.90, 0.90, 0.90)
        assert r.risk_level == "Risiko Kritis"


class TestDisagreementProtocol:
    """When any two models disagree by >0.30, flag for manual review."""

    def test_agreement_no_flag(self) -> None:
        from backend.ml.ensemble import compute_ensemble
        # IF=0.5, XGB=0.5, ICW=0.5 -> no disagreement
        r = compute_ensemble("T010", 0.5, 0.5, 0.5)
        assert r.disagreement_flag is False
        assert r.manual_review_priority is False

    def test_high_disagreement_if_vs_xgb(self) -> None:
        """IF=0.9, XGB=0.2, ICW=0.55 -> IF vs XGB diff=0.7 > 0.30 -> flag."""
        from backend.ml.ensemble import compute_ensemble
        r = compute_ensemble("T011", 0.9, 0.2, 0.55)
        assert r.disagreement_flag is True
        assert r.manual_review_priority is True

    def test_disagreement_detail_contains_pair_names(self) -> None:
        from backend.ml.ensemble import compute_ensemble
        r = compute_ensemble("T012", 0.9, 0.1, 0.5)
        assert "isolation_forest" in r.disagreement_detail
        assert "xgboost" in r.disagreement_detail

    def test_all_three_pairs_checked(self) -> None:
        """IF=0.9, XGB=0.2, ICW=0.5 -> at least 2 pairs disagree."""
        from backend.ml.ensemble import compute_ensemble
        r = compute_ensemble("T013", 0.9, 0.2, 0.5)
        # IF-XGB: |0.9-0.2|=0.7 -> disagree
        # IF-ICW: |0.9-0.5|=0.4 -> disagree
        # XGB-ICW: |0.2-0.5|=0.3 -> exactly AT threshold (not > 0.30)
        assert r.disagreement_flag is True

    def test_exactly_at_threshold_no_flag(self) -> None:
        """Diff exactly == 0.30 should NOT trigger flag (threshold is strict >)."""
        from backend.ml.ensemble import compute_ensemble
        r = compute_ensemble("T014", 0.5, 0.2, 0.5)
        # IF-XGB: |0.5-0.2|=0.3 -> NOT > 0.30 (exact boundary)
        # IF-ICW: |0.5-0.5|=0.0 -> agree
        # XGB-ICW: |0.2-0.5|=0.3 -> NOT > 0.30
        assert r.disagreement_flag is False

    def test_agreement_detail_text(self) -> None:
        from backend.ml.ensemble import compute_ensemble
        r = compute_ensemble("T015", 0.5, 0.5, 0.5)
        assert "agree" in r.disagreement_detail.lower()


class TestBatchEnsemble:
    """batch_ensemble must return results matching input length."""

    def test_length_matches_input(self) -> None:
        from backend.ml.ensemble import batch_ensemble
        ids = ["T1", "T2", "T3"]
        results = batch_ensemble(ids, [0.3, 0.6, 0.9], [0.3, 0.6, 0.9], [0.3, 0.6, 0.9])
        assert len(results) == 3

    def test_tender_ids_preserved(self) -> None:
        from backend.ml.ensemble import batch_ensemble
        ids = ["A001", "B002", "C003"]
        results = batch_ensemble(ids, [0.1, 0.5, 0.9], [0.1, 0.5, 0.9], [0.1, 0.5, 0.9])
        for r, expected_id in zip(results, ids):
            assert r.tender_id == expected_id

    def test_numpy_arrays_accepted(self) -> None:
        from backend.ml.ensemble import batch_ensemble
        ids = ["T1", "T2"]
        scores = np.array([0.3, 0.7])
        results = batch_ensemble(ids, scores, scores, scores)
        assert len(results) == 2


# ===========================================================================
# 5. XGBoost helpers (score_to_label, label_to_risk_name, apply_smote)
# ===========================================================================

class TestScoreToLabel:
    """score_to_label must map continuous [0,1] to integer 0-3."""

    @pytest.mark.parametrize("score,expected", [
        (0.00, 0),
        (0.10, 0),
        (0.24, 0),       # just below 0.25 boundary
        (0.25, 1),       # exactly at boundary -> Perlu Pantauan
        (0.40, 1),
        (0.49, 1),
        (0.50, 2),       # exactly at boundary -> Risiko Tinggi
        (0.79, 2),
        (0.80, 3),       # exactly at boundary -> Risiko Kritis
        (0.95, 3),
        (1.00, 3),
    ])
    def test_threshold_boundaries(self, score: float, expected: int) -> None:
        from backend.ml.xgboost_model import score_to_label
        assert score_to_label(score) == expected


class TestLabelToRiskName:
    """label_to_risk_name must return exact Bahasa Indonesia names from proposal."""

    @pytest.mark.parametrize("label,expected", [
        (0, "Aman"),
        (1, "Perlu Pantauan"),
        (2, "Risiko Tinggi"),
        (3, "Risiko Kritis"),
    ])
    def test_mapping(self, label: int, expected: str) -> None:
        from backend.ml.xgboost_model import label_to_risk_name
        assert label_to_risk_name(label) == expected

    def test_unknown_label_returns_aman(self) -> None:
        from backend.ml.xgboost_model import label_to_risk_name
        # Unknown label falls back to "Aman"
        assert label_to_risk_name(99) == "Aman"


class TestApplySMOTE:
    """apply_smote must balance imbalanced classes, skip gracefully when impossible."""

    def test_balanced_output_same_size_each_class(self) -> None:
        from collections import Counter
        from backend.ml.xgboost_model import apply_smote
        X = np.random.default_rng(42).random((80, 5))
        y = _make_imbalanced_labels(80)
        X_res, y_res = apply_smote(X, y, seed=42)
        counts = Counter(y_res.tolist())
        # All classes should now have equal representation
        assert len(set(counts.values())) == 1, f"Classes not balanced: {counts}"

    def test_returns_numpy_arrays(self) -> None:
        from backend.ml.xgboost_model import apply_smote
        X = np.random.default_rng(42).random((60, 5))
        y = _make_imbalanced_labels(60)
        X_res, y_res = apply_smote(X, y)
        assert isinstance(X_res, np.ndarray)
        assert isinstance(y_res, np.ndarray)

    def test_feature_count_unchanged(self) -> None:
        from backend.ml.xgboost_model import apply_smote
        X = np.random.default_rng(42).random((60, 8))
        y = _make_imbalanced_labels(60)
        X_res, _ = apply_smote(X, y)
        assert X_res.shape[1] == 8

    def test_output_larger_than_input_when_imbalanced(self) -> None:
        from backend.ml.xgboost_model import apply_smote
        X = np.random.default_rng(42).random((60, 5))
        y = _make_imbalanced_labels(60)
        X_res, y_res = apply_smote(X, y)
        assert len(y_res) >= len(y)

    def test_skip_when_class_has_one_sample(self) -> None:
        """If a class has only 1 sample, SMOTE must skip gracefully."""
        from backend.ml.xgboost_model import apply_smote
        X = np.random.default_rng(42).random((10, 5))
        y = np.array([0, 0, 0, 0, 0, 0, 0, 1, 2, 3])  # class 1,2,3 have 1 sample each
        X_res, y_res = apply_smote(X, y)
        # Should return original unchanged
        assert len(y_res) == 10

    def test_seed_reproducibility(self) -> None:
        from backend.ml.xgboost_model import apply_smote
        X = np.random.default_rng(42).random((60, 5))
        y = _make_imbalanced_labels(60)
        X1, y1 = apply_smote(X, y, seed=42)
        X2, y2 = apply_smote(X, y, seed=42)
        np.testing.assert_array_equal(y1, y2)
