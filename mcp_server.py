"""Chart Library MCP: three public research tools, with legacy calls preserved.

Public menu: market_state, daily_note, research_quality.
Use CHART_LIBRARY_MCP_PROFILE=advanced only for an existing integration that
needs the extended menu. Old names remain registered in either profile.

Installed clients use the hosted API anonymously unless an optional API key is
configured. Direct Python execution is supported inside the full application
checkout, where services/ exists. No server packages are needed by pip users.
"""

import asyncio
import json
import logging
import os
import sys

# Ensure project root is on path for direct imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from public_research import (
    MCP_INSTRUCTIONS, PUBLIC_TOOLS, validate_session, validate_symbol,
)

load_dotenv()

log = logging.getLogger("mcp_server")

_API_KEY = os.getenv("CHART_LIBRARY_API_KEY")
_API_BASE = os.getenv("CHART_LIBRARY_API_URL", "https://chartlibrary.io")

# ── Tool annotations ───────────────────────────────────────────
READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)

WRITE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)

# Deprecated-read-only: signals to MCP clients that this legacy tool is kept
# only for backward compatibility. Newer clients should surface the canonical
# tool from the 9-tool canonical surface above.
DEPRECATED_READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
    deprecated=True,
)

mcp = FastMCP("chart-library", instructions=MCP_INSTRUCTIONS)


# ── Transport layer ──────────────────────────────────────────

def _use_http() -> bool:
    """Whether to use HTTP API calls (vs direct Python imports)."""
    return bool(_API_KEY) or not os.path.isdir(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "services")
    )


_MCP_USER_AGENT = "chartlibrary-mcp/6.2.0"


# ── Data freshness ────────────────────────────────────────────
# Tools that touch time-sensitive data attach this meta block so the
# calling LLM can communicate accurately to the user ("today's bar is
# already ingested" vs "data is one trading day stale because today's
# bar lands tonight at 21:00 UTC"). Without it the user sees null
# fields and assumes the tool is broken.

import datetime as _dt_freshness
_FRESHNESS_CACHE: dict = {"value": None, "expires_at": 0.0}
_FRESHNESS_TTL_SEC = 60


def _data_freshness() -> dict:
    """Return a small meta block describing current data state. Cached 60s
    to avoid hammering the DB on every tool call.

    Keys:
      as_of_db_date      — MAX(date) in daily_bars; what 'most recent' actually means
      today_date         — today (UTC date)
      lag_trading_days   — how many trading days behind we are (0 = today's bar landed)
      next_ingest_at     — when the next nightly ingest is expected (~21:00 UTC weekdays)
      note               — human-readable framing the LLM can paraphrase

    Failures are silent — return a minimal `note` and let the tool response
    still go through. We never want freshness lookup to break a real call.
    """
    import time as _time
    now = _time.time()
    if _FRESHNESS_CACHE["value"] is not None and now < _FRESHNESS_CACHE["expires_at"]:
        return _FRESHNESS_CACHE["value"]

    today = _dt_freshness.date.today()
    out: dict = {
        "today_date": today.isoformat(),
        "next_ingest_at": "~21:00 UTC each weekday (Tue–Sat)",
        "note": None,
    }
    try:
        from db.connection import get_conn, put_conn
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(date)::date FROM daily_bars")
                row = cur.fetchone()
                last_bar = row[0] if row and row[0] else None
        finally:
            put_conn(conn)

        if last_bar:
            out["as_of_db_date"] = last_bar.isoformat()
            delta = (today - last_bar).days
            # Crude lag estimate — calendar days, weekends count. Good enough
            # for the "today vs yesterday vs last week" decision the LLM needs.
            out["lag_calendar_days"] = delta
            if delta <= 0:
                out["note"] = (
                    "Most recent daily bar is today's close (already ingested). "
                    "Intraday quotes are not provided by this server; for live "
                    "prices, the LLM should defer to a quote source. Cohort and "
                    "regime analysis here are end-of-day."
                )
            elif delta == 1:
                out["note"] = (
                    "Most recent daily bar is yesterday's close. Today's bar will "
                    "land in the next nightly ingest (~21:00 UTC). Any 'today' "
                    "question is being answered against yesterday's data — the "
                    "LLM should say so explicitly to the user."
                )
            else:
                out["note"] = (
                    f"Most recent daily bar is {last_bar.isoformat()} "
                    f"({delta} calendar days behind today, {today.isoformat()}). "
                    "Likely a weekend or market holiday gap. The LLM should "
                    "name the as-of date explicitly when answering."
                )
    except Exception as exc:
        out["note"] = f"Freshness lookup unavailable: {exc}"

    _FRESHNESS_CACHE["value"] = out
    _FRESHNESS_CACHE["expires_at"] = now + _FRESHNESS_TTL_SEC
    return out


def _attach_freshness(payload: dict) -> dict:
    """Inject freshness into the response's meta block. Safe on any dict."""
    if not isinstance(payload, dict):
        return payload
    meta = payload.setdefault("meta", {}) if isinstance(payload.get("meta"), dict) or "meta" not in payload else payload["meta"]
    if isinstance(meta, dict):
        meta["freshness"] = _data_freshness()
    return payload


def _http_post(path: str, body: dict) -> dict:
    """Make an authenticated POST to the Chart Library API."""
    import requests
    url = f"{_API_BASE}{path}"
    headers = {
        **({"Authorization": f"Bearer {_API_KEY}"} if _API_KEY else {}),
        "Content-Type": "application/json",
        "User-Agent": _MCP_USER_AGENT,
    }
    resp = requests.post(url, json=body, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _http_get(path: str, timeout: int = 30) -> dict:
    """Make an authenticated GET to the Chart Library API."""
    import requests
    url = f"{_API_BASE}{path}"
    headers = {
        **({"Authorization": f"Bearer {_API_KEY}"} if _API_KEY else {}),
        "User-Agent": _MCP_USER_AGENT,
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


# Endpoints whose cold-path (post-deploy, pre-prewarm) legitimately
# exceeds the default 30s GET budget. decompose joins bar_metadata +
# forward_returns_cache + symbol_events for a 500-match fan-out; warm
# it's ~4-8s, but a fully-cold container can take longer.
_SLOW_GET_PATHS = ("/decompose",)


def _dispatch(http_path: str, http_method: str, direct_fn, **kwargs) -> dict:
    """Route to HTTP API or direct Python call based on config."""
    if _use_http():
        if http_method == "POST":
            return _http_post(http_path, kwargs)
        timeout = 75 if any(s in http_path for s in _SLOW_GET_PATHS) else 30
        return _http_get(http_path, timeout=timeout)
    return direct_fn(**kwargs)


# ── Direct Python imports (local mode) ──────────────────────

def _direct_search(query: str, timeframe: str = "auto", top_n: int = 10) -> dict:
    """Run search directly via Python imports."""
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
    from services.follow_through import compute_follow_through
    return compute_follow_through(results)


def _direct_cohort(
    anchor: dict,
    filters: dict | None = None,
    horizons: list[int] | None = None,
    top_k: int = 500,
    include_path_stats: bool = False,
) -> dict:
    """Build a conditional distribution cohort directly. Body shape matches
    the /api/v1/cohort HTTP endpoint so the same kwargs go through either path."""
    from services.cohort import build_cohort
    return build_cohort(
        anchor=anchor,
        filters=filters or {},
        horizons=horizons or [1, 5, 10],
        top_k=top_k,
        include_path_stats=include_path_stats,
    )


def _direct_cohort_refine(
    cohort_id: str,
    extra_filters: dict | None = None,
    horizons: list[int] | None = None,
    include_path_stats: bool = False,
) -> dict:
    from services.cohort import refine_cohort
    return refine_cohort(
        cohort_id=cohort_id,
        extra_filters=extra_filters or {},
        horizons=horizons,
        include_path_stats=include_path_stats,
    )


def _direct_cohort_explain(cohort_id: str, horizon: int = 5) -> dict:
    from services.cohort import explain_cohort
    return explain_cohort(cohort_id, horizon=horizon)


# ── v2 primitives ──────────────────────────────────────────
# Server-side v2_* helpers pin embedding_version="v2" so the MCP public surface
# never leaks the v5 internal work. Per feedback_v5_under_wraps.md, nothing
# v5-specific (cross_timeframe, v5 calibration meta, embedding_version kwarg) is
# exposed to clients.

def _direct_v2_search(query, top_k: int = 500) -> dict:
    from services.v2_api import v2_search
    return v2_search(query=query, top_k=top_k)


def _direct_v2_cohort(
    cohort_id: str | None = None,
    query=None,
    filters: dict | None = None,
    horizons: list[int] | None = None,
    top_k: int = 500,
    include_path_stats: bool = True,
) -> dict:
    from services.v2_api import v2_cohort
    return v2_cohort(
        cohort_id=cohort_id, query=query, filters=filters,
        horizons=horizons, top_k=top_k, include_path_stats=include_path_stats,
    )


def _direct_v2_explain(cohort_id: str, style: str = "filter_ranking", horizon: int = 5) -> dict:
    from services.v2_api import v2_explain
    return v2_explain(cohort_id=cohort_id, style=style, horizon=horizon)


def _direct_v2_context(target) -> dict:
    from services.v2_api import v2_context
    return v2_context(target=target)


def _direct_v2_analyze(
    cohort_id: str | None = None,
    symbol: str | None = None,
    date: str | None = None,
    metric: str = "anomaly",
    extra_args: dict | None = None,
) -> dict:
    from services.v2_api import v2_analyze
    return v2_analyze(
        cohort_id=cohort_id, symbol=symbol, date=date,
        metric=metric, extra_args=extra_args,
    )


def _direct_v2_portfolio(
    holdings: list,
    horizons: list | None = None,
    top_k_per_holding: int = 300,
    include_path_stats: bool = False,
) -> dict:
    from services.v2_api import v2_portfolio
    return v2_portfolio(
        holdings=holdings,
        horizons=horizons,
        top_k_per_holding=top_k_per_holding,
        include_path_stats=include_path_stats,
    )


def _direct_summary(query_label: str, n_matches: int, horizon_returns: dict) -> dict:
    """Generate summary directly."""
    from services.summary_service import generate_pattern_summary
    text = generate_pattern_summary(query_label, n_matches, horizon_returns)
    return {"summary": text}


_status_cache: dict = {}  # {"result": ..., "expires_at": float}


def _direct_status() -> dict:
    """Get embedding status directly (direct mode only).

    Same cache + stale-on-error contract as the HTTP endpoint: embedding_status()
    now raises rather than publishing a placeholder when a count is unavailable
    (it spent an unknown period reporting 9,045 symbols against a true 20,684),
    so an uncached direct call would surface that as a tool error to agents.

    Deliberately NOT using utils.cache.ttl_cache despite duplicating it: the
    public chart-library-mcp package vendors THIS FILE VERBATIM (see
    .github/workflows/mcp-sync-alarm.yml) and ships no utils/ or db/ package, so
    any new top-level import here is a ModuleNotFoundError at load for every
    remote-mode user. A decorator cannot be imported lazily, so the cache is
    inlined and the db import stays inside the function.
    """
    import time as _t

    from db.embeddings import embedding_status

    now = _t.time()
    if _status_cache and now < _status_cache.get("expires_at", 0):
        return _status_cache["result"]
    try:
        result = embedding_status()
    except Exception:
        if "result" in _status_cache:
            _status_cache["expires_at"] = now + 60   # back off, don't hammer
            return _status_cache["result"]
        raise
    _status_cache["result"] = result
    _status_cache["expires_at"] = now + 300
    return result


def _direct_analyze(query: str, timeframe: str = "auto", top_n: int = 10, include_summary: bool = True, same_sector: bool = False, context_weight: float = 0.0) -> dict:
    """Run combined analysis directly via Python imports."""
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
            import numpy as _np
            up = sum(1 for r in clean if r > 0)
            outcome_dist = {
                "up_count": up,
                "down_count": len(clean) - up,
                "total": len(clean),
                "median_return": round(sorted(clean)[len(clean) // 2], 2),
                "range_low": round(float(_np.percentile(clean, 10)), 2),
                "range_high": round(float(_np.percentile(clean, 90)), 2),
                "returns": [round(r, 2) for r in clean],
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


def _direct_discover_picks(date: str = "", limit: int = 20) -> dict:
    """Query discover picks directly from DB."""
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
                return {"date": "", "picks": [], "count": 0}

            cur.execute("""
                SELECT symbol, test_date::text, direction, interest_score,
                       wpred_1d, wpred_5d, wpred_10d, n_matches, summary_text,
                       avg_distance, up_count_5d, median_ret_5d,
                       ret_range_low, ret_range_high
                FROM forward_tests
                WHERE test_date = %s AND interest_score IS NOT NULL
                ORDER BY interest_score DESC LIMIT %s
            """, (pick_date, limit))
            rows = cur.fetchall()
            picks = [{
                "symbol": r[0], "date": r[1], "direction": r[2],
                "interest_score": r[3], "wpred_1d": r[4], "wpred_5d": r[5],
                "wpred_10d": r[6], "n_matches": r[7], "summary_text": r[8],
                "avg_distance": r[9], "up_count_5d": r[10],
                "median_ret_5d": r[11], "ret_range_low": r[12],
                "ret_range_high": r[13],
            } for r in rows]
    finally:
        put_conn(conn)
    return {"date": pick_date, "picks": picks, "count": len(picks)}


def _direct_search_batch(symbols: list[str], date: str, timeframe: str = "rth", top_n: int = 10) -> dict:
    """Run batch search directly via Python imports."""
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
    return {"date": date, "timeframe": timeframe, "results": batch_results}


# ── Canonical 8-tool surface ─────────────────────────────────
# These tools replace the 22 legacy tools. v5-specific internals (embedding_version,
# cross_timeframe, v5 calibration meta) are NEVER accepted/returned here. The server
# may internally pass embedding_version="v2" to the cohort API, but the public
# MCP surface stays v2-only.


@mcp.tool(title="Search Historical Patterns", annotations=READ_ONLY)
async def search(query: str, top_k: int = 500) -> str:
    """Entry point: find historical analogs for a ticker+date and get a cohort handle.

    Situation-first, then shape: the query's tape happening (how far, overhead,
    effort vs progress, crowd) screens prior names; V5 L2 ranks inside that pool.
    Shape twins that do not share the happening are not returned. Follow-through
    is a later layer on the frozen set. If the clock is unbanded or the analog
    set is thin, status is empty and data.retrieve explains why.

    Stored ticker+date without a timeframe token uses V5 1d. Pass 1h/5m/15m/30m
    to rank that scale inside the same daily happening.

    data.informative is the study-90 width receipt: verdict in {informative,
    uninformative, insufficient, unavailable}. `uninformative` means the frozen set's
    5-session spread and centre match the market's base rate: the analogs are real,
    but a band drawn from them would only restate the market, so abstain on the band
    (meta.warnings says so too). It is never a side. `informative.by_horizon` carries
    the same receipt per horizon: "5d" (study 90, the primary) and "1d" (study 95:
    tighter constants, abstains on ~15% of 1d sets instead of ~31%).
    Returns: {status, data: {cohort_id, anchor, n_matches, survivorship, retrieve, informative}, meta}.
    The cohort_id can be passed to `cohort`, `analyze`, or `explain` to chain
    (no kNN re-run). pull_comps on a stored ticker+date uses the same retrieve.

    data.retrieve.same_situation is the event receipt: on a gap-day anchor (|open gap| >= 3%),
    same_situation_share = the fraction of the frozen set that was itself a same-sign >= 3% gap
    (study 102: median 4.5% -- the analogs are the STATE's twins, not the EVENT's, so the band
    is the state's width, not the gap's); gap_day_share on any anchor. A number, never a side.

    Args:
        query: 'SYMBOL YYYY-MM-DD' (optional ' timeframe' suffix, e.g. 'NVDA 2024-06-18 1h')
        top_k: Cohort size to establish (10-2000, default 500)
    """
    try:
        result = _dispatch(
            "/api/v2/search", "POST", _direct_v2_search,
            query=query, top_k=top_k,
        )
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}})


def _direct_micro_comps(bars, k: int = 50, prior_close=None, minute_of_day=None) -> dict:
    from services.micro_comps import micro_comps as _mc
    return _mc(bars, k=k, prior_close=prior_close, minute_of_day=minute_of_day)


@mcp.tool(title="Micro Comps — 10-Minute Moments", annotations=READ_ONLY)
async def micro_comps(bars: list[dict], k: int = 50, prior_close: float | None = None,
                      minute_of_day: int | None = None) -> str:
    """Ten 1-minute bars -> the historical MOMENTS they rhyme with.

    Event-anchored micro-pattern retrieval from a 3.2M-window corpus (2016-2026, $20M+
    dollar-volume tape): matched moments with forward-outcome DISTRIBUTIONS at +5/10/30/60
    minutes and to-close, plus replicability conditions (moment types, sectors, news share,
    RVOL at the moment) so you can judge whether the matches transfer to your situation.

    Honesty contract: no calibrated band yet (coverage receipt accruing); percentiles are
    raw historical outcomes of matched moments — facts, not forecasts. The corpus holds
    detector-worthy moments (volume surges, range breaks, violent moves); ten minutes of
    quiet chop will still match, but against moments — read conditions accordingly.

    Args:
        bars: chronological 1-minute bars [{o,h,l,c,v}, ...] — the LAST 10 form the window
        k: matches to retrieve (10-200, default 50)
        prior_close: prior session close for gap context (optional)
        minute_of_day: minutes since 09:30 ET of the last bar (optional; time-of-day is
            part of moment context — omitting applies a declared midday default)
    """
    try:
        result = _dispatch(
            "/api/v1/micro/comps", "POST", _direct_micro_comps,
            bars=bars, k=k, prior_close=prior_close, minute_of_day=minute_of_day,
        )
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}})


@mcp.tool(title="Cohort Intelligence", annotations=DEPRECATED_READ_ONLY)
async def cohort(
    cohort_id: str | None = None,
    query: str | None = None,
    filters: dict | None = None,
    horizons: list[int] | None = None,
    top_k: int = 500,
    include_path_stats: bool = True,
) -> str:
    """Conditional distribution for a chart pattern. The core Chart Library primitive.

    Returns historical return distribution (p10/p25/p50/p75/p90 + calibrated bands),
    MAE (max adverse excursion), MFE (max favorable excursion), hit rates, survivorship,
    and top matches — conditioned on any filters you pass.

    Supply EITHER a cohort_id (refine a stored cohort, sub-second) OR a query (build
    fresh). Filters include sector, regime (VIX/trend/VRP/term/credit/curve/breadth),
    liquidity (market cap), event (earnings proximity), and date_range. This one call
    subsumes the legacy get_cohort_distribution, refine_cohort_with_filters, run_scenario,
    and get_regime_win_rates.

    Raw p10/p90 run ~68% coverage vs 80% nominal; calibrated_return_pct is split-conformal
    adjusted and validated to hit ~80% on held-out anchors. Use calibrated bands for sizing
    and risk, raw for ranking.

    Args:
        cohort_id: Handle from `search` or a previous `cohort` call (preferred — fast refine)
        query: 'SYMBOL YYYY-MM-DD' to build fresh (mutually exclusive with cohort_id)
        filters: Optional dict — {sector, regime: {same_vix_bucket, same_trend, same_vrp_bucket,
                 same_term_bucket, same_credit_bucket, same_curve_bucket, same_breadth_bucket},
                 liquidity: {same_cap_bucket}, event: {no_earnings_within_days}, date_range}.
                 For scenario analysis, pass regime filters; for regime-win-rate queries, filter
                 on same_vix_bucket + same_trend.
        horizons: Forward horizons in trading days (default [5, 10]; max 252)
        top_k: Cohort size (only used when building fresh, 10-2000)
        include_path_stats: Include MAE/MFE/realized-vol (default True, ~0ms from cache)
    """
    try:
        result = _dispatch(
            "/api/v2/cohort", "POST", _direct_v2_cohort,
            cohort_id=cohort_id, query=query, filters=filters or {},
            horizons=horizons, top_k=top_k, include_path_stats=include_path_stats,
        )
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}})


@mcp.tool(title="Analytic Metrics", annotations=READ_ONLY)
async def analyze(
    metric: str,
    cohort_id: str | None = None,
    symbol: str | None = None,
    date: str | None = None,
    extra_args: dict | None = None,
) -> str:
    """Analytic metrics on a cohort or (symbol, date), dispatched by `metric=` ∈ {anomaly,
    volume_profile, crowding, correlation_shift, earnings_reaction, pattern_degradation,
    regime_accuracy}. (Index in the summary so the metrics are discoverable without reading
    the full docstring — 2026-06-16 review.)

    Supply cohort_id (preferred, anchor inherited) OR explicit symbol+date.

    metric values:
      - 'anomaly'             — is the pattern unusual vs the symbol's own history?
      - 'volume_profile'      — intraday volume vs historical norms
      - 'crowding'            — cross-symbol crowding indicator (market-wide; no symbol needed)
      - 'correlation_shift'   — rolling correlation breakdowns (extra_args: lookback, window, symbols)
      - 'earnings_reaction'   — historical earnings gap reactions (extra_args: min_gap)
      - 'pattern_degradation' — are signals losing edge vs historical accuracy? (market-wide)
      - 'regime_accuracy'     — win rates filtered by current market regime (needs symbol)

    Replaces legacy: detect_anomaly, get_volume_profile, get_crowding, get_earnings_reaction,
    get_correlation_shift, get_pattern_degradation, get_regime_win_rates.

    Args:
        metric: one of the strings above (required)
        cohort_id: stored cohort handle from `search`/`cohort` (preferred)
        symbol: ticker if no cohort_id (e.g. 'NVDA')
        date: ISO date if no cohort_id
        extra_args: per-metric optional knobs (see metric descriptions)
    """
    try:
        # 'regime_accuracy' is a new metric name — route to the legacy regime_win_rates
        # implementation which lives outside v2_analyze. The other metrics use v2_analyze.
        if metric == "regime_accuracy":
            if not symbol and cohort_id:
                # Resolve anchor from stored cohort
                from services.cohort import _cache_get
                stored = _cache_get(cohort_id)
                if stored:
                    anchor = stored.get("anchor", {})
                    symbol = anchor.get("symbol")
                    if not date:
                        date = anchor.get("date")
            if not symbol:
                return json.dumps({
                    "status": "error", "data": {},
                    "meta": {"warnings": ["regime_accuracy requires symbol (or cohort_id with anchor)"]},
                })
            # Inline call — legacy `get_regime_win_rates` wrapper was
            # removed in the 2026-05-26 v5 consolidation. /api/v1/regime-win-rates
            # is still live; call it directly.
            try:
                qs = f"symbol={symbol}"
                if date:
                    qs += f"&date={date}"
                legacy_result = _http_get(f"/api/v1/regime-win-rates?{qs}")
            except Exception as exc:
                legacy_result = {"error": str(exc)}
            return json.dumps(_attach_freshness({
                "status": "ok" if "error" not in legacy_result else "error",
                "data": legacy_result,
                "meta": {"warnings": []},
            }), default=str, indent=2)

        result = _dispatch(
            "/api/v2/analyze", "POST", _direct_v2_analyze,
            cohort_id=cohort_id, symbol=symbol, date=date,
            metric=metric, extra_args=extra_args or {},
        )
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}})


def _direct_cohort_analyze(
    symbol: str,
    date: str,
    timeframe: str = "1d",
    cohort_size: int = 500,
    filters: dict | None = None,
    horizons: list[int] | None = None,
    include_feature_importance: bool = True,
    include_regime_stratification: bool = True,
    include_risk_profile: bool = True,
    include_cohort_anchors: bool = False,
    exclude_same_symbol_days: int = 10,
    include_modes: bool = False,
    n_modes: int = 4,
    include_first_passage: bool = False,
    first_passage_upper: float = 0.05,
    first_passage_lower: float = 0.05,
) -> dict:
    """Direct (in-process) implementation of cohort_analyze."""
    from services.cohort_analyzer import (
        Anchor, AnalyzeRequest, AnalyzeOptions, CohortFilters, analyze_cohort,
    )
    from dataclasses import asdict

    f = filters or {}
    cf = CohortFilters(
        vol_regime=f.get("vol_regime"),
        days_since_earnings=f.get("days_since_earnings"),
        days_since_ath=f.get("days_since_ath"),
        sector_rs=f.get("sector_rs"),
        has_news=f.get("has_news"),
        macro_state=f.get("macro_state"),
        relative_volume=f.get("relative_volume"),
        realized_vol=f.get("realized_vol"),
    )
    opt = AnalyzeOptions(
        include_cohort_anchors=include_cohort_anchors,
        include_feature_importance=include_feature_importance,
        include_regime_stratification=include_regime_stratification,
        include_risk_profile=include_risk_profile,
        exclude_same_symbol_days=exclude_same_symbol_days,
        include_modes=include_modes,
        n_modes=n_modes,
        include_first_passage=include_first_passage,
        first_passage_upper=first_passage_upper,
        first_passage_lower=first_passage_lower,
    )
    req = AnalyzeRequest(
        anchor=Anchor(symbol=symbol, date=date, timeframe=timeframe),
        cohort_size=cohort_size,
        horizons=horizons or [1, 5, 10],
        filters=cf,
        options=opt,
    )
    return asdict(analyze_cohort(req))


# 2026-06-09 naming Wave 2.5: hidden from tools/list so pull_comps is the ONE
# discoverable flagship (a fresh connector session was still choosing
# cohort_analyze and getting old field names — the two tools competed).
# Hidden-but-CALLABLE: every existing integration that names cohort_analyze
# keeps working verbatim; this is discovery-tier deprecation, not removal.
@mcp.tool(title="Cohort Analyze (Layer 3 full)", annotations=DEPRECATED_READ_ONLY)
async def cohort_analyze(  # same engine as pull_comps; original field names
    symbol: str,
    date: str,
    timeframe: str = "1d",
    cohort_size: int = 500,
    filters: dict | None = None,
    horizons: list[int] | None = None,
    include_feature_importance: bool = True,
    include_regime_stratification: bool = True,
    include_risk_profile: bool = True,
    exclude_same_symbol_days: int = 10,
    include_modes: bool = False,
    n_modes: int = 4,
    include_first_passage: bool = False,
    first_passage_upper: float = 0.05,
    first_passage_lower: float = 0.05,
    # ---- Layer-2 platform knobs (power-user tinkering; the calibration MOAT is unaffected —
    # these only NARROW the candidate universe / analog dates / scales before retrieval) ----
    universe_sector_etf: list[str] | None = None,
    universe_min_dollar_volume: float | None = None,
    universe_symbols: list[str] | None = None,
    universe_market_cap_min: float | None = None,
    universe_market_cap_max: float | None = None,
    universe_fundamentals: dict | None = None,
    exclude_symbols: list[str] | None = None,
    dedup_days: int | None = None,
    max_per_symbol: int | None = None,
    time_period_start: str | None = None,
    time_period_end: str | None = None,
    additional_timeframes: list[str] | None = None,
    timeframe_aggregate: str | None = None,
) -> str:
    """Layer 3 cohort intelligence — V5 retrieval + Layer 2 metadata.

    Given a (symbol, date, timeframe) anchor, returns:
      • outcome distribution per horizon (1d / 5d / 10d default)
      • per-feature importance — which Layer 2 metadata features separated
        winners from losers within this specific cohort
      • regime stratification — outcomes sliced by vol regime
      • risk profile — drawdown / runup percentiles
      • cohort tightness score

    Empirical-distribution analysis. Does NOT predict a single point return —
    surfaces what historical analogs did and which features mattered.

    Distinct from `cohort` (the v2-era distribution primitive). This tool
    runs the North Star Layer 3 analyzer on V5 embeddings with rich Layer 2
    metadata (vol regime, macro state, sector RS, earnings calendar, etc.).

    Args:
        symbol: Ticker (e.g. "NVDA")
        date: Anchor date, ISO YYYY-MM-DD
        timeframe: One of 5m / 15m / 30m / 1h / 1d (default 1d for stored ticker+date)
        cohort_size: Target K nearest neighbors (default 500)
        filters: Optional Layer 2 metadata constraints. Keys:
            vol_regime: list of "low"/"mid"/"high"
            macro_state: list of "bullish"/"neutral"/"bearish"
            has_news: bool (only meaningful for 2024+ anchors)
            days_since_earnings / days_since_ath / sector_rs / realized_vol /
            relative_volume: dict with "min" and/or "max"
        horizons: list of forward-return horizons (default [1, 5, 10])
        exclude_same_symbol_days: drop same-symbol analogs within N days
            of the anchor (default 10; autocorrelation control)
        include_modes: when True, also cluster the cohort's forward-bar
            trajectories into N outcome modes ('steady up', 'chop',
            'reversal', ...) and return them under `modes`. Each mode
            reports count, return stats, centroid trajectory, and a
            human-readable label. The "playbook surface" — the
            historical distribution broken out by what happened, not
            collapsed to a single median.
        n_modes: number of modes to cluster (default 4, range 2-8).
        include_first_passage: when True, also return `first_passage` — per
            horizon triple-barrier profiles over the cohort's forward PATHS:
            how often the upper target (+first_passage_upper) was tagged
            BEFORE the lower stop (-first_passage_lower) [p_upper], the
            reverse [p_lower], or neither within the horizon [p_none], plus
            median days-to-hit, an ambiguous_rate for same-day double-touches
            (daily bars can't order them), and a censored count for analogs
            whose forward window was too short to resolve. This is the path-
            ORDERING answer terminal MAE/MFE structurally cannot give (same
            worst-dip/best-runup, opposite barrier label, decided by order).
            Default off.
        first_passage_upper: upper target as a positive fraction of the
            anchor close (0.05 = +5%). Only used when include_first_passage.
        first_passage_lower: lower stop as a positive fraction of the anchor
            close (0.05 = -5%). Only used when include_first_passage.
        PLATFORM KNOBS: the universe_* / time_period_* / additional_timeframes / exclude_symbols /
            dedup_days / max_per_symbol parameters are an OWNER-ONLY private feature — gated
            server-side (ignored for non-owner callers). Not for public use.
    """
    try:
        if _use_http():
            # Endpoint expects nested anchor shape — build the body explicitly.
            body = {
                "anchor": {"symbol": symbol, "date": date, "timeframe": timeframe},
                "cohort_size": cohort_size,
                "horizons": horizons or [1, 5, 10],
                "filters": filters,
                "options": {
                    "include_feature_importance": include_feature_importance,
                    "include_regime_stratification": include_regime_stratification,
                    "include_risk_profile": include_risk_profile,
                    "exclude_same_symbol_days": exclude_same_symbol_days,
                    "dedup_days": dedup_days,
                    "max_per_symbol": max_per_symbol,
                    "include_modes": include_modes,
                    "n_modes": n_modes,
                    "include_first_passage": include_first_passage,
                    "first_passage_upper": first_passage_upper,
                    "first_passage_lower": first_passage_lower,
                },
            }
            # Layer-2 universe / time-period / multi-scale knobs — forward only when set
            # (REST CohortAnalyzeRequest accepts them as top-level fields; defaults keep
            # behavior identical). Calibration is applied server-side regardless = moat fixed.
            for _k, _v in (("universe_sector_etf", universe_sector_etf),
                           ("universe_min_dollar_volume", universe_min_dollar_volume),
                           ("universe_symbols", universe_symbols),
                           ("exclude_symbols", exclude_symbols),
                           ("universe_market_cap_min", universe_market_cap_min),
                           ("universe_market_cap_max", universe_market_cap_max),
                           ("universe_fundamentals", universe_fundamentals),
                           ("time_period_start", time_period_start),
                           ("time_period_end", time_period_end),
                           ("additional_timeframes", additional_timeframes),
                           ("timeframe_aggregate", timeframe_aggregate)):
                if _v is not None:
                    body[_k] = _v
            result = _http_post("/api/v1/cohort_analyze", body)
        else:
            result = _direct_cohort_analyze(
                symbol=symbol, date=date, timeframe=timeframe,
                cohort_size=cohort_size, filters=filters,
                horizons=horizons,
                include_feature_importance=include_feature_importance,
                include_regime_stratification=include_regime_stratification,
                include_risk_profile=include_risk_profile,
                exclude_same_symbol_days=exclude_same_symbol_days,
                include_modes=include_modes,
                n_modes=n_modes,
                include_first_passage=include_first_passage,
                first_passage_upper=first_passage_upper,
                first_passage_lower=first_passage_lower,
            )
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}})


_LIVE_DATE_SENTINELS = frozenset({"now", "live", "today"})


@mcp.tool(title="Pull Comps", annotations=READ_ONLY)
async def pull_comps(
    symbol: str,
    date: str | None = None,
    timeframe: str | None = None,
    comp_count: int = 500,
    filters: dict | None = None,
    horizons: list[int] | None = None,
    include_drivers: bool = True,
    include_risk_profile: bool = True,
    tail_bars: list[dict] | None = None,
    window_bars: list[dict] | None = None,
    include_modes: bool = False,
    # ---- Layer-2 platform knobs (STORED path) — power-user tinkering; moat unaffected ----
    universe_sector_etf: list[str] | None = None,
    universe_min_dollar_volume: float | None = None,
    universe_symbols: list[str] | None = None,
    universe_market_cap_min: float | None = None,
    universe_market_cap_max: float | None = None,
    universe_fundamentals: dict | None = None,
    exclude_symbols: list[str] | None = None,
    dedup_days: int | None = None,
    max_per_symbol: int | None = None,
    time_period_start: str | None = None,
    time_period_end: str | None = None,
    additional_timeframes: list[str] | None = None,
    timeframe_aggregate: str | None = None,
) -> str:
    """Pull the comp set for a subject (symbol, date, timeframe): the historical
    analogs, what they did next, the drivers that separated the best outcomes,
    and our coverage record — never a call.

    THE flagship primitive. One tool, three data sources, picked from your args:

      • STORED (default) — `date` is a YYYY-MM-DD (an as-of close), or OMITTED for
        the latest stored anchor. Analog retrieve is happening-then-shape
        (situation identity, then V5 1d unless timeframe is set). Unbanded/thin
        clocks abstain. Full comp set: outcome distribution per horizon,
        the calibrated band + coverage_record, drivers (winner/loser separation),
        risk profile, conditions, and grounding (confidence-to-ground: evidence-size
        score + thin/blind flags with the measured coverage receipt — check it
        before leaning on the base rate). Auto-steps back if that exact date has no
        embedding yet (weekend / holiday / pre-close).
      • WE-FETCH-LIVE — pass date="now" (or "live"/"today"). WE fetch the subject's
        recent intraday bars (~15m delayed) and embed them on the fly. Returns the
        LIVE calibrated comp set. Use timeframe=1h or finer for an intraday read.
      • YOUR-OWN-BARS LIVE — pass `tail_bars` (recent MINUTE bars we splice onto our
        history, with `symbol`) OR `window_bars` (a >=636-bar self-contained window
        already at `timeframe`, for symbols not in our corpus). No live-data cost to
        us. The cohort stays historical-only before the anchor (no lookahead).

    drivers / risk_profile are present on the STORED path only — a LIVE anchor
    (we-fetch or your-own-bars) has no stored bar metadata, so feature_importance /
    regime_stratification are omitted there. The calibrated band is present on all
    three paths.

    Same engine as the legacy `cohort_analyze`, front-of-house vocabulary at the
    boundary: subject / comp_set_id / comp_count / comp_strength / match_quality /
    drivers / coverage_record / up_rate / conditions (calm-normal-stressed). Chain
    the returned comp_set_id into cohort_introspect / cohort_members / cohort_groupby
    / cohort_rerank.

    REST equivalents (unchanged, all still live): the stored path maps to
    POST /api/v1/pull_comps (front-of-house {"subject": {...}}; legacy
    {"anchor": {...}} still accepted); date="now" routes to POST /api/v1/cohort_live;
    tail_bars/window_bars route to POST /api/v1/anchor/comps.

    READ conditioning_summary FIRST when it is present (stored path): it appears only
    when the subject sits in a special regime (within the earnings window, or near
    quarter-/month-end) and collapses the relevant calibration adjustments into one
    block — the active_conditioners, the single recommended widened band per horizon
    (recommended_band_by_horizon), whether a hold_path_band applies, and a plain
    sentence. When present, use its recommended band rather than the raw band: a
    setup heading into earnings has a historically wider outcome range than the
    plain analogs show. Absent on ordinary setups (nothing to flag).

    Args:
        symbol: Ticker for the subject (e.g. "NVDA")
        date: YYYY-MM-DD (stored as-of), OMITTED for the latest stored anchor, or
            "now"/"live"/"today" for the we-fetch-live read
        timeframe: V5 scale — 5m / 15m / 30m / 1h / 1d. Stored default 1d;
            live (date=now or your-own-bars) default 1h.
        comp_count: Comp set size (10-2000, default 500)
        filters: Same filter dict as cohort_analyze (back-of-house keys; stored path)
        horizons: Forward horizons in trading days (default [1, 5, 10])
        include_drivers: Include the winner/loser driver separation (stored path)
        include_risk_profile: Include drawdown / run-up profile (stored path)
        tail_bars: YOUR-OWN-BARS live — recent minute bars {t,o,h,l,c,v,vwap} to
            splice onto our history (pass with `symbol`)
        window_bars: YOUR-OWN-BARS live — >=636 self-contained scale-bars
            {o,h,l,c,v,vwap} (for symbols not in our corpus)
        include_modes: Cluster the cohort's forward paths into outcome modes
            (we-fetch-live and stored paths)
        PLATFORM KNOBS: the universe_* / time_period_* / additional_timeframes / exclude_symbols /
            dedup_days / max_per_symbol parameters are an OWNER-ONLY private feature — gated
            server-side (ignored for non-owner callers). Not for public use. (Longer horizons already
            work — pass horizons=[21,63,252].)
    """
    try:
        from services.lexicon import to_front_of_house
    except ImportError:  # vendored/PyPI flat layout (chart-library-mcp package)
        from lexicon import to_front_of_house

    try:
        from services.happening_shape_search import default_stored_scale
    except ImportError:
        from happening_shape_search import default_stored_scale

    timeframe = default_stored_scale(
        date, timeframe, live_bars=bool(tail_bars or window_bars)
    )

    # 1. YOUR-OWN-BARS live path — caller supplies the window.
    if tail_bars or window_bars:
        body: dict = {"scale": timeframe, "as_of": (date or "now"),
                      "cohort_size": comp_count, "horizons": horizons or [1, 5, 10]}
        if symbol:
            body["symbol"] = symbol
        if tail_bars:
            body["tail_bars"] = tail_bars
        if window_bars:
            body["window_bars"] = window_bars
        # embed-on-the-fly needs the server's V5 encoder runtime -> always via the API.
        result = _http_post("/api/v1/anchor/comps", body)
        try:
            return json.dumps(to_front_of_house(result), default=str, indent=2)
        except Exception:  # noqa: BLE001 — never let the remap break the data path
            return json.dumps(result, default=str, indent=2)

    # 2. WE-FETCH-LIVE path — date is a live sentinel ("now"/"live"/"today").
    if isinstance(date, str) and date.strip().lower() in _LIVE_DATE_SENTINELS:
        body = {"symbol": symbol, "scale": timeframe, "cohort_size": comp_count,
                "horizons": horizons or [1, 5, 10], "include_modes": include_modes}
        # embed-on-the-fly needs the server's V5 encoder runtime -> always via the API.
        result = _http_post("/api/v1/cohort_live", body)
        try:
            return json.dumps(to_front_of_house(result), default=str, indent=2)
        except Exception:  # noqa: BLE001 — never let the remap break the data path
            return json.dumps(result, default=str, indent=2)

    # 3. STORED path (default). date=None -> today's UTC date so the analyzer's
    # auto_step_back (default on) resolves to the most recent stored anchor.
    if not date:
        import datetime as _dt
        date = _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    raw = await cohort_analyze(
        symbol=symbol, date=date, timeframe=timeframe,
        cohort_size=comp_count, filters=filters, horizons=horizons,
        include_feature_importance=include_drivers,
        include_risk_profile=include_risk_profile,
        include_modes=include_modes,
        universe_sector_etf=universe_sector_etf,
        universe_min_dollar_volume=universe_min_dollar_volume,
        universe_symbols=universe_symbols,
        universe_market_cap_min=universe_market_cap_min,
        universe_market_cap_max=universe_market_cap_max,
        universe_fundamentals=universe_fundamentals,
        exclude_symbols=exclude_symbols, dedup_days=dedup_days, max_per_symbol=max_per_symbol,
        time_period_start=time_period_start, time_period_end=time_period_end,
        additional_timeframes=additional_timeframes, timeframe_aggregate=timeframe_aggregate,
    )
    try:
        return json.dumps(to_front_of_house(json.loads(raw)), default=str, indent=2)
    except Exception:  # noqa: BLE001 — never let the remap break the data path
        return raw


@mcp.tool(title="Replay Setup", annotations=READ_ONLY)
async def replay(
    symbol: str,
    date: str,
    timeframe: str = "1d",
    horizons: list[int] | None = None,
    cohort_size: int = 300,
) -> str:
    """Replay a PAST setup: what the historical-analog distribution SAID vs what ACTUALLY
    happened. The out-of-sample receipt a desk wants.

    For (symbol, date, timeframe), rebuilds the cohort historical-only AS-OF that date (no
    lookahead), takes the analog outcome distribution + calibrated 80% band, and joins the
    subject's REAL realized forward return. Per horizon: predicted p10/median/p90, the
    calibrated band, realized_return, in_calibrated_band, and realized_percentile.

    Answers "for setups like this, what actually followed?" — historical fact vs the analog
    distribution. NOT a recommendation, never a directional call.

    Args:
        symbol: ticker of the past setup (e.g. 'NVDA')
        date: setup date YYYY-MM-DD (the as-of)
        timeframe: V5 scale — 5m / 15m / 30m / 1h / 1d
        horizons: forward horizons in trading days (default [1, 5, 10])
        cohort_size: cohort size (30-1000, default 300)
    """
    body = {"symbol": symbol, "date": date, "timeframe": timeframe,
            "cohort_size": cohort_size, "horizons": horizons or [1, 5, 10]}
    try:
        if _use_http():
            result = _http_post("/api/v1/replay", body)
        else:
            from services.replay import replay_setup
            result = replay_setup(symbol, date, timeframe, horizons or [1, 5, 10], cohort_size)
        return json.dumps(result, default=str, indent=2)
    except Exception as e:  # noqa: BLE001
        return json.dumps({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}})


@mcp.tool(title="Size Position", annotations=READ_ONLY)
async def size_position(
    symbol: str,
    side: str = "long",
    horizon: int = 5,
    risk_amount: float | None = None,
    risk_pct: float | None = None,
    account_value: float | None = None,
    entry_price: float | None = None,
    stop_pct: float | None = None,
    profit_target_pct: float | None = None,
    as_of_date: str | None = None,
    timeframe: str = "1d",
    holdings: list | None = None,
    comp_set_id: str | None = None,
) -> str:
    """Calibrated, DIRECTION-FREE position sizing. YOU bring the side (your thesis); this
    returns the calibrated downside and a suggested size so a calibrated ~1-in-10 bad case
    ≈ your risk budget.

    Sizing is fixed-fractional DOWNSIDE CONTROL (not Kelly/edge-based) — it caps loss, it
    never implies a directional view. Every risk number is the conformal-calibrated one
    (the nominal-80% band held 80.8% across 302,880 audited cases — beta-independent). A
    supplied stop is audited (calibrated hit-rate from the cohort's first-passage) and used
    as a sizing cap; omit it and we suggest one beyond the calibrated band edge. We do NOT
    forecast direction — use this for the RISK leg, bring your own thesis for the side.

    Pass comp_set_id (a handle from a prior pull_comps / cohort_analyze) to size off that
    already-pulled comp set instead of re-retrieving — we adopt its anchor so you need not
    re-supply symbol/date. NOTE: reusing a comp set OMITS stop_analysis (the stop's
    first-passage is computed at YOUR barrier and isn't stored in the set) — call with
    symbol+date+stop_pct when you need the calibrated stop-hit odds.

    Args:
        symbol: ticker (e.g. 'NVDA')
        side: 'long' or 'short' — your thesis; we never choose it
        horizon: holding horizon in trading days (1, 5, or 10)
        risk_amount: max acceptable loss in $ (provide this OR risk_pct)
        risk_pct: max acceptable loss as % of account (needs account_value)
        account_value: account value in $ (for risk_pct and pct_of_account)
        entry_price: entry price; defaults to the last close
        stop_pct: stop magnitude in % (e.g. 5.0) — audited and used as a sizing cap
        profit_target_pct: optional target magnitude in %, refines stop-hit odds
        as_of_date: as-of date YYYY-MM-DD (point-in-time); defaults to latest
        timeframe: V5 scale — 1d / 1h / 30m / 15m / 5m
        holdings: existing book [{symbol, side, notional}, ...] — sizes the new position
            correlation-aware against it (a same-side correlated add is sized DOWN; a hedge caps
            at the standalone size, never up-sized)
        comp_set_id: reuse a prior comp set (its anchor) instead of re-retrieving
    """
    body = {"symbol": symbol, "side": side, "horizon": horizon,
            "risk_amount": risk_amount, "risk_pct": risk_pct, "account_value": account_value,
            "entry_price": entry_price, "stop_pct": stop_pct, "profit_target_pct": profit_target_pct,
            "as_of_date": as_of_date, "timeframe": timeframe, "holdings": holdings,
            "comp_set_id": comp_set_id}
    try:
        if _use_http():
            result = _http_post("/api/v1/size_position", body)
        else:
            from services.size_position import size_position as _sp
            result = _sp(symbol, side=side, horizon=horizon, risk_amount=risk_amount,
                         risk_pct=risk_pct, account_value=account_value, entry_price=entry_price,
                         stop_pct=stop_pct, profit_target_pct=profit_target_pct,
                         as_of_date=as_of_date, timeframe=timeframe, holdings=holdings,
                         comp_set_id=comp_set_id)
        return json.dumps(result, default=str, indent=2)
    except Exception as e:  # noqa: BLE001
        return json.dumps({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}})


@mcp.tool(title="Vol Premium Scan", annotations=READ_ONLY)
async def vol_premium(symbols: list, horizon: int = 5, as_of_date: str | None = None) -> str:
    """Scan a universe for where the CALIBRATED forward expected move is richest/cheapest vs the
    name's own recent realized vol. DIRECTION-FREE — this sizes the move, never calls direction.

    For each name: cohort_expected_move (the conformal-calibrated forward 1-sigma dispersion — our
    unique asset) vs realized_move (trailing realized vol scaled to the horizon). vol_premium_ratio
    >> 1 = the analog cohort expects a BIGGER move than the stock has been making (expansion / coiled,
    cheap optionality); << 1 = compression. Ranked, split into expansion / compression lists.

    NOTE: the options-IMPLIED comparison (`implied_move_pct`) is a documented drop-in — per-name
    options IV is not ingested yet, so this is a vol-divergence scan, not an options risk-premium arb.

    Args:
        symbols: tickers to scan (max 50)
        horizon: 1, 5, or 10 trading days
        as_of_date: as-of date YYYY-MM-DD; defaults to latest
    """
    body = {"symbols": symbols, "horizon": horizon, "as_of_date": as_of_date}
    try:
        if _use_http():
            result = _http_post("/api/v1/vol_premium", body)
        else:
            from services.vol_premium import scan_vol_premium
            result = scan_vol_premium(symbols, horizon=horizon, as_of_date=as_of_date, max_symbols=50)
        return json.dumps(result, default=str, indent=2)
    except Exception as e:  # noqa: BLE001
        return json.dumps({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}})


@mcp.tool(title="Calibration Benchmark", annotations=READ_ONLY)
async def calibration_benchmark(action: str = "get", submissions: list | None = None,
                                label: str = "your_predictor", n: int = 200) -> str:
    """The public calibration benchmark — score ANY interval predictor on the same frozen set.

    action='get' returns the frozen test set (QUESTIONS: symbol, date, horizon) + the standing
    reference leaderboard (Chart Library's calibrated band + the raw-cohort baseline scored by the
    Winkler interval score — lower is better — plus cited ungrounded-LLM baselines).

    action='score' grades YOUR 80% intervals (`submissions` = [{id, lo, hi}] in percent, ids from the
    'get' set) against realized outcomes, ranked vs the reference rows. A tight band that under-covers
    is penalized — honest coverage is rewarded. Direction-free: intervals are uncertainty, not a call.

    Args:
        action: 'get' (fetch the set + leaderboard) or 'score' (grade your submissions)
        submissions: for 'score' — [{id, lo, hi}] forward-return intervals at nominal 80%
        label: your entry name on the leaderboard
        n: benchmark set size (default 200)
    """
    try:
        if action == "score":
            body = {"submissions": submissions or [], "label": label, "n": n}
            if _use_http():
                result = _http_post("/api/v1/benchmark/score", body)
            else:
                from services.calibration_benchmark import score_submission
                result = score_submission(submissions or [], label=label, n=n)
        else:
            if _use_http():
                result = _http_get(f"/api/v1/benchmark?n={n}")
            else:
                from services.calibration_benchmark import get_benchmark
                result = get_benchmark(n=n)
        return json.dumps(result, default=str, indent=2)
    except Exception as e:  # noqa: BLE001
        return json.dumps({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}})


@mcp.tool(title="Symbol Intelligence", annotations=READ_ONLY)
async def symbol_intelligence(symbol: str, lookback_days: int = 365) -> str:
    """Layer 5 memory — what we've learned about this symbol across prior cohort analyses.

    Returns hit rate per horizon (sign of predicted median vs realized return),
    feature reliability ranked by sign-alignment with realized returns, regime
    exposure histogram, achieved conformal coverage, and the 10 most recent
    observations. Status='insufficient_history' when n < 5 prior analyses.

    Use this to ground recommendations: instead of treating each cohort_analyze
    in isolation, check whether a feature has historically been reliable for
    this ticker before leaning on it.

    Args:
        symbol: Ticker (e.g. "NVDA")
        lookback_days: How far back to aggregate observations (default 365)
    """
    try:
        if _use_http():
            result = _http_get(f"/api/v1/symbol_intelligence/{symbol.upper()}?lookback_days={lookback_days}")
        else:
            from services.cohort_memory import get_symbol_intelligence
            result = get_symbol_intelligence(symbol.upper(), lookback_days=lookback_days)
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}})


@mcp.tool(title="State Packet", annotations=READ_ONLY)
async def state_packet(symbol: str, date: str | None = None, lane: str = "v1") -> str:
    """The research packet for (symbol, session): the full memory read for one market state, in one call.

    data = the production happening-then-shape analog set of the state (n, symbols, sessions, closest members),
    its informative receipt (5d and 1d), what followed (1/5/10 d date-matched excess p10/p50/p90 and up-rate);
    transition_memory = every prior liquid instance of the name's own slow4 -> slow4 move (5 d excess p10/p50/p90,
    up-rate); tape (rvol, gap, intraday, close position, returns, MA200, 52w-high distance, overhead, peers, dollar
    volume, cap, sector). lane="gap" adds event: gap_pct/sign, earnings_session, width_1d/5d/10d (the analog band
    widened by the registered gap-day conditioner -- the honest range on a gap day), same_situation_share.

    The memory knows HOW MUCH, not WHICH WAY: bands are for sizing and stops; medians and up-rates are base-rate
    noise; no side is suggested anywhere. status: ok | empty (no happening identity for that session) | error.
    meta.lane_candidate says whether the name passed the lane's candidate rule that session.

    Args:
        symbol: Ticker (e.g. "NVDA")
        date: Session YYYY-MM-DD (default: the latest built session)
        lane: "v1" (slow-family flips with effort) or "gap" (event gaps >= 3%)
    """
    try:
        if _use_http():
            q = f"/api/v1/state-packet?symbol={symbol.upper()}&lane={lane}" + (f"&date={date}" if date else "")
            result = _http_get(q)
        else:
            from services.state_packet import build_state_packet
            result = build_state_packet(symbol, date, lane)
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}})


def _public_tool_error(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        warning = str(exc)
    else:
        log.exception("Public research tool failed")
        warning = "Research service unavailable. Please try again later."
    return json.dumps({"status": "error", "data": {}, "meta": {"warnings": [warning]}})


@mcp.tool(title="Market state", annotations=READ_ONLY)
async def market_state(symbol: str, date: str | None = None) -> str:
    """One call: completed-session state, tape, historical analogs, outcome ranges and transition memory.

    symbol is a stock ticker; optional date is YYYY-MM-DD. Omit date for the
    latest built session, not real-time prices. Preserve status, sample sizes,
    dates, informative receipts and missing values. Excess ranges describe
    historical percentage-point returns relative to a date-matched baseline;
    they are not calibrated forecasts or recommendations. No prior search needed.
    """
    try:
        from urllib.parse import urlencode
        symbol = validate_symbol(symbol)
        date = validate_session(date)
        if _use_http():
            params = {"symbol": symbol}
            if date:
                params["date"] = date
            result = await asyncio.to_thread(
                _http_get, "/api/v1/state-packet?" + urlencode(params), timeout=180,
            )
        else:
            from services.state_packet import build_state_packet
            result = await asyncio.to_thread(build_state_packet, symbol, date, "v1")
        return json.dumps(result, default=str, indent=2)
    except Exception as exc:
        return _public_tool_error(exc)


@mcp.tool(title="Daily research note", annotations=READ_ONLY)
async def daily_note(date: str | None = None) -> str:
    """Read the published daily research, its selection rule and settled-note tally in one call.

    No arguments needed. Optional date (YYYY-MM-DD) selects a published session.
    A missing note or unsettled outcome is unavailable evidence, not zero.
    The note is research selected by a disclosed rule, not a stock-pick list.
    """
    try:
        from urllib.parse import urlencode
        date = validate_session(date)
        if _use_http():
            path = "/api/v1/daily" + ("?" + urlencode({"session": date}) if date else "")
            result = await asyncio.to_thread(_http_get, path)
        else:
            from services.daily_note import daily_payload
            result = await asyncio.to_thread(daily_payload, date)
        return json.dumps(result, default=str, indent=2)
    except Exception as exc:
        return _public_tool_error(exc)


@mcp.tool(title="Research quality", annotations=READ_ONLY)
async def research_quality() -> str:
    """Read the published five-session calibration receipt; no arguments or earlier tool call needed.

    Preserve the receipt's dates, sample sizes and qualifications. Coverage
    applies to the calibrated cohort-band method and population named in the
    response, NOT automatically to market_state's empirical excess ranges,
    all research, or future returns. Daily-note results have a separate tally
    in daily_note. This is an evidence audit, not investment performance.
    """
    try:
        if _use_http():
            result = await asyncio.to_thread(_http_get, "/api/v1/calibration")
        else:
            from services.calibration_receipts import track_record as read_receipt
            result = await asyncio.to_thread(read_receipt)
        return json.dumps(result, default=str, indent=2)
    except Exception as exc:
        return _public_tool_error(exc)


@mcp.tool(title="Cohort Introspect", annotations=READ_ONLY)
async def cohort_introspect(
    cohort_id: str,
    where: dict | None = None,
    horizon: int = 5,
) -> str:
    """Second-hop drill-down on an EXISTING cohort — turn a base rate into a conditional one.

    PURPOSE: Given a cohort_id from a prior search / cohort / cohort_analyze
    call, slice the 300+ retrieved members by any macro / technical / event /
    news / sector / fundamentals attribute and return per-subset distribution
    stats versus the full-cohort baseline. This is the moat-revealing primitive — the
    introspection a quant analyst does by hand, conditioning a historical-analog
    cohort down to the subset that matches today.

    USE THIS WHEN you already have a cohort and want to know *why* its outcome
    distribution looks the way it does, or to condition on the segment the user
    actually cares about (their entry volume, their regime, their setup variant).
    It is the natural SECOND HOP after cohort_analyze — especially when the
    cohort's range is wide or bimodal, where the unconditional base rate hides a
    sharp winners-vs-losers split that a sub-cohort makes obvious.

    Stateless. No re-running of KNN. Reads from the 6-hour cohort_cache.

    Args:
        cohort_id: handle from a previous search / cohort / cohort_analyze
        where: filter dict. Each key is a fully-qualified attribute path,
            each value is one of: scalar (equality), list (IN), or
            {"min": X, "max": Y} (range). Supported keys include
            "macro.has_news", "macro.sector_etf", "technical.momentum_5d",
            "technical.pct_off_ath", "events.days_since_earnings",
            "events.days_to_earnings", plus point-in-time fundamentals:
            "fundamentals.net_margin", "fundamentals.roe",
            "fundamentals.debt_to_equity", "fundamentals.revenue_growth_yoy",
            "fundamentals.pe", "fundamentals.ps", etc. Call with no filter to
            see the full supported_filter_keys list in the response.
            Fundamentals are point-in-time (keyed on filing_date <= each
            member's date); non-filers (ETF/foreign/young) are excluded as
            'unknown' and reported in fundamentals_coverage. Revenue/earnings
            ratios (margins/pe/ps) are unreliable for financial-sector names —
            prefer roe / debt_to_equity / current_ratio there.
        horizon: forward-return horizon in trading days (1, 5, or 10)

    Returns subset_stats + full_cohort_stats + comparison block + an
    interpretation string templated from the magnitude of the delta. Use
    this to answer questions like:
      "Of the 300 NVDA analogs, how do the post-earnings-week ones do?"
      "Of the SPY cohort, what about just the low-VIX members?"
      "Compare the high-momentum subset to the full cohort."
    """
    try:
        body = {"cohort_id": cohort_id, "where": where or {}, "horizon": horizon}
        if _use_http():
            result = _http_post("/api/v1/cohort_introspect", body)
        else:
            return json.dumps(_attach_freshness({
                "status": "error", "data": {},
                "meta": {"warnings": ["cohort_introspect requires HTTP-backed MCP server"]},
            }), default=str, indent=2)
        result = _attach_freshness(result if isinstance(result, dict) else {"data": result})
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps(_attach_freshness({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}}), default=str, indent=2)


@mcp.tool(title="Cohort Members", annotations=READ_ONLY)
async def cohort_members(
    cohort_id: str,
    fields: str | None = None,
    sort_by: str | None = None,
    sort_desc: bool = False,
    limit: int | None = None,
    offset: int = 0,
) -> str:
    """Return the FULL cohort — one record per historical analog — for your own bucketing.

    The handover surface. Where cohort_analyze hands you OUR default
    calibrated distribution, cohort_members hands you the raw cohort so you
    can slice, sort, and bucket the analogs by YOUR objective. Given a
    cohort_id from a prior search / cohort_analyze call, returns every
    retrieved member with rich per-member metadata: forward outcomes,
    regime/macro state, anchor fundamentals, news presence, chart events.

    Stateless. Reads the stored cohort from the 6-hour cohort_cache — no
    re-running of KNN.

    Args:
        cohort_id: handle from a previous search / cohort_analyze
        fields: comma-separated metadata groups to include. Options:
            "outcomes" (forward returns), "regime", "anchor_meta", "news",
            "chart_events" — or "all" for everything. Default is
            "outcomes,regime". Pull only what you need to keep payloads small.
        sort_by: member field to sort by (e.g. "distance", "ret_5d",
            "momentum_5d", "relative_volume"). Default order is ascending
            distance (closest analog first).
        sort_desc: sort descending instead of ascending (default False)
        limit: max members to return (1–2000). Omit for the full cohort.
        offset: skip this many members, for pagination (default 0)

    Use this to drive customer-side analysis: pull the full cohort, then
    bucket it however you like — by sector, by your own volatility screen,
    by fundamentals you carry — instead of accepting our default lens.
    """
    try:
        if not _use_http():
            return json.dumps(_attach_freshness({
                "status": "error", "data": {},
                "meta": {"warnings": ["cohort_members requires HTTP-backed MCP server"]},
            }), default=str, indent=2)
        from urllib.parse import urlencode, quote
        params = {
            "fields": fields,
            "sort_by": sort_by,
            "sort_desc": "true" if sort_desc else "false",
            "limit": limit,
            "offset": offset,
        }
        qs = urlencode({k: v for k, v in params.items() if v is not None})
        result = _http_get(f"/api/v1/cohort/{quote(cohort_id, safe='')}/members?{qs}")
        result = _attach_freshness(result if isinstance(result, dict) else {"data": result})
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps(_attach_freshness({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}}), default=str, indent=2)


@mcp.tool(title="Cohort Group-By", annotations=READ_ONLY)
async def cohort_groupby(
    cohort_id: str,
    by: str,
    horizons: str | None = None,
    buckets: int = 4,
    min_group: int = 3,
) -> str:
    """Partition a stored cohort by one member dimension → per-bucket outcome distributions.

    The one-call "does this dimension matter?" primitive. Splits the
    cohort's analogs into groups along `by`, and for each group reports its
    forward-return distribution alongside the full-cohort baseline — so you
    can see which slice of the analogs drove the outcome. A categorical key
    groups by exact value; a numeric key is split into within-cohort
    quantile buckets. Same calibrated aggregator as the other cohort
    surfaces, so groups are directly comparable to baseline.

    Stateless. Reads the stored cohort from the 6-hour cohort_cache.

    Args:
        cohort_id: handle from a previous search / cohort_analyze
        by: the dimension to group by (REQUIRED). Categorical keys:
            "vol_regime", "sector_etf", "has_news", "broke_50d_high",
            "broke_50d_low", "broke_ath". Numeric keys (auto-bucketed):
            "distance", "vix", "ctx_vix_level", "ctx_spy_trend_20d",
            "relative_volume", "realized_vol_20d", "momentum_5d" /
            "momentum_20d" / "momentum_60d", "pct_off_ath", "sector_rs_60d",
            "market_rs_60d", "days_since_earnings", "days_to_earnings".
        horizons: comma-separated forward horizons to report (subset of
            "1,5,10"). Default is all three.
        buckets: number of quantile buckets for a numeric key (2–10,
            default 4). Ignored for categorical keys.
        min_group: groups smaller than this are suppressed (no stats) so
            thin buckets don't produce noise (1–100, default 3).

    Use this to ask "of these analogs, do the high-volume ones behave
    differently?" or "split the cohort by sector and show me each slice."
    """
    try:
        if not _use_http():
            return json.dumps(_attach_freshness({
                "status": "error", "data": {},
                "meta": {"warnings": ["cohort_groupby requires HTTP-backed MCP server"]},
            }), default=str, indent=2)
        from urllib.parse import urlencode, quote
        params = {
            "by": by,
            "horizons": horizons,
            "buckets": buckets,
            "min_group": min_group,
        }
        qs = urlencode({k: v for k, v in params.items() if v is not None})
        result = _http_get(f"/api/v1/cohort/{quote(cohort_id, safe='')}/groupby?{qs}")
        result = _attach_freshness(result if isinstance(result, dict) else {"data": result})
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps(_attach_freshness({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}}), default=str, indent=2)


@mcp.tool(title="Cohort Rerank", annotations=READ_ONLY)
async def cohort_rerank(
    cohort_id: str,
    by: str,
    limit: int | None = None,
    offset: int = 0,
) -> str:
    """Reorder a stored cohort by a weighted composite of member fields (YOUR objective).

    The "rank by what I care about" primitive. Instead of the default
    distance ordering, score every analog by a weighted within-cohort
    z-score composite of the numeric fields you name, and return the cohort
    in that order. This is how a caller imposes their own objective on the
    cohort — e.g. "favor the closest analogs that also had the highest
    forward return" — without us hard-coding that preference.

    Stateless. Reads the stored cohort from the 6-hour cohort_cache.

    Args:
        cohort_id: handle from a previous search / cohort_analyze
        by: comma-separated list of "field[:weight]" terms (REQUIRED). Each
            field is a numeric member field (e.g. "distance", "ret_5d",
            "relative_volume", "momentum_5d", "realized_vol_20d"). Weight
            defaults to 1.0; its SIGN sets direction — a POSITIVE weight
            favors high values, a NEGATIVE weight favors low values. So
            "ret_5d:1,distance:-0.5" ranks high-return, nearer analogs first.
        limit: max members to return after reranking (1–2000). Omit for all.
        offset: skip this many top-ranked members, for pagination (default 0)

    Each returned member carries its rerank_score and rerank_components
    (per-field contributions) so the ranking is fully auditable. It encodes
    the caller's objective, not a prediction.
    """
    try:
        if not _use_http():
            return json.dumps(_attach_freshness({
                "status": "error", "data": {},
                "meta": {"warnings": ["cohort_rerank requires HTTP-backed MCP server"]},
            }), default=str, indent=2)
        from urllib.parse import urlencode, quote
        params = {
            "by": by,
            "limit": limit,
            "offset": offset,
        }
        qs = urlencode({k: v for k, v in params.items() if v is not None})
        result = _http_get(f"/api/v1/cohort/{quote(cohort_id, safe='')}/rerank?{qs}")
        result = _attach_freshness(result if isinstance(result, dict) else {"data": result})
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps(_attach_freshness({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}}), default=str, indent=2)


@mcp.tool(title="Cohort Attribution", annotations=READ_ONLY)
async def cohort_attribution(
    cohort_id: str,
    side: str = "upside",
    horizon: int = 5,
    panel: str | None = None,
    date_floor: int = 30,
    n_boot: int = 1000,
    fdr_q: float = 0.10,
) -> str:
    """Within-cohort winner/loser attribution → which member traits separated the return tail from the rest.

    The "why did the rippers rip?" primitive. Splits the cohort's analogs
    into the forward-return TAIL (most-extreme decile-ish for upside, bottom
    for downside) versus everyone else, and reports which member traits
    (momentum, volatility, volume, distance-off-highs, regime, chart events)
    separated them — each with a by-DATE cluster-bootstrap confidence
    interval, a Benjamini-Hochberg false-discovery decision, and, when the
    anchor's own value is known, whether the anchor leans the tail's way.

    By-DATE deflated on purpose: the unit of evidence is a distinct DATE, not
    an analog, so a separation riding on a few clustered dates can't
    masquerade as broad. effective n is DISTINCT DATES. The tail cut is
    ADAPTIVE — it widens (10%→33%) only as far as needed to clear a
    distinct-date floor, and says "underpowered" out loud when even the widest
    cut can't.

    DESCRIPTIVE, never causal: "the tail disproportionately had X (CI excludes
    0)", never "X caused the move". The within-cohort companion to
    cohort_groupby — groupby asks "does THIS dimension matter?"; attribution
    scans the whole pre-specified panel and ranks what separated winners from
    the rest.

    Stateless. Reads the stored cohort from the 6-hour cohort_cache.

    Args:
        cohort_id: handle from a previous search / cohort_analyze
        side: "upside" (top-return tail = the rippers) or "downside" (bottom =
            the blow-ups). The tail is never discarded. Default "upside".
        horizon: forward horizon in trading days — one of 1, 5, 10. Default 5.
        panel: optional comma-separated feature subset to test. Defaults to a
            pre-specified anti-fishing panel. Valid names are the cohort_groupby
            keys (momentum_5d/20d/60d, pct_off_ath, relative_volume,
            realized_vol_20d, vix, sector_rs_60d, market_rs_60d,
            days_since_earnings, vol_regime, broke_50d_high, broke_ath,
            sector_etf, …).
        date_floor: min DISTINCT dates the tail needs before its CIs are
            trusted; the cut adapts to clear it (5–200, default 30).
        n_boot: by-date cluster-bootstrap resamples (200–5000, default 1000).
        fdr_q: Benjamini-Hochberg false-discovery rate across the panel
            (0.01–0.50, default 0.10).

    Use this after cohort_analyze to ask "of these analogs, what did the ones
    that ripped have in common — and does my anchor have it too?"
    """
    try:
        if not _use_http():
            return json.dumps(_attach_freshness({
                "status": "error", "data": {},
                "meta": {"warnings": ["cohort_attribution requires HTTP-backed MCP server"]},
            }), default=str, indent=2)
        from urllib.parse import urlencode, quote
        params = {
            "side": side,
            "horizon": horizon,
            "panel": panel,
            "date_floor": date_floor,
            "n_boot": n_boot,
            "fdr_q": fdr_q,
        }
        qs = urlencode({k: v for k, v in params.items() if v is not None})
        result = _http_get(f"/api/v1/cohort/{quote(cohort_id, safe='')}/attribution?{qs}")
        result = _attach_freshness(result if isinstance(result, dict) else {"data": result})
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps(_attach_freshness({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}}), default=str, indent=2)


@mcp.tool(title="Track Record (calibration receipts)", annotations=READ_ONLY)
async def track_record(
    vol_regime: str | None = None,
    tightness: str | None = None,
    horizon: str = "5d",
    verbosity: str = "summary",
) -> str:
    """Historical predicted-vs-realized coverage of our calibrated bands (a track record, not a forecast).

    The READ companion to the calibration that cohort_analyze APPLIES: it
    reports how often the realized return actually landed inside our nominal
    band across hundreds of thousands of prior cohort analyses. Everything is
    an audit of PAST outcomes — never a forward "we will be X% accurate" claim.

    Call with no args for the global receipt plus breakdowns by vol_regime and
    by tightness. Pass one slice arg for just that slice, or both for the
    (vol_regime x tightness) cell. When a slice has too few cases to trust, the
    receipt comes back flagged sufficient=false.

    Args:
        vol_regime: one of high | mid | low | unknown (volatility regime)
        tightness:  one of 1_loose | 2_mid | 3_firm | 4_tight (cohort tightness)
        horizon:    return horizon — "1d", "5d" (default), or "10d", whichever the
                    nightly builder has emitted. The response's available_horizons
                    lists exactly which are servable right now.

    Served from the nightly precomputed calibration map(s) — fast, no DB load.
    """
    try:
        if not _use_http():
            return json.dumps(_attach_freshness({
                "status": "error", "data": {},
                "meta": {"warnings": ["track_record requires HTTP-backed MCP server"]},
            }), default=str, indent=2)
        from urllib.parse import urlencode
        params = {
            "vol_regime": vol_regime,
            "tightness": tightness,
            "horizon": horizon,
            "verbosity": verbosity,
        }
        qs = urlencode({k: v for k, v in params.items() if v is not None})
        result = _http_get(f"/api/v1/calibration?{qs}")
        result = _attach_freshness(result if isinstance(result, dict) else {"data": result})
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps(_attach_freshness({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}}), default=str, indent=2)


@mcp.tool(title="Market Briefing", annotations=DEPRECATED_READ_ONLY)
async def market_briefing(
    n_movers: int = 10,
    n_setups: int = 5,
    n_catalysts: int = 5,
    horizon: int = 5,
) -> str:
    """One-call market synthesis — THE tool for 'what's going on?' questions.

    Combines five primitives into a single structured payload:
      • regime         — macro state (VIX, HY OAS) + one-line label
      • sectors        — top sector rotation (6 strongest + worst)
      • top_movers     — today's most-active price+volume movers from bar_metadata
      • top_setups     — highest cohort_score picks from the most recent scan
      • top_catalysts  — symbols with elevated narrative pulse today

    Use this for prompts like "what's going on in the market?", "find me
    interesting stocks today", "what's the tape?", "give me a quick market
    rundown." The agent renders the prose; everything quantitative is
    templated server-side from existing primitives (no fabrication).

    For drill-in on any symbol that surfaces, chain into cohort_analyze
    (historical analogs + forward-return distribution) or narrative_pulse
    (per-symbol news context).

    Args:
        n_movers: Max top movers to return (default 10, max 20)
        n_setups: Max scan picks to return (default 5, max 20)
        n_catalysts: Max news catalysts to return (default 5, max 20)
        horizon: Forward-return horizon for setup distributions (1, 5, or 10)
    """
    try:
        params = f"n_movers={n_movers}&n_setups={n_setups}&n_catalysts={n_catalysts}&horizon={horizon}"
        if _use_http():
            result = _http_get(f"/api/v1/market_briefing?{params}")
        else:
            return json.dumps(_attach_freshness({
                "status": "error", "data": {},
                "meta": {"warnings": ["market_briefing requires HTTP-backed MCP server"]},
            }), default=str, indent=2)
        result = _attach_freshness(result if isinstance(result, dict) else {"data": result})
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps(_attach_freshness({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}}), default=str, indent=2)


@mcp.tool(title="Market & Symbol Context", annotations=READ_ONLY)
async def context(target: str = "market", date: str | None = None) -> str:
    """Situational data about a target — ticker metadata, market regime, or DB coverage.

    target='NVDA'              → ticker metadata + sector + market cap
    target='NVDA', date=...    → ticker metadata PLUS point-in-time regime for that
                                 date (VIX/trend/vol/yield-curve/credit/earnings-distance
                                 ranks). The lightweight (symbol, date) anchor read — no
                                 kNN; use it to ask "what sector is this?", "what was the
                                 VIX percentile on date X?", "is this a mega-cap?".
    target='market'            → SPY/QQQ regime + sector rotation
    target='system'            → DB coverage stats (embeddings, daily_bars, date range)

    Replaces legacy: get_sector_rotation, get_status, anchor_fetch (the (symbol, date)
    metadata + point-in-time regime fetch — pass `date` for it).

    Response includes meta.freshness with as_of_db_date — the LLM should
    surface that explicitly when answering "how is X doing right now"
    style questions, because point-in-time regime fields are NULL until
    today's nightly ingest lands at ~21:00 UTC.

    Args:
        target: Ticker, 'market', or 'system' (default 'market')
        date: optional ISO date — only meaningful with a ticker target; adds the
            point-in-time regime ranks for that (symbol, date) (no kNN run)
    """
    try:
        # A ticker + date routes a {symbol, date} target so v2_context returns the
        # point-in-time regime (the old anchor_fetch behavior). 'market'/'system'
        # ignore date.
        tgt: str | dict = target
        if date and isinstance(target, str) and target.lower() not in ("market", "system"):
            tgt = {"symbol": target, "date": date}
        result = _dispatch(
            "/api/v2/context", "POST", _direct_v2_context,
            target=tgt,
        )
        result = _attach_freshness(result if isinstance(result, dict) else {"data": result})
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps(_attach_freshness({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}}), default=str, indent=2)


@mcp.tool(title="Explain Cohort", annotations=READ_ONLY)
async def explain(cohort_id: str, style: str = "filter_ranking", horizon: int = 5,
                  as_of_date: str = "") -> str:
    """Narrative + rankings for a stored cohort. Dispatched by `style=`.

    style values:
      - 'filter_ranking'    — rank candidate filters by how much each one shifts the
                              distribution at the given horizon. Use to discover conditional
                              structure before calling `cohort` with the winning filter.
      - 'prose'             — plain-English summary of the cohort outcome (Claude Haiku).
      - 'position_guidance' — exit-signal recommendation for an open position. Needs
                              extra_args in style-specific form: {side: 'long'|'short',
                              days_held: int}. Derives symbol+entry_date from the cohort anchor.
      - 'risk_ranking'      — today's risk-adjusted picks (Sharpe-like) from forward_tests.
                              LONG or SHORT — ranked by the magnitude of the expected move vs its
                              range (|predicted_5d|/range), so strong shorts interleave with strong
                              longs; read each pick's `side`. Score = risk/reward strength, NOT P(up).
                              Ignores cohort_id and horizon; pass `as_of_date` (YYYY-MM-DD) to pin
                              the scan date, or leave it '' for the latest scan.

    Replaces legacy: get_pattern_summary, explain_cohort_filters, get_exit_signal,
    get_risk_adjusted_picks.

    Args:
        cohort_id: Handle from `search` or `cohort` (required for filter_ranking/prose/position_guidance)
        style: 'filter_ranking' (default), 'prose', 'position_guidance', or 'risk_ranking'
        horizon: Forward horizon in trading days (default 5). NOT used by risk_ranking.
        as_of_date: only for risk_ranking — scan date YYYY-MM-DD ('' = latest). horizon means
                    forward-days on every other surface, so risk_ranking takes a DATE here instead
                    of overloading horizon (agent_feedback #15).
    """
    try:
        if style in ("filter_ranking", "prose"):
            result = _dispatch(
                "/api/v2/explain", "POST", _direct_v2_explain,
                cohort_id=cohort_id, style=style, horizon=horizon,
            )
            return json.dumps(result, default=str, indent=2)

        if style == "position_guidance":
            # Resolve symbol + entry_date from the cohort anchor
            from services.cohort import _cache_get
            stored = _cache_get(cohort_id)
            if stored is None:
                return json.dumps({
                    "status": "error", "data": {},
                    "meta": {"warnings": [f"unknown or expired cohort_id: {cohort_id}"]},
                })
            anchor = stored.get("anchor", {})
            symbol = anchor.get("symbol")
            entry_date = anchor.get("date")
            if not symbol or not entry_date:
                return json.dumps({
                    "status": "error", "data": {},
                    "meta": {"warnings": ["position_guidance needs cohort with symbol+date anchor"]},
                })
            # Inline call — legacy `get_exit_signal` wrapper was removed in
            # the 2026-05-26 v5 consolidation, but /api/v1/exit-signal is
            # still live.
            try:
                qs = (
                    f"symbol={symbol}&entry_date={entry_date}"
                    f"&side=long&days_held=0"
                )
                legacy_data = _http_get(f"/api/v1/exit-signal?{qs}")
            except Exception as exc:
                legacy_data = {"error": str(exc)}
            return json.dumps(_attach_freshness({
                "status": "ok" if "error" not in legacy_data else "error",
                "data": {"style": "position_guidance", **legacy_data},
                "meta": {"warnings": []},
            }), default=str, indent=2)

        if style == "risk_ranking":
            # Inline call — legacy `get_risk_adjusted_picks` wrapper was
            # removed in the 2026-05-26 v5 consolidation, but the underlying
            # HTTP endpoint /api/v1/risk-adjusted-picks is still live.
            from urllib.parse import quote
            _warns = []
            if horizon != 5:
                _warns.append("risk_ranking ignores `horizon` (it means forward-days "
                              "elsewhere) — use `as_of_date` to pin the scan date.")
            try:
                legacy_data = _http_get(
                    f"/api/v1/risk-adjusted-picks?date={quote(as_of_date or '', safe='')}&min_sharpe=0.3")
            except Exception as exc:
                legacy_data = {"error": str(exc)}
            return json.dumps(_attach_freshness({
                "status": "ok" if "error" not in legacy_data else "error",
                "data": {"style": "risk_ranking", **legacy_data},
                "meta": {"warnings": _warns},
            }), default=str, indent=2)

        return json.dumps({
            "status": "error", "data": {},
            "meta": {"warnings": [f"unknown style {style!r} — expected filter_ranking|prose|position_guidance|risk_ranking"]},
        })
    except Exception as e:
        return json.dumps({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}})


@mcp.tool(title="Portfolio Analysis", annotations=READ_ONLY)
async def portfolio(
    holdings: list,
    horizons: list | None = None,
    top_k_per_holding: int = 300,
    include_path_stats: bool = False,
) -> str:
    """Portfolio-level conditional distribution across holdings.

    Runs per-holding cohorts in parallel and weight-averages the distributions. Ranks
    tail contributors (weight × p10, most negative first). PM-agent primitive.

    Args:
        holdings: list of {symbol, weight, date} — weights normalized internally
        horizons: Forward horizons (default [5, 10])
        top_k_per_holding: Cohort size per holding (10-1000)
        include_path_stats: Include MAE/MFE (slower)
    """
    try:
        result = _dispatch(
            "/api/v2/portfolio", "POST", _direct_v2_portfolio,
            holdings=holdings, horizons=horizons,
            top_k_per_holding=top_k_per_holding,
            include_path_stats=include_path_stats,
        )
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "data": {}, "meta": {"warnings": [str(e)]}})


# ── Feedback ─────────────────────────────────────────────────

@mcp.tool(title="Report Feedback", annotations=WRITE)
async def report_feedback(message: str, endpoint: str = "", symbol: str = "", severity: str = "low") -> str:
    """Report an error or suggestion to the Chart Library team.

    Args:
        message: What happened? (e.g., "NVDA returned 0 matches, expected data")
        endpoint: Which endpoint had the issue (e.g., "/api/v1/intelligence/NVDA")
        symbol: Ticker symbol if relevant
        severity: "low", "medium", or "high"
    """
    try:
        if _use_http():
            import requests
            url = f"{_API_BASE}/api/v1/feedback"
            headers = {"Content-Type": "application/json"}
            if _API_KEY:
                headers["Authorization"] = f"Bearer {_API_KEY}"
            resp = requests.post(url, json={
                "message": message,
                "endpoint": endpoint,
                "symbol": symbol,
                "severity": severity,
                "agent_name": "mcp-server",
            }, headers=headers, timeout=10)
            return json.dumps(resp.json())
        else:
            return json.dumps({"status": "ok", "message": "Feedback logged locally (no API key set)"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# Legacy v3-era and v2_* prefixed wrappers were removed 2026-05-26 ahead
# of the Anthropic Connectors Directory submission, then the surface was
# consolidated 2026-05-29. The 21 registered tools above are 13 canonical
# (9 core + 3 cohort-handover + track_record) advertised on tools/list, plus
# 8 deprecated aliases that are registered/callable but hidden from the listing
# (see the surface filter below). Callers still using the legacy names
# (search_charts, get_cohort_distribution, v2_search, etc.) should
# migrate to the canonical surface — see chartlibrary.io/developers.
#
# 2026-06-01: removed the winning-vector tools (match_winning_vector,
# list_winning_vectors, get_cluster_signature) from the agent surface --
# they emitted directional long/short trade levels, conflicting with the
# similarity-not-returns principle. REST endpoints retained pending a
# website-usage review; this drops only the MCP tools agents can call.
#
# 2026-06-03: the deprecated aliases were HIDDEN from the advertised tools/list
# surface but stayed registered and callable by name (see _list_visible_tools
# below). Agents reliably ignore tools past ~7-9 in a selection menu, so every
# deprecated alias we advertised diluted selection of the canonical primitives.
# Hiding rather than deleting is an "announced sunset". See memory:
# mcp-surface-merit-review-2026-06-01.
#
# 2026-06-20 surface consolidation: (1) the three pull tools (pull_comps,
# pull_comps_now, pull_comps_live) were MERGED into one `pull_comps` that selects
# its data source from the args (stored / we-fetch-live via date='now' / your-own-
# bars via tail_bars|window_bars). (2) Five dead tools were DELETED from the MCP
# surface — narrative_pulse, narrative_alerts, discover_picks, similar_cohorts,
# cohort_compare — and `anchor_fetch` was folded into `context` (pass date= for the
# point-in-time regime). All the corresponding REST endpoints (/cohort_live,
# /anchor/comps, /narrative_*, /discover_picks, /similar_cohorts, /cohort_compare)
# remain live for back-compat — only the redundant MCP tool defs were removed. The
# only remaining hidden-but-callable deprecated aliases are `cohort` and
# `market_briefing`.


# ── Advertised surface filter ────────────────────────────────
# Hide deprecated tools from tools/list while keeping them dispatchable. This is
# safe because call routing is independent of what we advertise: CallToolRequest →
# FastMCP.call_tool → ToolManager.call_tool → get_tool(name) resolves against the
# full registry (mcp._tool_manager._tools), NOT the tools/list output. A hidden
# tool simply misses the low-level _tool_cache, which only gates optional input/
# output validation (already disabled via validate_input=False; our tools define
# no outputSchema) — never dispatch.
# Newly-added tools that are registered + callable by name but NOT yet
# advertised on tools/list — a deliberate "soft launch" pending a
# surface-promotion decision (the menu already holds 13; agents reliably
# ignore tools past ~7-9, so a new primitive earns its slot before we list
# it). Same hide mechanism as the deprecated aliases, opposite reason: not
# sunset, not-yet-listed. Promotion = drop the name here + add it to the
# canonical list. (cohort_attribution was unlisted during its Pillar B soft-launch, but
# suggested_next actively points agents at it — an unlisted-but-suggested tool reads as a
# phantom, 2026-06-16 external review. Promoted to the visible surface: if we suggest it,
# it must be discoverable.)
# micro_comps: hidden-but-callable until the eyeball verdict promotes it (2026-07-23)
# — the advertised surface is curated; existence != advertisement.
_UNLISTED_TOOLS = frozenset({"micro_comps"})


def _is_deprecated_tool(tool) -> bool:
    ann = getattr(tool, "annotations", None)
    return bool(ann is not None and getattr(ann, "deprecated", False))


async def _list_visible_tools():
    """A small default menu; all previous names still resolve through call_tool."""
    registered = await mcp.list_tools()
    if os.getenv("CHART_LIBRARY_MCP_PROFILE", "public").lower() == "advanced":
        return [
            t for t in registered
            if not _is_deprecated_tool(t) and t.name not in _UNLISTED_TOOLS
        ]
    by_name = {t.name: t for t in registered}
    return [by_name[name] for name in PUBLIC_TOOLS]


# Override FastMCP's default (list-everything) ListToolsRequest handler. Must run
# after all @mcp.tool registrations so mcp.list_tools() sees the full set.
mcp._mcp_server.list_tools()(_list_visible_tools)


# ── Entry point ──────────────────────────────────────────────

def main():
    """Entry point for `chartlibrary-mcp` console script and direct execution.

    Set MCP_TRANSPORT=streamable-http to run as a remote HTTP server
    (default: stdio for local MCP clients like Claude Desktop).
    """
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
