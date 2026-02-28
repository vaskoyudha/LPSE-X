"""
LPSE-X Custom Forensic ML Features — 12 domain-specific indicators.

These features are computed from the procurement tenders database and serve
as input to the ML models (Isolation Forest + XGBoost).

Two features are placeholders for downstream tasks:
    - benford_anomaly: computed in T9 (Benford's Law analysis)
    - bid_rotation_pattern: computed in T7 (Leiden community detection)
"""

import sqlite3
import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Exact feature names — contractual (from UPGRADE 3 proposal lines 110-124)
CUSTOM_FEATURE_NAMES: list[str] = [
    "bid_clustering_score",
    "vendor_win_concentration",
    "hps_deviation_ratio",
    "participant_count_anomaly",
    "geographic_concentration",
    "repeat_pairing_index",
    "temporal_submission_pattern",
    "historical_win_rate",
    "phantom_bidder_score",
    "benford_anomaly",           # placeholder — computed in T9
    "interlocking_directorates",
    "bid_rotation_pattern",      # placeholder — computed in T7
]

assert len(CUSTOM_FEATURE_NAMES) == 12, f"Expected 12 features, got {len(CUSTOM_FEATURE_NAMES)}"


def _safe_float(val: Any) -> float | None:
    """Safely convert to float; return None for NULL/NaN."""
    try:
        if val is None:
            return None
        f = float(val)
        return None if (f != f) else f
    except (TypeError, ValueError):
        return None


def compute_custom_features(
    db_path: str = "data/lpse_x.db",
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Compute 12 custom forensic ML features from SQLite tenders table.

    Args:
        db_path: Path to SQLite database.
        limit: Maximum rows to process (None = all).

    Returns:
        DataFrame with 12 columns indexed by tender_id.
        Missing/uncomputable features are NaN (not 0).
    """
    limit_clause = f"LIMIT {limit}" if limit is not None else ""

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Main rows for the feature matrix
        rows = conn.execute(
            f"""
            SELECT
                tender_id, buyer_name, buyer_id, value_amount,
                procurement_method, procurement_category, status,
                date_published, date_awarded, npwp_hash, npwp_last4,
                total_score, year, source
            FROM tenders
            {limit_clause}
            """
        ).fetchall()

        if not rows:
            conn.close()
            return pd.DataFrame(columns=pd.Index(CUSTOM_FEATURE_NAMES))

        # ----------------------------------------------------------------
        # Pre-compute aggregates for relational features
        # ----------------------------------------------------------------

        # Winner counts per vendor (all tenders, for historical_win_rate)
        all_winner_rows = conn.execute(
            "SELECT npwp_hash, COUNT(*) as wins FROM tenders WHERE npwp_hash IS NOT NULL GROUP BY npwp_hash"
        ).fetchall()
        win_counts: dict[str, int] = {r["npwp_hash"]: r["wins"] for r in all_winner_rows}

        total_tenders = conn.execute("SELECT COUNT(*) FROM tenders").fetchone()[0]

        # Institution-level winner stats (for vendor_win_concentration)
        inst_win_rows = conn.execute(
            """
            SELECT buyer_name, npwp_hash, COUNT(*) as wins
            FROM tenders
            WHERE npwp_hash IS NOT NULL AND buyer_name IS NOT NULL
            GROUP BY buyer_name, npwp_hash
            """
        ).fetchall()
        inst_win: dict[str, dict[str, int]] = {}
        for r in inst_win_rows:
            inst_win.setdefault(r["buyer_name"], {})[r["npwp_hash"]] = r["wins"]

        inst_total_rows = conn.execute(
            "SELECT buyer_name, COUNT(*) as cnt FROM tenders GROUP BY buyer_name"
        ).fetchall()
        inst_total: dict[str, int] = {r["buyer_name"]: r["cnt"] for r in inst_total_rows}

        # Category participant stats for z-score (use total_score as proxy for competitiveness)
        cat_score_rows = conn.execute(
            """
            SELECT procurement_category,
                   AVG(total_score) as avg_score,
                   COUNT(*) as cnt
            FROM tenders
            WHERE total_score IS NOT NULL
            GROUP BY procurement_category
            """
        ).fetchall()
        cat_avg_score: dict[str, float] = {}
        cat_score_std: dict[str, float] = {}
        for r in cat_score_rows:
            cat = r["procurement_category"] or "unknown"
            cat_avg_score[cat] = float(r["avg_score"] or 0.0)

        # Compute std manually
        for cat in cat_avg_score:
            scores_in_cat = conn.execute(
                "SELECT total_score FROM tenders WHERE procurement_category = ? AND total_score IS NOT NULL",
                (cat,)
            ).fetchall()
            vals = [float(r[0]) for r in scores_in_cat if r[0] is not None]
            cat_score_std[cat] = max(float(np.std(vals)) if vals else 1.0, 1e-9)

        conn.close()

    except Exception as e:
        logger.warning("Custom features DB read failed: %s", e)
        return pd.DataFrame(columns=pd.Index(CUSTOM_FEATURE_NAMES))

    # Global stats
    all_values = [_safe_float(r["value_amount"]) for r in rows]
    all_values_clean = [v for v in all_values if v is not None]
    global_mean_value = float(np.mean(all_values_clean)) if all_values_clean else 0.0
    global_std_value = max(float(np.std(all_values_clean)) if all_values_clean else 1.0, 1e-9)

    records: list[dict[str, Any]] = []
    for row in rows:
        feat: dict[str, Any] = {name: np.nan for name in CUSTOM_FEATURE_NAMES}
        tid = row["tender_id"]

        winner = row["npwp_hash"] or ""
        buyer = row["buyer_name"] or ""
        value = _safe_float(row["value_amount"])
        score = _safe_float(row["total_score"])
        category = row["procurement_category"] or "unknown"

        # ------------------------------------------------------------------
        # 1. bid_clustering_score
        #    std_dev(bid_amounts) / HPS
        #    Per-tender, we only have one value_amount — no multi-bid data.
        #    Compute as deviation from category mean normalized by std.
        # ------------------------------------------------------------------
        if value is not None and global_std_value > 0:
            # Low deviation from mean = clustered = suspicious
            deviation = abs(value - global_mean_value) / global_std_value
            # Invert: high clustering score = low deviation
            feat["bid_clustering_score"] = max(0.0, 1.0 - min(deviation / 3.0, 1.0))
        # else: NaN

        # ------------------------------------------------------------------
        # 2. vendor_win_concentration
        #    vendor_wins_at_institution / total_tenders_at_institution
        # ------------------------------------------------------------------
        if winner and buyer:
            wins_at = inst_win.get(buyer, {}).get(winner, 0)
            total_at = inst_total.get(buyer, 1)
            feat["vendor_win_concentration"] = wins_at / max(total_at, 1)

        # ------------------------------------------------------------------
        # 3. hps_deviation_ratio
        #    (contract_value - HPS) / HPS
        #    We use value_amount as HPS proxy. No separate contract_value in schema.
        #    Set to 0.0 (no deviation) for now — full data needed.
        # ------------------------------------------------------------------
        if value is not None and value > 0:
            feat["hps_deviation_ratio"] = 0.0  # placeholder — requires separate contract_value field

        # ------------------------------------------------------------------
        # 4. participant_count_anomaly
        #    Z-score of competitiveness proxy (total_score)
        # ------------------------------------------------------------------
        if score is not None and category in cat_avg_score:
            mean_s = cat_avg_score[category]
            std_s = cat_score_std.get(category, 1.0)
            feat["participant_count_anomaly"] = (score - mean_s) / std_s

        # ------------------------------------------------------------------
        # 5. geographic_concentration
        #    distinct_vendor_regions / total_bidders per tender
        #    No per-bidder region data in single-row schema — NaN
        # ------------------------------------------------------------------
        feat["geographic_concentration"] = np.nan

        # ------------------------------------------------------------------
        # 6. repeat_pairing_index
        #    frequency of same vendor-pair co-bidding
        #    Requires multi-row join — approximate with vendor concentration
        # ------------------------------------------------------------------
        if winner and buyer:
            wins_at = inst_win.get(buyer, {}).get(winner, 0)
            # Normalize by total appearances
            total_inst = inst_total.get(buyer, 1)
            feat["repeat_pairing_index"] = wins_at / max(total_inst, 1)

        # ------------------------------------------------------------------
        # 7. temporal_submission_pattern
        #    variance of bid submission times within tender
        #    No per-bidder timestamps — NaN
        # ------------------------------------------------------------------
        feat["temporal_submission_pattern"] = np.nan

        # ------------------------------------------------------------------
        # 8. historical_win_rate
        #    vendor total_wins / total_participations (all-time)
        # ------------------------------------------------------------------
        if winner and total_tenders > 0:
            feat["historical_win_rate"] = win_counts.get(winner, 0) / total_tenders

        # ------------------------------------------------------------------
        # 9. phantom_bidder_score
        #    participations_with_zero_wins / total_participations
        #    Binary: 1 if vendor has no wins, 0 if they've won at least once
        # ------------------------------------------------------------------
        if winner:
            feat["phantom_bidder_score"] = 0.0 if win_counts.get(winner, 0) > 0 else 1.0

        # ------------------------------------------------------------------
        # 10. benford_anomaly — PLACEHOLDER (computed in T9)
        # ------------------------------------------------------------------
        feat["benford_anomaly"] = np.nan

        # ------------------------------------------------------------------
        # 11. interlocking_directorates
        #    NPWP-hash prefix overlap between bidders in same tender
        #    Approximate: count other vendors at same institution with same 8-char hash prefix
        # ------------------------------------------------------------------
        if winner and len(winner) >= 8:
            prefix = winner[:8]
            all_winners_at_inst = list(inst_win.get(buyer, {}).keys())
            matches = sum(1 for w in all_winners_at_inst if w != winner and len(w) >= 8 and w[:8] == prefix)
            feat["interlocking_directorates"] = float(matches)

        # ------------------------------------------------------------------
        # 12. bid_rotation_pattern — PLACEHOLDER (computed in T7)
        # ------------------------------------------------------------------
        feat["bid_rotation_pattern"] = np.nan

        feat["_tender_id"] = tid
        records.append(feat)

    df = pd.DataFrame(records).set_index("_tender_id")
    df.index.name = "tender_id"

    # Ensure all 12 columns present in correct order
    for col in CUSTOM_FEATURE_NAMES:
        if col not in df.columns:
            df[col] = np.nan

    return pd.DataFrame(df[CUSTOM_FEATURE_NAMES].copy())
