"""
LPSE-X Feature Engineering Pipeline.

Orchestrates Cardinal (73 flags) + Custom (12 features) into an 85-column
feature matrix. Saves results to the `features` table in SQLite.
Tags each row with temporal_split: train (≤2021) / val (2022) / test (≥2023).
"""

import sqlite3
import logging
from typing import Any

import numpy as np
import pandas as pd

from backend.features.cardinal_flags import compute_cardinal_flags, CARDINAL_FLAG_NAMES
from backend.features.custom_features import compute_custom_features, CUSTOM_FEATURE_NAMES

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Temporal split logic
# ---------------------------------------------------------------------------

def _assign_temporal_split(year: Any) -> str:
    """Map tender year to train/val/test split."""
    if year is None:
        return "train"
    try:
        y = int(year)
    except (TypeError, ValueError):
        return "train"
    if y <= 2021:
        return "train"
    if y == 2022:
        return "val"
    return "test"


# ---------------------------------------------------------------------------
# DDL for features table
# ---------------------------------------------------------------------------

_CREATE_FEATURES_TABLE = """
CREATE TABLE IF NOT EXISTS features (
    tender_id       TEXT PRIMARY KEY,
    temporal_split  TEXT NOT NULL DEFAULT 'train',
    icw_total_score REAL,
    feature_json    TEXT NOT NULL,
    computed_at     TEXT DEFAULT (datetime('now'))
)
"""


def _ensure_features_table(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(_CREATE_FEATURES_TABLE)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_feature_pipeline(
    db_path: str = "data/lpse_x.db",
    limit: int | None = None,
    save_to_db: bool = False,
) -> pd.DataFrame:
    """
    Run full feature engineering pipeline.

    Args:
        db_path:    Path to SQLite database.
        limit:      Maximum rows to process (None = all).
        save_to_db: If True, upsert feature rows back to `features` table.

    Returns:
        DataFrame with ≥85 columns (73 cardinal + 12 custom + metadata).
        Index is tender_id.
    """
    import json as _json

    cardinal_df = compute_cardinal_flags(db_path, limit)
    custom_df = compute_custom_features(db_path, limit)

    # Edge case: both empty
    if cardinal_df.empty and custom_df.empty:
        cols = list(CARDINAL_FLAG_NAMES) + list(CUSTOM_FEATURE_NAMES) + [
            "temporal_split", "icw_total_score"
        ]
        empty = pd.DataFrame(columns=pd.Index(cols))
        empty.index.name = "tender_id"
        return empty

    # Merge on tender_id index (outer join to preserve all rows)
    if cardinal_df.empty:
        merged = custom_df.reindex(columns=pd.Index(CARDINAL_FLAG_NAMES + list(custom_df.columns)))
    elif custom_df.empty:
        merged = cardinal_df.reindex(columns=pd.Index(list(cardinal_df.columns) + CUSTOM_FEATURE_NAMES))
    else:
        merged = cardinal_df.join(custom_df, how="outer")

    # Fetch metadata for temporal split and ICW score
    limit_clause = f"LIMIT {limit}" if limit is not None else ""
    try:
        conn = sqlite3.connect(db_path)
        meta_rows = conn.execute(
            f"SELECT tender_id, year, total_score FROM tenders {limit_clause}"
        ).fetchall()
        conn.close()
        meta: dict[str, dict[str, Any]] = {
            r[0]: {"year": r[1], "icw_total_score": r[2]} for r in meta_rows
        }
    except Exception as exc:
        logger.warning("Pipeline metadata query failed: %s", exc)
        meta = {}

    # Annotate rows
    merged["temporal_split"] = [
        _assign_temporal_split(meta.get(str(tid), {}).get("year"))
        for tid in merged.index
    ]
    merged["icw_total_score"] = [
        meta.get(str(tid), {}).get("icw_total_score", np.nan)
        for tid in merged.index
    ]

    # Validate: assert no duplicate tender_ids
    n_dupes = merged.index.duplicated().sum()
    if n_dupes > 0:
        logger.warning("Feature pipeline: %d duplicate tender_ids detected, keeping first.", n_dupes)
        merged = merged[~merged.index.duplicated(keep="first")]

    # Validate: assert feature count (73 cardinal + 12 custom = 85, plus metadata)
    feature_cols = [c for c in merged.columns if c not in ("temporal_split", "icw_total_score")]
    n_feat = len(feature_cols)
    if n_feat < 85:
        logger.warning("Feature pipeline: expected ≥85 feature cols, got %d.", n_feat)
    else:
        logger.info("Feature pipeline: %d feature cols — OK.", n_feat)

    logger.info(
        "Feature pipeline complete: shape=%s, splits=%s",
        merged.shape,
        pd.Series(merged["temporal_split"]).value_counts().to_dict(),
    )

    # Persist to DB if requested
    if save_to_db:
        try:
            _ensure_features_table(db_path)
            conn = sqlite3.connect(db_path)
            for tid, row_series in merged.iterrows():
                row_dict = row_series.to_dict()
                temporal_split = str(row_dict.pop("temporal_split", "train"))
                icw_score = row_dict.pop("icw_total_score", None)
                # Serialize NaN-safe feature JSON
                feat_json = _json.dumps(
                    {k: (None if (isinstance(v, float) and v != v) else v) for k, v in row_dict.items()}
                )
                conn.execute(
                    """
                    INSERT INTO features (tender_id, temporal_split, icw_total_score, feature_json)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(tender_id) DO UPDATE SET
                        temporal_split  = excluded.temporal_split,
                        icw_total_score = excluded.icw_total_score,
                        feature_json    = excluded.feature_json,
                        computed_at     = datetime('now')
                    """,
                    (str(tid), temporal_split, icw_score, feat_json),
                )
            conn.commit()
            conn.close()
            logger.info("Feature pipeline: saved %d rows to features table.", len(merged))
        except Exception as exc:
            logger.error("Feature pipeline: DB save failed: %s", exc)

    return pd.DataFrame(merged)
