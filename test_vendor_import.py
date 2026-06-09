"""Vendored-package import smoke test.

The pip package (`chartlibrary-mcp`) ships a FLAT layout: mcp_server.py +
lexicon.py at the wheel root, with NO db/ or services/ packages. This test
proves the vendored mcp_server imports clean in that layout (all db.*/services.*
imports are call-time inside functions, gated on the direct-mode path that an
API key bypasses), that the canonical flagship + core tools are registered, and
that the lexicon fallback (`from lexicon import to_front_of_house`) resolves.
"""
import os

# Force HTTP mode (the package's real-world config) before importing the server,
# so module import never reaches a direct-mode db/services import path.
os.environ.setdefault("CHART_LIBRARY_API_KEY", "dummy")

import mcp_server  # noqa: E402


def _tool_names():
    return [t.name for t in mcp_server.mcp._tool_manager.list_tools()]


def test_flagship_and_core_tools_registered():
    names = _tool_names()
    assert "pull_comps" in names, names
    assert "cohort_analyze" in names, names
    # A few more of the canonical surface to be safe.
    for expected in ("search", "cohort_introspect", "track_record", "report_feedback"):
        assert expected in names, (expected, names)


def test_lexicon_vendored_import_resolves():
    # The pull_comps tool does `from lexicon import to_front_of_house` in the
    # flat/vendored layout. Prove that flat import works here.
    from lexicon import to_front_of_house
    out = to_front_of_house({"cohort_id": "abc", "win_rate": 0.6, "vol_regime": "high"})
    assert out["comp_set_id"] == "abc"
    assert out["up_rate"] == 0.6
    # vol_regime key is remapped to "conditions" AND its value display-mapped.
    assert out["conditions"] == "stressed"
