"""OpenFIGI source — ISIN → exchange listings via the official Bloomberg-backed API."""
from __future__ import annotations

import asyncio
import logging
import time
from logging.handlers import RotatingFileHandler
from typing import Any

import httpx

from etf_mcp.cache import cached
from etf_mcp.config import config

_API_URL = "https://api.openfigi.com/v3/mapping"

_log = logging.getLogger("etf_mcp.openfigi")


def _ensure_log_handler() -> None:
    if _log.handlers:
        return
    config.cache_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        config.cache_path.parent / "calls.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    _log.addHandler(handler)
    _log.setLevel(config.log_level)


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if config.openfigi_api_key:
        h["X-OPENFIGI-APIKEY"] = config.openfigi_api_key
    return h


@cached(ttl_key="profile")
async def fetch_listings(isin: str) -> list[dict[str, Any]]:
    """Fetch all exchange listings for *isin* from the OpenFIGI API.

    Returns a list of dicts with figi, ticker, exchCode, micCode,
    currency, name, securityType, marketSector fields.
    """
    _ensure_log_handler()
    t0 = time.monotonic()
    delays = [1.0, 4.0, 10.0]
    async with httpx.AsyncClient(timeout=15) as client:
        for attempt, delay in enumerate(delays + [None]):
            try:
                resp = await client.post(
                    _API_URL,
                    headers=_headers(),
                    json=[{"idType": "ID_ISIN", "idValue": isin}],
                )
            except Exception as exc:
                _log.warning("error fn=fetch_listings isin=%s latency=%.3fs error=%r", isin, time.monotonic() - t0, exc)
                raise
            if resp.status_code == 429:
                if delay is None:
                    _log.warning("error fn=fetch_listings isin=%s status=429 all retries exhausted", isin)
                    resp.raise_for_status()
                _log.info("rate_limited fn=fetch_listings isin=%s attempt=%d retry_in=%.1fs", isin, attempt + 1, delay)
                await asyncio.sleep(delay)
                continue
            try:
                resp.raise_for_status()
            except Exception as exc:
                _log.warning("error fn=fetch_listings isin=%s latency=%.3fs error=%r", isin, time.monotonic() - t0, exc)
                raise
            break

    results = resp.json()
    latency = time.monotonic() - t0
    # Response is a list with one entry per requested job
    job = results[0] if results else {}
    if "error" in job or "warning" in job:
        msg = job.get("error") or job.get("warning")
        _log.info("ok fn=fetch_listings isin=%s no_results=True msg=%r latency=%.3fs", isin, msg, latency)
        return []

    rows = job.get("data", [])
    _log.info("ok fn=fetch_listings isin=%s results=%d latency=%.3fs", isin, len(rows), latency)

    return [
        {
            "figi": r.get("figi"),
            "ticker": r.get("ticker"),
            "name": r.get("name"),
            "exch_code": r.get("exchCode"),
            "mic_code": r.get("micCode"),
            "currency": r.get("currency"),
            "security_type": r.get("securityType"),
            "market_sector": r.get("marketSector"),
            "security_description": r.get("securityDescription"),
        }
        for r in rows
    ]


async def fetch_ticker_for_exchange(isin: str, mic_code: str) -> str | None:
    """Return the ticker for *isin* on the exchange identified by *mic_code*.

    Convenience wrapper over fetch_listings for the common "give me the
    Xetra ticker" use case. Returns None if no listing found.

    mic_code: MIC exchange code, e.g. 'XETR' (Xetra), 'XAMS' (Euronext
              Amsterdam), 'XLON' (LSE), 'XPAR' (Euronext Paris).
    """
    listings = await fetch_listings(isin)
    for listing in listings:
        if listing.get("mic_code") == mic_code:
            return listing.get("ticker")
    return None
