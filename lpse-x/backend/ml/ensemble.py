"""
LPSE-X Tri-Method Ensemble
============================
Combines Isolation Forest + XGBoost + ICW weak labels into a final risk score.

Ensemble weights read from runtime_config.yaml (NEVER hardcoded):
  default: isolation_forest=0.35, xgboost=0.40, icw=0.25

Disagreement Protocol (UPGRADE 3 line 134):
  When ANY two models disagree by >0.3 on risk score,
  the tender is flagged for "Manual Review Priority".
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from backend.config.runtime import get_config

logger = logging.getLogger(__name__)

# Disagreement threshold -- configurable via custom_params
DEFAULT_DISAGREEMENT_THRESHOLD: float = 0.30


@dataclass
class EnsembleResult:
    """Full ensemble prediction result for one tender."""
    tender_id: str
    final_score: float                            # weighted average [0, 1]
    risk_level: str                               # Aman/Perlu Pantauan/Risiko Tinggi/Risiko Kritis
    individual_scores: dict[str, float]           # per-model scores
    disagreement_flag: bool                       # True when any two models diverge >threshold
    disagreement_detail: str                      # human-readable explanation
    manual_review_priority: bool = field(default=False)  # True when disagreement_flag


def _score_to_risk_level(score: float) -> str:
    """Map continuous score [0,1] to 4-level Bahasa Indonesia risk label."""
    if score < 0.25:
        return "Aman"
    if score < 0.50:
        return "Perlu Pantauan"
    if score < 0.80:
        return "Risiko Tinggi"
    return "Risiko Kritis"


def _get_weights() -> dict[str, float]:
    """Read ensemble weights from runtime config. Fall back to defaults."""
    cfg = get_config()
    weights: dict[str, float] = {
        "isolation_forest": float(cfg.custom_params.get("weight_iforest", 0.35)),
        "xgboost":          float(cfg.custom_params.get("weight_xgboost", 0.40)),
        "icw":              float(cfg.custom_params.get("weight_icw",     0.25)),
    }
    total = sum(weights.values())
    if abs(total - 1.0) > 0.01:
        logger.warning("Ensemble weights sum to %.4f (not 1.0) -- normalizing.", total)
        weights = {k: v / total for k, v in weights.items()}
    return weights


def _get_disagreement_threshold() -> float:
    cfg = get_config()
    return float(cfg.custom_params.get("disagreement_threshold", DEFAULT_DISAGREEMENT_THRESHOLD))


def compute_ensemble(
    tender_id: str,
    iforest_score: float,
    xgboost_score: float,
    icw_score: float,
) -> EnsembleResult:
    """
    Compute weighted-average ensemble result for one tender.

    Parameters
    ----------
    tender_id:
        Identifier for logging/output.
    iforest_score:
        Isolation Forest anomaly score in [0, 1].
    xgboost_score:
        XGBoost high-risk probability (max class probability mapped to [0,1] risk).
    icw_score:
        ICW normalized score in [0, 1].

    Returns
    -------
    EnsembleResult with final_score, risk_level, disagreement_flag, etc.
    """
    # Clamp all inputs to [0, 1]
    scores: dict[str, float] = {
        "isolation_forest": max(0.0, min(1.0, float(iforest_score))),
        "xgboost":          max(0.0, min(1.0, float(xgboost_score))),
        "icw":              max(0.0, min(1.0, float(icw_score))),
    }

    weights = _get_weights()
    final_score = sum(scores[k] * weights[k] for k in scores)
    final_score = max(0.0, min(1.0, final_score))

    # Disagreement Protocol
    threshold = _get_disagreement_threshold()
    score_values = list(scores.values())
    disagreements: list[str] = []
    model_pairs = [
        ("isolation_forest", "xgboost"),
        ("isolation_forest", "icw"),
        ("xgboost", "icw"),
    ]
    for m1, m2 in model_pairs:
        diff = abs(scores[m1] - scores[m2])
        if diff > threshold:
            disagreements.append(
                f"{m1}({scores[m1]:.3f}) vs {m2}({scores[m2]:.3f}) diff={diff:.3f}"
            )

    disagreement_flag = len(disagreements) > 0
    if disagreement_flag:
        disagreement_detail = "Disagreement detected: " + "; ".join(disagreements)
        logger.info("Tender %s flagged for manual review: %s", tender_id, disagreement_detail)
    else:
        disagreement_detail = "Models agree (all pairwise diffs <= threshold)"

    risk_level = _score_to_risk_level(final_score)

    return EnsembleResult(
        tender_id=tender_id,
        final_score=round(final_score, 6),
        risk_level=risk_level,
        individual_scores={k: round(v, 6) for k, v in scores.items()},
        disagreement_flag=disagreement_flag,
        disagreement_detail=disagreement_detail,
        manual_review_priority=disagreement_flag,
    )


def batch_ensemble(
    tender_ids: list[str],
    iforest_scores: Any,
    xgboost_scores: Any,
    icw_scores: Any,
) -> list[EnsembleResult]:
    """
    Vectorised ensemble over arrays of scores.

    Parameters
    ----------
    tender_ids:
        List of tender identifiers.
    iforest_scores, xgboost_scores, icw_scores:
        Array-like of float scores, one per tender.
    """
    results = []
    for i, tid in enumerate(tender_ids):
        results.append(
            compute_ensemble(
                tender_id=tid,
                iforest_score=float(iforest_scores[i]),
                xgboost_score=float(xgboost_scores[i]),
                icw_score=float(icw_scores[i]),
            )
        )
    return results
