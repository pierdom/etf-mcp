# etf-mcp

MCP server for ETF research via **justETF**, **Yahoo Finance**, and **OpenFIGI**. Complements a Ghostfolio MCP — this server focuses on fund discovery, profile depth, comparison, and exchange mapping. It does not do portfolio tracking or basic price lookups that Ghostfolio already handles.

## Tools

| Tool | Source | Description |
|---|---|---|
| `get_etf_profile` | justETF | Full profile: TER, replication, distribution, fund size, domicile, top holdings, country/sector breakdown |
| `search_etfs` | justETF screener | Filter by asset class, region, TER, fund size, distribution — the headline feature Ghostfolio cannot do |
| `compare_etfs` | justETF | Side-by-side: TER, 1/3/5Y returns, fund size, distribution, replication |
| `get_quote` | Yahoo → justETF Gettex | Latest price; falls back to Gettex live quote if Yahoo fails and an ISIN is provided |
| `get_history` | yfinance | OHLCV history; configurable period (`1mo`–`max`) and interval (`1d`/`1wk`/`1mo`) |
| `get_etf_listings` | OpenFIGI | All exchange listings for an ISIN — ticker, exchange code, currency. Use this to find the right Yahoo ticker for a given ISIN (e.g. IWDA on Euronext Amsterdam vs EUNL on Xetra vs SWDA on LSE) |

**Conventions used throughout:**
- TER is a **decimal**, not a percentage — `0.002` = 0.20% (20 bps)
- All money fields are in **EUR** unless the field name says otherwise
- All dates are **ISO 8601** strings (`2009-09-25`)
- Returns and volatility are **percentages** (`24.76` = +24.76%)

## Quick start (local / Claude Desktop on Linux)

```bash
git clone https://github.com/pierdom/etf-mcp
cd etf-mcp
uv sync
```

Verify it works:

```bash
uv run fastmcp call --server-spec src/etf_mcp/server.py \
  --target get_etf_profile --input-json '{"isin": "IE00B4L5Y983"}'
```

Add to `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "etf-mcp": {
      "command": "/home/<you>/.local/bin/uv",
      "args": [
        "run",
        "--project", "/home/<you>/Workspace/etf-mcp",
        "python", "-m", "etf_mcp"
      ],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

Replace `<you>` with your username. Use `which uv` to confirm the uv path. Then **fully quit and relaunch Claude Desktop** — it does not hot-reload the config. The hammer icon in the input bar should show 6 tools.

## Docker deploy

A pre-built multi-arch image (amd64, arm64) is published to the GitHub Container Registry on every push to `main`:

```bash
docker pull ghcr.io/pierdom/etf-mcp:edge
```

To run it:

```bash
mkdir -p ~/Docker/etf-mcp/data
docker run -d --restart unless-stopped \
  -p 8765:8765 \
  -v ~/Docker/etf-mcp/data:/data \
  -e MCP_TRANSPORT=http \
  -e MCP_HTTP_HOST=0.0.0.0 \
  -e MCP_HTTP_PORT=8765 \
  -e MCP_HTTP_BEARER_TOKEN=<your-token> \
  -e ETF_MCP_CACHE=/data/cache.db \
  ghcr.io/pierdom/etf-mcp:edge
```

Or with Docker Compose using the published image instead of building locally:

```bash
cp .env.example .env
# Edit .env — set MCP_HTTP_BEARER_TOKEN to a strong random value
#   openssl rand -hex 32
mkdir -p ~/Docker/etf-mcp/data
docker compose up -d
```

Add to Claude Desktop config on the client machine, replacing `<host>` with the server's IP or hostname:

```json
{
  "mcpServers": {
    "etf-mcp": {
      "type": "http",
      "url": "http://<host>:8765/mcp",
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
| `MCP_HTTP_HOST` | `127.0.0.1` | Bind address for HTTP transport (`0.0.0.0` in Docker) |
| `MCP_HTTP_PORT` | `8765` | Port for HTTP transport |
| `MCP_HTTP_BEARER_TOKEN` | — | **Required** when `MCP_TRANSPORT=http` |
| `ETF_MCP_CACHE` | `~/.cache/etf-mcp/cache.db` | SQLite cache file path |
| `CACHE_TTL_QUOTE` | `300` | Quote cache TTL in seconds (5 min) |
| `CACHE_TTL_PROFILE` | `86400` | Profile/screener/listings cache TTL in seconds (24 h) |
| `CACHE_TTL_HISTORY` | `3600` | History cache TTL in seconds (1 h) |
| `LOG_LEVEL` | `INFO` | Python log level |
| `OPENFIGI_API_KEY` | — | Optional. Free key from openfigi.com raises the rate limit from 25 req/min to 25 req/6 s and also populates the `mic_code` field in `get_etf_listings` results |

## Sample prompts

**Fund discovery**
> Find accumulating equity ETFs covering the world with TER ≤ 0.20% and fund size above €1B. List the top 5 with name, TER, and fund size.

**Deep profile**
> Give me the full profile for IWDA (IE00B4L5Y983): replication method, TER, fund size, distribution policy, top 5 holdings, and country breakdown.

**Side-by-side comparison**
> Compare IWDA (IE00B4L5Y983), VWCE (IE00BK5BQT80), and XDWD (IE00BJ0KDQ92) side by side — TER, 1Y/3Y/5Y returns, fund size, and replication.

**Finding the right ticker**
> I want to buy IWDA on Xetra (exch_code GR) and on Euronext Amsterdam (exch_code EO). What are the correct tickers for each exchange?

**Price and recent performance**
> What is the current price of EUNL? Then show me its weekly performance over the last 3 months — first bar, last bar, and overall return.

**Screener + deep dive**
> Find the cheapest physically-replicating bond ETFs domiciled in Ireland with fund size above €500M. Pick the most interesting one and show me its full profile.

**Income-focused search**
> Find distributing equity ETFs focused on Europe with TER below 0.30%. Rank them by 1-year return.

## Caching

All external calls are cached in a local SQLite database with per-type TTLs. The cache is transparent — repeated tool calls within the TTL window are instant and make no network requests. Delete the cache file to force a refresh.

Every outbound call (to Yahoo Finance, justETF, and OpenFIGI) is logged with latency and status to `~/.cache/etf-mcp/calls.log` (rotating, 5 MB × 3 files). Check this file first when diagnosing data problems.

## Troubleshooting

### Yahoo Finance returning stale data or errors

Yahoo's unofficial API changes without notice. Check the call log:

```bash
tail -f ~/.cache/etf-mcp/calls.log
```

If Yahoo is consistently failing, pass an `isin` argument to `get_quote` — it will fall back to the justETF Gettex live quote automatically.

### justETF screener or profile returning nothing

`search_etfs` and `get_etf_profile` results are cached for 24 hours. Delete the cache to force a fresh fetch:

```bash
rm ~/.cache/etf-mcp/cache.db          # local
rm ~/Docker/etf-mcp/data/cache.db     # Docker
```

The justETF scraper reads HTML pages — if justETF changes their structure the `justetf-scraping` library may break. Check for updates and re-pin the commit in `pyproject.toml`:

```bash
# See what the latest commit is
git ls-remote https://github.com/druzsan/justetf-scraping HEAD

# Update pyproject.toml, then:
uv lock
uv sync
uv run python tests/smoke_justetf.py   # verify it still works
```

### `get_etf_listings` returns no results

OpenFIGI may not have a mapping for very new or obscure ISINs. The `warning` field from the API will appear in `calls.log`. Without `OPENFIGI_API_KEY` set, the `mic_code` field in results is always null — use `exch_code` instead (Bloomberg exchange codes: `GR` = Xetra, `EO` = Euronext Amsterdam, `LN` = LSE, `SW` = SIX Swiss Exchange). Note: `currency` is never populated — the OpenFIGI mapping endpoint does not return it.

### Bearer auth rejected (HTTP transport)

Confirm `MCP_HTTP_BEARER_TOKEN` is set in the server environment and the client is sending an identical value. For Docker Compose, verify `.env` is in the same directory as `docker-compose.yml` and is not empty. Requests with the wrong or missing token receive `HTTP 401` with `WWW-Authenticate: Bearer error="invalid_token"`.
