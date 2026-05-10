# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

`etf-scout-mcp` is a [Model Context Protocol](https://modelcontextprotocol.io) server for ETF research. It exposes 6 MCP tools backed by three data sources: **justETF** (scraping), **Yahoo Finance** (yfinance + curl_cffi), and **OpenFIGI** (REST API).

## Commands

```bash
uv sync                          # install / sync dependencies
uv run etf-scout-mcp             # run server (stdio transport)

# smoke tests (hit real network)
uv run python tests/smoke_justetf.py
uv run python tests/smoke_yahoo.py
uv run python tests/smoke_openfigi.py

# unit tests
uv run pytest tests/

# docker
docker build -t etf-scout-mcp .
docker compose up -d
```

To call a single tool locally:
```bash
uv run fastmcp call --server-spec src/etf_scout_mcp/server.py \
  --target get_etf_profile --input-json '{"isin": "IE00B4L5Y983"}'
```

## Architecture

```
src/etf_scout_mcp/
├── server.py          # FastMCP instance; transport selection (stdio/http); registers tools
├── config.py          # Config dataclass loaded from env vars
├── cache.py           # @cached decorator — SQLite TTL cache, per-key TTLs
├── models.py          # Pydantic response models (EtfProfile, EtfSummary, Holding, …)
├── sources/
│   ├── justetf.py     # justETF scraping: profile, screener, overview
│   ├── yahoo.py       # yfinance with curl_cffi Firefox TLS impersonation; quote + history
│   └── openfigi.py    # httpx async; OpenFIGI exchange listings; handles 429 rate-limit
└── tools/
    ├── etf_profile.py, search.py, etf_compare.py
    ├── quote.py, history.py, etf_listings.py
```

**Request flow:** MCP client → `server.py` (tool dispatch) → `tools/` (input validation) → `cache.py` (@cached check) → `sources/` (network fetch) → Pydantic model → client.

**Fallback logic in `quote.py`:** Yahoo Finance is tried first; if it fails with a bare ISIN, it retries using the justETF Gettex price.

**Logging:** All outbound calls (latency, status) are written to `~/.cache/etf-scout-mcp/calls.log` (5 MB × 3 rotating). Check here first when debugging data-source failures.

## Key env vars

| Variable | Default | Notes |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio` or `http` |
| `MCP_HTTP_BEARER_TOKEN` | — | Required when transport is `http` |
| `MCP_HTTP_HOST` / `MCP_HTTP_PORT` | `127.0.0.1` / `8765` | HTTP bind |
| `ETF_SCOUT_MCP_CACHE` | `~/.cache/etf-scout-mcp/cache.db` | SQLite path |
| `CACHE_TTL_QUOTE` / `_PROFILE` / `_HISTORY` | `300` / `86400` / `3600` | Per-type TTLs in seconds |
| `OPENFIGI_API_KEY` | — | Optional; raises rate limit and adds `mic_code` to listings |

Copy `.env.example` to `.env` before running with HTTP transport.

## Data conventions

- TER as a decimal fraction (e.g. `0.0020` = 0.20%), not a percentage
- Monetary values in EUR
- Dates as ISO 8601
- Returns and volatility as percentages

## Fragile dependencies

- **justetf-scraping** is pinned to a specific Git commit (HTML scraping breaks when justETF changes its page structure). If scraping fails, check `git ls-remote` on the upstream repo for a newer commit and re-pin in `pyproject.toml`.
- **Yahoo Finance** uses an unofficial API that changes without notice. The curl_cffi Firefox TLS fingerprint is what keeps it working; if quote fetches regress, check for yfinance updates first.
