"""
T14: XAI Route
GET  /api/xai/{tender_id}  — run Oracle Sandwich (SHAP+Anchors+Benford+Leiden) for a tender
POST /api/xai/dice/precompute — kick off background DiCE computation (non-blocking)
"""
from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
import aiosqlite

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.xai import explain_tender, OracleSandwichResult
from backend.ml.predict import _load_xgboost, _filter_features
from backend.config.runtime import get_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/xai", tags=["xai"])

# Background DiCE task tracking: {tender_id: status}
_dice_tasks: dict[str, str] = {}  # "pending" | "running" | "done" | "error"
_dice_results: dict[str, Any] = {}


class XaiRequest(BaseModel):
    """Body for GET /api/xai/{tender_id} (features needed to run Oracle Sandwich)."""
    features: dict[str, Any] = Field(..., description="Feature vector for the tender")
    amount_values: list[float] | None = Field(
        None,
        description="Historical amount values for Benford analysis"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "features": {
                    "n_bidders": 1.0,
                    "price_ratio": 0.995,
                    "bid_spread": 0.005,
                    "winner_bid_rank": 1.0,
                    "hhi": 0.95,
                    "log_amount": 19.8,
                },
                "amount_values": [4980000000, 5100000000, 4850000000]
            }
        }
    }


class DicePrecomputeRequest(BaseModel):
    """Request body for POST /api/xai/dice/precompute."""
    tender_id: str = Field(..., description="Tender identifier to precompute DiCE for")
    features: dict[str, Any] = Field(..., description="Feature vector")
    n_cfs: int = Field(default=3, ge=1, le=5, description="Number of counterfactuals (max 5)")


def _oracle_result_to_dict(result: OracleSandwichResult) -> dict:
    """Serialize OracleSandwichResult to JSON-serializable dict."""
    def _layer(lr: Any) -> dict:
        return {
            "status": getattr(lr, "status", "unknown"),
            "data": getattr(lr, "data", None),
            "error": getattr(lr, "error", None),
        }

    return {
        "tender_id": result.tender_id,
        "layers_ok": result.layers_ok,
        "layers_failed": result.layers_failed,
        "total_seconds": result.total_seconds,
        "shap": _layer(result.shap),
        "anchors": _layer(result.anchors),
        "leiden": _layer(result.leiden),
        "benford": _layer(result.benford),
        "dice": _layer(result.dice),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/{tender_id}")
async def get_xai_explanation(tender_id: str, request: XaiRequest) -> dict:
    """
    Run Oracle Sandwich 5-layer XAI for a tender.

    Layers: SHAP (feature importance) + Anchors (rules) + Leiden (graph) +
            Benford (statistical forensics) + DiCE (counterfactuals from cache).

    Note: DiCE uses cached results only (non-blocking). Use /dice/precompute
    to pre-generate counterfactuals asynchronously.
    """
    try:
        model = _load_xgboost()  # may be None — each layer handles it gracefully

        # Build single-row DataFrame (filter to 21 training features)
        row = {k: float(v) if isinstance(v, (int, float)) else 0.0
               for k, v in request.features.items()
               if k != "tender_id"}
        instance_df_full = pd.DataFrame([row])
        instance_df = _filter_features(instance_df_full)

        # Get cached DiCE result if available
        dice_cache = None
        if tender_id in _dice_results:
            dice_cache = {tender_id: _dice_results[tender_id]}

        # ---- Leiden: look up tender's vendor community from DB ----
        leiden_communities = None
        amount_series = None
        try:
            async with aiosqlite.connect("data/lpse_x.db") as db:
                db.row_factory = aiosqlite.Row
                # Get tender's vendor hash
                cur = await db.execute(
                    "SELECT npwp_hash FROM tenders WHERE tender_id = ?",
                    (tender_id,),
                )
                tender_row = await cur.fetchone()
                vendor_hash = tender_row["npwp_hash"] if tender_row else None

                if vendor_hash:
                    # Find community containing this vendor
                    cur2 = await db.execute(
                        "SELECT community_id, member_ids, risk_score, size FROM communities"
                    )
                    comm_rows = await cur2.fetchall()
                    for crow in comm_rows:
                        members = json.loads(crow["member_ids"])
                        if vendor_hash in members:
                            leiden_communities = {
                                tender_id: {
                                    "community_id": crow["community_id"],
                                    "members": members,
                                    "risk_score": crow["risk_score"],
                                    "size": crow["size"],
                                    "vendor_hash": vendor_hash,
                                }
                            }
                            break

                # ---- Benford: fetch all positive value_amounts from DB ----
                cur3 = await db.execute(
                    "SELECT value_amount FROM tenders WHERE value_amount IS NOT NULL AND value_amount > 0"
                )
                amount_rows = await cur3.fetchall()
                if len(amount_rows) >= 100:
                    amount_series = pd.Series(
                        [float(r["value_amount"]) for r in amount_rows],
                        dtype=float,
                    )
        except Exception as db_exc:
            logger.warning("XAI DB lookup failed (Leiden/Benford): %s", db_exc)

        # Override with request-provided amounts if available
        if request.amount_values:
            amount_series = pd.Series(request.amount_values)

        result = explain_tender(
            tender_id=tender_id,
            model=model,
            instance_df=instance_df,
            leiden_communities=leiden_communities,
            dice_result_cache=dice_cache,
            amount_series=amount_series,
        )

        return {
            "status": "ok",
            "data": _oracle_result_to_dict(result),
        }

    except Exception as exc:
        logger.exception("get_xai_explanation failed for tender_id=%s", tender_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(exc),
                "tender_id": tender_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ) from exc


async def _background_dice_task(tender_id: str, features: dict, n_cfs: int) -> None:
    """Async background task for DiCE computation. NEVER blocks the main thread."""
    _dice_tasks[tender_id] = "running"
    try:
        from backend.xai.dice_explainer import DiceExplainer
        import numpy as np

        model = _load_xgboost()
        if model is None:
            raise ValueError("XGBoost model not loaded")

        row = {k: float(v) if isinstance(v, (int, float)) else 0.0
               for k, v in features.items()
               if k != "tender_id"}
        instance_df = pd.DataFrame([row])

        # DiceExplainer with genetic method (never "random" in production)
        explainer = DiceExplainer(
            model=model,
            feature_names=list(row.keys()),
            method="genetic",  # NOT "random" — competition rule
        )
        explainer.fit(instance_df)

        instance_array = instance_df.values
        result = explainer.generate_counterfactuals(
            instance=instance_array,
            n_cfs=n_cfs,
            desired_class=0,  # target: low risk
        )

        _dice_results[tender_id] = result
        _dice_tasks[tender_id] = "done"
        logger.info("DiCE precompute complete for tender_id=%s", tender_id)

    except Exception as exc:
        logger.exception("DiCE precompute failed for tender_id=%s: %s", tender_id, exc)
        _dice_tasks[tender_id] = "error"
        _dice_results[tender_id] = {"error": str(exc)}


@router.post("/dice/precompute")
async def precompute_dice(request: DicePrecomputeRequest) -> dict:
    """
    Kick off DiCE counterfactual precomputation in background.

    Returns 202 Accepted immediately — use GET /api/xai/dice/status/{tender_id}
    to check progress. Results cached in memory and used by Oracle Sandwich.

    Competition rule: max 5 counterfactuals per request.
    Competition rule: NEVER use method="random" — always "genetic".
    """
    tender_id = request.tender_id

    if _dice_tasks.get(tender_id) == "running":
        return {
            "status": "already_running",
            "tender_id": tender_id,
            "message": "DiCE computation already in progress",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Kick off as background task — non-blocking
    asyncio.create_task(
        _background_dice_task(tender_id, request.features, request.n_cfs)
    )
    _dice_tasks[tender_id] = "pending"

    return {
        "status": "accepted",
        "tender_id": tender_id,
        "n_cfs": request.n_cfs,
        "message": "DiCE computation started in background",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/dice/status/{tender_id}")
async def get_dice_status(tender_id: str) -> dict:
    """Check status of DiCE precomputation for a tender."""
    status = _dice_tasks.get(tender_id, "not_started")
    result_available = tender_id in _dice_results and _dice_tasks.get(tender_id) == "done"

    return {
        "tender_id": tender_id,
        "status": status,
        "result_available": result_available,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
