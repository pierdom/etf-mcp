"""FastMCP instance, transport switch, and tool registration."""
from __future__ import annotations

from fastmcp import FastMCP

from etf_mcp.config import config
from etf_mcp.tools import etf_profile

mcp = FastMCP(name="etf-mcp", instructions="ETF research tools sourced from justETF and Yahoo Finance.")

# Register all tools at import time so `fastmcp inspect/dev` sees them
# without having to call main().
etf_profile.register(mcp)


def main() -> None:
    if config.transport == "http":
        if not config.http_bearer_token:
            raise RuntimeError("MCP_HTTP_BEARER_TOKEN must be set when MCP_TRANSPORT=http")
        mcp.run(
            transport="streamable-http",
            host=config.http_host,
            port=config.http_port,
        )
    else:
        mcp.run(transport="stdio")
