"""Tool: get_history — OHLCV price history via yfinance."""
from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from etf_scout_mcp.sources import yahoo


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
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> list[OhlcvBar]:
        """Return OHLCV price history for an ETF from Yahoo Finance.

        Use this to chart performance or compute custom metrics over time.
        Use get_quote for the latest price only.
        This tool is for research only — for portfolio return calculations,
        pair it with a portfolio tool such as Ghostfolio (ghostfolio-mcp).

        symbol:   Yahoo Finance ticker, e.g. 'VWCE.DE' or 'CSPX.L'
        period:   Length of history: '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'max'
        interval: Bar size: '1d' (daily), '1wk' (weekly), '1mo' (monthly)
        """
        rows = await yahoo.fetch_history(symbol, period=period, interval=interval)
        return [OhlcvBar(**r) for r in rows]
