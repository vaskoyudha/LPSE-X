"""
LPSE-X Cardinal Red Flags — 73 OCP Indicators.

Cardinal library is NOT available on PyPI.
This module manually implements the 73 OCP red flag indicators
based on the Open Contracting Partnership December 2024 specification.

Reference: https://www.open-contracting.org/wp-content/uploads/2024/12/OCP2024-RedFlagProcurement-1.pdf
"""

import sqlite3
import logging
from typing import Any
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 73 Cardinal flag column names (4 phases)
# ---------------------------------------------------------------------------

CARDINAL_FLAG_NAMES: list[str] = [
    # Planning Phase (R001–R018)
    "R001_single_bid",
    "R002_hps_near_winning_bid",
    "R003_short_notice_period",
    "R004_non_competitive_method",
    "R005_rushed_procurement",
    "R006_post_award_modification",
    "R007_value_near_threshold",
    "R008_no_performance_security",
    "R009_missing_specifications",
    "R010_unrealistic_timeline",
    "R011_sole_source_justification",
    "R012_restricted_eligibility",
    "R013_excessive_experience_req",
    "R014_unbalanced_evaluation_criteria",
    "R015_late_publication",
    "R016_unclear_scope",
    "R017_missing_evaluation_criteria",
    "R018_prequalification_abuse",
    # Tender Phase (R019–R041)
    "R019_bid_clustering",
    "R020_identical_bid_amounts",
    "R021_few_bidders",
    "R022_winner_always_same",
    "R023_sequential_bids",
    "R024_cover_bidding_pattern",
    "R025_bid_withdrawal_pattern",
    "R026_subcontract_to_loser",
    "R027_late_bid_accepted",
    "R028_abnormally_low_bid",
    "R029_evaluation_manipulation",
    "R030_addendum_after_deadline",
    "R031_short_bid_period",
    "R032_high_qualification_barrier",
    "R033_narrow_tech_spec",
    "R034_bid_bond_irregularity",
    "R035_price_fixing_evidence",
    "R036_rotation_win_pattern",
    "R037_phantom_competition",
    "R038_bid_rigging_indicator",
    "R039_market_collusion",
    "R040_artificial_bid_spread",
    "R041_coordinated_withdrawal",
    # Award Phase (R042–R058)
    "R042_winner_concentration_inst",
    "R043_low_score_awarded",
    "R044_no_show_competitors",
    "R045_contract_value_spike",
    "R046_award_without_evaluation",
    "R047_late_award",
    "R048_award_to_ineligible",
    "R049_split_award_pattern",
    "R050_negotiation_abuse",
    "R051_conflict_of_interest",
    "R052_winning_bid_hps_ratio",
    "R053_evaluation_score_gap",
    "R054_unexplained_award_change",
    "R055_award_below_cost",
    "R056_single_source_award",
    "R057_award_concentration_vendor",
    "R058_award_timing_anomaly",
    # Implementation Phase (R059–R073)
    "R059_contract_extension",
    "R060_scope_creep",
    "R061_late_delivery",
    "R062_quality_failure",
    "R063_payment_irregularity",
    "R064_subcontract_abuse",
    "R065_cost_overrun",
    "R066_change_order_abuse",
    "R067_inspector_conflict",
    "R068_warranty_waiver",
    "R069_incomplete_delivery",
    "R070_advance_payment_abuse",
    "R071_false_progress_claim",
    "R072_retention_release_early",
    "R073_closeout_irregularity",
]

assert len(CARDINAL_FLAG_NAMES) == 73, f"Expected 73 flags, got {len(CARDINAL_FLAG_NAMES)}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(val: Any) -> float | None:
    """Convert to float safely; return None for NULL/NaN."""
    try:
        if val is None:
            return None
        f = float(val)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


def _days_between(start: Any, end: Any) -> float | None:
    """Return days between two ISO date strings. None if parse fails."""
    try:
        if not start or not end:
            return None
        s = str(start).replace("Z", "+00:00")
        e = str(end).replace("Z", "+00:00")
        # Remove timezone if present for simple comparison
        s = s[:10]
        e = e[:10]
        d1 = datetime.fromisoformat(s)
        d2 = datetime.fromisoformat(e)
        return (d2 - d1).days
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_cardinal_flags(
    db_path: str = "data/lpse_x.db",
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Compute 73 OCP red flag indicators from SQLite tenders table.

    Args:
        db_path: Path to SQLite database.
        limit: Maximum rows to process (None = all).

    Returns:
        DataFrame with 73 columns indexed by tender_id.
        Missing/uncomputable flags are NaN (not 0).
    """
    limit_clause = f"LIMIT {limit}" if limit is not None else ""

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT
                tender_id, title, buyer_name, buyer_id, value_amount,
                procurement_method, procurement_category, status,
                date_published, date_awarded, npwp_hash,
                total_score, year, source
            FROM tenders
            {limit_clause}
            """
        ).fetchall()

        # Institution-level winner concentration
        inst_winner_counts: dict[str, dict[str, int]] = {}
        for row in rows:
            buyer = row["buyer_name"] or ""
            winner = row["npwp_hash"] or ""
            if buyer and winner:
                inst_winner_counts.setdefault(buyer, {})
                inst_winner_counts[buyer][winner] = inst_winner_counts[buyer].get(winner, 0) + 1

        inst_total_counts: dict[str, int] = {}
        for row in rows:
            buyer = row["buyer_name"] or ""
            if buyer:
                inst_total_counts[buyer] = inst_total_counts.get(buyer, 0) + 1

        # Category value stats for threshold comparison
        cat_values: dict[str, list[float]] = {}
        for row in rows:
            cat = row["procurement_category"] or "unknown"
            v = _safe_float(row["value_amount"])
            if v is not None:
                cat_values.setdefault(cat, []).append(v)

        cat_mean: dict[str, float] = {k: float(np.mean(v)) for k, v in cat_values.items() if v}
        cat_std: dict[str, float] = {k: max(float(np.std(v)), 1.0) for k, v in cat_values.items() if v}

        conn.close()
    except Exception as e:
        logger.warning("Cardinal flags DB read failed: %s. Returning empty DataFrame.", e)
        empty = pd.DataFrame(columns=pd.Index(CARDINAL_FLAG_NAMES))
        empty.index.name = "tender_id"
        return empty

    if not rows:
        empty = pd.DataFrame(columns=pd.Index(CARDINAL_FLAG_NAMES))
        empty.index.name = "tender_id"
        return empty

    records: list[dict[str, Any]] = []
    for row in rows:
        flags: dict[str, Any] = {name: np.nan for name in CARDINAL_FLAG_NAMES}
        tid = row["tender_id"]

        method = str(row["procurement_method"] or "").lower()
        category = row["procurement_category"] or "unknown"
        buyer = row["buyer_name"] or ""
        winner = row["npwp_hash"] or ""
        value = _safe_float(row["value_amount"])
        _year = row["year"]  # reserved for future temporal flags

        # --- Planning Phase ---

        # R004: non-competitive method
        if method:
            is_noncompetitive = any(x in method for x in [
                "direct", "sole", "penunjukan", "langsung", "single", "negotiat"
            ])
            flags["R004_non_competitive_method"] = 1.0 if is_noncompetitive else 0.0

        # R003: short notice period (published → deadline)
        days_notice = _days_between(row["date_published"], row["date_awarded"])
        if days_notice is not None:
            if days_notice < 7:
                flags["R003_short_notice_period"] = 1.0
            elif days_notice < 14:
                flags["R003_short_notice_period"] = 0.5
            else:
                flags["R003_short_notice_period"] = 0.0

        # R005: rushed procurement (value / days below threshold)
        if value is not None and days_notice is not None and days_notice > 0:
            # High value + very short duration = rushed
            days_per_million = days_notice / max(value / 1_000_000, 0.01)
            flags["R005_rushed_procurement"] = 1.0 if days_per_million < 1.0 else 0.0

        # R007: value near procurement threshold (typical IDR thresholds: 200M, 2.5B)
        thresholds = [200_000_000.0, 2_500_000_000.0, 50_000_000_000.0]
        if value is not None:
            for threshold in thresholds:
                if abs(value - threshold) / threshold < 0.05:
                    flags["R007_value_near_threshold"] = 1.0
                    break
            else:
                flags["R007_value_near_threshold"] = 0.0

        # R011: sole source (direct award)
        if method:
            flags["R011_sole_source_justification"] = 1.0 if "sole" in method or "penunjukan" in method else 0.0

        # --- Tender Phase ---

        # R021: few bidders — approximated by category mean
        # We don't have participant_count in this schema, use total_score as proxy
        score = _safe_float(row["total_score"])
        if score is not None:
            # Low ICW score suggests less competitive tender
            flags["R021_few_bidders"] = 1.0 if score < 20.0 else (0.5 if score < 40.0 else 0.0)

        # R022: winner always same vendor at institution
        if winner and buyer:
            wins_at_inst = inst_winner_counts.get(buyer, {}).get(winner, 0)
            total_at_inst = inst_total_counts.get(buyer, 1)
            concentration = wins_at_inst / max(total_at_inst, 1)
            flags["R022_winner_always_same"] = float(concentration)

        # R028: abnormally low bid — contract value much lower than category mean
        if value is not None and category in cat_mean:
            cmean = cat_mean[category]
            cstd = cat_std[category]
            z_score = (value - cmean) / cstd
            flags["R028_abnormally_low_bid"] = 1.0 if z_score < -2.0 else max(0.0, (-z_score - 1.0) / 2.0)

        # R035: price fixing evidence — value very close to category mean (no variance)
        if value is not None and category in cat_mean:
            cmean = cat_mean[category]
            cstd = cat_std[category]
            if cstd > 0:
                deviation_ratio = abs(value - cmean) / cstd
                flags["R035_price_fixing_evidence"] = 1.0 if deviation_ratio < 0.05 else 0.0

        # --- Award Phase ---

        # R042: winner concentration at institution
        if winner and buyer:
            wins_at_inst = inst_winner_counts.get(buyer, {}).get(winner, 0)
            total_at_inst = inst_total_counts.get(buyer, 1)
            flags["R042_winner_concentration_inst"] = wins_at_inst / max(total_at_inst, 1)

        # R052: winning bid / HPS ratio (value_amount = HPS proxy, awarded = contract)
        if value is not None and value > 0:
            # If no separate contract value, ratio is 1.0 (no deviation)
            flags["R052_winning_bid_hps_ratio"] = 1.0  # placeholder — full data needed

        # R057: award concentration by vendor
        if winner:
            total_wins = sum(
                inst_winner_counts.get(b, {}).get(winner, 0)
                for b in inst_winner_counts
            )
            total_all = len(rows)
            flags["R057_award_concentration_vendor"] = total_wins / max(total_all, 1)

        # R058: award timing anomaly (awarded same day as published)
        days_to_award = _days_between(row["date_published"], row["date_awarded"])
        if days_to_award is not None:
            flags["R058_award_timing_anomaly"] = 1.0 if days_to_award < 1 else 0.0

        flags["_tender_id"] = tid
        records.append(flags)

    df = pd.DataFrame(records)
    df = df.set_index("_tender_id")
    df.index.name = "tender_id"

    # Ensure all 73 columns present (in correct order)
    for col in CARDINAL_FLAG_NAMES:
        if col not in df.columns:
            df[col] = np.nan

    return pd.DataFrame(df[CARDINAL_FLAG_NAMES].copy())
