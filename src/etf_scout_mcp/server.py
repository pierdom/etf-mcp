"""FastMCP instance, transport switch, and tool registration."""
from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.server.auth.auth import AccessToken, AuthProvider

from etf_scout_mcp.config import config
from etf_scout_mcp.tools import etf_compare, etf_listings, etf_profile, history, quote, search


class _StaticBearerAuth(AuthProvider):
    """Accepts exactly one pre-shared bearer token; rejects everything else."""

    def __init__(self, token: str) -> None:
        super().__init__()
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        if token == self._token:
            return AccessToken(token=token, client_id="homelab", scopes=[])
        return None


def _make_mcp() -> FastMCP:
    auth = None
    if config.transport == "http":
        if not config.http_bearer_token:
            raise RuntimeError("MCP_HTTP_BEARER_TOKEN must be set when MCP_TRANSPORT=http")
        auth = _StaticBearerAuth(config.http_bearer_token)

    return FastMCP(
        name="etf-scout-mcp",
        instructions="ETF research tools sourced from justETF and Yahoo Finance.",
        auth=auth,
    )


mcp = _make_mcp()

# Register all tools at import time so `fastmcp inspect/dev` sees them
# without having to call main().
etf_profile.register(mcp)
quote.register(mcp)
history.register(mcp)
etf_compare.register(mcp)
search.register(mcp)
etf_listings.register(mcp)


def main() -> None:
    if config.transport == "http":
        mcp.run(
            transport="streamable-http",
            host=config.http_host,
            port=config.http_port,
        )
    else:
        mcp.run(transport="stdio")
