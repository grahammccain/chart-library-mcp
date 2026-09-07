"""Flat-wheel smoke: no API key, services/ or db/ required."""
import asyncio
import json
import os
from pathlib import Path
import re
from unittest.mock import Mock

os.environ.pop("CHART_LIBRARY_API_KEY", None)
os.environ.pop("CHART_LIBRARY_MCP_PROFILE", None)

import mcp_server


def test_package_is_anonymous_http_by_default():
    assert mcp_server._use_http()
    assert not mcp_server._API_KEY


def test_public_menu_has_three_tools():
    names = [t.name for t in asyncio.run(mcp_server._list_visible_tools())]
    assert names == ["market_state", "daily_note", "research_quality"]


def test_legacy_names_stay_registered():
    names = {t.name for t in mcp_server.mcp._tool_manager.list_tools()}
    for expected in ("pull_comps", "cohort_analyze", "search", "cohort_introspect", "track_record", "state_packet"):
        assert expected in names


def test_keyless_tool_uses_http_not_server_imports(monkeypatch):
    read = Mock(return_value={"status": "ok", "data": {"symbol": "AAPL"}})
    monkeypatch.setattr(mcp_server, "_http_get", read)
    result = json.loads(asyncio.run(mcp_server.market_state("AAPL")))
    assert result["status"] == "ok"
    assert read.call_count == 1
    assert read.call_args.args[0] == "/api/v1/state-packet?symbol=AAPL"


def test_lexicon_vendored_import_resolves():
    from lexicon import to_front_of_house
    out = to_front_of_house({"cohort_id": "abc", "win_rate": 0.6, "vol_regime": "high"})
    assert out["comp_set_id"] == "abc"
    assert out["up_rate"] == 0.6
    assert out["conditions"] == "stressed"


def test_release_surfaces_have_matching_versions_and_public_tools():
    root = Path(__file__).parent
    version = re.search(r'^version = "([^"]+)"', (root / "pyproject.toml").read_text(), re.M).group(1)
    manifest = json.loads((root / "manifest.json").read_text())
    registry = json.loads((root / "server.json").read_text())
    smithery = (root / "smithery.yaml").read_text()
    assert manifest["version"] == registry["version"] == version
    assert registry["remotes"] == [{"type": "streamable-http", "url": "https://chartlibrary.io/mcp"}]
    assert all(package["version"] == version for package in registry["packages"])
    assert re.search(r'^version: (.+)$', smithery, re.M).group(1) == version
    assert re.findall(r'^  - name: (.+)$', smithery, re.M) == ["market_state", "daily_note", "research_quality"]
    requirements = (root / "requirements.txt").read_text().splitlines()
    assert "mcp>=1.28.1,<2.0.0" in requirements
    assert "python-dotenv>=1.0.0" in requirements
