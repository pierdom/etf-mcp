"""Tool: get_quote — latest price via Yahoo Finance, fallback to justETF Gettex."""
from __future__ import annotations

import asyncio

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from etf_scout_mcp.sources import yahoo
from etf_scout_mcp.sources.openfigi import resolve_yahoo_ticker


class Quote(BaseModel):
    symbol: str
    isin: str | None = None
    currency: str | None = None
    price: float | None = None
    previous_close: float | None = None
    open: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    volume: int | None = None
    market_cap: float | None = Field(None, description="Market cap in the instrument's native currency")
    as_of: str | None = Field(None, description="ISO 8601 date string")
    source: str = Field(description="'yahoo' or 'justetf_gettex'")


async def fetch_one(symbol: str | None, isin: str | None) -> Quote:
    """Fetch a single quote, resolving ISIN→ticker if needed, with Gettex fallback."""
    if not symbol and not isin:
        raise ValueError("Provide at least one of: symbol, isin")

    resolved_symbol = symbol
    if not resolved_symbol:
        resolved_symbol = await resolve_yahoo_ticker(isin)  # type: ignore[arg-type]
        if not resolved_symbol:
            raise RuntimeError(
                f"Could not resolve a Yahoo Finance ticker for ISIN {isin!r}. "
                "Try passing the ticker directly, e.g. 'EUNL.DE' or 'IWDA.AS'."
            )

    try:
        data = await yahoo.fetch_quote(resolved_symbol)
        if data.get("price") is None and isin:
            raise RuntimeError(f"Yahoo returned no price for {resolved_symbol!r}")
        return Quote(source="yahoo", isin=isin, **data)
    except Exception as yahoo_err:
        if not isin:
            raise

        # Gettex fallback — justETF live quote (EUR, Gettex only)
        try:
            import justetf_scraping

            def _gettex() -> dict:
                quotes = list(justetf_scraping.iterate_live_quote(isin))
                if not quotes:
                    raise RuntimeError("no gettex quote received")
                q = quotes[0]
                return {
                    "symbol": resolved_symbol,
                    "currency": q.get("currency", "EUR"),
                    "price": q.get("last"),
                    "previous_close": None,
                    "open": None,
                    "day_high": None,
                    "day_low": None,
                    "volume": None,
                    "market_cap": None,
                    "as_of": q["timestamp"].date().isoformat() if q.get("timestamp") else None,
                }

            data = await asyncio.wait_for(asyncio.to_thread(_gettex), timeout=20.0)
            return Quote(source="justetf_gettex", isin=isin, **data)
        except asyncio.TimeoutError:
            raise RuntimeError(f"Gettex fallback timed out for {isin}") from None
        except Exception:
            raise yahoo_err  # surface the original Yahoo error if both fail


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_quote(symbol: str | None = None, isin: str | None = None) -> Quote:
        """Return the latest price quote for an ETF.

        Accepts a Yahoo Finance ticker, an ISIN, or both. When only an ISIN
        is given, the ticker is auto-resolved via OpenFIGI (Xetra preferred,
        then Euronext Amsterdam, LSE, etc.). If Yahoo fails, falls back to
        the justETF Gettex live quote (EUR, European hours only).

        Use this for a current price check. Use get_quotes for multiple ETFs
        in one call, or get_history for OHLCV series.
        This tool is for research only — for portfolio valuation, pair it
        with a portfolio tool such as Ghostfolio (ghostfolio-mcp).

        symbol: Yahoo Finance ticker, e.g. 'IWDA.AS' or 'VWCE.DE'.
                Optional when isin is provided.
        isin:   ISIN, e.g. 'IE00B4L5Y983'. Used for ticker auto-resolution
                and as Gettex fallback when Yahoo fails.
        """
        return await fetch_one(symbol, isin)
