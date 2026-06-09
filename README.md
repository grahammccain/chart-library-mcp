# Chart Library MCP Server
<!-- mcp-name: io.github.grahammccain/chart-library -->

[![PyPI](https://img.shields.io/pypi/v/chartlibrary-mcp)](https://pypi.org/project/chartlibrary-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Glama Score](https://img.shields.io/badge/Glama-A_A_A-brightgreen)](https://glama.ai/mcp/servers/@grahammccain/chart-library-mcp)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-listed-1f6feb)](https://registry.modelcontextprotocol.io/v0/servers?search=io.github.grahammccain/chart-library)
[![Tools](https://img.shields.io/badge/MCP_Tools-14_canonical-brightgreen)]()

**Works with:** Claude Desktop | Claude Code | ChatGPT | GitHub Copilot | Cursor | VS Code | Any MCP client

**Cohort intelligence engine for stock chart patterns** — give your AI agent the cohort of historical analogs, the full forward-return distribution, and the features that separated winners from losers. Calibrated, methodology-honest, no overstated confidence.

📖 [What is cohort intelligence?](https://chartlibrary.io/concepts/cohort-intelligence) · 🛠️ [Full MCP setup guide](https://chartlibrary.io/guides/mcp-server-for-finance) · 🤖 [Build an AI trading agent with Claude](https://chartlibrary.io/guides/build-ai-trading-agent-claude)

25M+ pattern embeddings. 10 years of history. 19K+ stocks. One tool call.

```
> "What does NVDA's chart on 2024-08-05 1h look like historically?"

NVDA · 2024-08-05 · 1h — cohort of 500 historical analogs
(485 with realized 5-day returns)

  Distribution at 5 days forward:
    median:        −1.3%
    p10 ·· p90:    −11.3% ·· +6.8%   (80% empirical band)
    win rate:      44%
    cohort_score:  0.31 (modest)

  Features that separated winners from losers:
    + credit_spread_state = tight
    + macro_state = bullish
    + pct_off_52w_low (further off)
    − vol_regime = low

  Summary: NVDA's 1-hour pattern on 2024-08-05 has 500 historical
  analogs. The cohort's 5-day distribution is bearish-leaning
  (median −1.3%, win rate 44%) — the historical record does NOT
  show this pattern typically resolving bullish. Conditioning on
  tight credit spreads and a bullish macro state would have
  separated the outperformers within the cohort.
```

A retrieval, not a forecast. No hallucinated predictions. No cherry-picking. Just the empirical record your agent can cite.

---

## Quick Start

```bash
pip install chartlibrary-mcp
```

### Claude Desktop (One-Click Install)
Download the [chart-library-6.1.0.mcpb](https://github.com/grahammccain/chart-library-mcp/raw/master/chart-library-6.1.0.mcpb) extension file and open it with Claude Desktop for automatic installation.

### Claude Code
```bash
claude mcp add chart-library -- chartlibrary-mcp
```

### Claude Desktop (Manual)
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "chart-library": {
      "command": "chartlibrary-mcp",
      "env": {
        "CHART_LIBRARY_API_KEY": "cl_your_key"
      }
    }
  }
}
```

### Cursor / VS Code
Add to `.cursor/mcp.json` or VS Code MCP settings:
```json
{
  "servers": {
    "chart-library": {
      "command": "chartlibrary-mcp",
      "env": {
        "CHART_LIBRARY_API_KEY": "cl_your_key"
      }
    }
  }
}
```

### GitHub Copilot (VS Code)
Add to `.vscode/mcp.json` in your project (this file is already included in the chart-library repos):
```json
{
  "servers": {
    "chart-library": {
      "command": "chartlibrary-mcp",
      "env": {
        "CHART_LIBRARY_API_KEY": "cl_your_key"
      }
    }
  }
}
```
Copilot Chat will auto-detect the MCP server when you open the project. Use `@mcp` in Copilot Chat to invoke tools.

### ChatGPT (Developer Mode)
ChatGPT connects to MCP servers via remote HTTP endpoints. To set up:

1. **Enable Developer Mode**: Go to ChatGPT **Settings > Apps > Advanced settings > Developer mode** (requires Pro, Plus, Business, Enterprise, or Education plan)
2. **Create a connector**: In Settings > Connectors, click **Create** and enter:
   - **Name**: Chart Library
   - **Description**: Historical chart pattern search engine — 25M+ patterns across 19K+ stocks, 10 years of data
   - **URL**: `https://chartlibrary.io/mcp`
   - **Authentication**: No Authentication (or OAuth if using an API key)
3. **Use in conversations**: Select "Developer mode" from the Plus menu, choose the Chart Library app, and ask questions like "What does NVDA's chart look like historically?"

> **Note**: The remote endpoint at `https://chartlibrary.io/mcp` uses Streamable HTTP transport. If you need SSE fallback, use `https://chartlibrary.io/mcp/sse`.

### Remote MCP Endpoint
For any MCP client that supports remote HTTP connections:
```
https://chartlibrary.io/mcp
```
This endpoint supports both Streamable HTTP and SSE transports, no local installation required.

**Free tier: 200 calls/day, no credit card required.** Get an API key at [chartlibrary.io/developers](https://chartlibrary.io/developers) or use basic search without one.

---

## What Can Your Agent Do With This?

### "Should I be worried about my TSLA position?"

```
> search(query="TSLA")                              → cohort_id
> explain(cohort_id=..., style="position_guidance")

  Signal: HOLD
  Of the historical analogs to this setup, those that exited early
  avoided a drawdown 3/10 of the time; those that held gained a
  further +2.1% median over the next 5 days. No exit signal triggered
  — the cohort's record leans toward continuation, not reversal.
```

### "What sectors are rotating in right now?"

```
> context(target="market")

  Sector relative strength (30-day):
    Leaders:  XLK Technology +4.2% · XLY Cons. Disc. +3.1% · XLC Comm. +2.8%
    Laggards: XLU Utilities −1.4% · XLP Cons. Staples −2.1% · XLRE Real Estate −3.3%

  Regime: Risk-On (growth > defensives), SPY above 20d, VIX mid-band.
```

### "How does AMD behave when the broad tape is weak?"

```
> search(query="AMD 2024-06-18")                    → cohort_id
> cohort_groupby(cohort_id=..., by="ctx_spy_trend_20d")

  AMD's cohort, split by the SPY trend at each analog's date:
    SPY weak (bottom quartile):  median 5d −5.2%  ·  p10/p90 −11.4%/+1.1%  ·  18% positive
    SPY strong (top quartile):   median 5d +2.6%  ·  p10/p90 −3.1%/+8.4%   ·  61% positive

  A distribution conditioned on the tape — historical analogs, not a beta forecast.
```

---

## 14 Canonical Tools

Chart Library v6 exposes the same granular surface as the remote server at `chartlibrary.io/mcp` — so the pip package, the Claude connector, and the REST API all use the same tool names. The core loop is **search → pull_comps → cohort_introspect**. Chain tools via the `comp_set_id` / `cohort_id` handle for sub-second refinement without re-running kNN.

| Tool | What it does |
|------|-------------|
| `search` | Entry point. Find similar historical patterns for an anchor; returns a comp-set handle you can chain. `mode=` supports `text` (default), `live_bars` (raw OHLCV), `similar` (cohort-level neighbors). |
| `pull_comps` | **The flagship.** Pull the *comp set* for a subject `(symbol, date, timeframe)` — the historical analogs, what they did next, the **drivers** that separated the best outcomes, and our **coverage_record**. Front-of-house lexicon: `subject` · `comp_set_id` · `comp_count` · `comp_strength` · `match_quality` · `drivers` · `up_rate` · `conditions` (calm / normal / stressed). Same engine as `cohort_analyze` with the new vocabulary applied at the boundary. |
| `cohort_analyze` | Same engine as `pull_comps` under the **original field names** (`cohort_id`, `feature_importance`, `win_rate`, `vol_regime`, …). Kept callable verbatim for existing integrations; new ones should prefer `pull_comps`. |
| `cohort_introspect` | Slice/probe a stored comp set by ANY attribute (macro · technical · event) and get per-subset stats vs the full-cohort baseline. No kNN re-run. *"Of the 300 analogs, how do the post-earnings-week ones do?"* |
| `cohort_attribution` | Within-cohort winner/loser attribution — which member traits separated the forward-return tail from the rest, each with a by-date cluster-bootstrap CI and a false-discovery decision. Descriptive, never causal. |
| `track_record` | Historical predicted-vs-realized coverage of our calibrated bands (a track record, not a forecast). The nominal 80% band held 80.8% across 302,880 prior cases. |
| `symbol_intelligence` | Layer 5 memory — per-symbol feature reliability + achieved calibration across prior analyses. Ground a read in whether a feature has historically been reliable for this ticker. |
| `analyze` | Analytic metrics. `metric=` accepts `anomaly`, `volume_profile`, `crowding`, `correlation_shift`, `earnings_reaction`, `pattern_degradation`, `regime_accuracy`, `decompose` (slice winners vs losers), `clusters` (cohort-internal grouping). |
| `context` | Situational data. `target=` accepts `"market"`, a ticker symbol (`"NVDA"`), `{"symbol": ..., "date": ...}` for lightweight anchor metadata, or `"system"` for DB coverage. |
| `explain` | Narrative + rankings derived from a cohort. `style=` accepts `filter_ranking` (which filter shifts the distribution most), `prose` (plain-English summary), `position_guidance` (exit signals), `risk_ranking`. |
| `portfolio` | Multi-holding weighted conditional distribution. Runs per-holding cohorts in parallel, weight-averages the distributions, ranks tail contributors. |
| `report_feedback` | File an error or improvement suggestion back to the project. |

**Full-cohort handover** — hand the raw cohort back so you can bucket/sort by *your* objective, not our default lens:

| Tool | What it does |
|------|-------------|
| `cohort_members` | The full cohort, one record per analog, with rich per-member metadata (forward outcomes, regime, anchor fundamentals, news, chart events). Slice and bucket it yourself. |
| `cohort_groupby` | Partition the cohort by one dimension (`vol_regime`, `sector_etf`, `momentum_5d`, …) → per-bucket outcome distributions vs baseline. The one-call "does this dimension matter?" primitive. |
| `cohort_rerank` | Reorder the cohort by a weighted composite of member fields you name (e.g. `"ret_5d:1,distance:-0.5"`) — impose your objective on the analogs, fully auditable. |

These tools replace hallucinated "on average this pattern returns X%" with real conditional base rates. The full distinction — what they do and how to read responses — is documented at [/concepts/cohort-intelligence](https://chartlibrary.io/concepts/cohort-intelligence) and [/concepts/reading-a-cohort-response](https://chartlibrary.io/concepts/reading-a-cohort-response).

### Typical agent flow

```
1. search(query="NVDA 2024-06-18")                    → comp_set_id
2. pull_comps(symbol="NVDA", date="2024-06-18",
              filters={"vol_regime": ["high"]})
                                                       → comp set: distribution + drivers
3. cohort_introspect(cohort_id=...,
                     where={"events.days_since_earnings": {"max": 5}})
                                                       → how the post-earnings subset did
4. cohort_groupby(cohort_id=..., by="sector_etf")     → outcome split by sector
```

### Migrating from v5 (umbrella) / v4 / v3

v6 converges on the granular naming the live remote/connector surface already used. The v5 **umbrella** tools — `cohort` (`depth=`), `discover` (`mode=`), `narrative` (`mode=`), and `decision_brief` — are now **deprecated but still callable**, so existing code keeps working. `cohort(depth="full")` forwards to `cohort_analyze`. New agents should reach for the canonical tools above.

| v5 umbrella call (deprecated) | v6 canonical |
|--------|-------------|
| `cohort(depth="full", ...)` | `cohort_analyze(...)` |
| `cohort(depth="basic", cohort_id=...)` then slice | `cohort_introspect(cohort_id=..., where={...})` |
| `cohort(depth="compare", compare_with={...})` | `cohort_compare(...)` *(still callable)* |
| `portfolio(mode="symbol_intel", symbol=...)` | `symbol_intelligence(symbol=...)` |
| `discover(mode="picks" | "daily_setups")` | `discover_picks(...)` / `/api/v1/agent/setups` |
| `narrative(mode="pulse" | "alerts")` | `narrative_pulse(...)` / `narrative_alerts(...)` *(still callable)* |

The v4-era granular aliases (`cohort_compare`, `decompose`, `clusters`, `live_search`, `similar_cohorts`, `anchor_fetch`, `narrative_pulse`, `narrative_alerts`, `discover_picks`, `get_daily_setups`) remain deprecated-but-callable and forward to the canonical surface.

The v3-era tools (`search_charts`, `get_cohort_distribution`, `analyze_pattern`, etc.) were removed in v5. If your code still calls them, pin `chartlibrary-mcp<5.0.0` until you migrate. The mapping:

| Legacy (removed in v5) | Replacement |
|--------|-------------|
| `search_charts`, `search_batch`, `get_discover_picks` | `search` |
| `get_cohort_distribution`, `refine_cohort_with_filters`, `run_scenario`, `get_regime_win_rates`, `compare_to_peers` | `cohort_analyze` (+ `cohort_introspect` to refine) |
| `detect_anomaly`, `get_volume_profile`, `get_crowding`, `get_earnings_reaction`, `get_correlation_shift`, `get_pattern_degradation`, `get_regime_accuracy` | `analyze` (`metric=`) |
| `get_sector_rotation`, `get_status`, `get_market_context` | `context` |
| `get_pattern_summary`, `explain_cohort_filters`, `get_exit_signal`, `get_risk_adjusted_picks` | `explain` (`style=`) |
| `get_portfolio_health` | `portfolio` |
| `analyze_pattern`, `get_follow_through`, `check_ticker` | `search` + `cohort_analyze` |

---

## How It Works

Chart Library indexes a large library of historical chart patterns and exposes them behind a conditional-distribution API. Every query returns sample sizes, percentiles, and calibrated forward-return bands — never a point forecast.

When your agent calls `search("NVDA")` and chains `cohort_analyze`, the server:
1. Resolves NVDA's current chart state to a stored embedding
2. Retrieves the cohort of historically similar patterns
3. Looks up what happened over the following 1, 3, 5, and 10 days
4. Returns the calibrated distribution + a plain-English summary via Claude Haiku

The result: factual, citation-ready statements like *"out of N similar historical patterns, the median 5-day return was X% (80% band [p10, p90])"* that your agent can present without hallucinating or hedging.

---

## API Key

| Tier | Calls/day | Price |
|------|-----------|-------|
| Sandbox | 200 | Free |
| Builder | 5,000 | $29/mo |
| Scale | 50,000 | $99/mo |

Get your key at [chartlibrary.io/developers](https://chartlibrary.io/developers).

```bash
export CHART_LIBRARY_API_KEY=cl_your_key
```

---

## Links

- [Website](https://chartlibrary.io)
- [API Documentation](https://chartlibrary.io/api/docs)
- [Developer Portal](https://chartlibrary.io/developers)
- [Regime Tracker](https://chartlibrary.io/regime)
- [Python SDK](https://pypi.org/project/chartlibrary/) | [JavaScript SDK](https://www.npmjs.com/package/chartlibrary)

---

## Privacy Policy

Chart Library's privacy policy is published at [chartlibrary.io/privacy](https://chartlibrary.io/privacy) and covers:

- **What we collect**: account info (email when you create an account), usage data (search queries, features used), and device information (browser, OS, IP). API queries are stored for service operation and analytics.
- **How we use it**: providing and improving the service, processing your searches, communicating about your account, and analyzing usage patterns.
- **Data sharing**: we do not sell personal data. Operational service providers (hosting, analytics, payment processing) receive only what's necessary to provide the service.
- **Third-party services**: queries may be processed by upstream providers (Polygon.io for market data, Anthropic for narrative summaries) under their own privacy policies.
- **Retention**: account info while your account is active; usage data is anonymized or deleted periodically. You can request deletion at any time.
- **Security**: encryption in transit and at rest. No method of transmission is 100% secure.
- **California rights (CCPA)**: right to know, right to delete, right to opt-out, non-discrimination.
- **Contact**: support@chartlibrary.io for any privacy inquiry.

The MCP server itself sends only the arguments of your tool calls to `chartlibrary.io` (no local file or directory contents, no clipboard, no browser history). Your `CHART_LIBRARY_API_KEY` is sent only as a Bearer header to authenticate with the chart-library API.

---

## Security

- **Transport**: all calls to the remote API are HTTPS (TLS 1.2+).
- **Authentication**: optional API key passed as a Bearer header; the free Sandbox tier requires no key.
- **No write access** to your environment, files, or other accounts. The single MCP tool that performs a write (`report_feedback`) only writes back to chart-library's own feedback inbox and never touches your system.

Report security issues to support@chartlibrary.io.

---

## License

MIT. See [LICENSE](LICENSE).

---

*Chart Library provides historical pattern data for informational purposes. Not financial advice.*

<!-- mcp-name: io.github.grahammccain/chart-library -->
