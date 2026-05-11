from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    transport: str = field(
        default_factory=lambda: os.getenv("ETF_SCOUT_MCP_TRANSPORT", "stdio")
    )
    http_host: str = field(
        default_factory=lambda: os.getenv("ETF_SCOUT_MCP_HTTP_HOST", "127.0.0.1")
    )
    http_port: int = field(
        default_factory=lambda: int(os.getenv("ETF_SCOUT_MCP_HTTP_PORT", "8765"))
    )
    http_bearer_token: str | None = field(
        default_factory=lambda: os.getenv("ETF_SCOUT_MCP_HTTP_BEARER_TOKEN")
    )
    cache_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("ETF_SCOUT_MCP_CACHE", "~/.cache/etf-scout-mcp/cache.db")
        ).expanduser()
    )
    ttl_quote: int = field(
        default_factory=lambda: int(os.getenv("ETF_SCOUT_MCP_CACHE_TTL_QUOTE", "300"))
    )
    ttl_profile: int = field(
        default_factory=lambda: int(os.getenv("ETF_SCOUT_MCP_CACHE_TTL_PROFILE", "86400"))
    )
    ttl_history: int = field(
        default_factory=lambda: int(os.getenv("ETF_SCOUT_MCP_CACHE_TTL_HISTORY", "3600"))
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("ETF_SCOUT_MCP_LOG_LEVEL", "INFO")
    )
    openfigi_api_key: str | None = field(
        default_factory=lambda: os.getenv("OPENFIGI_API_KEY")
    )


config = Config()
