"""
LPSE-X Cartel Suspicion Scorer.

Combines four community-level signals into a cartel suspicion score (0–1)
using configurable weights.  All weight thresholds come from runtime_config.yaml
via get_config() — never hardcoded.

Weights (default — overridable via runtime config custom_params):
  intra_bid_frequency : 0.30
  win_rotation        : 0.30
  price_similarity    : 0.20
  geographic_overlap  : 0.20
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Weight defaults (loaded from runtime config if available)
# ---------------------------------------------------------------------------

_DEFAULT_WEIGHTS: dict[str, float] = {
    "intra_bid_frequency": 0.30,
    "win_rotation": 0.30,
    "price_similarity": 0.20,
    "geographic_overlap": 0.20,
}


def _get_weights() -> dict[str, float]:
    """Return weights from runtime config or fall back to defaults."""
    try:
        from backend.config.runtime import get_config  # local import — optional dep
        cfg = get_config()
        w = _DEFAULT_WEIGHTS.copy()
        for key in _DEFAULT_WEIGHTS:
            override = cfg.custom_params.get(f"cartel_weight_{key}")
            if override is not None:
                try:
                    w[key] = float(override)
                except (TypeError, ValueError):
                    pass
        return w
    except Exception:
        return _DEFAULT_WEIGHTS.copy()


# ---------------------------------------------------------------------------
# Per-signal computations
# ---------------------------------------------------------------------------

def _intra_bid_frequency(member_ids: list[str], db_path: str) -> float:
    """
    Fraction of tenders where ≥2 community members co-bid.

    Returns 0.0 when data is insufficient.
    """
    if len(member_ids) < 2:
        return 0.0
    try:
        placeholders = ",".join("?" * len(member_ids))
        query = f"""
            SELECT tender_id, COUNT(*) as member_count
            FROM tenders
            WHERE npwp_hash IN ({placeholders})
            GROUP BY tender_id
            HAVING member_count >= 2
        """
        conn = sqlite3.connect(db_path)
        co_bid_rows = conn.execute(query, member_ids).fetchall()

        total_rows = conn.execute(
            f"SELECT COUNT(DISTINCT tender_id) FROM tenders WHERE npwp_hash IN ({placeholders})",
            member_ids,
        ).fetchone()
        conn.close()

        total = int(total_rows[0]) if total_rows else 0
        co_bids = len(co_bid_rows)
        return min(1.0, co_bids / total) if total > 0 else 0.0
    except Exception as exc:
        logger.debug("intra_bid_frequency: %s", exc)
        return 0.0


def _win_rotation(member_ids: list[str], db_path: str) -> float:
    """
    Sequential win rotation score.

    High when wins are spread evenly among members (no single dominant winner).
    Shannon entropy of win distribution, normalised to [0, 1].
    """
    if len(member_ids) < 2:
        return 0.0
    try:
        import math
        placeholders = ",".join("?" * len(member_ids))
        query = f"""
            SELECT npwp_hash, COUNT(*) as wins
            FROM tenders
            WHERE npwp_hash IN ({placeholders})
              AND status LIKE '%award%'
            GROUP BY npwp_hash
        """
        conn = sqlite3.connect(db_path)
        rows = conn.execute(query, member_ids).fetchall()
        conn.close()

        if not rows:
            return 0.0

        wins = [int(r[1]) for r in rows]
        total = sum(wins)
        if total == 0:
            return 0.0

        # Normalised Shannon entropy
        probs = [w / total for w in wins]
        entropy = -sum(p * math.log2(p) for p in probs if p > 0)
        max_entropy = math.log2(len(member_ids))
        return (entropy / max_entropy) if max_entropy > 0 else 0.0
    except Exception as exc:
        logger.debug("win_rotation: %s", exc)
        return 0.0


def _price_similarity(member_ids: list[str], db_path: str) -> float:
    """
    Bid amount clustering score.

    Low coefficient of variation among member bid amounts → high similarity.
    Score = 1 - CV (clamped to [0, 1]).
    """
    if len(member_ids) < 2:
        return 0.0
    try:
        import statistics
        placeholders = ",".join("?" * len(member_ids))
        query = f"""
            SELECT value_amount FROM tenders
            WHERE npwp_hash IN ({placeholders})
              AND value_amount IS NOT NULL
              AND value_amount > 0
        """
        conn = sqlite3.connect(db_path)
        rows = conn.execute(query, member_ids).fetchall()
        conn.close()

        amounts = [float(r[0]) for r in rows]
        if len(amounts) < 2:
            return 0.0

        mean = statistics.mean(amounts)
        stdev = statistics.stdev(amounts)
        if mean == 0:
            return 0.0
        cv = stdev / mean
        return max(0.0, min(1.0, 1.0 - cv))
    except Exception as exc:
        logger.debug("price_similarity: %s", exc)
        return 0.0


def _geographic_overlap(member_ids: list[str], db_path: str) -> float:
    """
    Fraction of community tenders sharing the same buyer_name.

    High when all members concentrate on a single institution.
    """
    if len(member_ids) < 2:
        return 0.0
    try:
        placeholders = ",".join("?" * len(member_ids))
        query = f"""
            SELECT buyer_name, COUNT(*) as cnt
            FROM tenders
            WHERE npwp_hash IN ({placeholders})
              AND buyer_name IS NOT NULL
            GROUP BY buyer_name
            ORDER BY cnt DESC
            LIMIT 1
        """
        conn = sqlite3.connect(db_path)
        top_row = conn.execute(query, member_ids).fetchone()

        total_row = conn.execute(
            f"SELECT COUNT(*) FROM tenders WHERE npwp_hash IN ({placeholders})",
            member_ids,
        ).fetchone()
        conn.close()

        if not top_row or not total_row:
            return 0.0

        top_count = int(top_row[1])
        total = int(total_row[0])
        return min(1.0, top_count / total) if total > 0 else 0.0
    except Exception as exc:
        logger.debug("geographic_overlap: %s", exc)
        return 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_communities(
    communities: list[dict[str, Any]],
    db_path: str = "data/lpse_x.db",
) -> list[dict[str, Any]]:
    """
    Score each community with a cartel suspicion score in [0, 1].

    Mutates each community dict in-place (adds/updates ``risk_score``).
    Also updates the ``communities`` table in SQLite if records exist.

    Args:
        communities: Output from ``detect_communities()``.
        db_path:     Path to SQLite database.

    Returns:
        Same list with ``risk_score`` populated on every entry.
    """
    weights = _get_weights()
    logger.info("score_communities: weights=%s", weights)

    for c in communities:
        member_ids: list[str] = c.get("member_ids", [])

        ibf = _intra_bid_frequency(member_ids, db_path)
        wr = _win_rotation(member_ids, db_path)
        ps = _price_similarity(member_ids, db_path)
        go = _geographic_overlap(member_ids, db_path)

        score = (
            weights["intra_bid_frequency"] * ibf
            + weights["win_rotation"] * wr
            + weights["price_similarity"] * ps
            + weights["geographic_overlap"] * go
        )
        score = max(0.0, min(1.0, score))
        c["risk_score"] = round(score, 4)

        logger.debug(
            "community %s: ibf=%.3f wr=%.3f ps=%.3f go=%.3f → score=%.4f",
            c.get("community_id", "?"),
            ibf,
            wr,
            ps,
            go,
            score,
        )

    # Backfill scores to DB
    _update_scores_in_db(communities, db_path)
    return communities


def _update_scores_in_db(
    communities: list[dict[str, Any]], db_path: str
) -> None:
    """Update risk_score for existing community rows in SQLite."""
    try:
        conn = sqlite3.connect(db_path)
        for c in communities:
            conn.execute(
                "UPDATE communities SET risk_score = ? WHERE community_id = ?",
                (float(c["risk_score"]), c["community_id"]),
            )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.debug("_update_scores_in_db: %s", exc)
