"""
generate_reports.py
===================
Pre-generates IIA 2025-format investigation reports for the top-5 highest-risk
tenders and inserts them into the `reports` table.

Usage:
    cd /c/Hackthon/lpse-x
    .venv/Scripts/python.exe scripts/generate_reports.py

Constraints:
  - No ORM — raw sqlite3 only
  - No external API calls — fully offline
  - Uses existing tables exactly as-is (no migrations)
  - seed=42
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so backend package is importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.reports.generator import ReportGenerator  # noqa: E402

DB_PATH = PROJECT_ROOT / "data" / "lpse_x.db"
TOP_N = 5


def _make_dummy_oracle(tender_id: str) -> SimpleNamespace:
    """
    Build a minimal oracle result with all layers in not_applicable state.
    The generator is fault-tolerant and produces a valid report from this.
    """
    dummy_layer = SimpleNamespace(status="not_applicable", data=None, error=None)
    return SimpleNamespace(
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


def main() -> None:
    print(f"[generate_reports] Connecting to {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # ------------------------------------------------------------------
    # 1. Query top-5 tenders by risk_score
    # ------------------------------------------------------------------
    rows = conn.execute(
        """
        SELECT
            p.tender_id,
            p.risk_score,
            p.risk_level,
            t.title,
            t.buyer_name,
            t.value_amount,
            f.feature_json,
            f.icw_total_score
        FROM predictions p
        JOIN tenders t ON p.tender_id = t.tender_id
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

    gen = ReportGenerator()

    inserted = 0
    for row in rows:
        tender_id: str = row["tender_id"]
        title: str = row["title"] or "(tidak ada judul)"
        buyer_name: str = row["buyer_name"] or "(tidak ada satuan kerja)"
        value_amount: float = float(row["value_amount"] or 0.0)
        risk_score_float: float = float(row["risk_score"] or 0.0)

        print(
            f"  Generating report for {tender_id}  "
            f"(risk={risk_score_float:.3f}, buyer={buyer_name})"
        )

        oracle_result = _make_dummy_oracle(tender_id)

        tender_data = {
            "nama_paket": title,
            "satuan_kerja": buyer_name,
            "nilai_hps": value_amount,
        }

        result = gen.generate(
            oracle_result=oracle_result,
            tender_data=tender_data,
            tender_id=tender_id,
        )

        report_id = f"RPT-{uuid4().hex[:8].upper()}"
        content_json = json.dumps(
            {
                "risk_level": result.risk_level,
                "risk_score": result.risk_score,
                "evidence_count": result.evidence_count,
                "recommendations": result.recommendations,
                "sections": result.sections,
                "report_text": result.report_text,
            },
            ensure_ascii=False,
        )
        generated_at = datetime.now(timezone.utc).isoformat()

        conn.execute(
            """
            INSERT OR REPLACE INTO reports
                (report_id, tender_id, report_type, content, generated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (report_id, tender_id, "pre_investigation", content_json, generated_at),
        )
        conn.commit()
        inserted += 1
        print(f"     OK Inserted {report_id}  risk_level={result.risk_level}")

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
