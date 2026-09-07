# Changelog

## 6.2.0 — Unreleased

- Three independent public tools: market_state, daily_note, research_quality.
- Previous tools remain registered; CHART_LIBRARY_MCP_PROFILE=advanced restores the extended menu.
- Anonymous installed clients use HTTP without importing server-only packages or sending Bearer None.
- Pin the supported MCP 1.x SDK and declare python-dotenv explicitly.
- Align discovery, setup instructions and historical-evidence qualifications with the hosted API.
- No PyPI, MCP Registry or desktop-bundle release has been made for this candidate.

## 6.1.0

**New flagship tool `pull_comps` + full surface sync with the deployed remote
server.** `pull_comps` pulls the *comp set* for a subject `(symbol, date,
timeframe)` — the historical analogs, what they did next, the **drivers** that
separated the best outcomes, and our **coverage_record** — under the
institutional front-of-house lexicon: `subject` · `comp_set_id` · `comp_count`
· `comp_strength` · `match_quality` · `drivers` · `coverage_record` · `up_rate`
· `conditions` (calm / normal / stressed). It's the same engine as
`cohort_analyze` with the new vocabulary applied at the response boundary only
(via a vendored `lexicon.py` remap) — **storage, params, and internal field
names are untouched**.

The canonical loop is now **search → pull_comps → cohort_introspect**.

**Nothing breaks for existing callers.** `cohort_analyze` keeps its original
field-name contract verbatim and stays callable — it's just hidden from
`tools/list` (Wave 2.5 discovery-tier deprecation) so fresh connector sessions
land on the single flagship instead of competing between two tools that return
different field names. All other legacy aliases (`cohort`, `market_briefing`,
`anchor_fetch`, `similar_cohorts`, `cohort_compare`, `narrative_pulse`,
`narrative_alerts`, `discover_picks`) remain registered and callable by name.

The advertised canonical surface is **14 tools**: `search`, `pull_comps`,
`cohort_introspect`, `symbol_intelligence`, `cohort_members`, `cohort_groupby`,
`cohort_rerank`, `cohort_attribution`, `track_record`, `analyze`, `context`,
`explain`, `portfolio`, `report_feedback`. This matches the surface deployed at
`chartlibrary.io/mcp`. News still never drives direction; FinBERT sentiment
enters only as a structural divergence/change signal.

## 6.0.1

**Deprecated aliases are now hidden from `tools/list` (still callable).** The
advertised surface is now exactly the canonical tools — `search`,
`cohort_analyze`, `cohort_introspect`, `symbol_intelligence`, `analyze`,
`context`, `explain`, `portfolio`, `report_feedback`, `track_record`, plus the
handover surface `cohort_members` · `cohort_groupby` · `cohort_rerank`. The v5
umbrella tools (`cohort`, `discover`, `narrative`, `decision_brief`) and the
v4-era granular aliases (`cohort_compare`, `decompose`, `clusters`,
`live_search`, `similar_cohorts`, `anchor_fetch`, `narrative_pulse`,
`narrative_alerts`, `discover_picks`, `get_daily_setups`) stay **registered and
callable by name** — only their advertisement on `tools/list` is suppressed.

**Why:** agents reliably ignore tools past ~7–9 in a selection menu, so
advertising the deprecated aliases diluted selection of the canonical
primitives. Hiding rather than deleting is an announced sunset: any existing
connector/OAuth client still calling a legacy name by hand keeps working. This
matches the surface deployed at `chartlibrary.io/mcp`.

## 6.0.0

**Converged on the remote granular canonical surface.** The pip package, the
Claude connector, and the REST API now advertise the same tool names. The
canonical surface is **9 tools** — the same ones the deployed remote server at
`chartlibrary.io/mcp` exposes:

```
search · cohort_analyze · cohort_introspect · symbol_intelligence ·
analyze · context · explain · portfolio · report_feedback
```

plus a full-cohort **handover surface** for bucketing/sorting the raw cohort by
your own objective:

```
cohort_members · cohort_groupby · cohort_rerank
```

The core loop is **search → cohort_analyze → cohort_introspect**.

**What changed for callers:**

- `cohort_analyze`, `cohort_introspect`, `symbol_intelligence` are now
  first-class canonical tools (previously `cohort_analyze` /
  `symbol_intelligence` were deprecated wrappers and `cohort_introspect` was
  remote-only).
- The v5 **umbrella** tools — `cohort` (depth=), `discover` (mode=),
  `narrative` (mode=), and `decision_brief` — are **demoted to
  deprecated-but-callable**. Nothing breaks: existing code calling
  `cohort(depth="full")`, `discover(mode="picks")`, etc. keeps working, but new
  agents are steered to the granular names. `cohort(depth="full")` now forwards
  to `cohort_analyze`.
- All v4-era granular aliases (`cohort_compare`, `decompose`, `clusters`,
  `live_search`, `similar_cohorts`, `anchor_fetch`, `narrative_pulse`,
  `narrative_alerts`, `discover_picks`, `get_daily_setups`) remain
  deprecated-but-callable.

**Why:** the package and the website guides had drifted onto the umbrella API
(`cohort(depth=...)`) while the live remote/connector surface was already
granular — so tutorial code mis-taught connector users. This release makes one
naming family the standard everywhere. News still never drives direction;
FinBERT sentiment enters only as a structural divergence/change signal.

## 5.2.0

**Outcome-mode playbook on `cohort` (depth=full).** New `include_modes`
and `n_modes` args expose the Layer B v1 mode-clustering surface — the
cohort isn't treated as one distribution, it's split into K distinct
"playbook" clusters by what historical analogs actually did next:

```
{
  "modes": [
    {
      "mode_id": 0,
      "label": "sharp downtrend -8.9%",
      "n": 8,
      "median_return": -0.112,
      "win_rate": 0.0,
      "std_return": 0.041,
      "p25_return": -0.142,
      "p75_return": -0.082,
      "centroid_cum_returns": [0.0, -0.021, -0.044, ..., -0.089]
    },
    {"mode_id": 1, "label": "downtrend -2.5%", ...},
    {"mode_id": 2, "label": "uptrend +3.9%", ...},
    {"mode_id": 3, "label": "smooth sideways", ...}
  ]
}
```

Modes are sorted ASC by median_return (mode_id=0 = worst realized
cluster). Use for "playbook" framing: instead of agents reporting
"median return +1.2%", they can describe the distinct paths the
cohort took ("most analogs drifted sideways, but 8 of 300 collapsed
sharply").

Algorithmic labels are derived from centroid slope (direction) +
within-mode bar-to-bar volatility (smoothness) + final-return
magnitude — no LLM in the loop, deterministic across reruns.

`include_modes` defaults to False — default response shape is unchanged.

## 5.1.0

**Conversation-grade outputs — agents stop sounding robotic.** `decision_brief` and `cohort` (depth=full) now return a deterministic `summary` block of classification flags. Agents read the flags first and paraphrase the framings in their own voice, instead of quoting a templated `primary_finding` or enumerating raw stats. The result is desk-style commentary that reads like a portfolio manager, not a research report.

The summary shape:

```
summary = {
  verdict_class:    bullish | lean_bull | coin_flip | lean_bear | bearish | broken,
  edge_class:       trivial | small | meaningful | large,
  regime_alignment: tailwind | neutral | headwind,
  sample_quality:   thin | ok | strong,
  conviction:       low | med | high,
  swing_factors:    [ { factor, direction, framing } ],
  caveat_flags:     [ thin_in_regime_sample, regime_was_derived, ... ],
}
```

Each `swing_factors[].framing` is a short layman phrase ("vol is the limiting factor — read improves if realized vol drops to mid bucket") that the agent paraphrases. Flags are deterministic rules over the existing stats — no LLM in the loop.

### Breaking changes

- **`decision_brief.decision_card` and `decision_brief.system_prompt_excerpt` are removed.** Those fields were "scripts" that pushed agents into quoted, robotic prose. The new `summary` block replaces them. Existing structured fields (`current_regime`, `in_current_regime`, `outside_current_regime`, `conditional_edge`, `thesis_invalidation_triggers`, `memory_context`, `narrative_context`, `conviction`) are unchanged. If your integration relied on `decision_card.primary_finding`, switch to reading `summary.verdict_class` + `summary.swing_factors` and let your agent narrate.

### Tool surface

`cohort` (depth=full) gains `summary` in its response when `include_anchor_metadata=True` (default).  Pass `fields=["summary"]` to slim the payload to just the classification block — useful when chaining and you only need the verdict.

## 5.0.4

**New `decision_brief` tool — output-first orchestrator.** One call that composes `cohort` (depth=full) + anchor context + `portfolio` (symbol_intel / Layer 5 memory) + `narrative` (pulse) into a single decision-grade response. Output schema intentionally forces *conditional* language: fields are named `in_current_regime` / `outside_current_regime` / `conditional_edge` instead of `predicted_return`. Returns a `system_prompt_excerpt` field the agent should quote verbatim rather than paraphrasing.

Use `decision_brief` as the DEFAULT first call for any (symbol, date) anchor question. The 8 existing canonical tools remain for power users composing their own flow.

Wraps `POST /api/v1/decision_brief`.

## 5.0.3

**Bug fix — `narrative` tool was broken in production.** The tool wrapped the wrong API paths since v5.0.0: `mode="alerts"` called `/api/v1/narrative-alerts` (hyphen) but the API endpoint is `/api/v1/narrative_alerts` (underscore). `mode="pulse"` called `/api/v1/narrative_pulse?symbol={X}` (query string) but the API takes the symbol as a path parameter (`/{symbol}`). Both calls returned HTTP 404 to the agent. Other 7 canonical tools were unaffected. Upgrade if you use `narrative`.

## 5.0.2

`discover(mode="daily_setups")` now accepts a `fields` parameter that pass-throughs to `/api/v1/agent/setups?fields=`. Pass `fields=["setups"]` to drop `yesterday_recap` when you only need today's picks. Same trim mechanism as `cohort(depth="full", fields=[...])`.

## 5.0.1

`cohort` now accepts a `fields` parameter (depth="full" only) — an allowlist of top-level response keys, mirroring the new `fields=` query param on `/api/v1/cohort_analyze`. Pass `fields=["outcome_distribution"]` to drop ~97% of the response bytes when you only need the core distribution. Always-on keys (`anchor`, `cohort_size_actual`, `elapsed_ms`, `warnings`) are returned regardless. Shipped same-day after a real evaluator asked for it during a backtest.

## 5.0.0

**Major surface cleanup.** The drift problem: between v3.0 and v3.5 the tool surface grew from 8 canonical tools to 19 active + 26 deprecated = 45 total tool decorators. The Anthropic-style guidance is that tool descriptions cost tokens on every turn and overlapping tools (`cohort` vs `cohort_analyze`, `narrative_pulse` vs `narrative_alerts`) hurt tool-selection accuracy. v5 cuts the active surface back to the 8 canonical that were always supposed to be the surface, with 12 deprecated wrappers retained for v4 backward compatibility.

### Breaking changes

- The 26 v3-era deprecated tools (`search_charts`, `get_cohort_distribution`, `refine_cohort_with_filters`, `analyze_pattern`, `get_follow_through`, `get_pattern_summary`, `get_status`, `compare_to_peers`, `get_discover_picks`, `search_batch`, `get_market_context`, `check_ticker`, `get_portfolio_health`, `get_regime_accuracy`, `detect_anomaly`, `get_volume_profile`, `get_sector_rotation`, `get_crowding`, `get_earnings_reaction`, `get_correlation_shift`, `run_scenario`, `get_regime_win_rates`, `get_pattern_degradation`, `get_exit_signal`, `get_risk_adjusted_picks`, `explain_cohort_filters`) have been **removed**. If your code still calls them, pin `chartlibrary-mcp<5.0.0` until you migrate.

### Active surface — 8 canonical tools

1. `search` — entry point. `mode=` supports `text` (default), `live_bars`, `similar`.
2. `cohort` — conditional distribution. `depth=` supports `basic`, `full` (Layer 3), `compare`.
3. `discover` — what's interesting today. `mode=` supports `picks`, `daily_setups`, `risk_adjusted`.
4. `analyze` — analytic metrics. `metric=` adds `decompose` and `clusters` to the existing set.
5. `context` — situational data. `target=` now accepts dict form for anchor metadata (subsumes `anchor_fetch`).
6. `narrative` — news intelligence. `mode=` supports `pulse`, `alerts` (subsumes `narrative_pulse`, `narrative_alerts`).
7. `explain` — narrative + rankings (unchanged).
8. `portfolio` — multi-holding OR per-symbol Layer 5 memory. `mode=` supports `basic`, `symbol_intel` (subsumes `symbol_intelligence`).

Plus `report_feedback` (utility WRITE; unchanged).

### Deprecated (still callable, will be removed in v6)

`cohort_analyze`, `cohort_compare`, `decompose`, `clusters`, `live_search`, `similar_cohorts`, `symbol_intelligence`, `anchor_fetch`, `narrative_pulse`, `narrative_alerts`, `discover_picks`, `get_daily_setups`. Each forwards to the canonical tool with the appropriate parameter routing.

### Why this matters

- LLMs read every tool description in the system prompt on every turn. 19 tool descriptions cost ~1,900 tokens per turn; 8 cost ~800.
- Tool-selection accuracy degrades with overlapping tools (`cohort` vs `cohort_analyze` — model picks wrong one or calls both). Composite tools with `mode=` / `depth=` parameters teach the model the parameter space once instead of N times.
- Maintenance: 8 well-described tool docstrings are tractable to keep high quality. 45 was not.

### Migration

Most v4 code keeps working — the 12 v4-era tools are now deprecated wrappers. v3-era code (the 26 names listed above) needs migration; the mapping table is in the README.

## 3.5.0

Positioning + documentation alignment. No tool / API surface changes — drop-in upgrade from 3.4.0.

### Changes

- **Description rewrite**: leads with "cohort intelligence engine for stock chart patterns" to align with the new chartlibrary.io positioning. PyPI page now matches the canonical concept terminology.
- **README rewrite**: header now says "Cohort intelligence engine" and links to three new explainer pages on chartlibrary.io:
  - `/concepts/cohort-intelligence` — canonical definition
  - `/guides/mcp-server-for-finance` — full setup guide with Claude Desktop + Cursor configs
  - `/guides/build-ai-trading-agent-claude` — end-to-end agent walkthrough

### Why upgrade

Same tools, same API, same behavior. Upgrade so your dependency declaration matches the canonical concept naming. No breaking changes.

## 3.4.0

Single-call agent surface — replaces the multi-call discovery dance with one tool.

### New tool

- **`get_daily_setups`** — top picks pre-enriched with full-cohort statistics, top-3 features, and yesterday's calibration recap, all in one response. Replaces the typical workflow of calling `discover_picks` + `cohort_analyze` × N + recap separately. Each setup includes both the original top-K nightly predictions and the full-cohort stats (n=300) so callers can spot when headline consensus diverges from broader-cohort signal. Cold response after deploy: ~30-60s while the API pre-warms; warm response: <50ms.

### Why this exists

Dogfood test on 2026-05-04 found that an agent assembling "tomorrow's brief" needed 5+ HTTP calls and ~118s to complete. With `get_daily_setups`, the same task is 2 calls and ~35s. 8× fewer tool uses, half the tokens.

### Server-side changes (chartlibrary.io)

- `/discover/picks` now filters to V5-coverage symbols. No more 422s from downstream `cohort_analyze` calls — every pick is end-to-end queryable.
- `n_matches` field documented as top-K (default 10), not full cohort. New `cohort_compatible` field on each pick.
- `/api/v1/agent/setups` endpoint cached 23h, pre-warmed at API startup for `(top=3, timeframe=1d)` so agents don't hit cold path.

## 3.3.0

News v2 — realtime narrative anomaly detection exposed as agent tools.

### New tools

- **`narrative_pulse`** — single-symbol realtime narrative pulse.
  Returns today's article count anomaly + sentiment tone shift vs the
  symbol's 30d baseline, plus the 5 most recent articles (title,
  sentiment, time, publisher, URL). Pipeline latency: ~5 min from
  publish to scored. Use this to detect catalyst-driven setups in
  real time and combine with `cohort_analyze` for the full
  setup-plus-catalyst signal.
- **`narrative_alerts`** — multi-symbol scan. Returns symbols above a
  pulse threshold sorted DESC. Useful for "what's narrative-anomalous
  across the market right now?"

### Behind the scenes (server-side)

- `cohort_analyze` response now includes `narrative_pulse`,
  `pulse_boost`, and `combined_conviction` = `cohort_score + 0.4 *
  pulse`, capped at 1.0. Setup signal + catalyst signal fused into a
  single conviction. `discover_picks` re-ranks by combined.
- News pipeline: 3-min Polygon polling, CPU FinBERT scoring inside
  the worker container (no GPU). Phase 3 endpoint `/api/v1/narrative_alerts`
  on prod since 2026-05-01.

## 3.2.0

Layer 5 continual-learning memory — every cohort_analyze call now compounds.

### New tools

- **`symbol_intelligence`** — per-symbol memory aggregated across prior
  cohort analyses: hit rate per horizon, feature reliability ranked by
  sign-alignment with realized returns, regime exposure histogram,
  achieved conformal coverage, recent observations.
- **`similar_cohorts`** — second-order retrieval. V5 finds chart shapes,
  this finds *analyses* with similar fingerprint (distribution moments +
  top feature importances + regime onehot + score components). Surfaces
  the "this looks like the time when..." question.
- **`cohort_compare`** — cross-anchor structural diff. Returns
  distribution moments, feature-importance overlap with sign-direction
  tagging (`direction_disagreement` is the most actionable structural
  difference), regime fingerprint deltas, side-by-side risk profile.
- **`discover_picks`** — daily-scan output ranked by `cohort_score`
  (composite signal strength: delta-from-base-rate × tightness ×
  cohort-size × feature-concentration).

### Behind the scenes

- Server-side `feature_importance` now auto-applies historically-learned
  reliability weights when `n ≥ 20` observations back the (feature,
  regime, horizon) triple. Each weighted feature carries its
  `reliability_sign_alignment` and `reliability_n` forward.
- `/api/v1/cohort_track_record` validates the system: current numbers
  show a +14-19pp top-vs-bottom quintile spread on directional hit rate
  — empirical evidence cohort_score is informative.

## 3.1.0

Add `cohort_analyze` — Layer 3 cohort intelligence tool.

### New tool

- **`cohort_analyze`** — V5 retrieval + Layer 2 metadata join. Given a
  `(symbol, date, timeframe)` anchor, returns:
  - outcome distribution per horizon (1d / 5d / 10d)
  - per-feature importance (logistic regression of features → win/loss)
  - regime stratification (sliced by `vol_regime`)
  - risk profile (drawdown / runup percentiles)
  - cohort tightness score
  - `narrative_change_score` — composite of frequency anomaly, tone shift,
    sentiment-price misalignment (priced-in vs narrative-change distinction)
- Filters on 13 metadata dimensions including news sentiment (FinBERT-scored
  on the full news_articles corpus)
- Same-symbol exclusion default 10 days (autocorrelation control)

Distinct from `cohort` (the v2-era distribution primitive). `cohort_analyze`
is the new North Star Layer 3 analyzer with rich Layer 2 metadata (market
state, news sentiment via FinBERT, sector RS, calendar context).

## 2.0.0

Major consolidation: 22 legacy tools → 8 canonical primitives.

### New canonical surface (8 tools)

- **`search`** — entry point; returns `cohort_id` + anchor + n_matches
- **`cohort`** — conditional distribution primitive; subsumes `get_cohort_distribution`,
  `refine_cohort_with_filters`, `run_scenario`, `get_regime_win_rates`, `compare_to_peers`
- **`analyze`** — dispatched via `metric=` enum (`anomaly`, `volume_profile`, `crowding`,
  `correlation_shift`, `earnings_reaction`, `pattern_degradation`, `regime_accuracy`)
- **`context`** — dispatched via `target=` (ticker, `market`, `system`); subsumes
  `get_sector_rotation`, `get_status`, `get_market_context`
- **`explain`** — dispatched via `style=` enum (`filter_ranking`, `prose`,
  `position_guidance`, `risk_ranking`); subsumes `get_pattern_summary`,
  `explain_cohort_filters`, `get_exit_signal`, `get_risk_adjusted_picks`
- **`portfolio`** — portfolio-level conditional distribution; subsumes `get_portfolio_health`
- **`anchor_fetch`** — **NEW.** Lightweight `(symbol, date)` metadata fetch (sector, cap,
  point-in-time regime) without running full kNN. Use when an agent just needs anchor
  context, not matches.
- **`report_feedback`** — unchanged

### Deprecations

All 22 legacy tools remain callable but are now marked `deprecated` in their MCP
`ToolAnnotations` and prefixed with `[DEPRECATED - use X]` in their descriptions.
Agents should migrate to the canonical surface; legacy tools will be removed in a
future major release.

Legacy → canonical mapping:

| Legacy | Canonical |
|--------|-----------|
| `search_charts`, `search_batch`, `get_discover_picks` | `search` |
| `get_cohort_distribution`, `refine_cohort_with_filters`, `run_scenario`, `get_regime_win_rates`, `compare_to_peers` | `cohort` |
| `detect_anomaly`, `get_volume_profile`, `get_crowding`, `get_earnings_reaction`, `get_correlation_shift`, `get_pattern_degradation`, `get_regime_accuracy` | `analyze` (metric=) |
| `get_sector_rotation`, `get_status`, `get_market_context` | `context` |
| `get_pattern_summary`, `explain_cohort_filters`, `get_exit_signal`, `get_risk_adjusted_picks` | `explain` (style=) |
| `get_portfolio_health` | `portfolio` |
| `analyze_pattern`, `get_follow_through`, `check_ticker` | `search` + `cohort` (+ optional `explain`) |

### Internal

- User-Agent bumped to `chartlibrary-mcp/2.0.0`
- pip package is now a thin HTTP client — no direct DB imports (was already the case
  for the pip build; clarified in docstring)

---

## 1.4.1

Conformal-calibrated quantile bands on `get_cohort_distribution`. Raw p10/p90 runs at
~68% empirical coverage vs 80% nominal; `calibrated_return_pct` is split-conformal
adjusted and hits ~82.5% on held-out anchors.

Added 7 regime filters to `get_cohort_distribution` and `refine_cohort_with_filters`:
VIX bucket, SPY trend, variance risk premium, VIX term structure, credit spread,
yield curve, market breadth.

## 1.1.x

Initial public release. 22 tools covering pattern search, market intelligence,
trading intelligence, and utility. `get_cohort_distribution` introduced as the
primary agent primitive.
