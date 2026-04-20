# Chart Library MCP Server
<!-- mcp-name: io.github.grahammccain/chart-library -->

[![PyPI](https://img.shields.io/pypi/v/chartlibrary-mcp)](https://pypi.org/project/chartlibrary-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Glama Score](https://img.shields.io/badge/Glama-A_A_A-brightgreen)](https://glama.ai/mcp/servers/@grahammccain/chart-library-mcp)
[![Tools](https://img.shields.io/badge/MCP_Tools-8-orange)]()

**Works with:** Claude Desktop | Claude Code | ChatGPT | GitHub Copilot | Cursor | VS Code | Any MCP client

**Ask your AI agent "what happened the last 10 times a chart looked like this?" and get a real answer.**

24 million pattern embeddings. 10 years of history. 15,000+ stocks. One tool call.

```
> "What does NVDA's chart look like right now?"

Found 10 similar historical patterns for NVDA (2026-04-04, RTH timeframe):

  Closest match: AAPL 2023-05-12 (distance: 0.41)

  Forward returns across all 10 matches:
    1-day:  +0.8% avg  (7/10 positive)
    5-day:  +3.1% avg  (8/10 positive)
    10-day: +4.7% avg  (7/10 positive)

  Summary: NVDA's current consolidation near highs mirrors 10 historical
  setups, most notably AAPL's May 2023 pre-breakout pattern. 8 of 10
  resolved higher within a week, with a median 5-day gain of +2.8%.
```

No hallucinated predictions. No refusals. Just factual historical data your agent can cite.

---

## Quick Start

```bash
pip install chartlibrary-mcp
```

### Claude Desktop (One-Click Install)
Download the [chart-library-1.1.1.mcpb](https://github.com/grahammccain/chart-library-mcp/raw/master/chart-library-1.1.1.mcpb) extension file and open it with Claude Desktop for automatic installation.

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
   - **Description**: Historical chart pattern search engine -- 24M patterns, 10 years of data
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

Chart Library 2.0 consolidates 22 legacy tools into 8 composable primitives. Chain them via `cohort_id` handles for sub-second refinement without re-running kNN.

| Tool | What it does |
|------|-------------|
| `search` | Entry point. Returns `cohort_id` + anchor + n_matches for a ticker+date. Feed the handle into `cohort`, `analyze`, or `explain` to chain. |
| `cohort` | **The core primitive.** Conditional distribution (p10/p25/p50/p75/p90 + calibrated bands + MAE/MFE + hit rates + survivorship) for a chart pattern, filtered by regime/sector/liquidity/event. One call replaces the legacy `get_cohort_distribution`, `refine_cohort_with_filters`, `run_scenario`, and `get_regime_win_rates`. |
| `analyze` | Analytic metrics via `metric=` enum: `anomaly`, `volume_profile`, `crowding`, `correlation_shift`, `earnings_reaction`, `pattern_degradation`, `regime_accuracy`. |
| `context` | Situational data via `target=`: ticker metadata, market regime + sector rotation, or DB coverage stats. |
| `explain` | Narrative + rankings via `style=` enum: `filter_ranking` (which filter shifts the distribution most), `prose` (plain-English summary), `position_guidance` (exit signals), `risk_ranking` (Sharpe-ranked picks). |
| `portfolio` | Portfolio-level conditional distribution across holdings. Weight-averages distributions, ranks tail contributors. |
| `anchor_fetch` | **New in 2.0.** Lightweight (symbol, date) metadata fetch — sector, market cap, point-in-time regime. Avoids full kNN when you just need context for a ticker. |
| `report_feedback` | Report errors or suggest improvements. |

These tools replace hallucinated "on average this pattern returns X%" with real conditional base rates. See the [grounded-base-rates pattern](https://chartlibrary.io/blog/how-to-build-a-stock-agent-that-doesnt-hallucinate) for the full loop.

### Typical agent flow

```
1. search("NVDA 2024-06-18")                          → cohort_id
2. cohort(cohort_id=..., filters={regime:{same_vix_bucket: true}})
                                                       → conditional distribution
3. explain(cohort_id=..., style="filter_ranking")     → which filter matters most
4. cohort(cohort_id=..., filters={...new filter...})  → refined distribution
```

### Legacy tools (deprecated, still callable)

For backward compatibility, these 22 legacy tool names remain in place and are marked
`deprecated` in their MCP annotations. They forward to the canonical tool and will be
removed in a future major release. Migrate via the mapping below:

| Legacy | Replacement |
|--------|-------------|
| `search_charts`, `search_batch`, `get_discover_picks` | `search` |
| `get_cohort_distribution`, `refine_cohort_with_filters`, `run_scenario`, `get_regime_win_rates`, `compare_to_peers` | `cohort` |
| `detect_anomaly`, `get_volume_profile`, `get_crowding`, `get_earnings_reaction`, `get_correlation_shift`, `get_pattern_degradation`, `get_regime_accuracy` | `analyze` (metric=) |
| `get_sector_rotation`, `get_status`, `get_market_context` | `context` |
| `get_pattern_summary`, `explain_cohort_filters`, `get_exit_signal`, `get_risk_adjusted_picks` | `explain` (style=) |
| `get_portfolio_health` | `portfolio` |
| `analyze_pattern`, `get_follow_through`, `check_ticker` | `search` + `cohort` (+ optional `explain`) |

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

*Chart Library provides historical pattern data for informational purposes. Not financial advice.*

<!-- mcp-name: io.github.grahammccain/chart-library -->
