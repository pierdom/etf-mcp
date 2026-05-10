"""Tool: get_quote — latest price via Yahoo Finance, fallback to justETF Gettex."""
from __future__ import annotations

import asyncio

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from etf_scout_mcp.sources import yahoo


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


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_quote(symbol: str, isin: str | None = None) -> Quote:
        """Return the latest price quote for an ETF.

        Tries Yahoo Finance first using the ticker symbol (e.g. 'IWDA.AS',
        'VWCE.DE', 'CSPX.L'). If Yahoo fails and an ISIN is provided, falls
        back to the justETF Gettex live quote (EUR, European hours only).

        Use this for a current price check. Use get_history for OHLCV series.
        This tool is for research only — for portfolio valuation, pair it
        with a portfolio tool such as Ghostfolio (ghostfolio-mcp).

        symbol: Yahoo Finance ticker, e.g. 'IWDA.AS' or 'VWCE.DE'
        isin:   Optional ISIN for Gettex fallback, e.g. 'IE00B4L5Y983'
        """
        try:
            data = await yahoo.fetch_quote(symbol)
            if data.get("price") is None and isin:
                raise RuntimeError(f"Yahoo returned no price for {symbol!r}")
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
                        "symbol": symbol,
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
