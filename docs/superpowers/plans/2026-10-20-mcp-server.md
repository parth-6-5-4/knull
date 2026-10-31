# Hive MCP server implementation and verification plan

> **For agentic workers:** Use Superpowers native execution, TDD and final code review. Preserve this ledger because the project is inside an unrelated parent Git checkout; do not stage or commit there.

**Goal:** External MCP clients can inspect Hive health, submit research and poll runs.
**Architecture:** Independent Python SDK adapter over existing local HTTP routes; no app imports/dependency updates.
**Spec:** [HIVE-013](../specs/2026-10-20-mcp-server-design.md).
**Authorization:** User explicitly selected the external-client → Hive server build. No separate written spec/plan review is claimed.
**Execution:** Native local implementation candidate, with independent final review. New personal host registration/public hosting/paid calls excluded.
**Status:** Local implementation verified; maintainer document review pending. Host account registration/public deployment not performed.

## Global constraints and rulings

- Three tools only, loopback API, 10-second timeout, 1 MiB response limit; typed schema/input/error contracts in spec.
- Keep MCP dependencies in `integrations/mcp`, its own environment and lock. Application files/pins remain unchanged.
- No automatic POST retry. Submission ambiguity must be explicit; no fabricated run completion or idempotency.
- No real provider request, private database migration, personal host config change or public listener.
- Ruling: user direction/build selection authorizes reversible local implementation/testing. Keep document-review status explicit; do not record this as approval of unseen artifacts. Cost if scope misunderstood: reversible adapter files only.
- Ruling: At task start, Git-root-dependent workspace/commit scripts would have operated on the user's home checkout. Kept ledger here and used file-level review, with no Git mutation. A project-owned checkout appeared later during work; verification records its HEAD separately from uncommitted source hashes. Cost: review is by exact files rather than an agent-created commit range.

## Review focus

1. POST accepted before timeout/5xx: exactly one request and unknown-outcome error (Task 1).
2. Host/path injection or redirect: reject/refuse before external access (Task 1).
3. Oversized/error payloads: cap before decoding; no sensitive upstream body in MCP error (Task 1).
4. Unauthorized HTTP and protocol stdout framing: no tool invocation before authentication; real transports (Task 2).
5. Capability/config drift: exact tools, schemas, configuration examples and underlying lite limitations (Task 3).

## Task 1: HTTP seam and tool contract

**Files:** `integrations/mcp/pyproject.toml`, `src/hive_mcp/{__init__,api,server,__main__}.py`, `tests/test_server.py`.
**Interfaces:** `create_server(api_url=..., transport=None) -> MCPServer`; typed async API calls return dictionaries or safe `ToolError`. Inject HTTP transport for deterministic tests, not fake store/model logic.

- [x] Write/run failing behavioral tests for listing/schema, correct API forwarding, run-input limits, missing run, submission ambiguity/no retry, malformed/oversized response, base-origin/path rejection and redirect refusal.
- [x] Implement minimal SDK wrapper and HTTP seam; rerun all Task 1 checks green.

## Task 2: Launchers, authentication and real protocol

**Files:** `src/hive_mcp/server.py`, `__main__.py`, `tests/test_transport.py`.
**Interfaces:** `hive-mcp --api-url http://127.0.0.1:8000 --transport stdio|streamable-http`; HTTP `--host` loopback, `--port`, `HIVE_MCP_TOKEN` environment.

- [x] Write/run failing auth/bind/CLI tests; then implement bearer gate and launch options with safe stderr-only diagnostics.
- [x] Use official SDK client against real stdio subprocess and authenticated local HTTP server; list tools, call health, reject invalid/unknown operations. Verify supported modern/legacy modes through installed SDK.
- [x] Exercise actual existing Hive routes in a separate app-environment fixture process with mock providers/disposable SQLite; submit/poll through MCP without cloud requests. Record socket permission needs and cleanup all processes.

## Task 3: User setup, review and final evidence

**Files:** `integrations/mcp/README.md`, example Codex TOML/Claude JSON/GPT Python, adapter lock, spec index, problem register, graph outputs/provenance.

- [x] Parse examples, run CLI help and package install/lock checks; document separate Hive startup, run limits/ambiguity, static-token trust and remote GPT reachability requirement.
- [x] Run adapter suite, existing Hive suite and full app suite once; identify every failure/environment limitation by name without presenting old failures as new fixes.
- [x] Fresh code/security/contract review of new files; verify important fixes with failing-then-passing tests. Update requirement coverage/ledger and problems/fixes register from observed results.
- [x] Refresh source graph after new code; verify artifact integrity and links. Do not claim native host registration or live GPT/Claude/Codex account test.

## Coverage

| Requirements | Tasks | Oracle |
|---|---|---|
| MCP-01/02/03/04/05 | 1, 2 | Typed tool calls and captured HTTP requests; safe failure cases; real route fixture |
| MCP-06/07 | 2 | Real stdio/HTTP protocol and auth/bind rejection |
| MCP-08/09/10 | 3 | Parsed examples, suite results, unchanged app hashes, documented residual engine issues |

## Execution ledger

- 2026-10-20: confirmed direction; inspected existing routes and pinned SDK APIs. Installed MCP 2.3.0/httpx/test tools only in `/private/tmp/hive-mcp-venv`. Initial sandbox DNS/cache restrictions resolved with temporary cache and approved dependency-download execution. App environment unchanged.

## Verification record

| Check / command | Observed result | Boundary |
|---|---|---|
| Initial server contracts in isolated environment | 35 passed; first test failed while adapter absent; extra-argument regression reproduced before repair | SDK in-process protocol + controlled upstream HTTP |
| Initial real transports/real Hive route fixture | 46 passed combined | Stdio subprocess + authenticated loopback HTTP, auto/legacy modes; real lite routes in original Python with disposable SQLite and mock-only providers |
| Fresh code/security/contract review | Three P2/Important findings; all fixed in one pass | [Findings and evidence](../../reports/hive-mcp-review.md). No second review claimed |
| Eight new deadline/deep-JSON/encoding regression cases | All eight failed before repair, then passed | Error semantics, total deadline, no body decompression before refusal |
| `HIVE_APP_PYTHON=/opt/anaconda3/bin/python integrations/mcp/.venv/bin/python -m pytest -c integrations/mcp/pyproject.toml integrations/mcp/tests` | **54 passed in 13.63s**, after fixes | Locked installed adapter, real local transports and Hive fixture. Local socket permission granted; no paid calls |
| `DEBUG=false PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/test_hive.py tests/test_api_research.py tests/test_prompts.py -q` | **36 passed in 2.27s** | Original application environment |
| `DEBUG=false PYTHONDONTWRITEBYTECODE=1 python -m pytest -q` | **10 failed, 55 passed, 3 errors** | Existing `sentence_transformers` import of missing `huggingface_hub.HfFolder` causes ten cache/vector failures; sandbox blocked three fake-server socket fixtures. Every case retained in [machine evidence](../../reports/hive-mcp-verification.json) |
| Local-socket-authorized `python -m pytest tests/test_llm_sdk_wiring.py -q` | **3 passed, 1 failed** | Remaining Anthropic transport test fails because original environment lacks `anthropic`; no dependency installed into app environment |
| `UV_CACHE_DIR=/private/tmp/hive-mcp-cache uv sync --project integrations/mcp --frozen --python /opt/anaconda3/bin/python`; installed `hive-mcp --help`; offline lock check | Install/help/check passed | Independent `.venv`; app dependencies unchanged |
| Example JSON/TOML parsing and GPT Python AST parsing | Passed | Syntax only; personal host configs and model accounts untouched |
| Original app/test/eval/frontend SHA256 check | 85 reviewed files unchanged | Plus unchanged root dependency declarations; implementation isolated to adapter subtree |
| Graphify refresh and integrity | 1,107 nodes, 2,407 edges, 67 communities; zero endpoint/duplicate/self-loop errors | Local AST only; HTML embedded counts match JSON; source hashes retained. No new browser interaction claim |

Task 1 complete: request/schema/safe-error contracts verified. Task 2 complete: launch/auth/real protocol/real-route fixtures verified. Task 3 complete: packaging/examples/review fixes/graph/report delivered. All eight review regression cases and complete adapter suite passed after the repair pass.

Ruling on review exclusions: runtime F1/F2/F4/F13, research quality, public ingress/OAuth and real host-account registration remain separate scopes; adapter success is not evidence for them. Parent-executed application/socket tests are not claimed as independently repeated by reviewer. Cost: local MCP works but full application readiness remains limited by the existing engine/environment issues.

No unresolved Important adapter finding or deferred Minor finding was recorded. [Machine-readable results](../../reports/hive-mcp-verification.json) and [exported tool schemas](../../reports/hive-mcp-tool-catalog.json) are the completion evidence. No real Hive data migrated, public listener deployed, paid model call made, personal host config edited, or Git mutation performed by this agent.
