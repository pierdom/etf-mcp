"""Tool: get_quotes — fetch multiple ETF quotes concurrently."""
from __future__ import annotations

import asyncio

from fastmcp import FastMCP
from pydantic import Field

from etf_scout_mcp.tools.quote import Quote, fetch_one


class QuoteResult(Quote):
    error: str | None = Field(None, description="Set when this symbol/ISIN could not be fetched")


async def _safe_fetch(symbol: str | None, isin: str | None) -> QuoteResult:
    """Wrap fetch_one so a single failure doesn't abort the whole batch."""
    try:
        q = await fetch_one(symbol, isin)
        return QuoteResult(**q.model_dump())
    except Exception as exc:
        fallback_symbol = symbol or isin or "unknown"
        return QuoteResult(symbol=fallback_symbol, isin=isin, source="error", error=str(exc))


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_quotes(
        symbols: list[str] | None = None,
        isins: list[str] | None = None,
    ) -> list[QuoteResult]:
        """Return the latest price quotes for multiple ETFs in a single call.

        Fetches all quotes concurrently. Each entry in the result list corresponds
        to one requested symbol or ISIN in the order given. If a single lookup fails,
        that entry is still returned with price=null and an error field set — the
        rest of the batch is unaffected.

        Use get_quote for a single ETF, or this tool when you need prices for
        several ETFs at once (e.g. comparing a shortlist, marking a portfolio).

        symbols: Yahoo Finance tickers, e.g. ['VWCE.DE', 'EUNL.DE', 'CSPX.L'].
                 Optional when isins is provided.
        isins:   ISINs, e.g. ['IE00B4L5Y983', 'IE00BK5BQT80']. Each is
                 auto-resolved to a Yahoo ticker via OpenFIGI (Xetra preferred).
                 Can be combined with symbols.
        """
        if not symbols and not isins:
            raise ValueError("Provide at least one of: symbols, isins")

        coros = []
        for sym in (symbols or []):
            coros.append(_safe_fetch(sym, None))
        for isin in (isins or []):
            coros.append(_safe_fetch(None, isin))

        results = await asyncio.gather(*coros)
        return list(results)
