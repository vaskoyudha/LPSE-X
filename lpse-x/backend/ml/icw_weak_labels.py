"""
LPSE-X ICW Weak Labels Transformer
=====================================
Converts opentender.net ICW 'total_score' (0-100) to normalized risk scores [0, 1].
NOT a ML model -- a deterministic score transformer providing weak supervision signal.

Band mapping (UPGRADE 3 line 133):
  Low    0-40   -> 0.00-0.40
  Medium 41-70  -> 0.41-0.70
  High   71-100 -> 0.71-1.00
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def normalize_icw_score(raw_score: float | None) -> float:
    """
    Normalize a single ICW total_score (0-100) to risk [0, 1].
    None/NaN values default to 0.0 (no signal).
    """
    if raw_score is None or (isinstance(raw_score, float) and np.isnan(raw_score)):
        return 0.0
    clipped = max(0.0, min(100.0, float(raw_score)))
    return round(clipped / 100.0, 6)


def icw_score_to_label(normalized: float) -> int:
    """
    Convert normalized ICW score to 4-class integer label:
      0 = Aman            (<0.25)
      1 = Perlu Pantauan  (0.25-0.49)
      2 = Risiko Tinggi   (0.50-0.79)
      3 = Risiko Kritis   (>=0.80)
    """
    if normalized < 0.25:
        return 0
    if normalized < 0.50:
        return 1
    if normalized < 0.80:
        return 2
    return 3


def extract_icw_weak_labels(
    df: pd.DataFrame,
    score_col: str = "icw_total_score",
) -> pd.Series:
    """
    Extract and normalize ICW scores from a features DataFrame.

    Parameters
    ----------
    df:
        DataFrame with an icw_total_score column.
    score_col:
        Column name for raw ICW scores (0-100).

    Returns
    -------
    pd.Series of normalized scores (0.0-1.0) aligned to df index.
    """
    if score_col not in df.columns:
        logger.warning(
            "Column '%s' not found in DataFrame. Returning zeros (no ICW signal).",
            score_col,
        )
        return pd.Series(0.0, index=df.index, name="icw_normalized")

    raw = pd.to_numeric(df[score_col], errors="coerce")
    normalized = raw.apply(normalize_icw_score)
    normalized.name = "icw_normalized"

    n_valid = int((~raw.isna()).sum())
    logger.info(
        "ICW weak labels: %d valid scores, %d missing (set to 0.0)",
        n_valid, len(df) - n_valid,
    )
    return normalized


def build_weak_label_targets(
    df: pd.DataFrame,
    score_col: str = "icw_total_score",
) -> pd.Series:
    """
    Build integer 4-class weak labels from ICW scores for supervised training.
    These are WEAK labels -- used to bootstrap XGBoost when ground-truth labels are scarce.

    Returns
    -------
    pd.Series of int labels 0-3 aligned to df index.
    """
    normalized = extract_icw_weak_labels(df, score_col)
    labels = normalized.apply(icw_score_to_label).astype(int)
    labels.name = "icw_label"
    from collections import Counter
    dist = dict(Counter(labels.tolist()))
    logger.info("ICW weak label distribution: %s", dist)
    return labels
