"""Tool: compare_etfs — side-by-side comparison of multiple ETFs by ISIN."""
from __future__ import annotations

import asyncio

from fastmcp import FastMCP

from etf_mcp.models import EtfSummary
from etf_mcp.sources.justetf import fetch_summary


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def compare_etfs(isins: list[str]) -> list[EtfSummary]:
        """Return a side-by-side comparison of multiple ETFs identified by ISIN.

        Fetches TER, fund size, replication, distribution policy, 1/3/5-year
        returns, and volatility for each fund from justETF. Useful for
        choosing between similar ETFs (e.g. IWDA vs VWCE vs SPDR ACWI).

        Use get_etf_profile for deeper detail on a single fund (holdings,
        country/sector breakdowns). Use search_etfs to discover candidates
        before comparing. Do not use for portfolio tracking — use Ghostfolio.

        isins: List of ISINs to compare, e.g. ['IE00B4L5Y983', 'IE00BK5BQT80']
        """
        results = await asyncio.gather(*[fetch_summary(isin) for isin in isins])
        return [EtfSummary(**data) for data in results if data is not None]
