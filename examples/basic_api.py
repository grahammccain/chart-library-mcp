"""
Basic Chart Library API Example

Uses the `chartlibrary` Python SDK (no MCP required) to search for
similar chart patterns and inspect forward returns.

Prerequisites:
    pip install chartlibrary

Environment variables:
    CHART_LIBRARY_KEY   Your Chart Library API key (https://chartlibrary.io/developers)
"""

import os

from chartlibrary import ChartLibrary


def main():
    api_key = os.environ.get("CHART_LIBRARY_KEY")
    if not api_key:
        raise EnvironmentError("Set CHART_LIBRARY_KEY environment variable")

    client = ChartLibrary(api_key=api_key)

    # --- 1. Search for similar chart patterns ---
    print("Searching for patterns similar to NVDA 2026-04-04...\n")
    results = client.search("NVDA 2026-04-04", timeframe="rth", top_n=5)

    print(f"Found {len(results['matches'])} matches:")
    for i, match in enumerate(results["matches"], 1):
        print(
            f"  {i}. {match['symbol']} {match['date']}  "
            f"distance={match['distance']:.4f}"
        )

    # --- 2. Get follow-through (forward returns) ---
    print("\nForward returns from historical matches:")
    follow_through = client.follow_through(results["matches"])

    for horizon, stats in follow_through.get("horizon_returns", {}).items():
        avg = stats.get("avg_return", 0)
        win = stats.get("win_rate", 0)
        print(f"  {horizon}: avg={avg:+.2f}%  win_rate={win:.0f}%")

    # --- 3. Full analysis (search + follow-through + AI summary) ---
    print("\n--- Full Analysis ---")
    analysis = client.analyze("AAPL 2026-04-04", timeframe="rth")

    if "summary" in analysis:
        print(analysis["summary"])
    else:
        print(f"Matches: {analysis.get('n_matches', 0)}")
        for horizon, stats in analysis.get("horizon_returns", {}).items():
            avg = stats.get("avg_return", 0)
            win = stats.get("win_rate", 0)
            print(f"  {horizon}: avg={avg:+.2f}%  win_rate={win:.0f}%")

    # --- 4. Discover picks (daily scanner) ---
    print("\n--- Today's Top Picks ---")
    picks = client.discover(limit=5)

    for pick in picks.get("picks", []):
        symbol = pick.get("symbol", "?")
        score = pick.get("interest_score", 0)
        print(f"  {symbol}  interest_score={score:.1f}")


if __name__ == "__main__":
    main()
