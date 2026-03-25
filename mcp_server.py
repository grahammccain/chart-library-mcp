"""
Chart Library MCP Server — expose chart pattern search tools for Claude Desktop / Claude Code.

7 tools:
  1. search_charts       — text query → similar patterns
  2. get_follow_through  — results → forward returns
  3. get_pattern_summary — results → English summary
  4. get_status          — DB stats
  5. analyze_pattern     — combined search + follow-through + summary
  6. get_discover_picks  — top daily picks by interest score
  7. search_batch        — batch multi-symbol search

Dual mode:
  - If CHART_LIBRARY_API_KEY is set → HTTP API calls (cloud users)
  - Otherwise → direct Python imports (self-hosted / local dev)

Install:
  claude mcp add chart-library -- python mcp_server.py
"""

import json
import logging
import os
import sys

# Ensure project root is on path for direct imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

log = logging.getLogger("mcp_server")

_API_KEY = os.getenv("CHART_LIBRARY_API_KEY")
_API_BASE = os.getenv("CHART_LIBRARY_API_URL", "https://chartlibrary.io")

mcp = FastMCP("chart-library")


# ── Transport layer ──────────────────────────────────────────

def _use_http() -> bool:
    """Whether to use HTTP API calls (vs direct Python imports)."""
    return bool(_API_KEY)


def _http_post(path: str, body: dict) -> dict:
    """Make an authenticated POST to the Chart Library API."""
    import requests
    url = f"{_API_BASE}{path}"
    headers = {"Authorization": f"Bearer {_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(url, json=body, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _http_get(path: str) -> dict:
    """Make an authenticated GET to the Chart Library API."""
    import requests
    url = f"{_API_BASE}{path}"
    headers = {"Authorization": f"Bearer {_API_KEY}"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ── Direct Python imports (local mode) ──────────────────────

def _direct_search(query: str, timeframe: str = "auto", top_n: int = 10) -> dict:
    """Run search directly via Python imports."""
    from dotenv import load_dotenv
    load_dotenv()

    from services.query_parser import parse_text_query, validate_text_query
    from db.embeddings import search_similar_to_day, search_similar_to_window, MULTI_DAY_SCALES

    parsed = parse_text_query(query)
    if parsed is None:
        return {"error": "Could not parse query. Use format: AAPL 2024-06-15"}

    if len(parsed) == 3:
        symbol, date_str, scale = parsed
        timeframe = scale
    else:
        symbol, date_str = parsed
        if timeframe == "auto":
            timeframe = "rth"

    error = validate_text_query(symbol, date_str, timeframe)
    if error:
        return {"error": error}

    if timeframe in MULTI_DAY_SCALES:
        results = search_similar_to_window(symbol, date_str, top_n=top_n, scale=timeframe)
    else:
        results = search_similar_to_day(symbol, date_str, top_n=top_n, timeframe=timeframe)

    return {
        "query": {"symbol": symbol, "date": date_str},
        "results": results[:top_n],
        "count": len(results[:top_n]),
        "timeframe": timeframe,
    }


def _direct_follow_through(results: list[dict]) -> dict:
    """Compute follow-through directly."""
    from dotenv import load_dotenv
    load_dotenv()

    from services.follow_through import compute_follow_through
    return compute_follow_through(results)


def _direct_summary(query_label: str, n_matches: int, horizon_returns: dict) -> dict:
    """Generate summary directly."""
    from dotenv import load_dotenv
    load_dotenv()

    from services.summary_service import generate_pattern_summary
    text = generate_pattern_summary(query_label, n_matches, horizon_returns)
    return {"summary": text}


def _direct_status() -> dict:
    """Get embedding status directly."""
    from dotenv import load_dotenv
    load_dotenv()

    from db.embeddings import embedding_status
    return embedding_status()


def _direct_analyze(query: str, timeframe: str = "auto", top_n: int = 10, include_summary: bool = True) -> dict:
    """Run combined analysis directly via Python imports."""
    from dotenv import load_dotenv
    load_dotenv()

    # Search
    search_result = _direct_search(query, timeframe, top_n)
    if "error" in search_result:
        return search_result

    results = search_result.get("results", [])
    if not results:
        return {**search_result, "follow_through": None, "outcome_distribution": None, "summary": None}

    # Follow-through
    ft = _direct_follow_through(results)

    # Outcome distribution
    rets_5d = ft.get("horizon_returns", {}).get(5, [])
    outcome_dist = None
    if rets_5d:
        clean = [r for r in rets_5d if r is not None]
        if clean:
            up = sum(1 for r in clean if r > 0)
            outcome_dist = {
                "up_count": up,
                "down_count": len(clean) - up,
                "total": len(clean),
                "median_return": round(sorted(clean)[len(clean) // 2], 2),
            }

    # Summary
    summary_text = None
    if include_summary:
        try:
            q = search_result["query"]
            label = f"{q['symbol']} {q['date']}"
            summary_result = _direct_summary(label, len(results), ft.get("horizon_returns", {}))
            summary_text = summary_result.get("summary")
        except Exception:
            pass

    return {
        **search_result,
        "follow_through": ft,
        "outcome_distribution": outcome_dist,
        "summary": summary_text,
    }


# ── Tool implementations ─────────────────────────────────────

@mcp.tool()
async def search_charts(query: str, timeframe: str = "auto", top_n: int = 10) -> str:
    """Search for historically similar chart patterns.

    Input a symbol and date (e.g. 'AAPL 2024-06-15') to find the top 10
    most similar historical charts from 800M+ minute bars.
    Results include match scores and similarity distances.

    Args:
        query: Symbol + date, e.g. 'AAPL 2024-06-15' or 'TSLA 6/15/24 3d'
        timeframe: Session: rth (regular hours), premarket, rth_3d, rth_5d, or auto
        top_n: Number of results (1-50)
    """
    try:
        if _use_http():
            result = _http_post("/api/v1/search/text", {
                "query": query, "timeframe": timeframe, "top_n": top_n,
            })
        else:
            result = _direct_search(query, timeframe, top_n)
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def get_follow_through(results: list[dict]) -> str:
    """Get forward return analysis for search results.

    Pass the results from search_charts to see what happened 1, 3, 5, and 10
    days later in each historical match. Returns % returns and cumulative paths.

    Args:
        results: Search results from search_charts (list of {symbol, date, timeframe, metadata})
    """
    try:
        if _use_http():
            result = _http_post("/api/v1/follow-through", {"results": results})
        else:
            result = _direct_follow_through(results)
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def get_pattern_summary(query_label: str, n_matches: int, horizon_returns: dict) -> str:
    """Generate an AI-written plain English summary of pattern search results.

    Returns a concise 2-3 sentence summary suitable for retail traders.

    Args:
        query_label: Human-readable query label (e.g. 'AAPL 2024-06-15')
        n_matches: Number of matches found
        horizon_returns: Forward returns dict {1: [...], 3: [...], 5: [...], 10: [...]}
    """
    try:
        if _use_http():
            result = _http_post("/api/v1/summary", {
                "query_label": query_label,
                "n_matches": n_matches,
                "horizon_returns": horizon_returns,
            })
        else:
            result = _direct_summary(query_label, n_matches, horizon_returns)
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def get_status() -> str:
    """Get Chart Library database statistics.

    Returns total embeddings, coverage percentage, date range, and distinct symbols.
    """
    try:
        if _use_http():
            result = _http_get("/api/v1/status")
        else:
            result = _direct_status()
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def analyze_pattern(query: str, timeframe: str = "auto", top_n: int = 10, include_summary: bool = True) -> str:
    """Complete pattern analysis in one call: search + follow-through + AI summary.

    This is the recommended tool for most use cases. It combines search_charts,
    get_follow_through, and get_pattern_summary into a single call.

    Returns matching patterns, forward return statistics (1/3/5/10 day),
    outcome distribution, and an AI-written summary.

    Args:
        query: Symbol + date, e.g. 'AAPL 2024-06-15' or 'TSLA 6/15/24 3d'
        timeframe: Session: rth (regular hours), premarket, rth_3d, rth_5d, or auto
        top_n: Number of results (1-50)
        include_summary: Whether to include AI-generated summary (default True)
    """
    try:
        if _use_http():
            result = _http_post("/api/v1/analyze", {
                "query": query, "timeframe": timeframe,
                "top_n": top_n, "include_summary": include_summary,
            })
        else:
            result = _direct_analyze(query, timeframe, top_n, include_summary)
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def get_discover_picks(date: str = "", limit: int = 20) -> str:
    """Get top daily chart pattern picks ranked by interest score.

    Returns the most interesting patterns from the automated nightly scan,
    with AI summaries, predicted returns, and confidence scores.

    Args:
        date: Date in YYYY-MM-DD format (defaults to latest available)
        limit: Max picks to return (1-50, default 20)
    """
    try:
        if _use_http():
            params = f"?limit={limit}"
            if date:
                params += f"&date={date}"
            result = _http_get(f"/api/v1/discover/picks{params}")
        else:
            # Direct DB access for local mode
            from dotenv import load_dotenv
            load_dotenv()
            from db.connection import get_conn, put_conn
            conn = get_conn()
            try:
                with conn.cursor() as cur:
                    if date:
                        pick_date = date
                    else:
                        cur.execute("SELECT MAX(test_date)::text FROM forward_tests WHERE interest_score IS NOT NULL")
                        row = cur.fetchone()
                        pick_date = row[0] if row and row[0] else None

                    if not pick_date:
                        return json.dumps({"date": "", "picks": [], "count": 0})

                    cur.execute("""
                        SELECT symbol, test_date::text, direction, interest_score,
                               wpred_1d, wpred_5d, wpred_10d, n_matches, summary_text
                        FROM forward_tests
                        WHERE test_date = %s AND interest_score IS NOT NULL
                        ORDER BY interest_score DESC LIMIT %s
                    """, (pick_date, limit))
                    rows = cur.fetchall()
                    picks = [{
                        "symbol": r[0], "date": r[1], "direction": r[2],
                        "interest_score": r[3], "wpred_1d": r[4], "wpred_5d": r[5],
                        "wpred_10d": r[6], "n_matches": r[7], "summary_text": r[8],
                    } for r in rows]
            finally:
                put_conn(conn)
            result = {"date": pick_date, "picks": picks, "count": len(picks)}
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def search_batch(symbols: list[str], date: str, timeframe: str = "rth", top_n: int = 10) -> str:
    """Search for similar patterns across multiple symbols at once.

    Batch version of search_charts — runs parallel searches for up to 20 symbols
    on the same date and returns forward return statistics for each.

    Args:
        symbols: List of ticker symbols (max 20), e.g. ['AAPL', 'MSFT', 'NVDA']
        date: Date in YYYY-MM-DD format
        timeframe: Session: rth, premarket, rth_3d, rth_5d (default rth)
        top_n: Number of results per symbol (1-50)
    """
    try:
        if _use_http():
            result = _http_post("/api/v1/search/batch", {
                "symbols": symbols, "date": date,
                "timeframe": timeframe, "top_n": top_n,
            })
        else:
            # Direct mode: run searches sequentially
            from dotenv import load_dotenv
            load_dotenv()
            from services.follow_through import compute_follow_through
            from services.stats_service import compute_stats

            batch_results = []
            for sym in symbols[:20]:
                try:
                    sr = _direct_search(f"{sym} {date}", timeframe, top_n)
                    results = sr.get("results", [])
                    if results:
                        ft = compute_follow_through(results, max_workers=1)
                        stats = compute_stats(ft["horizon_returns"])
                        batch_results.append({
                            "symbol": sym.upper(), "date": date,
                            "count": len(results),
                            "horizon_returns": ft["horizon_returns"],
                            "stats": stats,
                        })
                    else:
                        batch_results.append({
                            "symbol": sym.upper(), "date": date,
                            "count": 0, "horizon_returns": {}, "stats": {},
                        })
                except Exception as e:
                    batch_results.append({
                        "symbol": sym.upper(), "date": date,
                        "count": 0, "horizon_returns": {}, "stats": {},
                        "error": str(e),
                    })
            result = {"date": date, "timeframe": timeframe, "results": batch_results}
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)
