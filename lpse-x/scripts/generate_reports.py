"""
generate_reports.py
===================
Pre-generates IIA 2025-format investigation reports for the top-5 highest-risk
tenders by reading directly from the predictions table (bypassing ReportGenerator).

Usage:
    cd C:/Hackthon/lpse-x
    .venv/Scripts/python.exe scripts/generate_reports.py

Constraints:
  - No ORM — raw sqlite3 only
  - No external API calls — fully offline
  - Uses existing tables exactly as-is (no migrations)
  - Maps English risk_level to Indonesian display names
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "lpse_x.db"
TOP_N = 5

# Risk level mapping: English -> Indonesian
RISK_LEVEL_MAP = {
    "high": "Kritis",
    "medium": "Berisiko",
    "low": "Aman",
}

# Recommendations per risk level (Indonesian)
RECOMMENDATIONS_MAP = {
    "high": [
        "SEGERA laporkan ke otoritas pengawas terkait",
        "Tunda proses pengadaan hingga investigasi selesai",
        "Cegah pemenang dari melakukan transaksi hingga clear verification",
    ],
    "medium": [
        "Lakukan investigasi lebih lanjut sebelum approval pengadaan",
        "Monitor pelaksanaan kontrak lebih ketat",
        "Dokumentasikan semua anomali yang terdeteksi",
    ],
    "low": [
        "Tidak ada tindakan khusus yang diperlukan",
        "Lanjutkan proses pengadaan sesuai prosedur normal",
        "Monitor berkala saja",
    ],
}

# Narrative per risk level (Indonesian)
NARRATIVE_MAP = {
    "high": "Sistem mendeteksi INDIKATOR KECURANGAN KRITIS pada tender ini. Diperlukan PENYELIDIKAN SEGERA untuk memverifikasi keaslian data dan integritas proses.",
    "medium": "Sistem mendeteksi ANOMALI SEDANG pada tender ini. Diperlukan investigasi lebih lanjut untuk memastikan kepatuhan terhadap regulasi pengadaan.",
    "low": "Sistem tidak mendeteksi anomali signifikan. Tender ini dapat dilanjutkan sesuai prosedur standar.",
}

EXPLANATION_TEXT_MAP = {
    "high": "LAPORAN PRA-INVESTIGASI - INDIKASI KECURANGAN KRITIS. Analisis machine learning menemukan pola risiko tinggi pada tender ini yang memerlukan tindakan segera.",
    "medium": "LAPORAN PRA-INVESTIGASI - ANOMALI TERDETEKSI. Analisis menemukan beberapa indikator risiko yang memerlukan verifikasi lebih lanjut.",
    "low": "LAPORAN PRA-INVESTIGASI - NORMAL. Analisis tidak menemukan indikasi kecurangan signifikan.",
}


def extract_top_features(feature_json: str, max_count: int = 3) -> list[dict[str, object]]:
    """Extract top features from feature_json for display."""
    try:
        features_dict = json.loads(feature_json) if isinstance(feature_json, str) else feature_json
        # Convert to list of dicts with name and value
        feature_list = [
            {"name": k, "value": v, "contribution": v}
            for k, v in features_dict.items()
            if isinstance(v, (int, float))
        ]
        # Sort by absolute value descending
        feature_list.sort(key=lambda x: abs(x["value"]), reverse=True)
        
        # Add nice labels for common features
        label_map = {
            "R001_single_bid": "Indikator Penawar Tunggal",
            "R002_bid_near_hps": "Penawar Sangat Dekat HPS",
            "R003_bid_pattern": "Pola Penawaran Mencurigakan",
        }
        
        for feature in feature_list[:max_count]:
            feature["label"] = label_map.get(feature["name"], feature["name"])  # type: ignore
        
        return feature_list[:max_count]
    except Exception as e:
        print(f"[WARNING] Error extracting features: {e}", file=sys.stderr)
        return []


def build_report_content(
    tender_id: str,
    risk_level_en: str,
    risk_score: float,
    feature_json: str,
) -> dict[str, object]:
    """Build complete report JSON content."""
    risk_level_id = RISK_LEVEL_MAP.get(risk_level_en, "Aman")
    
    return {
        "tender_id": tender_id,
        "risk_level": risk_level_id,
        "risk_level_en": risk_level_en,
        "risk_score": round(float(risk_score), 6),
        "evidence_count": 3,  # Placeholder
        "top_features": extract_top_features(feature_json),
        "recommendations": RECOMMENDATIONS_MAP.get(risk_level_en, []),
        "explanation_text": EXPLANATION_TEXT_MAP.get(risk_level_en, ""),
        "narrative": NARRATIVE_MAP.get(risk_level_en, ""),
        "sections": {
            "ringkasan": f"Tender {tender_id} dinilai memiliki risiko {risk_level_id}",
            "analisis": f"Score risiko: {risk_score:.4f}",
            "rekomendasi": ", ".join(RECOMMENDATIONS_MAP.get(risk_level_en, [])),
        },
    }


def main() -> None:
    print(f"[generate_reports] Connecting to {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # ------------------------------------------------------------------
    # 1. DELETE all existing reports
    # ------------------------------------------------------------------
    old_count = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    if old_count > 0:
        print(f"[generate_reports] Deleting {old_count} existing reports...")
        conn.execute("DELETE FROM reports")
        conn.commit()
        print(f"[generate_reports] Deleted {old_count} reports.")

    # ------------------------------------------------------------------
    # 2. Query top-5 tenders by risk_score from predictions table
    # ------------------------------------------------------------------
    rows = conn.execute(
        """
        SELECT
            p.tender_id,
            p.risk_score,
            p.risk_level,
            f.feature_json
        FROM predictions p
        JOIN features f ON p.tender_id = f.tender_id
        ORDER BY p.risk_score DESC
        LIMIT ?
        """,
        (TOP_N,),
    ).fetchall()

    if not rows:
        print("[generate_reports] ERROR: No predictions found — run batch_predict.py first.")
        sys.exit(1)

    print(f"[generate_reports] Found {len(rows)} top-risk tenders to process.")

    inserted = 0
    for row in rows:
        tender_id: str = row["tender_id"]
        risk_score_float: float = float(row["risk_score"])
        risk_level_en: str = row["risk_level"]
        feature_json: str = row["feature_json"]

        print(
            f"  Generating report for {tender_id}  "
            f"(risk={risk_score_float:.3f}, level={risk_level_en})"
        )

        # Build report content directly from predictions
        content = build_report_content(tender_id, risk_level_en, risk_score_float, feature_json)
        
        report_id = f"RPT-{uuid4().hex[:8].upper()}"
        content_json = json.dumps(content, ensure_ascii=False)
        generated_at = datetime.now(timezone.utc).isoformat()

        conn.execute(
            """
            INSERT INTO reports
                (report_id, tender_id, report_type, content, generated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (report_id, tender_id, "pre_investigation", content_json, generated_at),
        )
        conn.commit()
        inserted += 1
        risk_level_id = RISK_LEVEL_MAP.get(risk_level_en, "Aman")
        print(f"     OK Inserted {report_id}  risk_level={risk_level_id}")

    # ------------------------------------------------------------------
    # 3. Verify
    # ------------------------------------------------------------------
    count = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    conn.close()

    print(f"\n[generate_reports] Done — {inserted} reports inserted. Total in DB: {count}")
    if count < TOP_N:
        print(f"[generate_reports] WARNING: expected {TOP_N} reports, got {count}.")
        sys.exit(1)
    print("[generate_reports] All reports verified in DB.")


if __name__ == "__main__":
    main()
