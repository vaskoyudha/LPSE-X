"""
LPSE-X Oracle Sandwich Orchestrator
=====================================
Combines all 5 XAI layers into a unified fault-tolerant response.

Layers:
  1. SHAP    — Global/Local Feature Importance (TreeSHAP)
  2. DiCE    — Counterfactual Explanations (cached, not blocking)
  3. Anchors — Rule-based Explanation (AnchorTabular from alibi)
  4. Leiden  — Graph Community Detection (from backend.graph)
  5. Benford — Statistical Forensics (from backend.analysis)

Design principles:
  - Each layer runs independently — one failure does NOT crash others
  - Returns partial result with error info if any layer fails
  - Configurable timeouts via runtime_config.yaml custom_params
  - All timing logged for SLA monitoring

Performance SLAs (from plan):
  SHAP:   < 2s
  DiCE:   cached/async, not blocking
  Anchors: < 5s
  Leiden: < 3s
  Benford: < 1s

References:
  UPGRADE 3 lines 137-148 — Oracle Sandwich architecture
  DEEP_RESEARCH_SYNTHESIS.md lines 210-238 — Enhanced Oracle Sandwich
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.config.runtime import get_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default SLA timeouts (seconds) — overridable via custom_params
# ---------------------------------------------------------------------------
DEFAULT_TIMEOUTS: dict[str, float] = {
    "shap": 2.0,
    "dice": 10.0,
    "anchors": 5.0,
    "leiden": 3.0,
    "benford": 1.0,
}


def _get_timeouts() -> dict[str, float]:
    """Read per-layer timeouts from runtime config, fall back to defaults."""
    cfg = get_config()
    timeouts = dict(DEFAULT_TIMEOUTS)
    for layer in DEFAULT_TIMEOUTS:
        key = f"xai_timeout_{layer}"
        if key in cfg.custom_params:
            timeouts[layer] = float(cfg.custom_params[key])
    return timeouts


# ---------------------------------------------------------------------------
# Layer result container
# ---------------------------------------------------------------------------

@dataclass
class LayerResult:
    """Container for a single XAI layer result (success or failure)."""
    layer_name: str
    status: str                          # "ok" | "error" | "not_applicable"
    data: Any = None                     # Layer-specific result object
    error: str | None = None             # Error message if status == "error"
    computation_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Full Oracle Sandwich result
# ---------------------------------------------------------------------------

@dataclass
class OracleSandwichResult:
    """
    Complete 5-layer Oracle Sandwich explanation for a single tender.
    All layers are independent — partial results are valid.
    """
    tender_id: str
    shap: LayerResult
    dice: LayerResult
    anchors: LayerResult
    leiden: LayerResult
    benford: LayerResult

    total_seconds: float = 0.0
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    layers_ok: int = 0                   # count of successful layers
    layers_failed: int = 0               # count of failed layers

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict for API responses."""
        def _layer_dict(lr: LayerResult) -> dict[str, Any]:
            d: dict[str, Any] = {
                "status": lr.status,
                "computation_seconds": lr.computation_seconds,
            }
            if lr.error:
                d["error"] = lr.error
            if lr.data is not None:
                # Convert dataclasses to dicts
                if hasattr(lr.data, "__dataclass_fields__"):
                    import dataclasses
                    d["data"] = dataclasses.asdict(lr.data)
                elif hasattr(lr.data, "dict"):
                    d["data"] = lr.data.dict()
                else:
                    d["data"] = lr.data
            return d

        return {
            "tender_id": self.tender_id,
            "generated_at": self.generated_at,
            "total_seconds": self.total_seconds,
            "layers_ok": self.layers_ok,
            "layers_failed": self.layers_failed,
            "shap": _layer_dict(self.shap),
            "dice": _layer_dict(self.dice),
            "anchors": _layer_dict(self.anchors),
            "leiden": _layer_dict(self.leiden),
            "benford": _layer_dict(self.benford),
        }


# ---------------------------------------------------------------------------
# Layer runners (each wrapped in try/except for fault tolerance)
# ---------------------------------------------------------------------------

def _run_shap(
    tender_id: str,
    model: Any,
    instance_df: Any,
    timeout: float,
) -> LayerResult:
    """Run SHAP local explanation. Returns LayerResult."""
    t0 = time.perf_counter()
    try:
        from backend.xai.shap_explainer import compute_shap_local
        result = compute_shap_local(
            model=model,
            instance=instance_df,
            tender_id=tender_id,
        )
        elapsed = time.perf_counter() - t0
        return LayerResult(
            layer_name="shap",
            status="ok",
            data=result,
            computation_seconds=round(elapsed, 4),
        )
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error("SHAP layer failed for tender %s: %s", tender_id, exc)
        return LayerResult(
            layer_name="shap",
            status="error",
            error=str(exc),
            computation_seconds=round(elapsed, 4),
        )


def _run_dice(
    tender_id: str,
    dice_result_cache: dict[str, Any] | None,
) -> LayerResult:
    """
    Return DiCE result from cache. DiCE is pre-computed asynchronously —
    NOT blocking main inference per competition rules.
    If not cached, return not_applicable (do NOT block here).
    """
    t0 = time.perf_counter()
    try:
        if dice_result_cache and tender_id in dice_result_cache:
            cached = dice_result_cache[tender_id]
            elapsed = time.perf_counter() - t0
            return LayerResult(
                layer_name="dice",
                status="ok",
                data=cached,
                computation_seconds=round(elapsed, 4),
            )
        else:
            elapsed = time.perf_counter() - t0
            return LayerResult(
                layer_name="dice",
                status="not_applicable",
                data={"message": "DiCE counterfactuals not yet computed. Run /api/xai/dice/precompute to generate."},
                computation_seconds=round(elapsed, 4),
            )
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error("DiCE layer failed for tender %s: %s", tender_id, exc)
        return LayerResult(
            layer_name="dice",
            status="error",
            error=str(exc),
            computation_seconds=round(elapsed, 4),
        )


def _run_anchors(
    tender_id: str,
    anchor_explainer: Any,
    instance_df: Any,
    timeout: float,
) -> LayerResult:
    """Run Anchors rule extraction. Returns LayerResult."""
    t0 = time.perf_counter()
    try:
        if anchor_explainer is None:
            return LayerResult(
                layer_name="anchors",
                status="not_applicable",
                data={"message": "Anchor explainer not initialized. Call fit_anchor_explainer() first."},
                computation_seconds=0.0,
            )
        from backend.xai.anchor_explainer import compute_anchors
        result = compute_anchors(
            explainer=anchor_explainer,
            instance=instance_df,
            tender_id=tender_id,
            timeout=timeout,
        )
        elapsed = time.perf_counter() - t0
        status = "ok" if result.error is None else "error"
        return LayerResult(
            layer_name="anchors",
            status=status,
            data=result,
            error=result.error,
            computation_seconds=round(elapsed, 4),
        )
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error("Anchors layer failed for tender %s: %s", tender_id, exc)
        return LayerResult(
            layer_name="anchors",
            status="error",
            error=str(exc),
            computation_seconds=round(elapsed, 4),
        )


def _run_leiden(
    tender_id: str,
    leiden_communities: dict[str, Any] | None,
    timeout: float,
) -> LayerResult:
    """Look up tender in pre-computed Leiden community results."""
    t0 = time.perf_counter()
    try:
        if leiden_communities is None:
            return LayerResult(
                layer_name="leiden",
                status="not_applicable",
                data={"message": "Leiden graph not computed. Run graph detection first."},
                computation_seconds=0.0,
            )

        # leiden_communities is a dict: tender_id -> community info
        community_info = leiden_communities.get(tender_id, None)
        elapsed = time.perf_counter() - t0
        if community_info is None:
            return LayerResult(
                layer_name="leiden",
                status="not_applicable",
                data={"message": f"Tender {tender_id} not found in any detected community."},
                computation_seconds=round(elapsed, 4),
            )
        return LayerResult(
            layer_name="leiden",
            status="ok",
            data=community_info,
            computation_seconds=round(elapsed, 4),
        )
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error("Leiden layer failed for tender %s: %s", tender_id, exc)
        return LayerResult(
            layer_name="leiden",
            status="error",
            error=str(exc),
            computation_seconds=round(elapsed, 4),
        )


def _run_benford(
    tender_id: str,
    amount_series: Any | None,
    timeout: float,
) -> LayerResult:
    """Run Benford's Law analysis on the amount series for context."""
    t0 = time.perf_counter()
    try:
        if amount_series is None or len(amount_series) < 100:
            n = len(amount_series) if amount_series is not None else 0
            return LayerResult(
                layer_name="benford",
                status="not_applicable",
                data={
                    "message": f"Benford analysis requires >=100 records, got {n}.",
                    "applicability": False,
                },
                computation_seconds=0.0,
            )
        from backend.analysis.benford import run_benford_analysis
        import pandas as pd
        series = pd.Series(amount_series, dtype=float)
        result = run_benford_analysis(series, label=f"tender_{tender_id}_context")
        elapsed = time.perf_counter() - t0
        return LayerResult(
            layer_name="benford",
            status="ok" if result.get("applicable") else "not_applicable",
            data=result,
            computation_seconds=round(elapsed, 4),
        )
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error("Benford layer failed for tender %s: %s", tender_id, exc)
        return LayerResult(
            layer_name="benford",
            status="error",
            error=str(exc),
            computation_seconds=round(elapsed, 4),
        )


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def explain_tender(
    tender_id: str,
    model: Any,
    instance_df: Any,
    *,
    anchor_explainer: Any | None = None,
    leiden_communities: dict[str, Any] | None = None,
    dice_result_cache: dict[str, Any] | None = None,
    amount_series: Any | None = None,
) -> OracleSandwichResult:
    """
    Run all 5 Oracle Sandwich XAI layers for a single tender.

    Each layer is fault-tolerant — if one fails, the others continue.
    Returns a complete OracleSandwichResult with status per layer.

    Parameters
    ----------
    tender_id:
        Tender identifier for logging and output.
    model:
        Fitted XGBClassifier (used by SHAP + Anchors).
    instance_df:
        Single-row pandas DataFrame with feature values.
    anchor_explainer:
        Optional pre-fitted AnchorTabular explainer. If None, anchors layer
        returns not_applicable.
    leiden_communities:
        Optional dict mapping tender_id → community info. If None, leiden
        layer returns not_applicable.
    dice_result_cache:
        Optional dict mapping tender_id → pre-computed DiCE result.
        DiCE is NEVER computed synchronously here — must be pre-cached.
    amount_series:
        Optional array/Series of amounts for Benford analysis. Needs >=100 values.

    Returns
    -------
    OracleSandwichResult with all 5 LayerResults.
    """
    t_total = time.perf_counter()
    timeouts = _get_timeouts()

    logger.info("Oracle Sandwich: explaining tender %s", tender_id)

    # Run all layers sequentially (each is fast except Anchors)
    # Anchors is the slowest; SHAP and Benford are <2s each
    shap_result = _run_shap(tender_id, model, instance_df, timeouts["shap"])
    dice_result = _run_dice(tender_id, dice_result_cache)
    anchor_result = _run_anchors(tender_id, anchor_explainer, instance_df, timeouts["anchors"])
    leiden_result = _run_leiden(tender_id, leiden_communities, timeouts["leiden"])
    benford_result = _run_benford(tender_id, amount_series, timeouts["benford"])

    total_elapsed = time.perf_counter() - t_total

    layers = [shap_result, dice_result, anchor_result, leiden_result, benford_result]
    ok_count = sum(1 for lr in layers if lr.status == "ok")
    fail_count = sum(1 for lr in layers if lr.status == "error")

    logger.info(
        "Oracle Sandwich complete for tender %s: %d/5 OK, %d errors, total=%.3fs",
        tender_id, ok_count, fail_count, total_elapsed,
    )

    return OracleSandwichResult(
        tender_id=tender_id,
        shap=shap_result,
        dice=dice_result,
        anchors=anchor_result,
        leiden=leiden_result,
        benford=benford_result,
        total_seconds=round(total_elapsed, 4),
        layers_ok=ok_count,
        layers_failed=fail_count,
    )
