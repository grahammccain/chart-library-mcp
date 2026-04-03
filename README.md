# Chart Library MCP Server

A compliance-safe way for AI agents to discuss stocks using real historical data.

Instead of hallucinating predictions or refusing to answer, your agent can say: "The last 10 times a chart looked like NVDA, 7 went up over 5 days (avg +3.1%)." This is factual historical data from 24 million pattern embeddings across 10 years and 15,000+ stocks — not financial advice, not predictions, just what happened before.

## Install

```bash
pip install chartlibrary-mcp
```

## Usage with Claude

```bash
# Claude Code
claude mcp add chart-library -- chartlibrary-mcp

# Or run directly
CHART_LIBRARY_API_KEY=cl_your_key chartlibrary-mcp
```

## Tools (19)

### Core Search
| Tool | Description |
|------|-------------|
| `analyze_pattern` | Search + forward returns + AI summary in one call (recommended) |
| `search_charts` | Find 10 most similar historical patterns |
| `get_follow_through` | Forward returns (1/3/5/10-day) for matches |
| `get_pattern_summary` | AI-generated plain-English summary |
| `get_discover_picks` | Daily top patterns ranked by interest score |
| `search_batch` | Multi-symbol parallel search (up to 20) |
| `get_status` | Database stats and coverage |

### Market Intelligence
| Tool | Description |
|------|-------------|
| `detect_anomaly` | Check if a stock's pattern is unusual vs history |
| `get_volume_profile` | Intraday volume breakdown vs historical average |
| `get_sector_rotation` | Which sectors are leading/lagging |
| `get_crowding` | Are too many stocks signaling the same direction? |
| `get_earnings_reaction` | Historical earnings gap reactions |
| `get_correlation_shift` | Stocks breaking from usual market correlation |
| `run_scenario` | What happens to a stock when the market moves X%? |

### Trading Intelligence
| Tool | Description |
|------|-------------|
| `get_regime_win_rates` | Pattern win rates filtered by current market regime |
| `get_pattern_degradation` | Are signals degrading vs historical accuracy? |
| `get_exit_signal` | Pattern-based exit recommendations for open positions |
| `get_risk_adjusted_picks` | Picks scored by Sharpe-like risk/reward ratio |

### Utility
| Tool | Description |
|------|-------------|
| `report_feedback` | Report errors or suggestions |

## Example Conversation

> **User:** What does NVDA's chart look like right now?
>
> **Claude (using Chart Library):** NVDA's current pattern matches 10 historical setups. The closest is AAPL from May 2016 (93% similarity). Of the 10 matches, 8 went up over 5 days with an average gain of +3.0%. The current market regime resembles the post-SVB period of early 2023, which historically resolved bullishly.

## API Key

Get a free API key (500 calls/day) at [chartlibrary.io/developers](https://chartlibrary.io/developers).

Set it as an environment variable:
```bash
export CHART_LIBRARY_API_KEY=cl_your_key
```

## Links

- Website: [chartlibrary.io](https://chartlibrary.io)
- API Docs: [chartlibrary.io/api/docs](https://chartlibrary.io/api/docs)
- Developer Portal: [chartlibrary.io/developers](https://chartlibrary.io/developers)
- Regime Tracker: [chartlibrary.io/regime](https://chartlibrary.io/regime)

<!-- mcp-name: io.github.grahammccain/chart-library -->
