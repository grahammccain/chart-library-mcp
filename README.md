# Chart Library MCP Server

MCP server for [Chart Library](https://chartlibrary.io) — a visual chart pattern search engine. Find historically similar stock charts from 24M+ patterns across 15K+ symbols and 10 years of data. See what happened next.

## What it does

Given a stock ticker and date, Chart Library finds the 10 most similar historical chart patterns using ML embeddings (DINOv2-ViT-B/14) and pgvector similarity search. Returns forward returns (1/3/5/10 day), outcome distributions, and AI summaries.

## Tools

| Tool | Description |
|------|-------------|
| `analyze_pattern` | **Recommended** — complete analysis in one call: search + forward returns + AI summary |
| `search_charts` | Find similar historical chart patterns for a ticker + date |
| `search_batch` | Search multiple symbols at once (up to 20) |
| `get_follow_through` | Compute 1/3/5/10-day forward returns from matches |
| `get_pattern_summary` | AI-generated plain-English summary |
| `get_discover_picks` | Today's most interesting patterns from the daily scanner |
| `get_status` | Database stats: embeddings, symbols, date range |

## Install

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "chart-library": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "/path/to/chart-library-mcp"
    }
  }
}
```

### Claude Code (CLI)

```bash
claude mcp add chart-library -- python mcp_server.py
```

## Configuration

Set `CHART_LIBRARY_API_KEY` for higher rate limits (optional — free tier works without a key):

```bash
export CHART_LIBRARY_API_KEY=cl_your_key_here
```

Get a free key at [chartlibrary.io/developers](https://chartlibrary.io/developers).

## Example

```
User: "What does AAPL's chart from March 20 look like historically?"

Agent uses analyze_pattern("AAPL 2026-03-20"):
→ 10 matches found (JNJ, CVX, MSFT, TJX, RTX...)
→ 5-day forward: avg +0.39%, 6 of 10 went up
→ AI summary: "Based on 10 similar patterns, AAPL shows..."
```

## Links

- [chartlibrary.io](https://chartlibrary.io) — Live app
- [API docs](https://chartlibrary.io/developers)
- [OpenAPI spec](https://chartlibrary.io/api/openapi.json)
- [AI plugin manifest](https://chartlibrary.io/.well-known/ai-plugin.json)

## License

MIT
