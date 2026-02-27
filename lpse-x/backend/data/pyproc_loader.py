"""
LPSE-X pyproc Loader — Real-time LPSE scraping via pyproc library.

Wraps pyproc for scraping live LPSE procurement data.
Handles Cloudflare blocks and network errors gracefully — never crashes.
Falls back to opentender.net API if pyproc is unavailable.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from backend.config.runtime import get_config
from backend.data.ingestion import hash_npwp
from backend.data.storage import get_connection, upsert_tender

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# pyproc optional import — graceful if not installed
# ---------------------------------------------------------------------------

_pyproc_available: bool = False
_LpseClass: Any = None
try:
    from pyproc import Lpse as _LpseClass  # type: ignore[import-untyped]
    _pyproc_available = True
except ImportError:
    logger.warning("pyproc not installed — PyProcLoader will be non-functional. Install via: pip install pyproc")

# ---------------------------------------------------------------------------
# Known LPSE hosts (MVP scope: 5 institutions)
# ---------------------------------------------------------------------------

_DEFAULT_LPSE_HOSTS = {
    "kemenkeu": "https://lpse.kemenkeu.go.id",
    "kemen-pupr": "https://lpse.pu.go.id",
    "kemenkes": "https://lpse.kemenkes.go.id",
    "dki-jakarta": "https://lpse.jakarta.go.id",
    "sumbar": "https://lpse.sumbarprov.go.id",
}

# Thread pool for blocking pyproc calls (pyproc is synchronous)
_executor = ThreadPoolExecutor(max_workers=2)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _scrape_lpse_sync(
    host_url: str,
    host_name: str,
    start: int,
    length: int,
) -> list[Any]:
    """
    Synchronous pyproc scraping (runs in thread pool).

    Args:
        host_url: LPSE host URL.
        host_name: Human-readable name for logging.
        start: Starting offset.
        length: Number of records to fetch.

    Returns:
        List of raw tender dicts from pyproc.
    """
    if not _pyproc_available:
        logger.warning("pyproc not available — skipping %s", host_name)
        return []

    try:
        lpse = _LpseClass(host_url)
        result = lpse.get_paket_tender(start=start, length=length)
        records = result.get("data", [])
        logger.info("pyproc: fetched %d records from %s", len(records), host_name)
        return records
    except ConnectionError as exc:
        logger.warning(
            "Cloudflare/connection error scraping %s (%s): %s — falling back",
            host_name,
            host_url,
            str(exc)[:120],
        )
        return []
    except TimeoutError as exc:
        logger.warning("Timeout scraping %s: %s", host_name, exc)
        return []
    except Exception as exc:
        logger.warning(
            "Unexpected error scraping %s (%s): %s — skipping",
            host_name,
            host_url,
            str(exc)[:200],
        )
        return []


def _parse_pyproc_record(raw: Any, host_name: str) -> Optional[dict[str, Any]]:
    """
    Parse a pyproc tender record (list format) into a dict for upsert.

    pyproc returns rows as lists:
    [0] = id, [1] = kode_tender, [2] = nama_paket, [3] = instansi,
    [4] = hps, [5] = metode, ...
    Format varies by LPSE version — handle gracefully.
    """
    try:
        if not isinstance(raw, (list, tuple)) or len(raw) < 3:
            return None

        tender_id = str(raw[1]) if len(raw) > 1 and raw[1] else str(raw[0])
        title = str(raw[2]) if len(raw) > 2 and raw[2] else None

        # HPS / value extraction
        value_amount = None
        if len(raw) > 4 and raw[4] is not None:
            try:
                value_amount = float(raw[4])
            except (ValueError, TypeError):
                value_amount = None

        return {
            "tender_id": f"pyproc-{host_name}-{tender_id}",
            "title": title,
            "buyer_name": host_name,
            "buyer_id": None,
            "value_amount": value_amount,
            "value_currency": "IDR",
            "procurement_method": str(raw[5]) if len(raw) > 5 and raw[5] else None,
            "procurement_category": None,
            "status": None,
            "date_published": None,
            "date_awarded": None,
            "npwp_hash": None,
            "npwp_last4": None,
            "total_score": None,
            "year": None,
            "source": f"pyproc:{host_name}",
        }
    except Exception as exc:
        logger.warning("Failed to parse pyproc record from %s: %s", host_name, exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class PyProcLoader:
    """
    Async wrapper for pyproc LPSE scraping.

    Usage:
        loader = PyProcLoader(db_path="data/lpse_x.db")
        count = await loader.scrape_all()
    """

    def __init__(self, db_path: str) -> None:
        """
        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = db_path

    async def scrape_host(
        self,
        host_name: str,
        host_url: str,
        batch_size: int = 50,
        max_records: int = 500,
    ) -> int:
        """
        Scrape tenders from a single LPSE host.

        Args:
            host_name: Human-readable institution name.
            host_url: LPSE host URL.
            batch_size: Records per request.
            max_records: Maximum records to fetch from this host.

        Returns:
            Number of records ingested.
        """
        if not _pyproc_available:
            logger.warning("pyproc not installed — cannot scrape %s", host_name)
            return 0

        config = get_config()
        logger.info("Scraping %s (%s) via pyproc", host_name, host_url)

        total_ingested = 0
        start = 0

        db = await get_connection(self.db_path)
        try:
            while start < max_records:
                loop = asyncio.get_event_loop()
                records = await loop.run_in_executor(
                    _executor,
                    _scrape_lpse_sync,
                    host_url,
                    host_name,
                    start,
                    batch_size,
                )

                if not records:
                    logger.info("No more records from %s at offset %d", host_name, start)
                    break

                for raw in records:
                    parsed = _parse_pyproc_record(raw, host_name)
                    if parsed is None:
                        continue

                    # Filter by institution_filter from config
                    if config.institution_filter:
                        matched = any(
                            inst.lower() in host_name.lower()
                            for inst in config.institution_filter
                        )
                        if not matched:
                            continue

                    await upsert_tender(db, parsed)
                    total_ingested += 1

                await db.commit()
                start += batch_size

                # Rate limit between batches
                await asyncio.sleep(2)

        except Exception as exc:
            logger.error("Error scraping %s: %s", host_name, exc)
        finally:
            await db.close()

        logger.info("pyproc: %d records ingested from %s", total_ingested, host_name)
        return total_ingested

    async def scrape_all(
        self,
        hosts: Optional[dict[str, str]] = None,
        max_records_per_host: int = 500,
    ) -> int:
        """
        Scrape all configured LPSE hosts sequentially.

        Args:
            hosts: Dict of {name: url}. Defaults to MVP 5 institutions.
            max_records_per_host: Maximum records per host.

        Returns:
            Total number of records ingested across all hosts.
        """
        if not _pyproc_available:
            logger.warning("pyproc not installed — scrape_all is a no-op")
            return 0

        config = get_config()
        target_hosts = hosts or _DEFAULT_LPSE_HOSTS

        # Filter hosts by institution_filter if set
        if config.institution_filter:
            filtered = {}
            for name, url in target_hosts.items():
                if any(inst.lower() in name.lower() for inst in config.institution_filter):
                    filtered[name] = url
            if filtered:
                target_hosts = filtered
                logger.info("Filtered hosts by institution_filter: %s", list(target_hosts.keys()))

        logger.info("Starting pyproc scrape of %d hosts", len(target_hosts))
        total = 0

        for name, url in target_hosts.items():
            count = await self.scrape_host(name, url, max_records=max_records_per_host)
            total += count

        logger.info("pyproc scrape complete: %d total records from %d hosts", total, len(target_hosts))
        return total
