"""
LPSE-X Benford's Law Analysis
==============================
Forensic analysis of procurement value distributions using Benford's Law.

Benford's Law (also known as the first-digit law) states that in naturally
occurring numerical data, the leading digit is more likely to be small.
Deviations from this distribution in procurement data can indicate
manipulation, fraud, or anomalous behavior.

CRITICAL RULES:
- Requires >= 50 data points (configurable via custom_params.benford_min_records)
- Data must span >= 2 orders of magnitude (max/min >= 100)
- Returns {"applicable": False, "reason": "..."} when pre-check fails
- anomaly_flag=True ONLY when applicable=True AND p_value < threshold
- Threshold from get_config().custom_params.get("benford_threshold", 0.05)
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import scipy.stats

import benford as benford_lib  # type: ignore[import-untyped]

from backend.config.runtime import get_config

logger = logging.getLogger(__name__)


def run_benford_analysis(
    values: list[float],
    label: str = "value_amount",
) -> dict[str, Any]:
    """
    Run Benford's Law analysis on a list of procurement values.

    Pre-check gate (CRITICAL — must not flag when not applicable):
      1. Need >= min_records data points (default 50, configurable)
      2. Must span >= 2 orders of magnitude (max/min >= 100)

    Returns {"applicable": False, "reason": "..."} when pre-check fails.
    anomaly_flag=True ONLY when applicable=True AND p_value < threshold.

    Parameters
    ----------
    values:
        Raw numeric procurement values (e.g. tender value_amount in IDR).
        Negative and zero values are filtered out automatically.
    label:
        Human-readable label for logging / report output.

    Returns
    -------
    dict with keys:
        applicable (bool)    -- False if pre-check fails
        reason (str)         -- explanation when applicable=False
        count (int)          -- number of valid positive values used
        p_value (float)      -- chi-square p-value (only when applicable=True)
        threshold (float)    -- configured significance threshold
        anomaly_flag (bool)  -- True when p_value < threshold
        chi2_stat (float)    -- raw chi-square statistic
        expected_dist (dict) -- expected Benford distribution per digit
        found_dist (dict)    -- observed distribution per digit
        risk_signal (str)    -- human-readable signal description
    """
    cfg = get_config()
    min_records: int = int(cfg.custom_params.get("benford_min_records", 50))
    threshold: float = float(cfg.custom_params.get("benford_threshold", 0.05))

    # Filter: keep only strictly positive values
    positives: list[float] = [
        v for v in values if isinstance(v, (int, float)) and v > 0
    ]

    # -- Pre-check 1: Minimum record count --------------------------------
    if len(positives) < min_records:
        logger.debug(
            "Benford pre-check failed [insufficient records]: label=%s count=%d min=%d",
            label,
            len(positives),
            min_records,
        )
        return {
            "applicable": False,
            "reason": (
                f"Insufficient data: {len(positives)} records "
                f"(need >= {min_records})"
            ),
            "count": len(positives),
            "label": label,
        }

    # -- Pre-check 2: Range must span >= 2 orders of magnitude ------------
    max_val: float = max(positives)
    min_val: float = min(positives)
    range_ratio: float = max_val / min_val if min_val > 0 else 0.0

    if range_ratio < 100.0:
        logger.debug(
            "Benford pre-check failed [insufficient range]: label=%s ratio=%.2f",
            label,
            range_ratio,
        )
        return {
            "applicable": False,
            "reason": (
                f"Insufficient range: max/min = {range_ratio:.1f} "
                "(need >= 100 for 2+ orders of magnitude)"
            ),
            "count": len(positives),
            "label": label,
        }

    # -- Benford analysis -------------------------------------------------
    try:
        series = pd.Series(positives, dtype=float)

        # Get first-digit distribution DataFrame (columns: Counts, Found, Expected)
        dist_df: pd.DataFrame = benford_lib.first_digits(  # type: ignore[attr-defined]
            series,
            digs=1,           # first-digit test (most sensitive for procurement)
            decimals=2,
            sign="all",
            verbose=False,
            confidence=None,  # suppress internal critical-value printing
            chi_square=False,
            KS=False,
            show_plot=False,
        )

        # Compute chi-square statistic (matches benford_lib internal logic)
        total_n: int = int(dist_df["Counts"].sum())
        expected_arr = dist_df["Expected"].to_numpy(dtype=float)
        observed_arr = dist_df["Counts"].to_numpy(dtype=float)

        exp_counts: Any = total_n * expected_arr
        dif_counts: Any = observed_arr - exp_counts
        chi2_stat: float = float((dif_counts**2 / exp_counts).sum())
        dof: int = len(dist_df) - 1  # degrees of freedom = 8 for first-digit test

        # Compute p-value using scipy chi-square survival function
        p_value: float = float(scipy.stats.chi2.sf(chi2_stat, dof))

        anomaly_flag: bool = p_value < threshold

        # Build digit distribution dicts for reporting
        digit_index: list[int] = list(range(1, 10))
        expected_dist: dict[str, float] = {
            str(d): round(float(e), 6)
            for d, e in zip(digit_index, expected_arr)
        }
        found_dist: dict[str, float] = {
            str(d): round(float(f), 6)
            for d, f in zip(digit_index, dist_df["Found"].to_numpy(dtype=float))
        }

        risk_signal: str = (
            f"Benford deviation detected (p={p_value:.4f} < threshold={threshold})"
            if anomaly_flag
            else (
                f"Benford distribution normal (p={p_value:.4f} >= threshold={threshold})"
            )
        )

        result: dict[str, Any] = {
            "applicable": True,
            "label": label,
            "count": len(positives),
            "chi2_stat": round(chi2_stat, 4),
            "dof": dof,
            "p_value": round(p_value, 6),
            "threshold": threshold,
            "anomaly_flag": anomaly_flag,
            "expected_dist": expected_dist,
            "found_dist": found_dist,
            "risk_signal": risk_signal,
        }

        logger.info(
            "Benford analysis complete: label=%s count=%d chi2=%.4f p=%.4f anomaly=%s",
            label,
            len(positives),
            chi2_stat,
            p_value,
            anomaly_flag,
        )
        return result

    except Exception as exc:
        logger.exception("Benford analysis raised an unexpected error: %s", exc)
        return {
            "applicable": False,
            "reason": f"Analysis error: {exc}",
            "count": len(positives),
            "label": label,
        }
