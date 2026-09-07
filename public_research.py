"""Small, shared public research catalog. Runtime compatibility routes stay separate."""
from copy import deepcopy
from datetime import date as _date
import re

CONTACT_EMAIL = "graham@chartlibrary.io"
PUBLIC_TOOLS = {
    "market_state": {
        "path": "/api/v1/state-packet",
        "parameters": ("symbol", "date"),
        "summary": "A market state, its historical analogs, and what followed",
        "description": (
            "Supply a stock symbol and optionally a completed session (YYYY-MM-DD). "
            "Omit date for the latest built session, not a real-time quote. Returns the "
            "state, tape, historical analog sample, outcome ranges, and the name's prior "
            "state transitions in one call. Preserve status, sample sizes, dates, and "
            "informative receipts. Excess-return ranges are empirical observations in "
            "percentage points relative to a date-matched liquid-stock baseline; they "
            "are not automatically calibrated forecasts. Empty or weak evidence is not "
            "a directional signal. Advanced lane options remain compatibility-only."
        ),
    },
    "daily_note": {
        "path": "/api/v1/daily",
        "parameters": ("session",),
        "summary": "The latest published daily research note",
        "description": (
            "No arguments needed. An optional session selects a published note by "
            "YYYY-MM-DD. Returns the note, its selection rule, available sessions, "
            "and the settled-note tally. A missing note or unsettled outcome is "
            "unavailable evidence, not zero. This is published research, not a stock-pick list."
        ),
    },
    "research_quality": {
        "path": "/api/v1/calibration",
        "parameters": (),
        "summary": "Published calibration evidence and its limitations",
        "description": (
            "No arguments needed. Returns the default five-session calibration receipt "
            "and its dated sample and qualifications. The receipt audits the calibrated "
            "cohort-band method and population named in the response. Do not apply its "
            "coverage percentage to raw market-state excess ranges, all research, or "
            "future returns. Daily-note results have their own tally in /api/v1/daily."
        ),
    },
}

MCP_INSTRUCTIONS = (
    "Chart Library is a free market-state research library. Three read-only tools, "
    "each useful on its own; no search handle or multi-tool chain is required.\n"
    "market_state(symbol, date?) gives a completed-session state, historical analogs, "
    "outcome ranges and transition memory in one call. Omit date for the latest built "
    "session; this does not mean real-time data.\n"
    "daily_note(date?) reads the published daily research, selection rule and settled tally.\n"
    "research_quality() reads the published calibration receipt. That receipt applies "
    "only to the method and population it names, not automatically to market_state's "
    "empirical excess-return ranges.\n"
    "Keep the response's dates, sample sizes, provenance, missing values, warnings and "
    "informative receipts. Historical frequencies are not buy/sell recommendations. "
    "Do not invent evidence or turn an empty or weak result into a confident claim.\n"
    "Research access is free; service limits and data terms apply. Existing advanced "
    "tools remain callable for compatibility but are not the public getting-started menu. "
    "For custom integrations, larger studies or building a product, contact Graham at "
    + CONTACT_EMAIL + " or https://chartlibrary.io/developers#build."
)

API_DESCRIPTION = (
    "Free market-state research. Three read-only requests, each useful on its own.\n\n"
    "## Try it\n"
    "`GET /api/v1/state-packet?symbol=AAPL` — no account, API key or preceding search required. "
    "Add `date=YYYY-MM-DD` to inspect a completed historical session. "
    "Omitting date uses the latest built session, not a real-time quote.\n\n"
    "## Read the evidence\n"
    "Keep dates, sample sizes, informative receipts, warnings and missing values. "
    "State-packet excess ranges are empirical historical observations, not automatically "
    "calibrated forecasts. The calibration receipt applies only to its named method "
    "and population. Daily research has its own settled-note tally.\n\n"
    "## Build with us\n"
    "Research is free; service limits and data terms apply. "
    "Existing integrations remain supported through their existing routes. "
    "For advanced workflows or a product integration, "
    "[contact Graham](mailto:" + CONTACT_EMAIL + ")."
)


def validate_session(value):
    """Accept a real ISO date only; do not silently slice timestamps or query strings."""
    if value is None:
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("date must be a completed session in YYYY-MM-DD format")
    try:
        _date.fromisoformat(value)
    except ValueError:
        raise ValueError("date must be a valid calendar date in YYYY-MM-DD format") from None
    return value


def validate_symbol(value):
    symbol = value.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-^]{0,19}", symbol):
        raise ValueError("symbol must be a stock ticker, for example AAPL or BRK.B")
    return symbol


def public_openapi(full_schema):
    """Project only the getting-started catalog; do not change route dispatch or auth.

    Drop unused components as well as paths: hiding paths alone leaves private
    request models and authentication requirements in the generated document.
    """
    schema = deepcopy(full_schema)
    paths = {}
    for name, entry in PUBLIC_TOOLS.items():
        source = full_schema.get("paths", {}).get(entry["path"], {}).get("get")
        if source is None:
            raise ValueError("Public research route is missing: " + entry["path"])
        operation = deepcopy(source)
        operation.update(
            operationId=name,
            summary=entry["summary"],
            description=entry["description"],
            tags=["Research"],
            security=[],
        )
        operation["parameters"] = [
            p for p in operation.get("parameters", [])
            if p.get("in") == "query" and p.get("name") in entry["parameters"]
        ]
        paths[entry["path"]] = {"get": operation}
    schema["paths"] = paths
    schema["tags"] = [{"name": "Research", "description": "Free, read-only research."}]
    schema.pop("security", None)
    components = full_schema.get("components", {})
    kept = {}
    visited = set()

    def retain_refs(node):
        if isinstance(node, dict):
            ref = node.get("$ref", "")
            if ref.startswith("#/components/") and ref not in visited:
                visited.add(ref)
                category, key = ref[len("#/components/"):].split("/", 1)
                value = components[category][key]
                kept.setdefault(category, {})[key] = deepcopy(value)
                retain_refs(value)
            for value in node.values():
                retain_refs(value)
        elif isinstance(node, list):
            for value in node:
                retain_refs(value)

    retain_refs(paths)
    schema["components"] = kept
    return schema


def discovery_manifest():
    return {
        "name": "Chart Library",
        "description": "Free market-state research. Three independent, read-only tools.",
        "url": "https://chartlibrary.io",
        "mcp_endpoint": "https://chartlibrary.io/mcp",
        "mcp_server": {
            "transport": "streamable-http",
            "transports": [{"type": "streamable-http", "url": "https://chartlibrary.io/mcp"}],
        },
        "tools_count": len(PUBLIC_TOOLS),
        "tools": [{"name": name, "description": item["summary"]}
                  for name, item in PUBLIC_TOOLS.items()],
        "authentication": {"required": False},
        "pricing": {"free_tier": "All public research; service limits apply.", "paid_tiers": []},
        "contact_email": CONTACT_EMAIL,
        "links": {
            "documentation": "https://chartlibrary.io/developers",
            "openapi": "https://chartlibrary.io/api/openapi.json",
            "github": "https://github.com/grahammccain/chart-library-mcp",
            "contact": "mailto:" + CONTACT_EMAIL,
        },
    }
