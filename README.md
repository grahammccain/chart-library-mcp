# Chart Library MCP
<!-- mcp-name: io.github.grahammccain/chart-library -->

Free market-state research. One question, one call.

Version 6.2.0 introduces the same three-tool starting point as the hosted
service. Existing integrations retain their callable tool names.

## Three read-only tools

| Tool | Input | Result |
| --- | --- | --- |
| `market_state` | Symbol; optional date | Completed-session state, historical analogs, outcome ranges, transition memory and tape |
| `daily_note` | Optional date | Published daily research, selection rule and settled-note tally |
| `research_quality` | None | Published calibration receipt, dated sample and qualifications |

Each tool works independently. No preliminary search or cohort handle is needed.

Example question: “Read AAPL's latest completed-session state. Report the
historical analog ranges, sample sizes, session date and limitations.”

Omitting date uses the latest built/published session, not a real-time quote.
Dates use YYYY-MM-DD. Missing or thin evidence stays missing or thin.

## Connect

The primary remote endpoint is **https://chartlibrary.io/mcp**, using
Streamable HTTP and no authentication.

For a command-based client, install or upgrade the package:

```sh
python -m pip install --upgrade chartlibrary-mcp
```

Then use the equivalent of this configuration in your MCP client:

```json
{
  "mcpServers": {
    "chartlibrary": {
      "command": "chartlibrary-mcp"
    }
  }
}
```

No API key or server-side Python packages are required. An optional
`CHART_LIBRARY_API_KEY` is forwarded as a Bearer token when set. An empty key
does not send an Authorization header. `CHART_LIBRARY_API_URL` can select your
own compatible endpoint; only point it at a server you trust with that key.

Python 3.10+ is required. This release uses the MCP 1.x FastMCP interface and
pins `mcp>=1.28.1,<2.0.0`; MCP 2.x is a separate migration.

## The equivalent HTTP calls

```sh
curl "https://chartlibrary.io/api/v1/state-packet?symbol=AAPL"
curl "https://chartlibrary.io/api/v1/daily"
curl "https://chartlibrary.io/api/v1/calibration"
```

Use only the call relevant to the question. For a historical state add
`&date=YYYY-MM-DD`. Daily REST requests call the date parameter `session`.

## Read the evidence accurately

- Preserve dates, sample sizes, informative receipts, warnings and provenance.
- State-packet excess returns are percentage-point observations relative to a
  date-matched liquid-stock baseline. Each horizon has its own observed n.
- Raw historical percentiles are not automatically calibrated forecasts.
- `research_quality` audits only the method and population its receipt names.
  Do not transfer its coverage percentage to every market state or all research.
- Daily research has its own selection rule and settled-note tally.
- Historical frequencies are not recommendations to buy or sell.

Research access is free. Service limits and underlying data terms still apply.
Honor HTTP 429 and retry guidance; do not assume unlimited throughput.

## Existing integrations

Existing tool names stay registered and callable, including `pull_comps`,
`search`, `state_packet`, and the cohort inspection tools. To discover the
extended menu in a local client, set `CHART_LIBRARY_MCP_PROFILE=advanced`.
This changes discovery, not authorization or access to private research.

The public menu does not expose private fund operations or every experimental
state-memory method. Legacy examples in `examples/` use the advanced interface.

## Build with us

For a custom integration, a larger study, or a product built on the memory,
contact **Graham McCain — [graham@chartlibrary.io](mailto:graham@chartlibrary.io)**.

[Developer guide](https://chartlibrary.io/developers) ·
[Methodology](https://chartlibrary.io/methodology) ·
[Data terms](https://chartlibrary.io/data-licensing) ·
[Privacy](https://chartlibrary.io/privacy)

## Local verification

```sh
python -m pytest test_vendor_import.py
```

The import smoke runs without an API key and without application `services/`
or `db/` packages. No package or registry publication is performed by tests.
