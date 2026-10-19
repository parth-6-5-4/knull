"""MCP → real HTTP → existing lite routes → disposable SQLite/mock providers."""
import asyncio
from contextlib import contextmanager
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
from mcp import Client
from mcp.client.stdio import StdioServerParameters
import pytest


@contextmanager
def real_hive(tmp_path):
    python = os.environ.get("HIVE_APP_PYTHON")
    if not python:
        pytest.skip("Set HIVE_APP_PYTHON to the original app environment for real-route integration")
    fixture = Path(__file__).with_name("fixture_hive.py")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        port = sock.getsockname()[1]
        with (tmp_path / "hive.stderr").open("w+") as stderr:
            process = subprocess.Popen([python, str(fixture), "--fd", str(sock.fileno())],
                env={**os.environ, "DEBUG": "false", "HIVE_MCP_TEST_DB": str(tmp_path / "hive.db")},
                pass_fds=(sock.fileno(),), stdout=subprocess.DEVNULL, stderr=stderr)
            try:
                url = f"http://127.0.0.1:{port}"
                deadline = time.monotonic() + 10
                ready = False
                with httpx.Client(trust_env=False, timeout=0.2) as http:
                    while time.monotonic() < deadline and process.poll() is None:
                        try:
                            ready = http.get(url + "/health").status_code == 200
                        except httpx.HTTPError:
                            pass
                        if ready:
                            break
                        time.sleep(0.02)
                if not ready:
                    stderr.seek(0)
                    pytest.fail("Fixture Hive did not start: " + stderr.read()[-2000:])
                yield url
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


async def test_submit_and_poll_real_hive_through_stdio(tmp_path):
    src = str(Path(__file__).resolve().parents[1] / "src")
    with real_hive(tmp_path) as url:
        params = StdioServerParameters(command=sys.executable,
            args=["-m", "hive_mcp", "--api-url", url], env={"PYTHONPATH": src})
        async with Client(params, read_timeout_seconds=10) as client:
            submitted = await client.call_tool("hive_start_run", {
                "objective": "Attention and caching", "workers": 2, "subtasks": 1,
                "budget_tokens": 10000,
            })
            assert not submitted.is_error
            assert submitted.structured_content["status"] == "running"
            run_id = submitted.structured_content["run_id"]
            deadline = time.monotonic() + 10
            while True:
                response = await client.call_tool("hive_get_run", {"run_id": run_id})
                assert not response.is_error
                result = response.structured_content
                if result["status"] != "running":
                    break
                assert time.monotonic() < deadline, "Hive fixture did not finish"
                await asyncio.sleep(0.02)
            assert result["status"] == "done"
            assert len([f for f in result["facts"] if f["status"] == "verified"]) == 2
            assert "[F-" in result["report"] and "## Sources" in result["report"]
            assert all(u["provider"] == "mock" for u in result["usage_by_route"])
            assert (tmp_path / "hive.db").exists()
