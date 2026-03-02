"""
T14: Tenders Route
GET /api/tenders — list tenders with pagination, risk scores, and filters
GET /api/tenders/{id} — get full tender with features and prediction
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tenders", tags=["tenders"])


@router.get("")
async def get_tenders(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    risk_level: str | None = Query(default=None, description="Filter by risk level"),
) -> dict:
    """
    List tenders with pagination and optional risk level filter.
    Returns tenders with LEFT JOIN to predictions (may be null).
    """
    try:
        db_path = "data/lpse_x.db"
        
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Build WHERE clause for risk_level filter
            where_clause = ""
            params: list = []
            if risk_level:
                where_clause = "WHERE p.risk_level = ?"
                params.append(risk_level)
            
            # Count total
            count_query = f"""
                SELECT COUNT(DISTINCT t.tender_id) as total
                FROM tenders t
                LEFT JOIN predictions p ON t.tender_id = p.tender_id
                {where_clause}
            """
            cursor = await db.execute(count_query, params)
            count_row = await cursor.fetchone()
            total = count_row["total"] if count_row else 0
            
            # Fetch paginated data
            offset = (page - 1) * page_size
            data_query = f"""
                SELECT 
                    t.tender_id,
                    t.title,
                    t.buyer_name,
                    t.buyer_id,
                    t.value_amount,
                    t.value_currency,
                    t.procurement_method,
                    t.procurement_category,
                    t.status,
                    t.date_published,
                    t.date_awarded,
                    t.npwp_hash,
                    t.npwp_last4,
                    t.total_score,
                    t.year,
                    t.source,
                    p.risk_score,
                    p.risk_level,
                    p.model_version,
                    p.predicted_at
                FROM tenders t
                LEFT JOIN predictions p ON t.tender_id = p.tender_id
                {where_clause}
                ORDER BY t.date_published DESC
                LIMIT ? OFFSET ?
            """
            params.extend([page_size, offset])
            cursor = await db.execute(data_query, params)
            rows = await cursor.fetchall()
            
            items = []
            for row in rows:
                item = {
                    "tender_id": row["tender_id"],
                    "title": row["title"],
                    "buyer_name": row["buyer_name"],
                    "buyer_id": row["buyer_id"],
                    "value_amount": row["value_amount"],
                    "value_currency": row["value_currency"],
                    "procurement_method": row["procurement_method"],
                    "procurement_category": row["procurement_category"],
                    "status": row["status"],
                    "date_published": row["date_published"],
                    "date_awarded": row["date_awarded"],
                    "npwp_hash": row["npwp_hash"],
                    "npwp_last4": row["npwp_last4"],
                    "total_score": row["total_score"],
                    "year": row["year"],
                    "source": row["source"],
                }
                
                # Add prediction if available
                if row["risk_score"] is not None:
                    item["prediction"] = {
                        "risk_score": row["risk_score"],
                        "risk_level": row["risk_level"],
                        "model_version": row["model_version"],
                        "predicted_at": row["predicted_at"],
                    }
                else:
                    item["prediction"] = None
                
                items.append(item)
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    except Exception as exc:
        logger.exception("get_tenders failed")
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ) from exc


@router.get("/{tender_id}")
async def get_tender(tender_id: str) -> dict:
    """
    Get full tender with features and prediction.
    Returns 404 if tender not found.
    """
    try:
        db_path = "data/lpse_x.db"
        
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Fetch tender + prediction
            cursor = await db.execute(
                """
                SELECT 
                    t.tender_id,
                    t.title,
                    t.buyer_name,
                    t.buyer_id,
                    t.value_amount,
                    t.value_currency,
                    t.procurement_method,
                    t.procurement_category,
                    t.status,
                    t.date_published,
                    t.date_awarded,
                    t.npwp_hash,
                    t.npwp_last4,
                    t.total_score,
                    t.year,
                    t.source,
                    p.risk_score,
                    p.risk_level,
                    p.model_version,
                    p.predicted_at
                FROM tenders t
                LEFT JOIN predictions p ON t.tender_id = p.tender_id
                WHERE t.tender_id = ?
                """,
                (tender_id,),
            )
            tender_row = await cursor.fetchone()
            
            if not tender_row:
                raise HTTPException(
                    status_code=404,
                    detail={"error": f"Tender {tender_id} not found"}
                )
            
            # Fetch features
            cursor = await db.execute(
                "SELECT feature_json FROM features WHERE tender_id = ?",
                (tender_id,),
            )
            features_row = await cursor.fetchone()
            
            features_dict = {}
            if features_row and features_row["feature_json"]:
                try:
                    features_dict = json.loads(features_row["feature_json"])
                except json.JSONDecodeError:
                    logger.warning("Failed to parse features JSON for %s", tender_id)
                    features_dict = {}
        
        # Build response
        result = {
            "tender_id": tender_row["tender_id"],
            "title": tender_row["title"],
            "buyer_name": tender_row["buyer_name"],
            "buyer_id": tender_row["buyer_id"],
            "value_amount": tender_row["value_amount"],
            "value_currency": tender_row["value_currency"],
            "procurement_method": tender_row["procurement_method"],
            "procurement_category": tender_row["procurement_category"],
            "status": tender_row["status"],
            "date_published": tender_row["date_published"],
            "date_awarded": tender_row["date_awarded"],
            "npwp_hash": tender_row["npwp_hash"],
            "npwp_last4": tender_row["npwp_last4"],
            "total_score": tender_row["total_score"],
            "year": tender_row["year"],
            "source": tender_row["source"],
            "features": features_dict,
        }
        
        # Add prediction if available
        if tender_row["risk_score"] is not None:
            result["prediction"] = {
                "risk_score": tender_row["risk_score"],
                "risk_level": tender_row["risk_level"],
                "model_version": tender_row["model_version"],
                "predicted_at": tender_row["predicted_at"],
            }
        else:
            result["prediction"] = None
        
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return result
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_tender failed for %s", tender_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ) from exc
