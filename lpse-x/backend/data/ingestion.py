"""
LPSE-X Opentender.net Ingestion — Paginated OCDS download with NPWP hashing.

Downloads tender data from opentender.net REST API, parses OCDS fields,
hashes NPWP values (SHA-256 + last 4 digits), and stores into SQLite.
ALL parameters read from get_config() — nothing hardcoded.
"""

import asyncio
import hashlib
import logging
from typing import Any, Optional

import httpx

from backend.config.runtime import get_config
from backend.data.storage import get_connection, upsert_tender

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NPWP hashing utility
# ---------------------------------------------------------------------------


def hash_npwp(raw_npwp: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Hash NPWP with SHA-256. Returns (hex_digest, last_4_digits).
    Raw NPWP is NEVER stored — only hash + last 4 digits.

    Args:
        raw_npwp: Raw NPWP string (may be None).

    Returns:
        Tuple of (sha256_hex, last_4_chars) or (None, None) if input is None/empty.
    """
    if not raw_npwp or not raw_npwp.strip():
        return None, None

    cleaned = raw_npwp.strip().replace(".", "").replace("-", "")
    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
    last4 = cleaned[-4:] if len(cleaned) >= 4 else cleaned
    return digest, last4


# ---------------------------------------------------------------------------
# OCDS field extraction
# ---------------------------------------------------------------------------


def _parse_opentender_record(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Extract OCDS-standard fields from an opentender.net API response record.

    Maps opentender.net JSON structure to our tenders table schema.
    """
    buyer: dict[str, Any] = raw.get("buyer") or {}
    tender_data: dict[str, Any] = raw.get("tender") or {}
    value: dict[str, Any] = tender_data.get("value") or {}
    awards: list[Any] = raw.get("awards") or []

    # Extract award date from first award
    date_awarded = None
    if awards and isinstance(awards, list) and len(awards) > 0:
        date_awarded = awards[0].get("date")

    # NPWP hashing — extract from awards or suppliers
    raw_npwp = None
    if awards and isinstance(awards, list) and len(awards) > 0:
        suppliers = awards[0].get("suppliers") or []
        if suppliers and isinstance(suppliers, list) and len(suppliers) > 0:
            contact = suppliers[0].get("contactPoint") or {}
            raw_npwp = contact.get("npwp") or suppliers[0].get("npwp")

    npwp_hash, npwp_last4 = hash_npwp(raw_npwp)

    # Extract year from date_published or fallback
    date_published: Any = tender_data.get("tenderPeriod", {}).get("startDate")
    year = None
    if date_published and len(date_published) >= 4:
        try:
            year = int(date_published[:4])
        except (ValueError, TypeError):
            year = None

    return {
        "tender_id": raw.get("id") or raw.get("ocid"),
        "title": tender_data.get("title") or raw.get("title"),
        "buyer_name": buyer.get("name"),
        "buyer_id": buyer.get("id"),
        "value_amount": value.get("amount"),
        "value_currency": value.get("currency", "IDR"),
        "procurement_method": tender_data.get("procurementMethod"),
        "procurement_category": tender_data.get("procurementCategory"),
        "status": tender_data.get("status"),
        "date_published": date_published,
        "date_awarded": date_awarded,
        "npwp_hash": npwp_hash,
        "npwp_last4": npwp_last4,
        "total_score": raw.get("totalScore") or raw.get("total_score"),
        "year": year,
        "source": "opentender",
    }


# ---------------------------------------------------------------------------
# Paginated download
# ---------------------------------------------------------------------------

_BASE_URL = "https://opentender.net/api/tender/"
_PAGE_SIZE = 100


async def ingest_opentender(
    db_path: str,
    max_pages: Optional[int] = None,
) -> int:
    """
    Download tenders from opentender.net API with pagination and rate limiting.

    Reads procurement_scope, year_range, and institution_filter from runtime config.
    Applies 1-second rate limit between API calls.

    Args:
        db_path: Path to SQLite database file.
        max_pages: Optional cap on pages to fetch (None = fetch all).

    Returns:
        Number of tender records ingested.
    """
    config = get_config()
    start_year, end_year = config.year_range

    logger.info(
        "Starting opentender.net ingestion: scope=%s, years=%d-%d, institutions=%s",
        config.procurement_scope.value,
        start_year,
        end_year,
        config.institution_filter or "all",
    )

    total_ingested = 0
    page = 0

    db = await get_connection(db_path)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                if max_pages is not None and page >= max_pages:
                    logger.info("Reached max_pages limit (%d)", max_pages)
                    break

                params: dict[str, Any] = {
                    "page": page,
                    "pageSize": _PAGE_SIZE,
                    "country": "ID",
                }

                logger.debug("Fetching page %d from opentender.net", page)

                try:
                    response = await client.get(_BASE_URL, params=params)
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    logger.error(
                        "HTTP %d on page %d: %s",
                        exc.response.status_code,
                        page,
                        exc.response.text[:200],
                    )
                    break
                except httpx.RequestError as exc:
                    logger.error("Request failed on page %d: %s", page, exc)
                    break

                data = response.json()
                records = data.get("data", [])
                meta = data.get("meta", {})
                total_available = meta.get("total", 0)

                if not records:
                    logger.info("No more records at page %d", page)
                    break

                page_count = 0
                for raw_record in records:
                    parsed = _parse_opentender_record(raw_record)

                    # Filter by year_range from config
                    rec_year = parsed.get("year")
                    if rec_year is not None and (rec_year < start_year or rec_year > end_year):
                        continue

                    # Filter by procurement_scope from config
                    rec_category = (parsed.get("procurement_category") or "").lower()
                    if rec_category and config.procurement_scope.value not in rec_category:
                        continue

                    # Filter by institution_filter from config
                    if config.institution_filter:
                        buyer_name = (parsed.get("buyer_name") or "").lower()
                        matched = any(
                            inst.lower() in buyer_name
                            for inst in config.institution_filter
                        )
                        if not matched:
                            continue

                    await upsert_tender(db, parsed)
                    page_count += 1

                await db.commit()
                total_ingested += page_count

                logger.info(
                    "Page %d: %d/%d records ingested (total: %d, available: %d)",
                    page,
                    page_count,
                    len(records),
                    total_ingested,
                    total_available,
                )

                page += 1

                # Rate limit: 1 second between requests
                await asyncio.sleep(1)

    except Exception as exc:
        logger.exception("Unexpected error during opentender ingestion: %s", exc)
        raise
    finally:
        await db.close()

    logger.info("Opentender ingestion complete: %d records total", total_ingested)
    return total_ingested
