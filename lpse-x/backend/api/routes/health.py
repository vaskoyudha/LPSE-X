"""
T14: Health Check Route
GET /api/health — returns version, uptime, model status, config hash.
"""
from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone

from fastapi import APIRouter

from backend.config.runtime import get_config

router = APIRouter(prefix="/api/health", tags=["health"])

# Module-level start time (set when app starts)
_START_TIME: float = time.time()


@router.get("")
async def health_check() -> dict:
    """
    Health check endpoint.
    Returns version, uptime, model availability, and config hash.
    """
    cfg = get_config()
    cfg_str = str(cfg.model_dump())
    cfg_hash = hashlib.md5(cfg_str.encode()).hexdigest()[:8]  # noqa: S324 — non-crypto hash for display

    uptime_seconds = int(time.time() - _START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    # Check if model files exist
    from pathlib import Path
    model_dir = Path(__file__).parent.parent.parent / "models"
    xgb_ok = (model_dir / "xgboost.ubj").exists()
    iforest_ok = (model_dir / "iforest.pkl").exists()

    return {
        "status": "ok",
        "version": "0.1.0",
        "uptime": uptime_str,
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "models": {
            "xgboost": "loaded" if xgb_ok else "not_found",
            "isolation_forest": "loaded" if iforest_ok else "not_found",
        },
        "config_hash": cfg_hash,
        "config": {
            "risk_threshold": cfg.risk_threshold,
            "anomaly_method": cfg.anomaly_method.value,
            "procurement_scope": cfg.procurement_scope.value,
        },
    }
