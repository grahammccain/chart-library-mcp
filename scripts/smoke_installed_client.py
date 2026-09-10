"""Exercise an INSTALLED wheel through real MCP stdio, using a local read-only HTTP fixture."""
import asyncio
import importlib.metadata
import importlib.util
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

seen = []


class Fixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        status = 200
        payload = {"status": "ok", "data": {"fixture": True}, "meta": {"warnings": ["fixture, not market evidence"]}}
        if query.get("version") == ["0" * 64]:
            status, payload = 409, {"detail": "private-fixture-error"}
        elif query.get("offset") == ["5490"]:
            status, payload = 422, {"error": {"message": "offset is beyond this document"}}
        elif query.get("research_id") == ["study:absent"]:
            status, payload = 404, {"detail": "private-fixture-error"}
        elif query.get("research_id") == ["study:unsafe"]:
            status, payload = 422, {"detail": "private-fixture-error"}
        seen.append({"path": self.path, "authorization_present": "Authorization" in self.headers, "status": status})
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


async def run():
    assert importlib.util.find_spec("services") is None
    assert importlib.util.find_spec("db") is None
    server = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    env = dict(os.environ)
    env.pop("CHART_LIBRARY_API_KEY", None)
    env.pop("CHART_LIBRARY_MCP_PROFILE", None)
    env["PYTHON_DOTENV_DISABLED"] = "1"
    env["CHART_LIBRARY_API_URL"] = "http://127.0.0.1:" + str(server.server_port)
    params = StdioServerParameters(command=sys.executable, args=["-I", "-m", "mcp_server"], env=env)
    try:
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                initialized = await session.initialize()
                listed = await session.list_tools()
                names = [t.name for t in listed.tools]
                assert names == ["market_state", "daily_note", "research_quality", "search_research", "read_research"], names
                for name, arguments in [
                    ("market_state", {"symbol": "aapl", "date": "2026-09-04"}),
                    ("daily_note", {}),
                    ("research_quality", {}),
                    ("state_packet", {"symbol": "AAPL", "lane": "gap"}),
                    ("search_research", {"query": "IONQ & missing"}),
                    ("read_research", {"research_id": "casebook:ionq-noon", "section": "article"}),
                ]:
                    before = len(seen)
                    result = await session.call_tool(name, arguments)
                    assert not result.isError, result
                    payload = json.loads(next(part.text for part in result.content if part.type == "text"))
                    assert payload["data"]["fixture"] is True
                    assert result.structuredContent == {"result": next(part.text for part in result.content if part.type == "text")}
                    assert len(seen) == before + 1
                for arguments, status, word in [
                    ({"research_id": "study:100", "section": "result", "version": "0" * 64}, 409, "section=overview"),
                    ({"research_id": "study:100", "section": "result", "offset": 5490}, 422, "offset"),
                    ({"research_id": "study:absent"}, 404, "unavailable"),
                    ({"research_id": "study:unsafe"}, 422, "invalid"),
                ]:
                    before = len(seen)
                    result = await session.call_tool("read_research", arguments)
                    assert result.isError is True
                    text = next(part.text for part in result.content if part.type == "text")
                    payload = json.loads(text)
                    assert result.structuredContent == {"result": text}
                    assert payload["status"] == "error" and payload["data"] == {}
                    assert payload["meta"]["http_status"] == status
                    assert word in " ".join(payload["meta"]["warnings"]).lower()
                    assert "private-fixture" not in result.model_dump_json()
                    assert len(seen) == before + 1
                assert not any(r["authorization_present"] for r in seen)
                assert seen[0]["path"] == "/api/v1/state-packet?symbol=AAPL&date=2026-09-04"
                assert seen[1]["path"] == "/api/v1/daily"
                assert seen[2]["path"] == "/api/v1/calibration"
                assert "lane=gap" in seen[3]["path"]
                assert seen[4]["path"].startswith("/api/v1/research/search?query=IONQ+%26+missing")
                assert seen[5]["path"].startswith("/api/v1/research/read?research_id=casebook%3Aionq-noon")
                print(json.dumps({
                    "package": importlib.metadata.version("chartlibrary-mcp"),
                    "sdk": importlib.metadata.version("mcp"),
                    "tools": names,
                    "tool_list_bytes": len(listed.model_dump_json().encode()),
                    "instructions_bytes": len((initialized.instructions or "").encode()),
                    "http_calls": seen,
                    "hidden_legacy_dispatch": "passed",
                    "public_error_envelopes": "passed: 409, offset 422, missing 404, unknown 422 redaction",
                    "no_server_packages": True,
                }, indent=2))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


asyncio.run(run())
