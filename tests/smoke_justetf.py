"""Smoke test: fetch a real ETF profile and screener results from justETF."""
import asyncio

from etf_scout_mcp.sources.justetf import fetch_profile, fetch_screener, fetch_summary

ISIN = "IE00B4L5Y983"  # iShares Core MSCI World


async def main() -> None:
    print(f"Fetching profile for {ISIN} (IWDA)…")
    profile = await fetch_profile(ISIN)

    assert profile["isin"] == ISIN
    assert profile["ter"] is not None, "TER missing"
    # TER must be decimal: IWDA is 0.20% → 0.002
    assert profile["ter"] < 0.01, f"TER looks like a percentage, not decimal: {profile['ter']}"
    assert profile["fund_size_eur"] > 1_000_000_000, f"fund_size_eur suspiciously small: {profile['fund_size_eur']}"
    assert len(profile["top_holdings"]) > 0, "no top holdings"
    assert len(profile["countries"]) > 0, "no country breakdown"
    assert len(profile["sectors"]) > 0, "no sector breakdown"
    assert profile["inception_date"] == "2009-09-25", f"unexpected inception_date: {profile['inception_date']}"

    print(f"  name:            {profile['name']}")
    print(f"  TER (decimal):   {profile['ter']}  ({profile['ter']*100:.2f}%)")
    print(f"  fund_size_eur:   €{profile['fund_size_eur']:,.0f}")
    print(f"  replication:     {profile['replication']}")
    print(f"  distribution:    {profile['distribution_policy']}")
    print(f"  domicile:        {profile['fund_domicile']}")
    print(f"  inception_date:  {profile['inception_date']}")
    print(f"  top holding:     {profile['top_holdings'][0]}")
    print("✓ profile OK")

    print("\nRunning screener: equity / world / max_ter=0.002 / min_fund_size=1B…")
    results = await fetch_screener(
        asset_class="equity",
        region="world",
        max_ter=0.002,
        min_fund_size_eur=1_000_000_000,
        limit=5,
    )
    assert len(results) > 0, "no screener results"
    for r in results:
        assert r["ter"] is None or r["ter"] <= 0.002, f"TER filter broken: {r['ter']}"
        assert r["fund_size_eur"] is None or r["fund_size_eur"] >= 1_000_000_000, f"size filter broken: {r['fund_size_eur']}"
        print(f"  {r['isin']}  {r['name'][:50]:<50}  TER={r['ter']}  size=€{r['fund_size_eur']:,.0f}")
    print("✓ screener OK")

    print(f"\nFetching summary for {ISIN} (used by compare_etfs)…")
    summary = await fetch_summary(ISIN)
    assert summary is not None, "fetch_summary returned None"
    assert summary["isin"] == ISIN
    assert summary["ter"] is not None and summary["ter"] < 0.01, f"TER looks wrong: {summary['ter']}"
    assert summary["fund_size_eur"] is not None and summary["fund_size_eur"] > 1_000_000_000
    assert summary["return_1y"] is not None, "missing 1Y return"
    print(f"  TER={summary['ter']}  size=€{summary['fund_size_eur']:,.0f}  1Y={summary['return_1y']}%")
    print("✓ fetch_summary OK")


if __name__ == "__main__":
    asyncio.run(main())
