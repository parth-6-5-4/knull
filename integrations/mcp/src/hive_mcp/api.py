"""One bounded HTTP seam; Hive remains the run/state authority."""
from __future__ import annotations

import json
import asyncio
import math
import re
from typing import Any
from urllib.parse import urlsplit

import httpx
from mcp.server.mcpserver.exceptions import ToolError

RUN_ID = re.compile(r"[a-f0-9]{12}\Z")
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
REQUEST_DEADLINE_SECONDS = 10


def _failure(mutation: bool, code: str) -> ToolError:
    if mutation and code not in ("upstream_rejected", "upstream_redirect_refused"):
        return ToolError("submission_outcome_unknown: Hive may have accepted the run; inspect Hive state before resubmitting")
    messages = {
        "run_not_found": "Run not found",
        "upstream_rejected": "Hive rejected the request",
        "upstream_redirect_refused": "Hive redirect refused",
        "upstream_unavailable": "Hive is unavailable or request timed out",
        "upstream_invalid_response": "Hive returned an invalid or oversized response",
    }
    return ToolError(f"{code}: {messages[code]}")


def _valid_structure(payload: dict) -> bool:
    # O(depth) traversal space; do not allocate a second list of every JSON value.
    stack = [(iter([payload]), 0)]
    while stack:
        iterator, depth = stack[-1]
        try:
            value = next(iterator)
        except StopIteration:
            stack.pop()
            continue
        if depth > 32:
            return False
        if isinstance(value, dict):
            stack.append((iter(value.values()), depth + 1))
        elif isinstance(value, list):
            stack.append((iter(value), depth + 1))
        elif isinstance(value, float) and not math.isfinite(value):
            return False
    return True


class HiveAPI:
    def __init__(self, api_url: str, transport: httpx.AsyncBaseTransport | None = None):
        parsed = urlsplit(api_url)
        if (parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
            raise ValueError("Hive API URL must be an HTTP loopback origin without credentials, path, query or fragment")
        # Accessing port also validates malformed or out-of-range values.
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("Invalid Hive API port")
        self.url = api_url.rstrip("/")
        self.transport = transport

    async def request(self, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        try:
            async with asyncio.timeout(REQUEST_DEADLINE_SECONDS):
                return await self._request(method, path, body)
        except TimeoutError:
            raise _failure(method == "POST", "upstream_unavailable") from None

    async def _request(self, method: str, path: str, body: dict | None) -> dict[str, Any]:
        mutation = method == "POST"

        def failure(code: str) -> ToolError:
            return _failure(mutation, code)

        try:
            async with httpx.AsyncClient(timeout=REQUEST_DEADLINE_SECONDS, follow_redirects=False, trust_env=False,
                                         headers={"Accept-Encoding": "identity"},
                                         transport=self.transport) as client:
                async with client.stream(method, self.url + path, json=body) as response:
                    if 300 <= response.status_code < 400:
                        raise failure("upstream_redirect_refused")
                    if response.status_code == 404 and not mutation:
                        raise failure("run_not_found")
                    if 400 <= response.status_code < 500:
                        raise failure("upstream_rejected")
                    if response.status_code != (202 if mutation else 200):
                        raise failure("upstream_unavailable")
                    if response.headers.get("content-encoding", "identity").lower() != "identity":
                        raise failure("upstream_invalid_response")
                    data = bytearray()
                    # Real streaming responses stay raw. Mock/in-memory responses may
                    # already be materialized; neither path applies decompression here.
                    chunks = response.aiter_bytes(chunk_size=65536) if response.is_stream_consumed else response.aiter_raw(chunk_size=65536)
                    async for chunk in chunks:
                        if len(data) + len(chunk) > 1024 * 1024:
                            raise failure("upstream_invalid_response")
                        data.extend(chunk)
            try:
                payload = json.loads(data)
            except (ValueError, UnicodeError, RecursionError):
                raise failure("upstream_invalid_response") from None
            if not isinstance(payload, dict) or not isinstance(payload.get("status"), str):
                raise failure("upstream_invalid_response")
            if not _valid_structure(payload):
                raise failure("upstream_invalid_response")
            if path != "/health":
                run_id = payload.get("run_id")
                if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
                    raise failure("upstream_invalid_response")
                if mutation and payload["status"] != "running":
                    raise failure("upstream_invalid_response")
                if not mutation and run_id != path.rsplit("/", 1)[-1]:
                    raise failure("upstream_invalid_response")
            return payload
        except httpx.HTTPError:
            raise failure("upstream_unavailable") from None

