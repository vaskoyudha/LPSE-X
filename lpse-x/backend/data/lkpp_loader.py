"""
LPSE-X LKPP XLSX Loader — Reads LKPP Open Data Excel files into SQLite.

Loads lkpp_*.xlsx files from a configurable path using pandas/openpyxl,
maps columns to tenders table schema, and inserts into SQLite.
Handles missing files gracefully.
"""

import glob
import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from backend.config.runtime import get_config
from backend.data.ingestion import hash_npwp
from backend.data.storage import get_connection, upsert_tender

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column mapping: LKPP XLSX → tenders table
# ---------------------------------------------------------------------------

# LKPP datasets have varying column names; map common variants
_COLUMN_MAP = {
    # tender_id candidates
    "kode_tender": "tender_id",
    "kode_rup": "tender_id",
    "kode_paket": "tender_id",
    "id_paket": "tender_id",
    # title
    "nama_paket": "title",
    "nama_tender": "title",
    "uraian_pekerjaan": "title",
    # buyer
    "nama_satker": "buyer_name",
    "nama_kldi": "buyer_name",
    "instansi": "buyer_name",
    "kementerian_lembaga": "buyer_name",
    "satuan_kerja": "buyer_name",
    # buyer_id
    "kode_satker": "buyer_id",
    "kode_kldi": "buyer_id",
    # value
    "pagu": "value_amount",
    "hps": "value_amount",
    "nilai_kontrak": "value_amount",
    "total_anggaran": "value_amount",
    # method
    "metode_pengadaan": "procurement_method",
    "metode_pemilihan": "procurement_method",
    # category
    "jenis_pengadaan": "procurement_category",
    "kategori": "procurement_category",
    # year
    "tahun_anggaran": "year",
    "tahun": "year",
    # npwp
    "npwp_penyedia": "npwp_raw",
    "npwp": "npwp_raw",
    # status
    "status_tender": "status",
    "status": "status",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize LKPP column names to match tenders table schema.

    Converts all columns to lowercase and applies the column mapping.
    Uses first matched column for each target field.
    """
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    renamed = {}
    used_targets: set[str] = set()

    for source_col, target_col in _COLUMN_MAP.items():
        if source_col in df.columns and target_col not in used_targets:
            renamed[source_col] = target_col
            used_targets.add(target_col)

    return df.rename(columns=renamed)


def _row_to_tender(row: pd.Series, source_file: str) -> Optional[dict[str, Any]]:
    """
    Convert a pandas row to a tender dict for upsert.
    """
    tender_id = row.get("tender_id")
    if tender_id is None or bool(pd.isna(tender_id)) or not str(tender_id).strip():
        return None
    npwp_hash = None
    npwp_last4 = None
    raw_npwp = row.get("npwp_raw")
    if raw_npwp is not None and not bool(pd.isna(raw_npwp)):
        npwp_hash, npwp_last4 = hash_npwp(str(raw_npwp))
    year = row.get("year")
    if year is not None and not bool(pd.isna(year)):
        try:
            year = int(float(year))
        except (ValueError, TypeError):
            year = None
    else:
        year = None
    # Parse value_amount
    value_amount = row.get("value_amount")
    if value_amount is not None and not bool(pd.isna(value_amount)):
        try:
            value_amount = float(value_amount)
        except (ValueError, TypeError):
            value_amount = None
    else:
        value_amount = None

    def _safe_str(val: object) -> Optional[str]:
        """Safely convert a value to stripped string, returning None for NaN."""
        if val is None or bool(pd.isna(val)):
            return None
        return str(val).strip() or None
    return {
        "tender_id": str(tender_id).strip(),
        "title": _safe_str(row.get("title")),
        "buyer_name": _safe_str(row.get("buyer_name")),
        "buyer_id": _safe_str(row.get("buyer_id")),
        "value_amount": value_amount,
        "value_currency": "IDR",
        "procurement_method": _safe_str(row.get("procurement_method")),
        "procurement_category": _safe_str(row.get("procurement_category")),
        "status": _safe_str(row.get("status")),
        "date_published": None,
        "date_awarded": None,
        "npwp_hash": npwp_hash,
        "npwp_last4": npwp_last4,
        "total_score": None,
        "year": year,
        "source": f"lkpp:{Path(source_file).stem}",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def load_lkpp_xlsx(
    db_path: str,
    xlsx_dir: Optional[str] = None,
) -> int:
    """
    Load all lkpp_*.xlsx files from the given directory into SQLite tenders table.

    Uses glob.glob() to find matching files. Handles missing directory/files gracefully.
    Respects year_range and procurement_scope from runtime config.

    Args:
        db_path: Path to SQLite database file.
        xlsx_dir: Directory containing lkpp_*.xlsx files.
                  Defaults to project-level path read from config custom_params
                  or fallback to 'C:\\Hackthon'.

    Returns:
        Number of tender records loaded.
    """
    config = get_config()
    start_year, end_year = config.year_range

    # Determine XLSX directory
    if xlsx_dir is None:
        # Check custom_params for override, fallback to known location
        xlsx_dir = str(config.custom_params.get("lkpp_xlsx_dir", str(Path(__file__).parent.parent.parent.parent)))

    pattern = str(Path(xlsx_dir) / "lkpp_*.xlsx")
    files = glob.glob(pattern)

    if not files:
        logger.warning("No lkpp_*.xlsx files found at pattern: %s", pattern)
        return 0

    logger.info("Found %d LKPP XLSX files: %s", len(files), [Path(f).name for f in files])

    total_loaded = 0
    db = await get_connection(db_path)

    try:
        for filepath in files:
            try:
                logger.info("Loading LKPP file: %s", Path(filepath).name)
                df = pd.read_excel(filepath, engine="openpyxl")

                if df.empty:
                    logger.warning("Empty file: %s", filepath)
                    continue

                df = _normalize_columns(df)
                file_count = 0

                for _, row in df.iterrows():
                    tender = _row_to_tender(row, filepath)
                    if tender is None:
                        continue

                    # Filter by year_range from config
                    rec_year = tender.get("year")
                    if rec_year is not None and (rec_year < start_year or rec_year > end_year):
                        continue

                    # Filter by procurement_scope from config
                    rec_category = (tender.get("procurement_category") or "").lower()
                    if rec_category and config.procurement_scope.value not in rec_category:
                        continue

                    await upsert_tender(db, tender)
                    file_count += 1

                await db.commit()
                total_loaded += file_count

                logger.info(
                    "Loaded %d records from %s (total: %d)",
                    file_count,
                    Path(filepath).name,
                    total_loaded,
                )

            except Exception as exc:
                logger.error("Failed to load %s: %s", filepath, exc)
                continue

    except Exception as exc:
        logger.exception("Unexpected error during LKPP loading: %s", exc)
        raise
    finally:
        await db.close()

    logger.info("LKPP XLSX loading complete: %d records from %d files", total_loaded, len(files))
    return total_loaded
