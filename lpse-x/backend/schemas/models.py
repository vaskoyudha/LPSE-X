"""
LPSE-X Pydantic Models — Shared contracts between backend API and frontend.
ALL models must be competition-compliant and support dynamic injection.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================================
# ENUMS (CRITICAL FOR COMPETITION)
# ============================================================================


class RiskLevel(str, Enum):
    """Risk classification levels — EXACT labels, EXACT order (competition contract)"""
    AMAN = "Aman"
    PERLU_PANTAUAN = "Perlu Pantauan"
    RISIKO_TINGGI = "Risiko Tinggi"
    RISIKO_KRITIS = "Risiko Kritis"


class ProcurementScope(str, Enum):
    """Procurement categories (Injectable Parameter #1)"""
    KONSTRUKSI = "konstruksi"
    BARANG = "barang"
    JASA_KONSULTANSI = "jasa_konsultansi"
    JASA_LAINNYA = "jasa_lainnya"


class AnomalyMethod(str, Enum):
    """ML model selection (Injectable Parameter #5)"""
    ISOLATION_FOREST = "isolation_forest"
    XGBOOST = "xgboost"
    ENSEMBLE = "ensemble"


class OutputFormat(str, Enum):
    """Output format selection (Injectable Parameter #6)"""
    DASHBOARD = "dashboard"
    API_JSON = "api_json"
    AUDIT_REPORT = "audit_report"


# ============================================================================
# DATA MODELS
# ============================================================================


class TenderRecord(BaseModel):
    """
    OCDS-format tender record with OCP red flags.
    Minimum schema; can be extended via ocds_data field.
    """
    tender_id: str = Field(..., description="Unique tender identifier")
    buyer: str = Field(..., description="Institution name")
    buyer_lpse: Optional[str] = Field(None, description="LPSE code (e.g., 'kemenkeu')")
    title: str = Field(..., description="Tender title/description")
    procurement_scope: str = Field(
        ...,
        description="Procurement category: konstruksi/barang/jasa_konsultansi/jasa_lainnya"
    )
    method: str = Field(..., description="Procurement method: open/limited/direct")
    amount: Optional[float] = Field(None, description="Contract value in IDR")
    hps: Optional[float] = Field(None, description="Owner estimate (Harga Perkiraan Sendiri)")
    year: int = Field(..., description="Tender year")
    province: Optional[str] = Field(None, description="Province name")
    winner_npwp_hash: Optional[str] = Field(None, description="Winner NPWP (SHA-256 hash, NOT raw)")
    winner_name: Optional[str] = Field(None, description="Winner company name")
    participant_count: Optional[int] = Field(None, description="Number of bidders", ge=0)
    ocds_data: Optional[dict] = Field(None, description="Raw OCDS JSON (flexible)")
    icw_total_score: Optional[float] = Field(
        None,
        description="Weak label from opentender.net (0-100)",
        ge=0.0,
        le=100.0
    )
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "tender_id": "ID-2024-0001",
                "buyer": "Kemenkeu",
                "buyer_lpse": "kemenkeu",
                "title": "Konstruksi Gedung Kantor",
                "procurement_scope": "konstruksi",
                "method": "open",
                "amount": 500_000_000.0,
                "hps": 480_000_000.0,
                "year": 2024,
                "province": "DKI Jakarta",
                "winner_npwp_hash": "a1b2c3d4e5f6...",
                "winner_name": "PT Mitra Bangunan",
                "participant_count": 12,
                "icw_total_score": 45.5,
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
    }


class RiskPrediction(BaseModel):
    """Risk prediction result from ML models with disagreement tracking."""
    tender_id: str = Field(..., description="Reference to TenderRecord")
    risk_level: RiskLevel = Field(..., description="4-level risk classification")
    score: float = Field(
        ...,
        description="Risk score (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    model_scores: dict[str, float] = Field(
        ...,
        description="Individual model scores: xgboost, iforest, icw_weak"
    )
    disagreement_flag: bool = Field(
        False,
        description="True if models disagree by >0.3"
    )
    predicted_at: Optional[datetime] = Field(None, description="Prediction timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "tender_id": "ID-2024-0001",
                "risk_level": "Risiko Tinggi",
                "score": 0.81,
                "model_scores": {
                    "xgboost": 0.83,
                    "iforest": 0.78,
                    "icw_weak": 0.82
                },
                "disagreement_flag": False,
                "predicted_at": "2024-01-15T10:35:00Z"
            }
        }
    }


class XAIExplanation(BaseModel):
    """
    Oracle Sandwich: 5-layer explainability for a single prediction.
    All layers are optional (computed on demand).
    """
    tender_id: str = Field(..., description="Reference to prediction")
    
    # Layer 1: SHAP (Global Feature Importance)
    shap_values: Optional[dict[str, float]] = Field(
        None,
        description="Feature name → SHAP contribution value"
    )
    shap_base_value: Optional[float] = Field(None, description="SHAP base value (model mean)")
    
    # Layer 2: DiCE (Local Counterfactuals)
    dice_counterfactuals: Optional[list[dict]] = Field(
        None,
        description="List of counterfactual scenarios"
    )
    
    # Layer 3: Anchors (Rule-based Explanations)
    anchor_rules: Optional[list[str]] = Field(
        None,
        description="Human-readable decision rules"
    )
    anchor_precision: Optional[float] = Field(None, description="Rule precision", ge=0.0, le=1.0)
    anchor_coverage: Optional[float] = Field(None, description="Rule coverage", ge=0.0, le=1.0)
    
    # Layer 4: Leiden (Graph Community Detection)
    leiden_community_id: Optional[int] = Field(None, description="Community ID if in cartel")
    leiden_community_size: Optional[int] = Field(None, description="Size of detected community")
    
    # Layer 5: Benford (Statistical Forensics)
    benford_result: Optional[dict] = Field(
        None,
        description="{'chi2_stat': float, 'p_value': float, 'applicability': bool}"
    )
    
    generated_at: Optional[datetime] = Field(None, description="Generation timestamp")


class GraphCommunity(BaseModel):
    """Cartel network: detected vendor community from Leiden algorithm."""
    community_id: int = Field(..., description="Unique community identifier")
    members: list[str] = Field(..., description="List of vendor IDs / NPWP hashes")
    edge_weights: dict[str, float] = Field(
        ...,
        description="Vendor pair key → co-bidding weight (e.g., 'vendor1-vendor2': 5.0)"
    )
    tender_ids: list[str] = Field(..., description="Tenders where members co-bid")
    risk_score: Optional[float] = Field(None, description="Community risk aggregation", ge=0.0, le=1.0)
    leiden_modularity: Optional[float] = Field(None, description="Community modularity metric")
    detected_at: Optional[datetime] = Field(None, description="Detection timestamp")


class RuntimeConfig(BaseModel):
    """
    CRITICAL: All 7 injectable parameters (competition rules).
    Must accept partial updates via PUT /api/config/inject.
    custom_params is wildcard for judge-injected unknown parameters.
    """
    procurement_scope: ProcurementScope = Field(
        default=ProcurementScope.KONSTRUKSI,
        description="Injectable #1: Procurement category filter"
    )
    institution_filter: list[str] = Field(
        default_factory=list,
        description="Injectable #2: Specific K/L/Pemda institutions (empty = all)"
    )
    risk_threshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Injectable #3: Risk score threshold (0.0-1.0) for classification"
    )
    year_range: tuple[int, int] = Field(
        default=(2022, 2024),
        description="Injectable #4: Analysis year range (start, end inclusive)"
    )
    anomaly_method: AnomalyMethod = Field(
        default=AnomalyMethod.ENSEMBLE,
        description="Injectable #5: Detection method (isolation_forest/xgboost/ensemble)"
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.DASHBOARD,
        description="Injectable #6: Output format (dashboard/api_json/audit_report)"
    )
    custom_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Injectable #7: WILDCARD dict for unexpected judge-injected parameters"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "procurement_scope": "konstruksi",
                "institution_filter": ["kemenkeu", "kemenkes"],
                "risk_threshold": 0.65,
                "year_range": [2022, 2024],
                "anomaly_method": "ensemble",
                "output_format": "dashboard",
                "custom_params": {"judge_secret_param": 42}
            }
        }
    }


class InvestigationReport(BaseModel):
    """Auto-generated pre-investigation report (Bahasa Indonesia, IIA 2025 standards)."""
    report_id: str = Field(..., description="Unique report identifier")
    tender_id: str = Field(..., description="Reference to TenderRecord")
    risk_level: RiskLevel = Field(..., description="Final risk classification")
    findings: list[str] = Field(
        default_factory=list,
        description="Bullet-point findings in Bahasa Indonesia"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Investigation recommendations"
    )
    template_version: str = Field(
        default="IIA-2025",
        description="Report template version (for audit trail)"
    )
    generated_at: Optional[datetime] = Field(None, description="Report generation timestamp")
    evidence_summary: Optional[str] = Field(None, description="Consolidated evidence summary")


class InjectionRequest(BaseModel):
    """
    Request body for PUT /api/config/inject.
    All fields optional (partial config updates).
    Pydantic validates before injection; invalid params rejected.
    """
    procurement_scope: Optional[ProcurementScope] = None
    institution_filter: Optional[list[str]] = None
    risk_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    year_range: Optional[tuple[int, int]] = None
    anomaly_method: Optional[AnomalyMethod] = None
    output_format: Optional[OutputFormat] = None
    custom_params: Optional[dict[str, Any]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "risk_threshold": 0.75,
                "anomaly_method": "xgboost",
                "custom_params": {"secret_judge_filter": "DKI Jakarta"}
            }
        }
    }


class InjectionResponse(BaseModel):
    """Response from PUT /api/config/inject."""
    success: bool = Field(..., description="Whether injection succeeded")
    old_values: dict = Field(..., description="Previous config values (before injection)")
    new_values: dict = Field(..., description="Updated config values (after injection)")
    validation_errors: Optional[list[str]] = Field(None, description="Validation errors if any")
    injected_at: datetime = Field(..., description="Injection timestamp (audit trail)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "old_values": {"risk_threshold": 0.65, "anomaly_method": "ensemble"},
                "new_values": {"risk_threshold": 0.75, "anomaly_method": "xgboost"},
                "validation_errors": None,
                "injected_at": "2024-01-15T10:40:00Z"
            }
        }
    }
