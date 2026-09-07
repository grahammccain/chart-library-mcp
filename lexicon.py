"""lexicon — the front-of-house rename, applied at the boundary ONLY.

The 2026-06-09 naming rethink locked an institutional lexicon (Comp Set /
The Subject / Coverage Record / Drivers / comp_strength / Conditions). The
blast-radius study's verdict: decouple display ⟂ contract ⟂ storage — emit
the new vocabulary at the serialization boundary and NEVER rename internals
or stored values. In particular (the #1 landmine): data/calibration_map.json
and calibration_theta_online are KEYED on the literal vol_regime value
strings ("high", "high|1_loose") — renaming values in storage would silently
no-op every calibration lookup and quietly degrade the 80.8%/302,880 receipt.
This module is the whole Wave-2 keystone: a pure, recursive key-remap +
display-value map. Internals keep speaking cohort/anchor/vol_regime; the
new `pull_comps` surface speaks comps.

Forbidden-word note: comp_strength replaces cohort_score/"conviction"
(conviction implies WE hold a directional view; we never do).
"""
from __future__ import annotations

from typing import Any

# Back-of-house key -> front-of-house key. Applied recursively to response
# payloads at the boundary. Storage, params, and internal field names are
# NEVER touched by this map.
KEY_MAP: dict[str, str] = {
    "anchor": "subject",
    "corrected_anchor": "corrected_subject",
    "cohort_id": "comp_set_id",
    "cohort_size_actual": "comp_count",
    "cohort_score": "comp_strength",
    "combined_conviction": "comp_strength",
    "cohort_tightness_score": "match_quality",
    "cohort_tightness": "match_quality",
    "feature_importance": "drivers",
    "calibration": "coverage_record",
    # Effective-n disclosure (memory_at_scale_v1 §1.5): the coverage_record must surface the
    # honest sample size — distinct trading days and the design-effect-deflated effective_n —
    # alongside the raw row count, never a coverage number stripped of its independence.
    "calibration_n": "n_cases",
    "calibration_n_dates": "n_distinct_dates",
    "calibration_effective_n": "n_effective",
    "win_rate": "up_rate",
    "trimmed_mean": "typical",
    "vol_regime": "conditions",
    "anchor_vol_regime": "subject_conditions",
    "anchor_metadata": "subject_metadata",
    "cohort_anchors": "comp_members",
}

# vol_regime display values (DISPLAY tier only — storage keeps low/mid/high).
CONDITIONS_DISPLAY: dict[str, str] = {
    "low": "calm",
    "mid": "normal",
    "high": "stressed",
    "unknown": "unknown",
}

# Input-side acceptance for the new surface: subject -> anchor.
INPUT_KEY_MAP: dict[str, str] = {v: k for k, v in KEY_MAP.items()}


def to_front_of_house(payload: Any) -> Any:
    """Recursively remap keys (and vol_regime display values) on a response.

    Pure + defensive: unknown structures pass through untouched; never raises
    on ordinary JSON-shaped data. Old keys are REPLACED (this is only ever
    applied on the NEW pull_comps surface — cohort_analyze keeps the old
    contract verbatim, so nothing existing breaks)."""
    if isinstance(payload, dict):
        out = {}
        for k, v in payload.items():
            nk = KEY_MAP.get(k, k)
            nv = to_front_of_house(v)
            if k in ("vol_regime", "anchor_vol_regime") and isinstance(nv, str):
                nv = CONDITIONS_DISPLAY.get(nv.lower(), nv)
            out[nk] = nv
        return out
    if isinstance(payload, list):
        return [to_front_of_house(x) for x in payload]
    return payload


def subject_to_anchor(kwargs: dict) -> dict:
    """Accept new-vocabulary inputs on the new surface; map to internals.

    The response renames cohort_size_actual -> comp_count, so a client that reads
    comp_count and sends it back must be understood: until 2026-09-02 it was silently
    ignored (Pydantic dropped the unknown key) and the request fell back to the default
    cohort_size of 500 — the same anchor froze 500 comps through pull_comps and 300
    through cohort_analyze. Field-allowlist entries in front-of-house vocabulary
    (e.g. fields=["comp_members"]) are mapped back to internals for the same reason."""
    out = dict(kwargs)
    if "subject" in out and "anchor" not in out:
        out["anchor"] = out.pop("subject")
    if "comp_set_id" in out and "cohort_id" not in out:
        out["cohort_id"] = out.pop("comp_set_id")
    if "comp_count" in out and "cohort_size" not in out:
        out["cohort_size"] = out.pop("comp_count")
    fields = out.get("fields")
    if isinstance(fields, list):
        out["fields"] = [INPUT_KEY_MAP.get(f, f) if isinstance(f, str) else f for f in fields]
    return out
