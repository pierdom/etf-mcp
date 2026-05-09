# etf-mcp

MCP server for ETF research via **justETF** and **Yahoo Finance**. Complements a Ghostfolio MCP — this server focuses on fund discovery, profile depth, and comparison. It does not do portfolio tracking or basic price lookups that Ghostfolio already handles.

## Tools

| Tool | Source | Description |
|---|---|---|
| `get_etf_profile` | justETF | Full profile: TER, replication, distribution, fund size, domicile, top holdings, country/sector breakdown |
| `get_quote` | Yahoo → justETF Gettex | Latest price; falls back to Gettex live quote if Yahoo fails and an ISIN is provided |
| `get_history` | yfinance | OHLCV history; configurable period and interval |
| `compare_etfs` | justETF | Side-by-side: TER, 1/3/5Y returns, fund size, distribution, replication |
| `search_etfs` | justETF screener | Filter by asset class, region, TER, fund size, distribution — the headline feature Ghostfolio cannot do |

**Conventions:**
- TER is a **decimal**, not a percentage. `0.002` = 0.20% (20 bps).
- All money fields are in **EUR** unless the field name says otherwise.
- All dates are **ISO 8601** strings (`2009-09-25`).

## Install (local / Claude Desktop)

```bash
git clone https://github.com/pierdom/etf-mcp
cd etf-mcp
uv sync
```

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `~/.config/Claude/claude_desktop_config.json` (Linux):

```json
{
  "mcpServers": {
    "etf-mcp": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/etf-mcp", "python", "-m", "etf_mcp"],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

## Homelab deploy (Docker Compose + Tailscale)

```bash
cp .env.example .env
# edit .env — set MCP_HTTP_BEARER_TOKEN to a strong random string
mkdir -p ~/Docker/etf-mcp/data
docker compose up -d
```

Connect from Claude Desktop via the Tailscale address:

```json
{
  "mcpServers": {
    "etf-mcp": {
      "type": "http",
      "url": "http://<tailscale-ip>:8765/mcp",
      "headers": {
        "Authorization": "Bearer <your-token>"
      }
    }
  }
}
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio` or `http` |
| `MCP_HTTP_HOST` | `127.0.0.1` | Bind address for HTTP transport |
| `MCP_HTTP_PORT` | `8765` | Port for HTTP transport |
| `MCP_HTTP_BEARER_TOKEN` | — | **Required** when `MCP_TRANSPORT=http` |
| `ETF_MCP_CACHE` | `~/.cache/etf-mcp/cache.db` | SQLite cache file path |
| `CACHE_TTL_QUOTE` | `300` | Quote cache TTL in seconds |
| `CACHE_TTL_PROFILE` | `86400` | Profile/screener cache TTL in seconds |
| `CACHE_TTL_HISTORY` | `3600` | History cache TTL in seconds |
| `LOG_LEVEL` | `INFO` | Python log level |

## Troubleshooting

### Yahoo Finance returning stale data or 401 errors

Yahoo occasionally rotates their anti-scraping measures. The server logs every outbound call (with status and latency) to `~/.cache/etf-mcp/calls.log`. Check there first:

```bash
tail -f ~/.cache/etf-mcp/calls.log
```

If Yahoo is consistently failing, use `get_quote` with an ISIN to fall back to the justETF Gettex live quote.

### justETF screener returning no results

`search_etfs` results are cached for 24 hours. If you suspect stale data, delete the cache:

```bash
rm ~/.cache/etf-mcp/cache.db
# or, in the Docker deployment:
rm ~/Docker/etf-mcp/data/cache.db
```

The screener itself calls justETF's overview endpoint, which scrapes HTML. If justETF updates their page structure the `justetf-scraping` library may break. Check for updates:

```bash
uv lock --upgrade-package justetf-scraping
```

Then update the pinned commit in `pyproject.toml` after testing.

### Bearer auth rejected (HTTP transport)

- Confirm `MCP_HTTP_BEARER_TOKEN` is set in the environment and the client is sending the same token.
- For Docker Compose, verify the `.env` file is in the same directory as `compose.yml` and contains `MCP_HTTP_BEARER_TOKEN=<value>`.
