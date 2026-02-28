"""
T14: Reports Route
GET /api/reports/{tender_id} — generate IIA 2025-format pre-investigation report.
POST /api/reports/{tender_id} — generate report from supplied oracle_result JSON.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.reports.generator import ReportGenerator, ReportResult
from backend.config.runtime import get_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports"])

# Module-level generator (single instance, thread-safe for reads)
_generator: ReportGenerator | None = None


def _get_generator() -> ReportGenerator:
    global _generator
    if _generator is None:
        _generator = ReportGenerator()
    return _generator


def _report_to_dict(result: ReportResult, tender_id: str) -> dict:
    """Serialize ReportResult to JSON-serializable dict."""
    return {
        "status": "ok",
        "tender_id": tender_id,
        "risk_level": result.risk_level,
        "risk_score": result.risk_score,
        "generated_at": result.generated_at,
        "evidence_count": result.evidence_count,
        "recommendations": result.recommendations,
        "sections": result.sections,
        "report_text": result.report_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class ReportRequest(BaseModel):
    """Optional request body for POST /api/reports/{tender_id}."""
    oracle_result: dict[str, Any] | None = Field(
        None,
        description="Pre-computed OracleSandwichResult as dict (from /api/xai). "
                    "If omitted, report is generated with default null oracle result.",
    )
    tender_data: dict[str, Any] | None = Field(
        None,
        description="Tender metadata (nama_paket, satuan_kerja, etc.)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "oracle_result": {
                    "tender_id": "ID-2024-0001",
                    "layers_ok": 3,
                    "layers_failed": 2,
                    "total_seconds": 1.24,
                    "shap": {"status": "ok", "data": {"model_output": 0.85}, "error": None},
                    "anchors": {"status": "ok", "data": {"rules": ["n_bidders <= 1"]}, "error": None},
                    "leiden": {"status": "not_applicable", "data": None, "error": None},
                    "benford": {"status": "ok", "data": {"suspicious": True, "chi2": 42.3, "p_value": 0.001}, "error": None},
                    "dice": {"status": "not_applicable", "data": None, "error": None},
                },
                "tender_data": {
                    "nama_paket": "Konstruksi Gedung Kantor Pemerintah",
                    "satuan_kerja": "Dinas PUPR Kabupaten X",
                    "nilai_hps": 5000000000,
                }
            }
        }
    }


def _dict_to_oracle_namespace(oracle_dict: dict | None, tender_id: str) -> Any:
    """
    Convert oracle_result dict (from /api/xai JSON response) into a
    SimpleNamespace that matches OracleSandwichResult attribute access.
    """
    from types import SimpleNamespace

    def _layer_ns(layer_dict: dict | None) -> SimpleNamespace:
        if not layer_dict or not isinstance(layer_dict, dict):
            return SimpleNamespace(status="not_applicable", data=None, error=None)
        return SimpleNamespace(
            status=layer_dict.get("status", "not_applicable"),
            data=layer_dict.get("data"),
            error=layer_dict.get("error"),
        )

    if oracle_dict is None:
        dummy = SimpleNamespace(status="not_applicable", data=None, error=None)
        return SimpleNamespace(
            tender_id=tender_id,
            shap=dummy, anchors=dummy,
            leiden=dummy, benford=dummy, dice=dummy,
            layers_ok=0, layers_failed=0, total_seconds=0.0,
        )

    return SimpleNamespace(
        tender_id=oracle_dict.get("tender_id", tender_id),
        shap=_layer_ns(oracle_dict.get("shap")),
        anchors=_layer_ns(oracle_dict.get("anchors")),
        leiden=_layer_ns(oracle_dict.get("leiden")),
        benford=_layer_ns(oracle_dict.get("benford")),
        dice=_layer_ns(oracle_dict.get("dice")),
        layers_ok=int(oracle_dict.get("layers_ok", 0)),
        layers_failed=int(oracle_dict.get("layers_failed", 0)),
        total_seconds=float(oracle_dict.get("total_seconds", 0.0)),
    )


@router.get("/{tender_id}")
async def get_report(tender_id: str) -> dict:
    """
    Generate an IIA 2025-formatted pre-investigation report for a tender
    using default (null) oracle results.

    For a richer report, use POST /api/reports/{tender_id} and pass
    the oracle_result JSON from /api/xai/{tender_id}.
    """
    try:
        oracle_ns = _dict_to_oracle_namespace(None, tender_id)
        gen = _get_generator()
        result = gen.generate(oracle_result=oracle_ns, tender_id=tender_id)
        return _report_to_dict(result, tender_id)

    except Exception as exc:
        logger.exception("get_report failed for tender_id=%s", tender_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(exc),
                "tender_id": tender_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ) from exc


@router.post("/{tender_id}")
async def generate_report(tender_id: str, request: ReportRequest) -> dict:
    """
    Generate an IIA 2025-formatted pre-investigation report for a tender.

    Supply oracle_result (from /api/xai/{tender_id}) and optional tender metadata
    for a comprehensive 6-section report in Bahasa Indonesia:
      1. Ringkasan Eksekutif
      2. Identitas Pengadaan
      3. Indikator Risiko (SHAP + Anchors)
      4. Matriks Bukti (Benford + Leiden)
      5. Analisis What-If (DiCE counterfactuals)
      6. Kesimpulan dan Rekomendasi
    """
    try:
        oracle_ns = _dict_to_oracle_namespace(request.oracle_result, tender_id)
        gen = _get_generator()
        result = gen.generate(
            oracle_result=oracle_ns,
            tender_data=request.tender_data,
            tender_id=tender_id,
        )
        return _report_to_dict(result, tender_id)

    except Exception as exc:
        logger.exception("generate_report failed for tender_id=%s", tender_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(exc),
                "tender_id": tender_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ) from exc
