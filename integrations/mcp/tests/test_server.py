"""Contract tests: real SDK protocol, controlled upstream HTTP boundary."""
import importlib.util
import asyncio
import gzip
import json

import httpx
from mcp import Client
import pytest


def factory():
    assert importlib.util.find_spec("hive_mcp") is not None, "Hive MCP adapter is not implemented"
    from hive_mcp.server import create_server
    return create_server


def text(result):
    return " ".join(c.text for c in result.content if c.type == "text")


def make_server(handler):
    return factory()(transport=httpx.MockTransport(handler))


async def test_discovery_and_forwarding_preserve_hive_contract():
    calls = []

    def upstream(request):
        calls.append((request.method, str(request.url), json.loads(request.content or b"{}")))
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "healthy", "components": {}})
        if request.method == "POST":
            return httpx.Response(202, json={"run_id": "abcdef012345", "status": "running"})
        return httpx.Response(200, json={"run_id": "abcdef012345", "status": "done", "report": "fixture"})

    async with Client(make_server(upstream)) as client:
        tools = (await client.list_tools()).tools
        assert {t.name for t in tools} == {"hive_health", "hive_start_run", "hive_get_run"}
        start = next(t for t in tools if t.name == "hive_start_run")
        assert start.annotations.idempotent_hint is False
        assert start.input_schema["properties"]["workers"]["maximum"] == 8
        assert not (await client.call_tool("hive_health")).is_error
        result = await client.call_tool("hive_start_run", {"objective": "Compare graph memory"})
        assert result.structured_content == {"run_id": "abcdef012345", "status": "running"}
        result = await client.call_tool("hive_get_run", {"run_id": "abcdef012345"})
        assert result.structured_content["report"] == "fixture"
    assert calls == [
        ("GET", "http://127.0.0.1:8000/health", {}),
        ("POST", "http://127.0.0.1:8000/v1/hive/runs",
         {"objective": "Compare graph memory", "workers": 3, "subtasks": 4, "budget_tokens": 200000}),
        ("GET", "http://127.0.0.1:8000/v1/hive/runs/abcdef012345", {}),
    ]


@pytest.mark.parametrize("arguments", [
    {"objective": "tiny"}, {"objective": "x" * 10001},
    {"objective": "valid request", "workers": 9},
    {"objective": "valid request", "workers": True},
    {"objective": "valid request", "workers": "2"},
    {"objective": "valid request", "subtasks": 0},
    {"objective": "valid request", "budget_tokens": 999},
    {"objective": "valid request", "budget_tokens": 200001},
    {"objective": "valid request", "api_url": "http://evil.invalid"},
])
async def test_invalid_submission_never_reaches_upstream(arguments):
    calls = []
    async with Client(make_server(lambda r: calls.append(r))) as client:
        result = await client.call_tool("hive_start_run", arguments)
        assert result.is_error
    assert not calls


@pytest.mark.parametrize("run_id", ["../health", "abcdef012345?x=1", "", "ABCDEF012345"])
async def test_invalid_run_id_never_reaches_upstream(run_id):
    calls = []
    async with Client(make_server(lambda r: calls.append(r))) as client:
        assert (await client.call_tool("hive_get_run", {"run_id": run_id})).is_error
    assert not calls


@pytest.mark.parametrize("url", ["https://evil.invalid", "http://127.0.0.1:8000/private",
    "http://user:secret@localhost:8000", "http://localhost:8000?x=1", "http://localhost:8000#frag"])
def test_upstream_origin_cannot_escape_loopback(url):
    with pytest.raises(ValueError):
        factory()(api_url=url)


@pytest.mark.parametrize("failure", ["timeout", "connect", "server", "malformed", "wrong_id", "wrong_status", "oversize"])
async def test_uncertain_submission_is_not_retried_or_reported_successful(failure):
    calls = []

    def upstream(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("private objective or credential", request=request)
        if failure == "connect":
            raise httpx.ConnectError("private network detail", request=request)
        if failure == "server": return httpx.Response(500, text="secret server detail")
        if failure == "malformed": return httpx.Response(202, text="private non-JSON")
        if failure == "wrong_id": return httpx.Response(202, json={"run_id": "bad", "status": "running"})
        if failure == "wrong_status": return httpx.Response(200, json={"run_id": "abcdef012345", "status": "done"})
        return httpx.Response(202, content=b"x" * (1024 * 1024 + 1))

    async with Client(make_server(upstream)) as client:
        result = await client.call_tool("hive_start_run", {"objective": "valid request"})
        assert result.is_error
        assert "submission_outcome_unknown" in text(result)
        assert "private" not in text(result) and "secret" not in text(result)
    assert len(calls) == 1


@pytest.mark.parametrize("status,code", [(404, "run_not_found"), (401, "upstream_rejected"),
    (500, "upstream_unavailable"), (302, "upstream_redirect_refused")])
async def test_read_errors_are_safe_and_redirects_not_followed(status, code):
    calls = []

    def upstream(request):
        calls.append(request)
        return httpx.Response(status, text="secret response", headers={"location": "http://evil.invalid"})

    async with Client(make_server(upstream)) as client:
        result = await client.call_tool("hive_get_run", {"run_id": "abcdef012345"})
        assert result.is_error and code in text(result)
        assert "secret" not in text(result)
    assert len(calls) == 1


async def test_unknown_tool_never_reaches_upstream():
    calls = []
    async with Client(make_server(lambda r: calls.append(r))) as client:
        assert (await client.call_tool("shell", {"command": "anything"})).is_error
    assert not calls


@pytest.mark.parametrize("payload", [b"not-json", b"[]", b'{"wrong":"shape"}', b"x" * (1024 * 1024 + 1)])
async def test_invalid_read_payload_is_not_returned_as_success(payload):
    async with Client(make_server(lambda r: httpx.Response(200, content=payload))) as client:
        result = await client.call_tool("hive_health")
        assert result.is_error and "upstream_invalid_response" in text(result)


@pytest.mark.parametrize("mutation", [False, True])
async def test_total_deadline_stops_a_continuously_trickling_response(monkeypatch, mutation):
    import hive_mcp.api as api
    monkeypatch.setattr(api, "REQUEST_DEADLINE_SECONDS", 0.04, raising=False)
    calls = []

    class Trickle(httpx.AsyncByteStream):
        async def __aiter__(self):
            payload = (b'{"status":"running","run_id":"abcdef012345"}' if mutation
                       else b'{"status":"healthy"}')
            for piece in [payload[:5], payload[5:10], payload[10:]]:
                await asyncio.sleep(0.025)
                yield piece

    def upstream(request):
        calls.append(request)
        return httpx.Response(202 if mutation else 200, stream=Trickle())

    async with Client(make_server(upstream)) as client:
        result = await client.call_tool("hive_start_run" if mutation else "hive_health",
                                       {"objective": "valid request"} if mutation else {})
        assert result.is_error
        assert ("submission_outcome_unknown" if mutation else "upstream_unavailable") in text(result)
    assert len(calls) == 1


@pytest.mark.parametrize("mutation", [False, True])
@pytest.mark.parametrize("depth", [64, 1200])
async def test_deep_json_is_rejected_inside_safe_api_error_boundary(mutation, depth):
    prefix = (b'{"status":"running","run_id":"abcdef012345","extra":' if mutation
              else b'{"status":"healthy","extra":')
    payload = prefix + b'[' * depth + b'0' + b']' * depth + b'}'
    async with Client(make_server(lambda r: httpx.Response(202 if mutation else 200, content=payload))) as client:
        result = await client.call_tool("hive_start_run" if mutation else "hive_health",
                                       {"objective": "valid request"} if mutation else {})
        assert result.is_error
        assert ("submission_outcome_unknown" if mutation else "upstream_invalid_response") in text(result)


@pytest.mark.parametrize("mutation", [False, True])
async def test_encoded_response_is_rejected_before_decompression(mutation):
    consumed = []
    requests = []

    class Compressed(httpx.AsyncByteStream):
        async def __aiter__(self):
            consumed.append(True)
            yield gzip.compress(b'x' * (2 * 1024 * 1024))

    def upstream(request):
        requests.append(request)
        return httpx.Response(202 if mutation else 200, headers={"content-encoding": "gzip"}, stream=Compressed())

    async with Client(make_server(upstream)) as client:
        result = await client.call_tool("hive_start_run" if mutation else "hive_health",
                                       {"objective": "valid request"} if mutation else {})
        assert result.is_error
        assert ("submission_outcome_unknown" if mutation else "upstream_invalid_response") in text(result)
    assert not consumed, "Compressed body must never be consumed/decompressed"
    assert requests[0].headers["accept-encoding"] == "identity"
