"""Real transport/auth checks against loopback fixtures; no cloud providers."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

import httpx
import httpx2
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp.client.streamable_http import streamable_http_client
import pytest
import uvicorn

from hive_mcp.server import create_server

SRC = str(Path(__file__).resolve().parents[1] / "src")
TOKEN = "test-token-used-only-in-fixtures-123456789"


@pytest.fixture
def upstream():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b'{"status":"healthy","components":{}}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@contextmanager
def serving(app):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="on"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started, "HTTP server did not start"
        yield f"http://127.0.0.1:{sock.getsockname()[1]}/mcp"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()
        assert not thread.is_alive(), "HTTP server did not stop"


def test_cli_entrypoint_exists_and_explains_transport_options():
    result = subprocess.run([sys.executable, "-m", "hive_mcp", "--help"],
                            env={**os.environ, "PYTHONPATH": SRC}, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert "--transport" in result.stdout and "streamable-http" in result.stdout


@pytest.mark.parametrize("args,token", [(["--host", "0.0.0.0"], TOKEN), ([], "short"), ([], "")])
def test_http_launch_refuses_untrusted_binding_or_weak_token(args, token):
    result = subprocess.run([sys.executable, "-m", "hive_mcp", "--transport", "streamable-http", *args],
                            env={**os.environ, "PYTHONPATH": SRC, "HIVE_MCP_TOKEN": token},
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert token not in result.stderr if token else True


@pytest.mark.parametrize("token", [None, "wrong"])
async def test_http_auth_rejects_before_any_upstream_request(token):
    from hive_mcp.server import create_http_app
    calls = []
    server = create_server(transport=httpx.MockTransport(lambda r: calls.append(r)))
    app = create_http_app(server, TOKEN)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1") as client:
        response = await client.post("/mcp", headers={"Authorization": f"Bearer {token}"} if token else {},
                                     json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert response.status_code == 401
    assert not calls and TOKEN not in response.text


@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_real_stdio_discovers_tools_and_calls_health(upstream, mode):
    params = StdioServerParameters(command=sys.executable,
        args=["-m", "hive_mcp", "--api-url", upstream], env={"PYTHONPATH": SRC})
    async with Client(params, mode=mode, read_timeout_seconds=10) as client:
        assert len((await client.list_tools()).tools) == 3
        result = await client.call_tool("hive_health")
        assert not result.is_error and result.structured_content["status"] == "healthy"


@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_real_http_authenticated_discovery_and_tool_call(upstream, mode):
    from hive_mcp.server import create_http_app
    with serving(create_http_app(create_server(upstream), TOKEN)) as url:
        async with httpx2.AsyncClient(headers={"Authorization": f"Bearer {TOKEN}"}, trust_env=False) as http:
            async with Client(streamable_http_client(url, http_client=http), mode=mode,
                              read_timeout_seconds=10) as client:
                assert len((await client.list_tools()).tools) == 3
                result = await client.call_tool("hive_health")
                assert not result.is_error and result.structured_content["status"] == "healthy"
