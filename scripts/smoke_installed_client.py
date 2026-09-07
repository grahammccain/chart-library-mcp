"""Exercise an INSTALLED wheel through real MCP stdio, using a local read-only HTTP fixture."""
import asyncio
import importlib.metadata
import importlib.util
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

seen = []


class Fixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        seen.append({"path": self.path, "authorization_present": "Authorization" in self.headers})
        body = json.dumps({"status": "ok", "data": {"fixture": True}, "meta": {"warnings": ["fixture, not market evidence"]}}).encode()
        self.send_response(200)
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
                assert names == ["market_state", "daily_note", "research_quality"], names
                for name, arguments in [
                    ("market_state", {"symbol": "aapl", "date": "2026-09-04"}),
                    ("daily_note", {}),
                    ("research_quality", {}),
                    ("state_packet", {"symbol": "AAPL", "lane": "gap"}),
                ]:
                    before = len(seen)
                    result = await session.call_tool(name, arguments)
                    assert not result.isError, result
                    payload = json.loads(next(part.text for part in result.content if part.type == "text"))
                    assert payload["data"]["fixture"] is True
                    assert len(seen) == before + 1
                assert not any(r["authorization_present"] for r in seen)
                assert seen[0]["path"] == "/api/v1/state-packet?symbol=AAPL&date=2026-09-04"
                assert seen[1]["path"] == "/api/v1/daily"
                assert seen[2]["path"] == "/api/v1/calibration"
                assert "lane=gap" in seen[3]["path"]
                print(json.dumps({
                    "package": importlib.metadata.version("chartlibrary-mcp"),
                    "sdk": importlib.metadata.version("mcp"),
                    "tools": names,
                    "tool_list_bytes": len(listed.model_dump_json().encode()),
                    "instructions_bytes": len((initialized.instructions or "").encode()),
                    "http_calls": seen,
                    "hidden_legacy_dispatch": "passed",
                    "no_server_packages": True,
                }, indent=2))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


asyncio.run(run())
