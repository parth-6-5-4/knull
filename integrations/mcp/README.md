# Hive MCP server

Connect Codex, Claude Code, or another MCP host to the existing Hive Lite API. Separate adapter process/environment; application dependencies and execution remain owned by Hive. [Design](../../docs/superpowers/specs/2026-10-20-mcp-server-design.md) · [verification ledger](../../docs/superpowers/plans/2026-10-20-mcp-server.md).

## Install and start

From repository root, install the adapter's locked environment with Python 3.12+:

```bash
uv sync --project integrations/mcp --frozen
integrations/mcp/.venv/bin/hive-mcp --help
```

Start Hive separately, using its existing app environment and provider setup from the [main README](../../README.md). Do not activate the MCP environment to start the app:

```bash
DEBUG=false python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then launch MCP, or let a configured host launch it:

```bash
integrations/mcp/.venv/bin/hive-mcp --api-url http://127.0.0.1:8000
```

Default transport is stdio. Stdout carries MCP protocol only; diagnostics use stderr. API origin must be HTTP loopback (`127.0.0.1`, `localhost`, or `::1`) without credentials, path, query or fragment. `HIVE_API_URL` supplies the default when `--api-url` is omitted. MCP does not launch or configure the Hive app or its providers.

## Tools

| Tool | Inputs | Result |
|---|---|---|
| `hive_health` | None | Existing health/routing response |
| `hive_start_run` | `objective`, optional `workers`, `subtasks`, `budget_tokens` | Accepted `run_id`, `status: running` |
| `hive_get_run` | `run_id` | Current status, report, facts, tasks, usage, recent events |

Example flow: call `hive_start_run` with `{"objective":"Compare graph memory approaches","workers":2,"subtasks":2,"budget_tokens":10000}`; take its returned ID and poll `hive_get_run`. Accepted is not completed. A run uses the Hive service's configured providers and may incur charges.

Bounds: objective 5–10,000 characters; workers/subtasks 1–8; requested tokens 1,000–200,000. Defaults: 3 workers, 4 subtasks, 200,000 requested tokens. Run IDs use the current lite engine's 12-character lowercase hex format. Unknown arguments are rejected. Upstream requests have a 10-second total deadline; identity-encoded responses are capped at 1 MiB and JSON nesting at 32 levels. Compressed/non-finite/deep responses and large run projections fail explicitly rather than bypassing the resource bound or truncating facts/reports.

Submission is **not idempotent**. No automatic retry. `submission_outcome_unknown` means Hive may already have accepted the run: inspect the local Hive database/run records before manually resubmitting. `run_not_found` is a missing run; other safe error codes include `upstream_rejected`, `upstream_redirect_refused`, `upstream_unavailable`, and `upstream_invalid_response`. Raw upstream errors/bodies are not echoed. Disconnecting/cancelling MCP cannot undo an accepted Hive run; no stop/resume tool exists.

## Codex and Claude Code

Ready-to-edit examples:

- [Codex stdio](examples/codex.stdio.toml), [Codex HTTP](examples/codex.http.toml)
- [Claude Code stdio](examples/claude-code.stdio.json), [Claude Code HTTP](examples/claude-code.http.json)

Examples use an absolute placeholder executable path. Replace it with your local checkout path. Choose one transport; merge the entry into the host's existing configuration instead of overwriting unrelated servers. Keep personal host configuration local. No personal configuration was changed by this task.

Codex accepts stdio `command`/`args` or HTTP `url` with a bearer-token environment reference. [Official Codex configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

Claude Code reads project `.mcp.json` entries under `mcpServers`; HTTP entries need an explicit type and can expand token environment references. Host approval/discovery is separate from writing a config file. [Official Claude Code configuration](https://code.claude.com/docs/en/mcp).

## Local HTTP and GPT clients

For Streamable HTTP, set `HIVE_MCP_TOKEN` through your secret manager or shell environment to a random ASCII token of at least 32 characters, without whitespace. Do not commit or paste its value into config examples. Then run:

```bash
integrations/mcp/.venv/bin/hive-mcp --transport streamable-http --port 8765
```

Endpoint: `http://127.0.0.1:8765/mcp`; requires `Authorization: Bearer <token>`. Binding is loopback only. Authentication precedes MCP handling; duplicate/missing/wrong authorization headers are denied. This is a trusted single-operator gate: token holders can inspect runs and start research using service credentials. It is not OAuth, tenant isolation or per-run access control.

[GPT Responses example](examples/gpt_responses.py) uses an existing OpenAI client environment and a user-selected model. OpenAI's remote MCP API needs a reachable authenticated endpoint, or a separately configured private tunnel; cloud APIs cannot reach your machine's loopback URL directly. [Official remote MCP guidance](https://developers.openai.com/api/docs/guides/tools-connectors-mcp). The example is read-only and keeps tool approval enabled. It was syntax-checked, not executed against a model.

No public listener, tunnel, TLS proxy, OAuth server or hosted deployment was created. If arranging private ingress yourself, keep this adapter loopback-only, preserve bearer authentication, and have the proxy connect with a loopback Host header so SDK host checks remain enabled. Shared/public deployment needs the separate HIVE-009 authorization scope and review.

## Verification and limitations

Run adapter checks from root:

```bash
HIVE_APP_PYTHON=/absolute/path/to/app/python \
  integrations/mcp/.venv/bin/python -m pytest \
  -c integrations/mcp/pyproject.toml integrations/mcp/tests
```

`HIVE_APP_PYTHON` selects the original application environment for the disposable real-route fixture. Without it, that one integration test skips; other adapter tests still run. Socket tests need permission to bind loopback. Fixtures use mock providers and temporary SQLite, never real app databases or paid requests. The official SDK client verifies stdio and authenticated HTTP, modern/legacy modes, exact tools, typed forwarding and safe failure cases. This is protocol/API evidence, not an actual Codex/Claude account login or live GPT call.

See the [problem register](../../docs/reports/problems-and-fixes.md) for lite-engine status. HIVE-001/002 repair run-scoped evidence provenance and exhausted-dependency termination; concurrent budget overshoot and missing shared-caller isolation remain open. Requested token budget is not a repaired hard-spend guarantee. Skill loading, hierarchy and Jev remain separate draft designs; this server does not advertise them as working tools. Adapter success does not establish research accuracy or production readiness.

Rollback: stop the MCP process/remove its host entry. Already accepted Hive jobs remain under Hive's existing lifecycle; adapter shutdown does not cancel them. No storage migration is needed.
