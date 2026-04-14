# Chart Library MCP Server
<!-- mcp-name: io.github.grahammccain/chart-library -->

[![PyPI](https://img.shields.io/pypi/v/chartlibrary-mcp)](https://pypi.org/project/chartlibrary-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Glama Score](https://img.shields.io/badge/Glama-A_A_A-brightgreen)](https://glama.ai/mcp/servers/@grahammccain/chart-library-mcp)
[![Tools](https://img.shields.io/badge/MCP_Tools-22-orange)]()

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

## 22 Tools

### Conditional Distribution (3 tools — the primitive)
| Tool | What it does |
|------|-------------|
| `get_cohort_distribution` | Return/MAE/MFE/realized-vol percentiles for a chart pattern, filtered by regime/sector/liquidity. One call, one distribution, with sample size + survivorship flag. **The tool every stock-research agent should call.** |
| `refine_cohort_with_filters` | Narrow a stored cohort with extra filters. Sub-second — no kNN re-run — so agents can fork and compare branches cheaply. |
| `explain_cohort_filters` | Rank which additional filter would shift the distribution most for a stored cohort. The edge-mining discovery step. |

These three tools replace hallucinated "on average this pattern returns X%" with real conditional base rates. See the [grounded-base-rates pattern](https://chartlibrary.io/blog/how-to-build-a-stock-agent-that-doesnt-hallucinate) for the full loop.

### Core Search (7 tools)
| Tool | What it does |
|------|-------------|
| `analyze_pattern` | Full analysis in one call: search + returns + AI summary |
| `search_charts` | Find the 10 most similar historical patterns for any ticker |
| `get_follow_through` | 1/3/5/10-day forward returns from matches |
| `get_pattern_summary` | Plain-English AI summary of pattern implications |
| `get_discover_picks` | Today's top patterns ranked by interest score |
| `search_batch` | Analyze up to 20 symbols in parallel |
| `get_status` | Database coverage and health stats |

### Market Intelligence (7 tools)
| Tool | What it does |
|------|-------------|
| `detect_anomaly` | Is this pattern unusual vs the stock's own history? |
| `get_volume_profile` | Intraday volume breakdown vs historical norms |
| `get_sector_rotation` | Sector leadership rankings with regime classification |
| `get_crowding` | Signal crowding: are too many stocks pointing the same way? |
| `get_earnings_reaction` | How has this stock historically reacted to earnings? |
| `get_correlation_shift` | Stocks breaking from their usual SPY correlation |
| `run_scenario` | Conditional returns: "what if the market does X?" |

### Trading Intelligence (4 tools)
| Tool | What it does |
|------|-------------|
| `get_regime_win_rates` | Win rates filtered by current VIX/yield regime |
| `get_pattern_degradation` | Are signals losing edge vs historical accuracy? |
| `get_exit_signal` | Should you hold or exit based on pattern data? |
| `get_risk_adjusted_picks` | Sharpe-ranked picks from today's pattern scan |

### Utility (1 tool)
| Tool | What it does |
|------|-------------|
| `report_feedback` | Report errors or suggest improvements |

---

## How It Works

Chart Library uses **24 million pre-computed pattern embeddings** (multi-channel numerical encodings of price, volume, volatility, and VWAP) indexed with **pgvector** for sub-10ms similarity search.

When your agent calls `analyze_pattern("NVDA")`, the server:
1. Computes NVDA's current embedding from the latest market data
2. Finds the 10 nearest neighbors by L2 distance across all stocks and dates
3. Looks up what happened 1, 3, 5, and 10 days after each historical match
4. Generates a plain-English summary via Claude Haiku

The result: factual, citation-ready statements like *"8 of 10 similar patterns gained over 5 days"* that your agent can present without hallucinating or hedging.

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
