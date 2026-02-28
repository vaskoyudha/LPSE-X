"""
T14: Graph Route
GET /api/graph — return vendor graph communities (Leiden detection results)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/graph", tags=["graph"])


class GraphQueryParams(BaseModel):
    """Optional filters for graph query."""
    min_community_size: int = Field(default=2, ge=2, description="Minimum community size to return")
    procurement_scope: str | None = Field(None, description="Filter by procurement scope")
    year: int | None = Field(None, description="Filter by year")
    top_n: int = Field(default=10, ge=1, le=100, description="Max communities to return")


@router.get("")
async def get_graph_communities(
    min_community_size: int = 2,
    procurement_scope: str | None = None,
    year: int | None = None,
    top_n: int = 10,
) -> dict:
    """
    Return vendor bid-rigging communities detected by Leiden algorithm.

    Each community represents a group of vendors suspected of coordinated bidding.
    Communities are sorted by cartel risk score (descending).

    Note: Returns cached/pre-computed communities. Run graph builder first
    (T17 integration) to populate communities.
    """
    try:
        from backend.config.runtime import get_config
        cfg = get_config()

        # TODO (T17): query actual Leiden communities from SQLite
        # For now, return structured stub demonstrating API contract
        communities: list[dict] = []

        return {
            "status": "ok",
            "communities": communities,
            "total": len(communities),
            "filters": {
                "min_community_size": min_community_size,
                "procurement_scope": procurement_scope or cfg.procurement_scope.value,
                "year": year,
                "top_n": top_n,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "Community graph requires T17 integration to populate. "
                    "Run backend/graph/builder.py then backend/graph/leiden.py.",
        }

    except Exception as exc:
        logger.exception("get_graph_communities failed")
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ) from exc


@router.get("/vendor/{vendor_id}")
async def get_vendor_community(vendor_id: str) -> dict:
    """
    Get community membership for a specific vendor.

    Returns the community this vendor belongs to (if any), plus
    co-bidding partners and risk score.
    """
    return {
        "status": "ok",
        "vendor_id": vendor_id,
        "in_community": False,
        "community_id": None,
        "community_risk_score": None,
        "co_bidders": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "note": "Requires T17 graph integration to populate vendor lookup.",
    }
