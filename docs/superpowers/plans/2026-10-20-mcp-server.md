# Hive MCP server implementation and verification plan

> **For agentic workers:** Use Superpowers native execution, TDD and final code review. Preserve this ledger because the project is inside an unrelated parent Git checkout; do not stage or commit there.

**Goal:** External MCP clients can inspect Hive health, submit research and poll runs.
**Architecture:** Independent Python SDK adapter over existing local HTTP routes; no app imports/dependency updates.
**Spec:** [HIVE-013](../specs/2026-10-20-mcp-server-design.md).
**Authorization:** User explicitly selected the external-client → Hive server build. No separate written spec/plan review is claimed.
**Execution:** Native local implementation candidate, with independent final review. New personal host registration/public hosting/paid calls excluded.
**Status:** In progress; document review pending.

## Global constraints and rulings

- Three tools only, loopback API, 10-second timeout, 1 MiB response limit; typed schema/input/error contracts in spec.
- Keep MCP dependencies in `integrations/mcp`, its own environment and lock. Application files/pins remain unchanged.
- No automatic POST retry. Submission ambiguity must be explicit; no fabricated run completion or idempotency.
- No real provider request, private database migration, personal host config change or public listener.
- Ruling: user direction/build selection authorizes reversible local implementation/testing. Keep document-review status explicit; do not record this as approval of unseen artifacts. Cost if scope misunderstood: reversible adapter files only.
- Ruling: Git-root-dependent workspace/commit scripts would operate on the user's home checkout. Keep ledger here and tests in isolated temporary environment; no Git mutation. Cost: no commit-based review range; review exact new files instead.

## Review focus

1. POST accepted before timeout/5xx: exactly one request and unknown-outcome error (Task 1).
2. Host/path injection or redirect: reject/refuse before external access (Task 1).
3. Oversized/error payloads: cap before decoding; no sensitive upstream body in MCP error (Task 1).
4. Unauthorized HTTP and protocol stdout framing: no tool invocation before authentication; real transports (Task 2).
5. Capability/config drift: exact tools, schemas, configuration examples and underlying lite limitations (Task 3).

## Task 1: HTTP seam and tool contract

**Files:** `integrations/mcp/pyproject.toml`, `src/hive_mcp/{__init__,api,server,__main__}.py`, `tests/test_server.py`.
**Interfaces:** `create_server(api_url=..., transport=None) -> MCPServer`; typed async API calls return dictionaries or safe `ToolError`. Inject HTTP transport for deterministic tests, not fake store/model logic.

- [ ] Write/run failing behavioral tests for listing/schema, correct API forwarding, run-input limits, missing run, submission ambiguity/no retry, malformed/oversized response, base-origin/path rejection and redirect refusal.
- [ ] Implement minimal SDK wrapper and HTTP seam; rerun all Task 1 checks green.

## Task 2: Launchers, authentication and real protocol

**Files:** `src/hive_mcp/server.py`, `__main__.py`, `tests/test_transport.py`.
**Interfaces:** `hive-mcp --api-url http://127.0.0.1:8000 --transport stdio|streamable-http`; HTTP `--host` loopback, `--port`, `HIVE_MCP_TOKEN` environment.

- [ ] Write/run failing auth/bind/CLI tests; then implement bearer gate and launch options with safe stderr-only diagnostics.
- [ ] Use official SDK client against real stdio subprocess and authenticated local HTTP server; list tools, call health, reject invalid/unknown operations. Verify supported modern/legacy modes through installed SDK.
- [ ] Exercise actual existing Hive routes in a separate app-environment fixture process with mock providers/disposable SQLite; submit/poll through MCP without cloud requests. Record socket permission needs and cleanup all processes.

## Task 3: User setup, review and final evidence

**Files:** `integrations/mcp/README.md`, example Codex TOML/Claude JSON/GPT Python, adapter lock, spec index, problem register, graph outputs/provenance.

- [ ] Parse examples, run CLI help and package install/lock checks; document separate Hive startup, run limits/ambiguity, static-token trust and remote GPT reachability requirement.
- [ ] Run adapter suite, existing Hive suite and full app suite once; identify every failure/environment limitation by name without presenting old failures as new fixes.
- [ ] Fresh code/security/contract review of new files; verify important fixes with failing-then-passing tests. Update requirement coverage/ledger and problems/fixes register from observed results.
- [ ] Refresh source graph after new code; verify artifact integrity and links. Do not claim native host registration or live GPT/Claude/Codex account test.

## Coverage

| Requirements | Tasks | Oracle |
|---|---|---|
| MCP-01/02/03/04/05 | 1, 2 | Typed tool calls and captured HTTP requests; safe failure cases; real route fixture |
| MCP-06/07 | 2 | Real stdio/HTTP protocol and auth/bind rejection |
| MCP-08/09/10 | 3 | Parsed examples, suite results, unchanged app hashes, documented residual engine issues |

## Execution ledger

- 2026-10-20: confirmed direction; inspected existing routes and pinned SDK APIs. Installed MCP 2.3.0/httpx/test tools only in `/private/tmp/hive-mcp-venv`. Initial sandbox DNS/cache restrictions resolved with temporary cache and approved dependency-download execution. App environment unchanged.

## Verification record

Pending execution; no transport, API or host compatibility pass claimed yet.
