"""
LPSE-X Auto Pre-Investigation Report Generator
================================================
T13: Automatic generation of IIA 2025-formatted pre-investigation reports
     in Bahasa Indonesia using Jinja2 NLG templates.

Design:
  - Takes OracleSandwichResult + tender metadata → ReportResult
  - 6-section IIA 2025 format (Ringkasan → Identitas → SHAP → Matriks → What-If → Kesimpulan)
  - Risk level mapping: 0=Aman, 1=Perlu Pantauan, 2=Berisiko, 3=Kritis
  - All config (threshold, scope, etc.) from get_config() — never hardcoded
  - Fully offline — no external calls
  - Gracefully handles missing/partial Oracle Sandwich layers

References:
  - IIA 2025 Internal Audit Standards — Chapter 6 (Reporting)
  - UPGRADE 3 lines 148-158 — Report generator spec
  - DEEP_RESEARCH_SYNTHESIS.md lines 238-260 — NLG design
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, Template

from backend.config.runtime import get_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Risk level mapping
# ---------------------------------------------------------------------------

RISK_LABELS: dict[int, str] = {
    0: "Aman",
    1: "Perlu Pantauan",
    2: "Berisiko",
    3: "Kritis",
}

# Narrative for each risk level (Bahasa Indonesia)
RISK_NARRATIVES: dict[int, str] = {
    0: (
        "Analisis sistem tidak menemukan indikator risiko signifikan pada tender ini. "
        "Semua fitur pengadaan berada dalam batas normal berdasarkan data historis. "
        "Tidak ada tindakan mendesak yang diperlukan."
    ),
    1: (
        "Sistem mendeteksi beberapa indikator yang memerlukan perhatian pada tender ini. "
        "Meskipun belum dikategorikan berisiko tinggi, auditor disarankan untuk "
        "melakukan pemantauan berkala terhadap perkembangan tender ini."
    ),
    2: (
        "Sistem mendeteksi INDIKATOR RISIKO SIGNIFIKAN pada tender ini. "
        "Pola pengadaan menunjukkan kemungkinan ketidakwajaran yang memerlukan "
        "investigasi lebih lanjut oleh tim audit. Tindak lanjut segera direkomendasikan."
    ),
    3: (
        "Sistem mendeteksi INDIKATOR KECURANGAN KRITIS pada tender ini. "
        "Multiple fitur risiko tinggi terdeteksi secara bersamaan, mengindikasikan "
        "kemungkinan kuat adanya bid-rigging, kolusi, atau manipulasi pengadaan. "
        "PENYELIDIKAN SEGERA DIPERLUKAN."
    ),
}

# Recommendations per risk level
RECOMMENDATIONS: dict[int, list[str]] = {
    0: [
        "Tidak ada tindakan mendesak yang diperlukan saat ini.",
        "Lanjutkan pemantauan rutin sesuai prosedur standar.",
        "Dokumentasikan hasil analisis untuk keperluan audit trail.",
    ],
    1: [
        "Lakukan pemantauan berkala terhadap perkembangan tender ini.",
        "Verifikasi keabsahan dokumen penawaran yang masuk.",
        "Pastikan proses evaluasi penawaran berjalan sesuai peraturan.",
        "Jadwalkan tinjauan lanjutan dalam 30 hari ke depan.",
    ],
    2: [
        "Segera lakukan tindak lanjut investigasi oleh tim audit internal.",
        "Kumpulkan dokumen pendukung: RKS, BA Aanwijzing, dokumen penawaran.",
        "Periksa rekam jejak peserta tender dan afiliasi perusahaan.",
        "Analisis komparatif harga penawaran dengan HPS dan harga pasar.",
        "Laporkan temuan kepada pejabat berwenang dalam 7 hari kerja.",
    ],
    3: [
        "SEGERA laporkan kepada Inspektur Jenderal / APIP sesuai PP 60/2008.",
        "Pertimbangkan penghentian sementara proses tender sambil menunggu investigasi.",
        "Amankan seluruh dokumentasi tender untuk keperluan pembuktian.",
        "Koordinasikan dengan BPKP/BPK jika indikasi kerugian negara signifikan.",
        "Pertimbangkan pelaporan kepada KPK jika indikasi korupsi kuat.",
        "Dokumentasikan chain of custody semua bukti digital.",
    ],
}

# Feature name translations (Indonesian)
FEATURE_TRANSLATIONS: dict[str, str] = {
    "n_bidders": "Jumlah Peserta Tender",
    "price_ratio": "Rasio Harga Penawaran/HPS",
    "winner_bid_ratio": "Rasio Harga Pemenang",
    "bid_spread": "Sebaran Penawaran",
    "days_to_deadline": "Hari Menjelang Deadline",
    "repeat_winner_flag": "Indikator Pemenang Berulang",
    "single_bidder_flag": "Indikator Peserta Tunggal",
    "cartel_community_size": "Ukuran Komunitas Kartel",
    "benford_chi2": "Statistik Chi-Square Benford",
    "benford_deviation": "Deviasi Benford",
    "isolation_score": "Skor Isolasi (Anomali)",
    "contract_amount": "Nilai Kontrak",
    "hps_amount": "Nilai HPS",
    "participant_overlap": "Tumpang Tindih Peserta",
    "submission_timing": "Waktu Penyerahan Dokumen",
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ReportResult:
    """
    Complete pre-investigation report result.

    Fields:
        tender_id:       Tender identifier
        report_text:     Full report in Bahasa Indonesia (rendered Jinja2 template)
        risk_level:      "Aman" / "Perlu Pantauan" / "Berisiko" / "Kritis"
        risk_score:      0-3 (maps to risk_level)
        generated_at:    ISO 8601 timestamp (UTC)
        sections:        dict mapping section name → section text
        evidence_count:  number of layers with status == "ok"
        recommendations: list of recommendation strings
    """
    tender_id: str
    report_text: str
    risk_level: str
    risk_score: int
    generated_at: str
    sections: dict[str, str]
    evidence_count: int
    recommendations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Context builders (extract data from Oracle Sandwich result)
# ---------------------------------------------------------------------------

def _extract_shap_context(shap_layer: Any) -> dict[str, Any]:
    """Extract SHAP data from LayerResult for template rendering."""
    ctx: dict[str, Any] = {
        "shap_status": shap_layer.status,
        "shap_ok": shap_layer.status == "ok",
        "shap_error": shap_layer.error or "Tidak tersedia",
        "top_risk_features": [],
        "top_safe_features": [],
        "shap_base_value": 0.0,
        "shap_model_output": 0.0,
        "shap_additivity_error": 0.0,
        "shap_summary": "Tidak tersedia",
    }
    if shap_layer.status != "ok" or shap_layer.data is None:
        return ctx

    data = shap_layer.data
    # Handle both dataclass and dict
    if hasattr(data, "__dataclass_fields__"):
        import dataclasses as dc
        data = dc.asdict(data)

    top_pos = data.get("top_positive_features", []) or []
    top_neg = data.get("top_negative_features", []) or []

    def _build_feat(f: dict[str, Any]) -> dict[str, Any]:
        name = f.get("name", "unknown")
        return {
            "name": FEATURE_TRANSLATIONS.get(name, name),
            "value": round(float(f.get("value", 0.0)), 4),
            "shap": round(float(f.get("shap", 0.0)), 6),
            "interpretation": _interpret_feature(name, float(f.get("value", 0.0))),
        }

    ctx["top_risk_features"] = [_build_feat(f) for f in top_pos[:3]]
    ctx["top_safe_features"] = [_build_feat(f) for f in top_neg[:2]]
    ctx["shap_base_value"] = round(float(data.get("base_value", 0.0)), 4)
    ctx["shap_model_output"] = round(float(data.get("model_output", 0.0)), 4)
    ctx["shap_additivity_error"] = round(float(data.get("additivity_error", 0.0)), 6)

    if top_pos:
        top_name = FEATURE_TRANSLATIONS.get(top_pos[0].get("name", ""), top_pos[0].get("name", ""))
        ctx["shap_summary"] = f"Risiko utama: {top_name}"
    else:
        ctx["shap_summary"] = "Tidak ada fitur risiko dominan"
    return ctx


def _extract_benford_context(benford_layer: Any) -> dict[str, Any]:
    """Extract Benford analysis data."""
    ctx: dict[str, Any] = {
        "benford_status": benford_layer.status,
        "benford_ok": benford_layer.status == "ok",
        "benford_summary": "Tidak tersedia",
    }
    if benford_layer.status == "not_applicable":
        ctx["benford_summary"] = "Tidak cukup data (<100 rekaman)"
        return ctx
    if benford_layer.status != "ok" or benford_layer.data is None:
        return ctx

    data = benford_layer.data
    if isinstance(data, dict):
        chi2 = data.get("chi2", 0.0)
        p_val = data.get("p_value", 1.0)
        suspicious = data.get("suspicious", False)
        if suspicious:
            ctx["benford_summary"] = f"MENCURIGAKAN (chi2={chi2:.2f}, p={p_val:.4f})"
        else:
            ctx["benford_summary"] = f"Normal (chi2={chi2:.2f}, p={p_val:.4f})"
    return ctx


def _extract_leiden_context(leiden_layer: Any) -> dict[str, Any]:
    """Extract Leiden community detection data."""
    ctx: dict[str, Any] = {
        "leiden_status": leiden_layer.status,
        "leiden_ok": leiden_layer.status == "ok",
        "leiden_summary": "Tidak tersedia",
    }
    if leiden_layer.status == "not_applicable":
        ctx["leiden_summary"] = "Tender tidak terdeteksi dalam komunitas mencurigakan"
        return ctx
    if leiden_layer.status != "ok" or leiden_layer.data is None:
        return ctx

    data = leiden_layer.data
    if isinstance(data, dict):
        community_size = data.get("community_size", 0)
        suspicion = data.get("suspicion_score", 0.0)
        ctx["leiden_summary"] = f"Komunitas {community_size} entitas, skor={suspicion:.2f}"
    return ctx


def _extract_anchors_context(anchors_layer: Any) -> dict[str, Any]:
    """Extract Anchors rule explanation data."""
    ctx: dict[str, Any] = {
        "anchors_status": anchors_layer.status,
        "anchor_rules": [],
        "anchor_precision": 0.0,
        "anchor_coverage": 0.0,
    }
    if anchors_layer.status != "ok" or anchors_layer.data is None:
        return ctx

    data = anchors_layer.data
    if hasattr(data, "__dataclass_fields__"):
        import dataclasses as dc
        data = dc.asdict(data)

    if isinstance(data, dict):
        ctx["anchor_rules"] = data.get("rules", []) or []
        ctx["anchor_precision"] = float(data.get("precision", 0.0))
        ctx["anchor_coverage"] = float(data.get("coverage", 0.0))
    return ctx


def _extract_dice_context(dice_layer: Any) -> dict[str, Any]:
    """Extract DiCE counterfactual data."""
    ctx: dict[str, Any] = {
        "dice_status": dice_layer.status,
        "dice_ok": dice_layer.status == "ok",
        "dice_not_applicable": dice_layer.status == "not_applicable",
        "dice_error": dice_layer.error or "Tidak tersedia",
        "dice_cf_count": 0,
        "dice_generation_time_ms": 0.0,
        "dice_from_cache": False,
        "dice_counterfactuals": [],
    }
    if dice_layer.status != "ok" or dice_layer.data is None:
        return ctx

    data = dice_layer.data
    if hasattr(data, "__dataclass_fields__"):
        import dataclasses as dc
        data = dc.asdict(data)

    if isinstance(data, dict):
        cfs_raw = data.get("counterfactuals", []) or []
        ctx["dice_cf_count"] = len(cfs_raw)
        ctx["dice_generation_time_ms"] = float(data.get("generation_time_ms", 0.0))
        ctx["dice_from_cache"] = bool(data.get("from_cache", False))

        # Build structured counterfactual items for template
        risk_label_map = {0: "Aman", 1: "Perlu Pantauan", 2: "Berisiko", 3: "Kritis"}
        cfs = []
        for cf in cfs_raw:
            if not isinstance(cf, dict):
                continue
            changes_raw = cf.get("changes", []) or []
            changes = []
            for ch in changes_raw:
                if isinstance(ch, dict):
                    feat = ch.get("feature", "")
                    changes.append({
                        "feature": FEATURE_TRANSLATIONS.get(feat, feat),
                        "from_val": ch.get("from", "?"),
                        "to_val": ch.get("to", "?"),
                        "direction": ch.get("direction", "change"),
                        "delta": ch.get("delta"),
                    })
            risk_sc = int(cf.get("risk_score", 0))
            cfs.append({
                "changes": changes,
                "risk_label": risk_label_map.get(risk_sc, str(risk_sc)),
            })
        ctx["dice_counterfactuals"] = cfs
    return ctx


def _interpret_feature(feature_name: str, value: float) -> str:
    """Generate a human-readable interpretation of a feature value."""
    interpretations: dict[str, Any] = {
        "n_bidders": lambda v: "Sangat sedikit peserta — indikasi pembatasan persaingan" if v <= 1 else "Peserta terbatas" if v <= 3 else "Normal",
        "price_ratio": lambda v: "Harga sangat dekat HPS — indikasi price fixing" if v >= 0.98 else "Normal",
        "single_bidder_flag": lambda v: "Hanya satu peserta — wajib investigasi" if v >= 0.5 else "Tidak berlaku",
        "repeat_winner_flag": lambda v: "Pemenang berulang terdeteksi" if v >= 0.5 else "Normal",
        "bid_spread": lambda v: "Sebaran penawaran sangat rendah — indikasi koordinasi" if v <= 0.01 else "Normal",
    }
    interp_fn = interpretations.get(feature_name)
    if interp_fn:
        return interp_fn(value)
    return "Nilai melebihi ambang batas normal"


# ---------------------------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------------------------

def _compute_risk_score(oracle_result: Any) -> int:
    """
    Derive overall risk score (0-3) from Oracle Sandwich result.

    Scoring logic:
      - Base score from SHAP model_output (0.0-1.0) → scaled to 0-3
      - Boosted by +1 if Benford suspicious AND Leiden found community
      - Capped at 3
    """
    base_score = 0

    # Extract from SHAP layer
    shap_layer = getattr(oracle_result, "shap", None)
    if shap_layer and shap_layer.status == "ok" and shap_layer.data is not None:
        data = shap_layer.data
        if hasattr(data, "__dataclass_fields__"):
            import dataclasses as dc
            data = dc.asdict(data)
        if isinstance(data, dict):
            model_output = float(data.get("model_output", 0.0))
            # Map [0.0, 1.0] → [0, 3]
            base_score = min(3, int(model_output * 4))

    # Evidence boost: if BOTH Benford AND Leiden confirm risk → boost
    benford_layer = getattr(oracle_result, "benford", None)
    leiden_layer = getattr(oracle_result, "leiden", None)

    benford_suspicious = False
    leiden_in_community = False

    if benford_layer and benford_layer.status == "ok" and isinstance(benford_layer.data, dict):
        benford_suspicious = bool(benford_layer.data.get("suspicious", False))

    if leiden_layer and leiden_layer.status == "ok":
        leiden_in_community = True

    if benford_suspicious and leiden_in_community:
        base_score = min(3, base_score + 1)

    return base_score


def _compute_evidence_alignment(oracle_result: Any) -> int:
    """Count how many of the 3 key methods (SHAP, Benford, Leiden) indicate risk."""
    count = 0

    shap_layer = getattr(oracle_result, "shap", None)
    if shap_layer and shap_layer.status == "ok" and shap_layer.data is not None:
        data = shap_layer.data
        if hasattr(data, "__dataclass_fields__"):
            import dataclasses as dc
            data = dc.asdict(data)
        if isinstance(data, dict):
            model_output = float(data.get("model_output", 0.0))
            if model_output > 0.5:
                count += 1

    benford_layer = getattr(oracle_result, "benford", None)
    if benford_layer and benford_layer.status == "ok" and isinstance(benford_layer.data, dict):
        if benford_layer.data.get("suspicious", False):
            count += 1

    leiden_layer = getattr(oracle_result, "leiden", None)
    if leiden_layer and leiden_layer.status == "ok":
        count += 1

    return count


# ---------------------------------------------------------------------------
# Main ReportGenerator class
# ---------------------------------------------------------------------------

class ReportGenerator:
    """
    Generates IIA 2025-compliant pre-investigation reports in Bahasa Indonesia.

    Usage:
        generator = ReportGenerator()
        result = generator.generate(
            oracle_result=oracle_sandwich_result,
            tender_data={"nama_paket": "Konstruksi Jembatan ...", ...},
            tender_id="TDR-2024-001",
        )
        print(result.report_text)
        print(result.risk_level)        # "Kritis"
        print(result.recommendations)  # list[str]
    """

    def __init__(self, template_dir: str | Path | None = None) -> None:
        """
        Parameters
        ----------
        template_dir:
            Path to Jinja2 templates directory.
            Defaults to the ``templates/`` subdirectory next to this file.
        """
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"
        self._template_dir = Path(template_dir)

        self._env = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,
        )
        # Register custom filters
        self._env.filters["abs"] = abs


        logger.info("ReportGenerator initialized with template_dir=%s", self._template_dir)

    def _load_template(self, name: str = "pre_investigation.j2") -> Template:
        return self._env.get_template(name)

    def generate(
        self,
        oracle_result: Any,
        tender_data: dict[str, Any] | None = None,
        tender_id: str = "unknown",
    ) -> ReportResult:
        """
        Generate a complete pre-investigation report.

        Parameters
        ----------
        oracle_result:
            OracleSandwichResult from oracle_sandwich.explain_tender().
            Can be None or partially failed — generator is fault-tolerant.
        tender_data:
            Optional dict with tender metadata (nama_paket, satuan_kerja, etc.)
        tender_id:
            Tender identifier string.

        Returns
        -------
        ReportResult with full report text, risk assessment, and structured fields.
        """
        now = datetime.now(timezone.utc).isoformat()
        cfg = get_config()

        # Safe defaults when oracle_result is None
        if oracle_result is None:
            from types import SimpleNamespace
            dummy_layer = SimpleNamespace(status="not_applicable", data=None, error=None)
            oracle_result = SimpleNamespace(
                tender_id=tender_id,
                shap=dummy_layer,
                dice=dummy_layer,
                anchors=dummy_layer,
                leiden=dummy_layer,
                benford=dummy_layer,
                layers_ok=0,
                layers_failed=0,
                total_seconds=0.0,
            )

        # Compute risk
        risk_score = _compute_risk_score(oracle_result)
        risk_level = RISK_LABELS.get(risk_score, "Aman")
        risk_narrative = RISK_NARRATIVES.get(risk_score, RISK_NARRATIVES[0])
        recommendations = list(RECOMMENDATIONS.get(risk_score, RECOMMENDATIONS[0]))
        evidence_alignment = _compute_evidence_alignment(oracle_result)
        evidence_count = getattr(oracle_result, "layers_ok", 0)

        # Extract per-layer contexts
        shap_ctx = _extract_shap_context(oracle_result.shap)
        benford_ctx = _extract_benford_context(oracle_result.benford)
        leiden_ctx = _extract_leiden_context(oracle_result.leiden)
        anchors_ctx = _extract_anchors_context(oracle_result.anchors)
        dice_ctx = _extract_dice_context(oracle_result.dice)

        # Build conclusion text
        conclusion_text = _build_conclusion(
            tender_id=tender_id,
            risk_score=risk_score,
            risk_level=risk_level,
            evidence_alignment=evidence_alignment,
            shap_ctx=shap_ctx,
            benford_ctx=benford_ctx,
            leiden_ctx=leiden_ctx,
        )

        # Build evidence narrative
        evidence_narrative = _build_evidence_narrative(
            evidence_alignment=evidence_alignment,
            shap_ctx=shap_ctx,
            benford_ctx=benford_ctx,
            leiden_ctx=leiden_ctx,
        )

        # Assemble template context
        template_ctx: dict[str, Any] = {
            "tender_id": tender_id,
            "generated_at": now,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_narrative": risk_narrative,
            "tender_data": tender_data or {},
            "evidence_alignment": evidence_alignment,
            "evidence_narrative": evidence_narrative,
            "conclusion_text": conclusion_text,
            "recommendations": recommendations,
            "risk_threshold": cfg.risk_threshold,
            "anomaly_method": cfg.anomaly_method.value,
            "procurement_scope": cfg.procurement_scope.value,
            **shap_ctx,
            **benford_ctx,
            **leiden_ctx,
            **anchors_ctx,
            **dice_ctx,
        }

        # Render template
        template = self._load_template()
        report_text = template.render(**template_ctx)

        # Extract individual sections from rendered text
        sections = _extract_sections(report_text)

        logger.info(
            "ReportGenerator: tender=%s risk=%s(%d) evidence=%d/3",
            tender_id, risk_level, risk_score, evidence_alignment,
        )

        return ReportResult(
            tender_id=tender_id,
            report_text=report_text,
            risk_level=risk_level,
            risk_score=risk_score,
            generated_at=now,
            sections=sections,
            evidence_count=evidence_count,
            recommendations=recommendations,
        )


# ---------------------------------------------------------------------------
# Text builders
# ---------------------------------------------------------------------------

def _build_conclusion(
    tender_id: str,
    risk_score: int,
    risk_level: str,
    evidence_alignment: int,
    shap_ctx: dict[str, Any],
    benford_ctx: dict[str, Any],
    leiden_ctx: dict[str, Any],
) -> str:
    """Build a plain-text conclusion paragraph in Bahasa Indonesia."""
    top_features = shap_ctx.get("top_risk_features", [])
    top_feat_names = [f["name"] for f in top_features[:2]] if top_features else []
    feat_str = " dan ".join(top_feat_names) if top_feat_names else "beberapa fitur"

    verdict_map = {
        0: "tidak menunjukkan indikasi kecurangan atau ketidakwajaran",
        1: "menunjukkan beberapa indikator yang perlu dipantau",
        2: "menunjukkan indikator risiko signifikan yang memerlukan tindak lanjut",
        3: "menunjukkan indikator kecurangan kritis yang memerlukan penyelidikan segera",
    }
    verdict = verdict_map.get(risk_score, verdict_map[0])

    lines = [
        f"Berdasarkan analisis multi-lapisan sistem LPSE-X, tender {tender_id} {verdict}.",
    ]

    if top_feat_names:
        lines.append(
            f"Faktor pendorong risiko utama yang teridentifikasi adalah {feat_str}."
        )

    if evidence_alignment >= 2:
        lines.append(
            f"Temuan ini dikuatkan oleh {evidence_alignment} dari 3 metode analisis "
            f"independen (SHAP, Benford, Graf Komunitas), yang meningkatkan tingkat "
            f"kepercayaan terhadap hasil analisis."
        )
    elif evidence_alignment == 1:
        lines.append(
            "Hanya satu metode analisis yang mengindikasikan risiko; "
            "diperlukan verifikasi lebih lanjut sebelum mengambil kesimpulan."
        )
    else:
        lines.append(
            "Tidak ada metode analisis independen yang mengkonfirmasi indikasi risiko."
        )

    lines.append(
        f"Tingkat risiko akhir yang ditetapkan: {risk_level.upper()} (skor {risk_score}/3)."
    )
    return "\n".join(lines)


def _build_evidence_narrative(
    evidence_alignment: int,
    shap_ctx: dict[str, Any],
    benford_ctx: dict[str, Any],
    leiden_ctx: dict[str, Any],
) -> str:
    """Build evidence matrix narrative paragraph."""
    if evidence_alignment == 0:
        return "Tidak ada metode yang mengindikasikan risiko. Hasil analisis konsisten: tender ini berada dalam batas normal."
    if evidence_alignment == 1:
        return (
            "Satu metode mengindikasikan risiko, namun tidak didukung oleh metode lain. "
            "Kepercayaan terhadap temuan ini SEDANG — verifikasi manual dianjurkan."
        )
    if evidence_alignment == 2:
        return (
            "Dua dari tiga metode independen mengindikasikan risiko secara bersamaan. "
            "Tingkat kepercayaan TINGGI. Tindak lanjut investigasi sangat direkomendasikan."
        )
    return (
        "SEMUA TIGA metode analisis independen (SHAP, Benford, Graf Komunitas) "
        "mengindikasikan risiko secara bersamaan. "
        "Tingkat kepercayaan SANGAT TINGGI. PENYELIDIKAN SEGERA DIPERLUKAN."
    )


def _extract_sections(report_text: str) -> dict[str, str]:
    """
    Parse rendered report text into individual section dict.

    Keys:
        "ringkasan_eksekutif", "identitas_pengadaan", "indikator_risiko",
        "matriks_bukti", "analisis_whatif", "kesimpulan_rekomendasi"
    """
    section_markers = [
        ("ringkasan_eksekutif", "BAGIAN 1 — RINGKASAN EKSEKUTIF"),
        ("identitas_pengadaan", "BAGIAN 2 — IDENTITAS PENGADAAN"),
        ("indikator_risiko", "BAGIAN 3 — INDIKATOR RISIKO"),
        ("matriks_bukti", "BAGIAN 4 — MATRIKS BUKTI"),
        ("analisis_whatif", "BAGIAN 5 — ANALISIS SKENARIO WHAT-IF"),
        ("kesimpulan_rekomendasi", "BAGIAN 6 — KESIMPULAN DAN REKOMENDASI"),
    ]

    sections: dict[str, str] = {}
    lines = report_text.split("\n")

    current_key: str | None = None
    current_lines: list[str] = []
    separator = "=" * 80

    for line in lines:
        matched = False
        for key, marker in section_markers:
            if marker in line:
                # Save previous section
                if current_key:
                    sections[current_key] = "\n".join(current_lines).strip()
                current_key = key
                current_lines = []
                matched = True
                break

        if not matched and current_key:
            # Stop section at next separator after content begins
            if line.startswith(separator) and current_lines:
                sections[current_key] = "\n".join(current_lines).strip()
                current_key = None
                current_lines = []
            else:
                current_lines.append(line)

    # Flush last section
    if current_key and current_lines:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections
