"""Tool: get_history — OHLCV price history via yfinance."""
from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from etf_scout_mcp.sources import yahoo
from etf_scout_mcp.sources.openfigi import resolve_yahoo_ticker


class OhlcvBar(BaseModel):
    date: str = Field(description="ISO 8601 date string")
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: int | None = None


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_history(
        symbol: str | None = None,
        isin: str | None = None,
        period: str = "1y",
        interval: str = "1d",
    ) -> list[OhlcvBar]:
        """Return OHLCV price history for an ETF from Yahoo Finance.

        Accepts a Yahoo Finance ticker, an ISIN, or both. When only an ISIN
        is given, the ticker is auto-resolved via OpenFIGI (Xetra preferred,
        then Euronext Amsterdam, LSE, etc.).

        Use this to chart performance or compute custom metrics over time.
        Use get_quote for the latest price only.
        This tool is for research only — for portfolio return calculations,
        pair it with a portfolio tool such as Ghostfolio (ghostfolio-mcp).

        symbol:   Yahoo Finance ticker, e.g. 'VWCE.DE' or 'CSPX.L'.
                  Optional when isin is provided.
        isin:     ISIN, e.g. 'IE00B4L5Y983'. Used for ticker auto-resolution.
        period:   Length of history: '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'max'
        interval: Bar size: '1d' (daily), '1wk' (weekly), '1mo' (monthly)
        """
        if not symbol and not isin:
            raise ValueError("Provide at least one of: symbol, isin")

        resolved_symbol = symbol
        if not resolved_symbol:
            resolved_symbol = await resolve_yahoo_ticker(isin)  # type: ignore[arg-type]
            if not resolved_symbol:
                raise RuntimeError(
                    f"Could not resolve a Yahoo Finance ticker for ISIN {isin!r}. "
                    "Try passing the ticker directly, e.g. 'EUNL.DE' or 'VWCE.DE'."
                )

        rows = await yahoo.fetch_history(resolved_symbol, period=period, interval=interval)
        return [OhlcvBar(**r) for r in rows]
