"""
LPSE-X Temporal Split
======================
Temporal train/val/test partitioning — NEVER shuffle, NEVER leak future data.

Split:
  Train : year <= 2021  (~70%)
  Val   : year == 2022  (~15%)
  Test  : year >= 2023  (~15%)

5-Fold TimeSeriesSplit is applied WITHIN the training set only.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TRAIN_END_YEAR = 2021
VAL_YEAR = 2022
TEST_START_YEAR = 2023
N_SPLITS = 5


def temporal_split(
    df: pd.DataFrame,
    year_col: str = "year",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split dataframe into train / val / test by year.

    Parameters
    ----------
    df:
        Feature DataFrame with a year column.
    year_col:
        Name of the year column.

    Returns
    -------
    train, val, test DataFrames (copies, NOT views).
    No row is in more than one partition.
    """
    if year_col not in df.columns:
        raise ValueError(f"Column '{year_col}' not found in DataFrame (cols={list(df.columns[:10])})")

    years = pd.to_numeric(df[year_col], errors="coerce")
    train_mask = years <= TRAIN_END_YEAR
    val_mask = years == VAL_YEAR
    test_mask = years >= TEST_START_YEAR

    train = df[train_mask].copy()
    val = df[val_mask].copy()
    test = df[test_mask].copy()

    logger.info(
        "Temporal split: train=%d (years<=%d), val=%d (year=%d), test=%d (years>=%d)",
        len(train), TRAIN_END_YEAR,
        len(val), VAL_YEAR,
        len(test), TEST_START_YEAR,
    )
    return train, val, test


def get_timeseries_cv(
    train_df: pd.DataFrame,
    year_col: str = "year",
    n_splits: int = N_SPLITS,
) -> list[tuple[Any, Any]]:
    """
    5-Fold TimeSeriesSplit indices for the training set.

    Returns list of (train_indices, val_indices) integer-position index pairs.
    Data is sorted by year before splitting to preserve temporal ordering.
    """
    sorted_df = train_df.sort_values(year_col, kind="stable").reset_index(drop=True)
    tscv = TimeSeriesSplit(n_splits=n_splits)
    splits: list[tuple[Any, Any]] = []
    for fold, (tr_idx, vl_idx) in enumerate(tscv.split(sorted_df)):
        splits.append((tr_idx, vl_idx))
        logger.debug(
            "CV fold %d: train=%d rows, val=%d rows",
            fold, len(tr_idx), len(vl_idx),
        )
    return splits
