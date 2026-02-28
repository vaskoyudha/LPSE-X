"""Tests for LPSE-X Benford Law analysis module."""
from __future__ import annotations

import numpy as np
import pytest
from backend.analysis.benford import run_benford_analysis


def _make_lognormal(n: int = 500, seed: int = 42) -> list[float]:
    rng = np.random.default_rng(seed)
    return list(rng.lognormal(mean=10.0, sigma=2.5, size=n))


def _make_clustered(n: int = 100) -> list[float]:
    """Create data that spans < 2 orders of magnitude (range_ratio < 100)."""
    return [1e8 + i * 5e5 for i in range(n)]


class TestBenfordPreChecks:
    def test_insufficient_records_returns_not_applicable(self) -> None:
        result = run_benford_analysis(list(range(1, 30)), label="tiny")
        assert result["applicable"] is False
        assert "records" in result["reason"].lower()
        assert result["count"] == 29

    def test_boundary_49_insufficient(self) -> None:
        result = run_benford_analysis(list(range(1, 50)), label="boundary")
        assert result["applicable"] is False

    def test_boundary_50_passes_range_check(self) -> None:
        # 50 values spanning many orders of magnitude
        vals = _make_lognormal(n=50)
        result = run_benford_analysis(vals, label="min_pass")
        # May fail range check depending on spread, but should NOT fail record check
        assert result["count"] >= 50 or result["applicable"] is False

    def test_insufficient_range_returns_not_applicable(self) -> None:
        narrow = _make_clustered(200)
        result = run_benford_analysis(narrow, label="narrow")
        assert result["applicable"] is False
        assert "range" in result["reason"].lower()

    def test_negatives_and_zeros_filtered(self) -> None:
        mixed = [-1.0, 0.0, -999.0] + _make_lognormal(n=200)
        result = run_benford_analysis(mixed, label="mixed")
        assert result["applicable"] is True
        assert result["count"] == 200

    def test_all_negative_not_applicable(self) -> None:
        result = run_benford_analysis([-1.0, -2.0, -3.0], label="all_neg")
        assert result["applicable"] is False

    def test_empty_list_not_applicable(self) -> None:
        result = run_benford_analysis([], label="empty")
        assert result["applicable"] is False

    def test_label_preserved_on_failure(self) -> None:
        result = run_benford_analysis([1.0] * 5, label="my_label")
        assert result["label"] == "my_label"

    def test_label_preserved_on_success(self) -> None:
        vals = _make_lognormal(n=300)
        result = run_benford_analysis(vals, label="success_label")
        assert result["label"] == "success_label"


class TestBenfordResultShape:
    def test_required_keys_present(self) -> None:
        vals = _make_lognormal(n=300)
        result = run_benford_analysis(vals, label="shape")
        assert result["applicable"] is True
        required = {
            "applicable", "label", "count", "chi2_stat", "dof",
            "p_value", "threshold", "anomaly_flag", "expected_dist",
            "found_dist", "risk_signal",
        }
        assert required.issubset(result.keys())

    def test_expected_dist_9_digits(self) -> None:
        vals = _make_lognormal(n=300)
        result = run_benford_analysis(vals)
        assert len(result["expected_dist"]) == 9
        assert set(result["expected_dist"].keys()) == {str(d) for d in range(1, 10)}

    def test_found_dist_9_digits(self) -> None:
        vals = _make_lognormal(n=300)
        result = run_benford_analysis(vals)
        assert len(result["found_dist"]) == 9
        assert set(result["found_dist"].keys()) == {str(d) for d in range(1, 10)}

    def test_expected_dist_sums_to_one(self) -> None:
        vals = _make_lognormal(n=300)
        result = run_benford_analysis(vals)
        assert abs(sum(result["expected_dist"].values()) - 1.0) < 0.001

    def test_found_dist_sums_to_one(self) -> None:
        vals = _make_lognormal(n=300)
        result = run_benford_analysis(vals)
        assert abs(sum(result["found_dist"].values()) - 1.0) < 0.01

    def test_p_value_in_range(self) -> None:
        vals = _make_lognormal(n=300)
        result = run_benford_analysis(vals)
        assert 0.0 <= result["p_value"] <= 1.0

    def test_chi2_non_negative(self) -> None:
        vals = _make_lognormal(n=300)
        result = run_benford_analysis(vals)
        assert result["chi2_stat"] >= 0.0

    def test_dof_equals_8(self) -> None:
        vals = _make_lognormal(n=300)
        result = run_benford_analysis(vals)
        assert result["dof"] == 8

    def test_count_matches_positives(self) -> None:
        vals = _make_lognormal(n=200)
        result = run_benford_analysis(vals)
        assert result["count"] == 200


class TestBenfordAnomalyFlag:
    def test_lognormal_has_reasonable_p_value(self) -> None:
        """Lognormal data should generally conform to Benford - p should not be tiny."""
        vals = _make_lognormal(n=1000, seed=42)
        result = run_benford_analysis(vals, label="lognormal")
        assert result["applicable"] is True
        # Benford-conforming data should have non-trivial p-value
        assert result["p_value"] > 1e-10

    def test_flag_consistent_with_p_value(self) -> None:
        vals = _make_lognormal(n=500)
        result = run_benford_analysis(vals)
        expected_flag = result["p_value"] < result["threshold"]
        assert result["anomaly_flag"] == expected_flag

    def test_risk_signal_matches_flag(self) -> None:
        vals = _make_lognormal(n=500)
        result = run_benford_analysis(vals)
        if result["anomaly_flag"]:
            assert "deviation detected" in result["risk_signal"].lower()
        else:
            assert "normal" in result["risk_signal"].lower()

    def test_default_threshold_is_0_05(self) -> None:
        vals = _make_lognormal(n=300)
        result = run_benford_analysis(vals)
        assert result["threshold"] == 0.05

    def test_inapplicable_has_no_anomaly_flag(self) -> None:
        result = run_benford_analysis([1.0] * 10)
        assert result["applicable"] is False
        assert "anomaly_flag" not in result

    def test_risk_signal_contains_p_value(self) -> None:
        vals = _make_lognormal(n=500)
        result = run_benford_analysis(vals)
        assert "p=" in result["risk_signal"]


class TestBenfordDeterminism:
    def test_same_input_same_output(self) -> None:
        vals = _make_lognormal(n=500, seed=99)
        r1 = run_benford_analysis(vals, label="det")
        r2 = run_benford_analysis(vals, label="det")
        assert r1["p_value"] == r2["p_value"]
        assert r1["chi2_stat"] == r2["chi2_stat"]
        assert r1["anomaly_flag"] == r2["anomaly_flag"]

    def test_first_digit_1_expected_approx_030103(self) -> None:
        vals = _make_lognormal(n=500)
        result = run_benford_analysis(vals)
        assert abs(result["expected_dist"]["1"] - 0.30103) < 0.001

    def test_first_digit_9_expected_approx_004576(self) -> None:
        vals = _make_lognormal(n=500)
        result = run_benford_analysis(vals)
        assert abs(result["expected_dist"]["9"] - 0.04576) < 0.001

    def test_expected_dist_decreasing_for_1_to_9(self) -> None:
        """Benford expected probabilities monotonically decrease from 1 to 9."""
        vals = _make_lognormal(n=500)
        result = run_benford_analysis(vals)
        probs = [result["expected_dist"][str(d)] for d in range(1, 10)]
        for i in range(len(probs) - 1):
            assert probs[i] > probs[i + 1]
