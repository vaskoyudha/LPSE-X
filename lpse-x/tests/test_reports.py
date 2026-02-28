"""
Tests for T13: Auto Pre-Investigation Report Generator
=======================================================
~30 tests covering all ReportResult fields, sections, risk levels,
Bahasa Indonesia content, and fault tolerance.
"""
from __future__ import annotations

import pytest
from types import SimpleNamespace
from pathlib import Path

from backend.reports.generator import (
    ReportGenerator,
    ReportResult,
    RISK_LABELS,
    RECOMMENDATIONS,
    _compute_risk_score,
    _compute_evidence_alignment,
    _extract_sections,
    _build_conclusion,
    _build_evidence_narrative,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _make_layer(status: str, data=None, error=None):
    """Create a mock LayerResult-like object."""
    return SimpleNamespace(status=status, data=data, error=error)


def _make_shap_data(model_output: float = 0.8):
    """Mock ShapLocalResult as dict."""
    return {
        "tender_id": "TEST-001",
        "feature_names": ["n_bidders", "price_ratio", "bid_spread"],
        "shap_values": [0.3, 0.25, 0.1],
        "base_value": 0.1,
        "model_output": model_output,
        "top_positive_features": [
            {"name": "n_bidders", "shap": 0.3, "value": 1.0},
            {"name": "price_ratio", "shap": 0.25, "value": 0.99},
        ],
        "top_negative_features": [
            {"name": "bid_spread", "shap": -0.05, "value": 0.15},
        ],
        "additivity_error": 0.001,
        "computation_seconds": 0.12,
    }


def _make_benford_data(suspicious: bool = True):
    """Mock Benford result as dict."""
    return {
        "applicable": True,
        "suspicious": suspicious,
        "chi2": 45.2 if suspicious else 8.3,
        "p_value": 0.001 if suspicious else 0.42,
    }


def _make_dice_data():
    """Mock DiCE counterfactual result."""
    return {
        "tender_id": "TEST-001",
        "original": {"n_bidders": 1.0, "price_ratio": 0.99},
        "counterfactuals": [
            {
                "features": {"n_bidders": 4.0, "price_ratio": 0.85},
                "changes": [
                    {"feature": "n_bidders", "from": 1.0, "to": 4.0, "direction": "increase", "delta": 3.0},
                    {"feature": "price_ratio", "from": 0.99, "to": 0.85, "direction": "decrease", "delta": -0.14},
                ],
                "risk_score": 0,
            }
        ],
        "generation_time_ms": 1500.0,
        "from_cache": False,
        "error": None,
    }


def _make_leiden_data():
    return {"community_size": 5, "suspicion_score": 0.82}


def _make_oracle_result(
    shap_output: float = 0.8,
    benford_suspicious: bool = True,
    leiden_ok: bool = True,
    dice_ok: bool = True,
):
    """Build a complete mock OracleSandwichResult."""
    return SimpleNamespace(
        tender_id="TEST-001",
        shap=_make_layer("ok", _make_shap_data(shap_output)),
        benford=_make_layer("ok", _make_benford_data(benford_suspicious)),
        leiden=_make_layer("ok" if leiden_ok else "not_applicable", _make_leiden_data() if leiden_ok else None),
        anchors=_make_layer("not_applicable"),
        dice=_make_layer("ok" if dice_ok else "not_applicable", _make_dice_data() if dice_ok else None),
        layers_ok=4 if dice_ok else 3,
        layers_failed=0,
        total_seconds=0.5,
    )


@pytest.fixture
def generator():
    """ReportGenerator with default template directory."""
    return ReportGenerator()


@pytest.fixture
def high_risk_result():
    """Oracle result indicating Kritis (score=3) risk."""
    return _make_oracle_result(shap_output=0.95, benford_suspicious=True, leiden_ok=True)


@pytest.fixture
def low_risk_result():
    """Oracle result indicating Aman (score=0) risk."""
    return _make_oracle_result(shap_output=0.1, benford_suspicious=False, leiden_ok=False)


@pytest.fixture
def tender_data():
    return {
        "tender_id": "TEST-001",
        "nama_paket": "Konstruksi Jembatan Tanjung Mas",
        "satuan_kerja": "Dinas PUPR Kota Semarang",
        "kategori": "konstruksi",
        "metode": "lelang umum",
        "nilai_hps": "5000000000",
        "nilai_kontrak": "4980000000",
        "jumlah_peserta": "1",
        "pemenang": "PT Kontraktor Jaya",
        "tahun_anggaran": "2024",
    }


# ---------------------------------------------------------------------------
# TestReportResultStructure — verify all required fields exist
# ---------------------------------------------------------------------------

class TestReportResultStructure:
    def test_result_has_tender_id(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="TEST-001")
        assert result.tender_id == "TEST-001"

    def test_result_has_report_text(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="TEST-001")
        assert isinstance(result.report_text, str)
        assert len(result.report_text) > 0

    def test_result_has_risk_level(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="TEST-001")
        assert result.risk_level in {"Aman", "Perlu Pantauan", "Berisiko", "Kritis"}

    def test_result_has_risk_score_int(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="TEST-001")
        assert isinstance(result.risk_score, int)
        assert 0 <= result.risk_score <= 3

    def test_result_has_generated_at_iso(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="TEST-001")
        assert isinstance(result.generated_at, str)
        assert "T" in result.generated_at  # ISO 8601

    def test_result_has_sections_dict(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="TEST-001")
        assert isinstance(result.sections, dict)

    def test_result_has_evidence_count(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="TEST-001")
        assert isinstance(result.evidence_count, int)
        assert result.evidence_count >= 0

    def test_result_has_recommendations_list(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="TEST-001")
        assert isinstance(result.recommendations, list)


# ---------------------------------------------------------------------------
# TestRiskLevelMapping — verify risk_score → risk_level consistency
# ---------------------------------------------------------------------------

class TestRiskLevelMapping:
    def test_high_shap_output_gives_high_risk(self, generator):
        oracle = _make_oracle_result(shap_output=0.95, benford_suspicious=True, leiden_ok=True)
        result = generator.generate(oracle, tender_id="X")
        assert result.risk_score >= 2  # Berisiko or Kritis

    def test_low_shap_output_gives_low_risk(self, generator):
        oracle = _make_oracle_result(shap_output=0.05, benford_suspicious=False, leiden_ok=False)
        result = generator.generate(oracle, tender_id="X")
        assert result.risk_score <= 1

    def test_risk_level_matches_risk_score(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="X")
        expected = RISK_LABELS[result.risk_score]
        assert result.risk_level == expected

    @pytest.mark.parametrize("score,expected_level", [
        (0, "Aman"),
        (1, "Perlu Pantauan"),
        (2, "Berisiko"),
        (3, "Kritis"),
    ])
    def test_risk_labels_mapping(self, score, expected_level):
        assert RISK_LABELS[score] == expected_level

    def test_recommendations_non_empty(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="X")
        assert len(result.recommendations) > 0

    def test_high_risk_has_more_recommendations(self, generator):
        high = _make_oracle_result(shap_output=0.95, benford_suspicious=True, leiden_ok=True)
        low = _make_oracle_result(shap_output=0.05, benford_suspicious=False, leiden_ok=False)
        r_high = generator.generate(high, tender_id="X")
        r_low = generator.generate(low, tender_id="X")
        assert len(r_high.recommendations) >= len(r_low.recommendations)


# ---------------------------------------------------------------------------
# TestSectionsContent — verify 6 IIA sections are present
# ---------------------------------------------------------------------------

class TestSectionsContent:
    EXPECTED_SECTIONS = [
        "ringkasan_eksekutif",
        "identitas_pengadaan",
        "indikator_risiko",
        "matriks_bukti",
        "analisis_whatif",
        "kesimpulan_rekomendasi",
    ]

    def test_all_6_sections_present(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="TEST-001")
        for section in self.EXPECTED_SECTIONS:
            assert section in result.sections, f"Missing section: {section}"

    def test_sections_are_non_empty_strings(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="TEST-001")
        for section in self.EXPECTED_SECTIONS:
            content = result.sections.get(section, "")
            assert isinstance(content, str)
            assert len(content) > 0, f"Section {section} is empty"

    def test_ringkasan_contains_tender_id(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="TEST-UNIQUE-ID")
        assert "TEST-UNIQUE-ID" in result.sections.get("ringkasan_eksekutif", "")

    def test_identitas_contains_tender_info(self, generator, high_risk_result, tender_data):
        result = generator.generate(high_risk_result, tender_data=tender_data, tender_id="TEST-001")
        identitas = result.sections.get("identitas_pengadaan", "")
        assert "Konstruksi Jembatan" in identitas or "Tidak Tersedia" in identitas


# ---------------------------------------------------------------------------
# TestBahasaIndonesia — verify Indonesian language content
# ---------------------------------------------------------------------------

class TestBahasaIndonesia:
    def test_report_contains_ringkasan_header(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="X")
        assert "RINGKASAN EKSEKUTIF" in result.report_text

    def test_report_contains_identitas_header(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="X")
        assert "IDENTITAS PENGADAAN" in result.report_text

    def test_report_contains_rekomendasi(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="X")
        assert "REKOMENDASI" in result.report_text

    def test_report_contains_kesimpulan(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="X")
        assert "KESIMPULAN" in result.report_text

    def test_high_risk_contains_kritis_keyword(self, generator):
        oracle = _make_oracle_result(shap_output=0.95, benford_suspicious=True, leiden_ok=True)
        result = generator.generate(oracle, tender_id="X")
        # High risk (score >= 2) should mention Kritis or Berisiko
        assert result.risk_level in {"Berisiko", "Kritis"}
        assert result.risk_level.upper() in result.report_text

    def test_low_risk_contains_aman_keyword(self, generator, low_risk_result):
        result = generator.generate(low_risk_result, tender_id="X")
        if result.risk_score == 0:
            assert "AMAN" in result.report_text or "Aman" in result.report_text

    def test_iia_2025_reference_present(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="X")
        assert "IIA 2025" in result.report_text or "LPSE-X" in result.report_text


# ---------------------------------------------------------------------------
# TestFaultTolerance — generator handles missing/partial Oracle data
# ---------------------------------------------------------------------------

class TestFaultTolerance:
    def test_none_oracle_result_does_not_crash(self, generator):
        result = generator.generate(None, tender_id="NONE-TEST")
        assert isinstance(result, ReportResult)
        assert result.tender_id == "NONE-TEST"
        assert len(result.report_text) > 0

    def test_none_oracle_gives_score_0(self, generator):
        result = generator.generate(None, tender_id="X")
        assert result.risk_score == 0

    def test_partial_layers_ok(self, generator):
        """Only SHAP available, others not_applicable."""
        oracle = SimpleNamespace(
            tender_id="PARTIAL",
            shap=_make_layer("ok", _make_shap_data(0.6)),
            benford=_make_layer("not_applicable"),
            leiden=_make_layer("not_applicable"),
            anchors=_make_layer("not_applicable"),
            dice=_make_layer("not_applicable"),
            layers_ok=1,
            layers_failed=0,
            total_seconds=0.1,
        )
        result = generator.generate(oracle, tender_id="PARTIAL")
        assert isinstance(result, ReportResult)
        assert result.evidence_count == 1

    def test_all_layers_error_gives_result(self, generator):
        """All layers errored — should still produce a report."""
        oracle = SimpleNamespace(
            tender_id="ERROR-TEST",
            shap=_make_layer("error", error="SHAP failed"),
            benford=_make_layer("error", error="Benford failed"),
            leiden=_make_layer("error", error="Leiden failed"),
            anchors=_make_layer("error", error="Anchors failed"),
            dice=_make_layer("error", error="DiCE failed"),
            layers_ok=0,
            layers_failed=5,
            total_seconds=0.0,
        )
        result = generator.generate(oracle, tender_id="ERROR-TEST")
        assert isinstance(result, ReportResult)
        assert result.risk_score == 0  # Defaults to safe when no data

    def test_no_tender_data_does_not_crash(self, generator, high_risk_result):
        """Omitting tender_data should work fine."""
        result = generator.generate(high_risk_result, tender_id="X")
        assert isinstance(result, ReportResult)
        assert "tidak tersedia" in result.report_text.lower()

    def test_dice_not_applicable_renders_message(self, generator):
        oracle = _make_oracle_result(shap_output=0.8, dice_ok=False)
        result = generator.generate(oracle, tender_id="X")
        bagian5 = result.sections.get("analisis_whatif", "")
        assert len(bagian5) > 0  # Section still exists


# ---------------------------------------------------------------------------
# TestHelperFunctions — unit tests for individual helpers
# ---------------------------------------------------------------------------

class TestHelperFunctions:
    def test_compute_risk_score_high(self):
        oracle = _make_oracle_result(shap_output=0.9, benford_suspicious=True, leiden_ok=True)
        score = _compute_risk_score(oracle)
        assert score >= 2

    def test_compute_risk_score_low(self):
        oracle = _make_oracle_result(shap_output=0.05, benford_suspicious=False, leiden_ok=False)
        score = _compute_risk_score(oracle)
        assert score <= 1

    def test_compute_evidence_alignment_all(self):
        oracle = _make_oracle_result(shap_output=0.9, benford_suspicious=True, leiden_ok=True)
        count = _compute_evidence_alignment(oracle)
        assert count == 3

    def test_compute_evidence_alignment_none(self):
        oracle = _make_oracle_result(shap_output=0.1, benford_suspicious=False, leiden_ok=False)
        count = _compute_evidence_alignment(oracle)
        assert count == 0

    def test_build_conclusion_returns_string(self):
        oracle = _make_oracle_result()
        shap_ctx = {"top_risk_features": [{"name": "n_bidders", "shap": 0.3, "value": 1.0}]}
        conclusion = _build_conclusion(
            tender_id="TEST",
            risk_score=2,
            risk_level="Berisiko",
            evidence_alignment=2,
            shap_ctx=shap_ctx,
            benford_ctx={},
            leiden_ctx={},
        )
        assert isinstance(conclusion, str)
        assert "TEST" in conclusion

    def test_build_evidence_narrative_all_methods(self):
        narrative = _build_evidence_narrative(3, {}, {}, {})
        assert "TIGA" in narrative or "tiga" in narrative or "SEMUA" in narrative

    def test_build_evidence_narrative_no_methods(self):
        narrative = _build_evidence_narrative(0, {}, {}, {})
        assert "normal" in narrative.lower() or "tidak" in narrative.lower()

    def test_extract_sections_parses_6_keys(self, generator, high_risk_result):
        result = generator.generate(high_risk_result, tender_id="X")
        sections = _extract_sections(result.report_text)
        expected = {
            "ringkasan_eksekutif", "identitas_pengadaan", "indikator_risiko",
            "matriks_bukti", "analisis_whatif", "kesimpulan_rekomendasi",
        }
        assert expected.issubset(set(sections.keys()))
