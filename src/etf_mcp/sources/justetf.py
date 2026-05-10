"""justETF source — wraps justetf-scraping for profiles, overviews, and screener."""
from __future__ import annotations

import asyncio
import logging
import math
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any

import justetf_scraping
from justetf_scraping.overview import load_overview

from etf_mcp.cache import cached
from etf_mcp.config import config

# ---------------------------------------------------------------------------
# Logging — same rotating-file pattern as sources/yahoo.py
# ---------------------------------------------------------------------------

_log = logging.getLogger("etf_mcp.justetf")


def _ensure_log_handler() -> None:
    if _log.handlers:
        return
    config.cache_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = config.cache_path.parent / "calls.log"
    handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    _log.addHandler(handler)
    _log.setLevel(config.log_level)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_DATE_FORMATS = (
    "%d %B %Y",    # "25 September 2009"
    "%d/%m/%Y",    # "31/03/2026"
    "%Y-%m-%d",    # already ISO
)


def _parse_date(value: str | None) -> str | None:
    if not value or value == "-":
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return value  # return as-is if unparseable


def _safe_float(value: Any) -> float | None:
    """Return None for NaN/None, else round to 6 decimal places."""
    if value is None:
        return None
    try:
        f = float(value)
        return None if math.isnan(f) else round(f, 6)
    except (TypeError, ValueError):
        return None


def _ter_to_decimal(pct: Any) -> float | None:
    """Convert TER from percent (library) to decimal (our convention).
    0.20 (percent) → 0.002 (decimal, 20 bps).
    """
    f = _safe_float(pct)
    return round(f / 100, 8) if f is not None else None


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------


@cached(ttl_key="profile")
async def fetch_profile(isin: str) -> dict[str, Any]:
    """Fetch full ETF profile for *isin* from justETF.

    Returns a dict suitable for building an EtfProfile model.
    TER is decimal (0.002 = 0.20%). fund_size_eur is in EUR (not millions).
    """
    def _inner() -> dict[str, Any]:
        _ensure_log_handler()
        t0 = time.monotonic()
        try:
            ov = justetf_scraping.get_etf_overview(isin, include_gettex=False, expand_allocations=True)
        except Exception as exc:
            _log.warning("error fn=get_etf_overview isin=%s latency=%.3fs error=%r", isin, time.monotonic() - t0, exc)
            raise
        _log.info("ok fn=get_etf_overview isin=%s latency=%.3fs", isin, time.monotonic() - t0)
        return {
            "isin": ov["isin"],
            "name": ov.get("name"),
            "description": ov.get("description"),
            "index": ov.get("index"),
            "investment_focus": ov.get("investment_focus"),
            # fund_size from library is in EUR millions → convert to EUR
            "fund_size_eur": (ov["fund_size_eur"] * 1_000_000) if ov.get("fund_size_eur") else None,
            "ter": _ter_to_decimal(ov.get("ter")),
            "replication": ov.get("replication"),
            "distribution_policy": ov.get("distribution_policy"),
            "distribution_frequency": ov.get("distribution_frequency"),
            "fund_currency": ov.get("fund_currency"),
            "currency_hedged": ov.get("currency_hedged"),
            "fund_domicile": ov.get("fund_domicile"),
            "fund_provider": ov.get("fund_provider"),
            "legal_structure": ov.get("legal_structure"),
            "sustainability": ov.get("sustainability"),
            "volatility_1y": _safe_float(ov.get("volatility_1y")),
            "inception_date": _parse_date(ov.get("inception_date")),
            "holdings_date": _parse_date(ov.get("holdings_date")),
            "top_holdings": [
                {
                    "name": h["name"],
                    "isin": h.get("isin"),
                    "weight": _safe_float(h["percentage"]),
                }
                for h in (ov.get("top_holdings") or [])
            ],
            "countries": [
                {"name": c["name"], "weight": _safe_float(c["percentage"])}
                for c in (ov.get("countries") or [])
            ],
            "sectors": [
                {"name": s["name"], "weight": _safe_float(s["percentage"])}
                for s in (ov.get("sectors") or [])
            ],
        }

    return await asyncio.to_thread(_inner)


def _row_to_summary(isin: str, row: Any) -> dict[str, Any]:
    """Convert a load_overview DataFrame row to a summary dict."""
    inc = row.get("inception_date")
    return {
        "isin": isin,
        "name": row.get("name"),
        "ticker": row.get("ticker"),
        "fund_provider": None,
        "fund_domicile": str(row.get("domicile_country")) if row.get("domicile_country") else None,
        "fund_size_eur": (float(row["size"]) * 1_000_000) if row.get("size") and not math.isnan(float(row["size"])) else None,
        "ter": _ter_to_decimal(row.get("ter")),
        "replication": str(row.get("replication")) if row.get("replication") else None,
        "distribution_policy": str(row.get("dividends")) if row.get("dividends") else None,
        "currency_hedged": bool(row.get("hedged")),
        "sustainability": bool(row.get("is_sustainable")),
        "inception_date": inc.date().isoformat() if hasattr(inc, "date") else None,
        "return_1y": _safe_float(row.get("last_year")),
        "return_3y": _safe_float(row.get("last_three_years")),
        "return_5y": _safe_float(row.get("last_five_years")),
        "volatility_1y": _safe_float(row.get("last_year_volatility")),
    }


@cached(ttl_key="profile")
async def fetch_summary(isin: str) -> dict[str, Any] | None:
    """Fetch a lightweight summary row for a single ETF by ISIN from justETF."""
    def _inner() -> dict[str, Any] | None:
        _ensure_log_handler()
        t0 = time.monotonic()
        try:
            df = load_overview(isin=isin)
        except Exception as exc:
            _log.warning("error fn=load_overview isin=%s latency=%.3fs error=%r", isin, time.monotonic() - t0, exc)
            raise
        _log.info("ok fn=load_overview isin=%s rows=%d latency=%.3fs", isin, len(df), time.monotonic() - t0)
        if df.empty:
            return None
        return _row_to_summary(df.index[0], df.iloc[0])

    return await asyncio.to_thread(_inner)


@cached(ttl_key="profile")
async def fetch_screener(
    asset_class: str | None = None,
    region: str | None = None,
    max_ter: float | None = None,
    min_fund_size_eur: float | None = None,
    distribution: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Query the justETF screener and return matching ETFs.

    max_ter is decimal (0.002 = 0.20%). min_fund_size_eur is in EUR.
    Returns are percentages (24.76 means +24.76%).
    """
    # Map friendly strings to justETF query values
    _asset_map = {
        "equity": "class-equity",
        "bonds": "class-bonds",
        "commodities": "class-commodities",
        "real_estate": "class-realEstate",
        "money_market": "class-moneyMarket",
        "precious_metals": "class-preciousMetals",
        "currency": "class-currency",
    }
    _region_map = {
        "world": "World",
        "europe": "Europe",
        "north_america": "North%2BAmerica",
        "asia_pacific": "Asia%2BPacific",
        "emerging_markets": "Emerging%2BMarkets",
        "eastern_europe": "Eastern%2BEurope",
        "latin_america": "Latin%2BAmerica",
        "africa": "Africa",
    }

    def _inner() -> list[dict[str, Any]]:
        _ensure_log_handler()
        ac = _asset_map.get((asset_class or "").lower(), asset_class)
        rg = _region_map.get((region or "").lower(), region)
        t0 = time.monotonic()
        try:
            df = load_overview(asset_class=ac, region=rg)
        except Exception as exc:
            _log.warning("error fn=load_overview asset_class=%s region=%s latency=%.3fs error=%r", ac, rg, time.monotonic() - t0, exc)
            raise
        _log.info("ok fn=load_overview asset_class=%s region=%s rows=%d latency=%.3fs", ac, rg, len(df), time.monotonic() - t0)

        # Post-filters
        if max_ter is not None:
            # library TER is percent; max_ter is decimal → compare after converting
            df = df[df["ter"].notna() & (df["ter"] / 100 <= max_ter)]
        if min_fund_size_eur is not None:
            # library size is EUR millions
            df = df[df["size"].notna() & (df["size"] * 1_000_000 >= min_fund_size_eur)]
        if distribution is not None:
            dist_norm = distribution.lower()
            df = df[df["dividends"].astype(str).str.lower() == dist_norm]

        df = df.head(limit)

        return [_row_to_summary(isin, row) for isin, row in df.iterrows()]

    return await asyncio.to_thread(_inner)
