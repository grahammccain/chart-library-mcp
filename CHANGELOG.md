# Changelog

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
