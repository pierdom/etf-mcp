"""Smoke test: fetch exchange listings for IWDA from OpenFIGI."""
import asyncio

from etf_scout_mcp.sources.openfigi import fetch_listings

ISIN = "IE00B4L5Y983"  # iShares Core MSCI World


async def main() -> None:
    print(f"Fetching exchange listings for {ISIN} (IWDA)…")
    listings = await fetch_listings(ISIN)

    assert len(listings) > 0, "no listings returned"

    exch_codes = {r["exch_code"] for r in listings if r.get("exch_code")}
    tickers = {r["ticker"] for r in listings if r.get("ticker")}

    # IWDA trades on at least Euronext Amsterdam (NA) and LSE (LN)
    assert "NA" in exch_codes, f"expected Euronext Amsterdam (NA), got: {exch_codes}"
    assert "LN" in exch_codes, f"expected LSE (LN), got: {exch_codes}"
    assert "IWDA" in tickers, f"expected ticker IWDA, got: {tickers}"

    print(f"  {len(listings)} listings across exchanges: {sorted(exch_codes)}")
    print(f"  tickers seen: {sorted(tickers)}")
    # Print a few representative rows
    for r in listings[:3]:
        print(f"  {r['exch_code']:>4}  {r['ticker']:<8}  {r['name']}")
    print("✓ fetch_listings OK")


if __name__ == "__main__":
    asyncio.run(main())
