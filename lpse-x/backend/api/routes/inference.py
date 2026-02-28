"""
T14: Inference Route
POST /api/predict — run full ensemble prediction for a tender.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.ml.predict import predict_single
from backend.config.runtime import get_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/predict", tags=["inference"])


class PredictRequest(BaseModel):
    """Request body for POST /api/predict."""
    tender_id: str = Field(..., description="Tender identifier")
    features: dict[str, Any] = Field(
        ...,
        description="Feature name → numeric value dict. Missing features default to 0.0"
    )
    icw_raw_score: float | None = Field(
        None,
        description="Raw ICW total_score from opentender.net (0-100, optional)",
        ge=0.0,
        le=100.0
    )
    tender_metadata: dict[str, Any] | None = Field(
        None,
        description="Optional tender metadata (satuan_kerja, nama_paket, etc.) for context"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "tender_id": "ID-2024-0001",
                "features": {
                    "n_bidders": 1.0,
                    "price_ratio": 0.995,
                    "bid_spread": 0.005,
                    "winner_bid_rank": 1.0,
                    "hhi": 0.95,
                    "log_amount": 19.8,
                },
                "icw_raw_score": 78.5,
                "tender_metadata": {
                    "nama_paket": "Konstruksi Gedung Kantor",
                    "satuan_kerja": "Dinas PUPR",
                }
            }
        }
    }


class PredictResponse(BaseModel):
    """Response from POST /api/predict."""
    status: str = "ok"
    tender_id: str
    risk_level: str
    final_score: float
    individual_scores: dict[str, float]
    disagreement_flag: bool
    disagreement_detail: str
    risk_threshold: float
    timestamp: str


@router.post("")
async def predict_tender(request: PredictRequest) -> PredictResponse:
    """
    Run ensemble risk prediction for a tender.

    Uses EnsembleResult from Tri-Method AI (XGBoost + IsolationForest + ICW weak labels).
    All parameters come from runtime_config.yaml — no hardcoded thresholds.

    Returns risk level in 4 categories:
    - Aman (safe)
    - Perlu Pantauan (monitor)
    - Risiko Tinggi (high risk)
    - Risiko Kritis (critical risk)
    """
    cfg = get_config()

    try:
        # Inject tender_id into features dict for predict_single
        feature_vector = dict(request.features)
        feature_vector["tender_id"] = request.tender_id

        result = predict_single(
            feature_vector=feature_vector,
            icw_raw_score=request.icw_raw_score,
        )

        return PredictResponse(
            status="ok",
            tender_id=request.tender_id,
            risk_level=result.risk_level,
            final_score=round(result.final_score, 6),
            individual_scores={k: round(v, 6) for k, v in result.individual_scores.items()},
            disagreement_flag=result.disagreement_flag,
            disagreement_detail=result.disagreement_detail,
            risk_threshold=cfg.risk_threshold,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:
        logger.exception("predict_tender failed for tender_id=%s", request.tender_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(exc),
                "tender_id": request.tender_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ) from exc
