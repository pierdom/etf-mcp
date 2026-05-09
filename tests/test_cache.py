"""Smoke test: SQLite TTL cache stores, retrieves, and expires correctly."""
import asyncio
import os
import tempfile
import time

# Must be set before importing config/cache
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["ETF_MCP_CACHE"] = _tmp.name
os.environ["CACHE_TTL_QUOTE"] = "1"  # 1s so the expiry test is fast

from etf_mcp.cache import cached  # noqa: E402

call_count = 0


@cached(ttl_key="quote")
async def fake_fetch(symbol: str) -> dict:
    global call_count
    call_count += 1
    return {"symbol": symbol, "price": 42.0}


async def main() -> None:
    global call_count

    result = await fake_fetch("TEST")
    assert result == {"symbol": "TEST", "price": 42.0}, f"wrong result: {result}"
    assert call_count == 1, f"expected 1 call, got {call_count}"
    print("✓ first call hits function")

    result = await fake_fetch("TEST")
    assert call_count == 1, f"expected still 1 call, got {call_count}"
    print("✓ second call served from cache")

    print("  sleeping 2s for TTL to expire…")
    time.sleep(2)

    result = await fake_fetch("TEST")
    assert call_count == 2, f"expected 2 calls after expiry, got {call_count}"
    print("✓ call after TTL expiry hits function again")

    # Different args → different cache key
    await fake_fetch("OTHER")
    assert call_count == 3, f"expected 3 calls for new symbol, got {call_count}"
    print("✓ different args produce distinct cache keys")

    print("\nAll cache tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
