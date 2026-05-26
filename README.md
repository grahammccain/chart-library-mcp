# Chart Library MCP Server
<!-- mcp-name: io.github.grahammccain/chart-library -->

[![PyPI](https://img.shields.io/pypi/v/chartlibrary-mcp)](https://pypi.org/project/chartlibrary-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Glama Score](https://img.shields.io/badge/Glama-A_A_A-brightgreen)](https://glama.ai/mcp/servers/@grahammccain/chart-library-mcp)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-listed-1f6feb)](https://registry.modelcontextprotocol.io/v0/servers?search=io.github.grahammccain/chart-library)
[![Tools](https://img.shields.io/badge/MCP_Tools-8_canonical-brightgreen)]()

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
Download the [chart-library-5.3.0.mcpb](https://github.com/grahammccain/chart-library-mcp/raw/master/chart-library-5.3.0.mcpb) extension file and open it with Claude Desktop for automatic installation.

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
> get_exit_signal("TSLA")

  Signal: HOLD (confidence: 72%)
  Similar patterns that exited early: 3/10 would have avoided a drawdown
  Similar patterns that held: 7/10 gained an additional +2.1% over 5 days
  Recommendation: Pattern suggests continuation. No exit signal triggered.
```

### "What sectors are rotating in right now?"

```
> get_sector_rotation()

  Leaders (30-day relative strength):
    1. XLK  Technology     +4.2%
    2. XLY  Cons. Disc.    +3.1%
    3. XLC  Communication  +2.8%

  Laggards:
    9. XLU  Utilities      -1.4%
   10. XLP  Cons. Staples  -2.1%
   11. XLRE Real Estate    -3.3%

  Regime: Risk-On (growth > defensives)
```

### "What happens to AMD if SPY drops 3%?"

```
> run_scenario("AMD", spy_change=-3.0)

  When SPY fell ~3%, AMD historically:
    Median move:  -5.2%
    Best case:    +1.1%
    Worst case:  -11.4%
    Positive:     18% of the time

  AMD shows 1.7x beta to SPY downside moves.
```

---

## 8 Canonical Tools

Chart Library v5 ships a clean 8-tool surface. Chain them via `cohort_id` handles for sub-second refinement without re-running kNN.

| Tool | What it does |
|------|-------------|
| `search` | Entry point. Find similar historical patterns for an anchor; returns a `cohort_id` you can chain. `mode=` supports `text` (default), `live_bars` (raw OHLCV), `similar` (cohort-level neighbors). |
| `cohort` | **The core primitive.** Conditional distribution analysis. `depth="basic"` returns kNN + outcome distribution; `depth="full"` adds Layer 3 feature importance + regime stratification + risk profile; `depth="compare"` pits two anchors side-by-side. Filters across regime / sector / liquidity / event. |
| `discover` | What's interesting today. `mode="picks"` (cohort-ranked top picks), `mode="daily_setups"` (pre-enriched briefs in one call), `mode="risk_adjusted"` (Sharpe-ranked). |
| `analyze` | Analytic metrics. `metric=` accepts `anomaly`, `volume_profile`, `crowding`, `correlation_shift`, `earnings_reaction`, `pattern_degradation`, `regime_accuracy`, `decompose` (slice winners vs losers), `clusters` (cohort-internal grouping). |
| `context` | Situational data. `target=` accepts `"market"`, a ticker symbol (`"NVDA"`), `{"symbol": ..., "date": ...}` for lightweight anchor metadata, or `"system"` for DB coverage. |
| `narrative` | News intelligence. `mode="pulse"` (single-symbol narrative-change score + FinBERT sentiment) or `mode="alerts"` (market-wide divergence anomalies). |
| `explain` | Narrative + rankings derived from a cohort. `style=` accepts `filter_ranking` (which filter shifts the distribution most), `prose` (plain-English summary), `position_guidance` (exit signals), `risk_ranking`. |
| `portfolio` | Multi-holding analysis OR per-symbol track record. `mode="basic"` (multi-holding weighted cohort) or `mode="symbol_intel"` (per-symbol Layer 5 memory). |

Plus `report_feedback` for filing errors / suggestions back to the project.

These tools replace hallucinated "on average this pattern returns X%" with real conditional base rates. The full distinction — what they do and how to read responses — is documented at [/concepts/cohort-intelligence](https://chartlibrary.io/concepts/cohort-intelligence) and [/concepts/reading-a-cohort-response](https://chartlibrary.io/concepts/reading-a-cohort-response).

### Typical agent flow

```
1. search(query="NVDA 2024-06-18")                    → cohort_id
2. cohort(symbol="NVDA", date="2024-06-18", depth="full",
          filters={"vol_regime": ["high"]})
                                                       → Layer 3 distribution + features
3. explain(cohort_id=..., style="filter_ranking")     → which filter matters most
4. cohort(symbol=..., date=..., depth="full",
          filters={...refined...})                    → re-conditioned distribution
```

### Migrating from v4 / v3 / v2

v5 reduces the surface from 19 active tools to 8 composite tools. Twelve previously-active tools (`cohort_analyze`, `cohort_compare`, `decompose`, `clusters`, `live_search`, `similar_cohorts`, `symbol_intelligence`, `anchor_fetch`, `narrative_pulse`, `narrative_alerts`, `discover_picks`, `get_daily_setups`) are retained as DEPRECATED wrappers that forward to the canonical tools — v4 callers keep working unchanged. New agents should reach for the 8 canonical tools.

The v3-era tools (`search_charts`, `get_cohort_distribution`, etc.) have been removed in v5. If your code still calls them, pin `chartlibrary-mcp<5.0.0` until you migrate to the canonical surface. The mapping:

| Legacy (removed in v5) | Replacement |
|--------|-------------|
| `search_charts`, `search_batch`, `get_discover_picks` | `search` / `discover` |
| `get_cohort_distribution`, `refine_cohort_with_filters`, `run_scenario`, `get_regime_win_rates`, `compare_to_peers` | `cohort` |
| `detect_anomaly`, `get_volume_profile`, `get_crowding`, `get_earnings_reaction`, `get_correlation_shift`, `get_pattern_degradation`, `get_regime_accuracy` | `analyze` (`metric=`) |
| `get_sector_rotation`, `get_status`, `get_market_context` | `context` |
| `get_pattern_summary`, `explain_cohort_filters`, `get_exit_signal`, `get_risk_adjusted_picks` | `explain` (`style=`) |
| `get_portfolio_health` | `portfolio` |
| `analyze_pattern`, `get_follow_through`, `check_ticker` | `search` + `cohort` (+ optional `explain`) |

| Previously active in v4 (now DEPRECATED in v5) | Replacement |
|--------|-------------|
| `cohort_analyze` | `cohort(depth="full")` |
| `cohort_compare` | `cohort(depth="compare", compare_with={...})` |
| `decompose`, `clusters` | `analyze(metric="decompose" | "clusters")` |
| `live_search`, `similar_cohorts` | `search(mode="live_bars" | "similar")` |
| `symbol_intelligence` | `portfolio(mode="symbol_intel")` |
| `anchor_fetch` | `context(target={"symbol": ..., "date": ...})` |
| `narrative_pulse`, `narrative_alerts` | `narrative(mode="pulse" | "alerts")` |
| `discover_picks`, `get_daily_setups` | `discover(mode="picks" | "daily_setups")` |

---

## How It Works

Chart Library indexes a large library of historical chart patterns and exposes them behind a conditional-distribution API. Every query returns sample sizes, percentiles, and calibrated forward-return bands — never a point forecast.

When your agent calls `analyze_pattern("NVDA")`, the server:
1. Builds a representation of NVDA's current chart state
2. Retrieves historically similar patterns
3. Looks up what happened over the following 1, 3, 5, and 10 days
4. Returns the distribution + a plain-English summary via Claude Haiku

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
