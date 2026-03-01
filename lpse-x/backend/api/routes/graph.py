"""
T14: Graph Route
GET /api/graph — return vendor graph communities (Leiden detection results)
"""
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
import aiosqlite
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
    Communities are sorted by cartel risk score (descending).
    """
    try:
        from backend.config.runtime import get_config
        cfg = get_config()
        db_path = "data/lpse_x.db"
        communities: list[dict] = []
        try:
            async with aiosqlite.connect(db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    """
                    SELECT community_id, member_ids, risk_score, size, detected_at
                    FROM communities
                    WHERE size >= ?
                    ORDER BY risk_score DESC
                    LIMIT ?
                    """,
                    (min_community_size, top_n),
                )
                rows = await cursor.fetchall()
                for row in rows:
                    communities.append({
                        "community_id": row["community_id"],
                        "members": json.loads(row["member_ids"]),
                        "risk_score": row["risk_score"],
                        "size": row["size"],
                        "detected_at": row["detected_at"],
                    })
        except aiosqlite.OperationalError:
            # Table doesn't exist yet — no communities have been computed
            logger.info("get_graph_communities: communities table not found — no data ingested yet")

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
    co-bidding partners and risk score.
    """
    try:


        db_path = "data/lpse_x.db"

        result: dict = {
            "status": "ok",
            "vendor_id": vendor_id,
            "in_community": False,
            "community_id": None,
            "community_risk_score": None,
            "co_bidders": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            async with aiosqlite.connect(db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT community_id, member_ids, risk_score FROM communities",
                )
                rows = await cursor.fetchall()
                for row in rows:
                    members = json.loads(row["member_ids"])
                    if vendor_id in members:
                        co_bidders = [m for m in members if m != vendor_id]
                        result.update({
                            "in_community": True,
                            "community_id": row["community_id"],
                            "community_risk_score": row["risk_score"],
                            "co_bidders": co_bidders,
                        })
                        break
        except aiosqlite.OperationalError:
            logger.info("get_vendor_community: communities table not found")

        return result

    except Exception as exc:
        logger.exception("get_vendor_community failed for vendor_id=%s", vendor_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ) from exc
