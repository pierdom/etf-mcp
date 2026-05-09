"""Smoke test: fetch a real quote and history for IWDA.AS from Yahoo Finance."""
import asyncio

from etf_mcp.sources.yahoo import fetch_quote, fetch_history


async def main() -> None:
    symbol = "IWDA.AS"
    print(f"Fetching quote for {symbol}…")
    quote = await fetch_quote(symbol)
    assert quote["price"] is not None, f"no price in quote: {quote}"
    assert quote["currency"] is not None, f"no currency in quote: {quote}"
    print(f"  price={quote['price']} {quote['currency']}  prev_close={quote['previous_close']}")
    print("✓ quote OK")

    print(f"\nFetching 3-month daily history for {symbol}…")
    rows = await fetch_history(symbol, period="3mo", interval="1d")
    assert len(rows) > 0, "empty history"
    first, last = rows[0], rows[-1]
    print(f"  {len(rows)} bars  first={first['date']} close={first['close']}  last={last['date']} close={last['close']}")
    print("✓ history OK")

    print("\nFetching quote again (should hit cache, no network call)…")
    quote2 = await fetch_quote(symbol)
    assert quote2["price"] == quote["price"]
    print("✓ cache hit confirmed (same price)")


if __name__ == "__main__":
    asyncio.run(main())
