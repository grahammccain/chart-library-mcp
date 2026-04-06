# Chart Library Integration Examples

Working code examples showing how to use Chart Library with popular AI agent frameworks.

## Prerequisites

All examples require a Chart Library API key. Get one free at [chartlibrary.io/developers](https://chartlibrary.io/developers).

```bash
export CHART_LIBRARY_KEY="your-api-key"
```

## Examples

### basic_api.py -- Python SDK (no MCP)

The simplest way to use Chart Library. Uses the `chartlibrary` Python SDK directly.

```bash
pip install chartlibrary
python basic_api.py
```

### langchain_agent.py -- LangChain ReAct Agent

A ReAct agent that uses Chart Library MCP tools for multi-step chart analysis.

```bash
pip install chartlibrary-mcp langchain-mcp-adapters langchain-openai langgraph
export OPENAI_API_KEY="your-openai-key"
python langchain_agent.py
```

### openai_agents.py -- OpenAI Agents SDK

An agent built with OpenAI's Agents SDK, connecting to Chart Library via MCP stdio.

```bash
pip install chartlibrary-mcp openai-agents
export OPENAI_API_KEY="your-openai-key"
python openai_agents.py
```

### crewai_agent.py -- CrewAI

A CrewAI crew with a Market Analyst agent that writes a data-driven morning report.

```bash
pip install chartlibrary-mcp crewai crewai-tools
export OPENAI_API_KEY="your-openai-key"
python crewai_agent.py
```

## Available MCP Tools

When connected via MCP, agents get access to 19 tools:

| Tool | Description |
|------|-------------|
| `search_charts` | Find similar historical chart patterns |
| `analyze_pattern` | Full analysis: search + follow-through + AI summary |
| `get_follow_through` | Forward returns from matched patterns |
| `get_pattern_summary` | AI-generated plain-English summary |
| `get_discover_picks` | Daily top pattern picks ranked by interest |
| `search_batch` | Search multiple symbols at once |
| `get_status` | API health and stats |
| `detect_anomaly` | Pattern anomaly detection |
| `get_volume_profile` | Intraday volume vs historical average |
| `get_sector_rotation` | Sector ETF relative strength rankings |
| `get_crowding` | Signal crowding indicator |
| `get_earnings_reaction` | Historical earnings gap reactions |
| `get_correlation_shift` | Stocks decorrelating from SPY |
| `run_scenario` | Conditional forward returns ("what if SPY drops 3%?") |
| `get_regime_win_rates` | Win rates adjusted for current market regime |
| `get_pattern_degradation` | Is a signal losing accuracy over time? |
| `get_exit_signal` | Pattern-based exit recommendations |
| `get_risk_adjusted_picks` | Sharpe-scored daily picks |
| `report_feedback` | Submit feedback or bug reports |

## Links

- [Chart Library](https://chartlibrary.io)
- [API Docs](https://chartlibrary.io/developers)
- [MCP Server on PyPI](https://pypi.org/project/chartlibrary-mcp/)
- [Python SDK on PyPI](https://pypi.org/project/chartlibrary/)
