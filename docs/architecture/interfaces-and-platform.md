# Interfaces and platform control

[Main guide](../../ARCHITECTURE.md) · [Knull walkthrough](knull.html)

The platform exposes authoritative state and commands. Knull is a coordinating role inside that platform, not an unrestricted administrator of it.

| Surface | Current behavior | Proposed extension |
|---|---|---|
| HTTP API | `POST /v1/hive/runs`, `GET /v1/hive/runs/{id}` | Separate v2 modular run, command and cursor-event contracts |
| CLI | Calls the lite runner | Explicit `--engine modular-v1`; lite remains default |
| React console | v1/demo run display | Authoritative RunView, dependency/parent distinction and causes |
| MCP server | Health/start/get forwards to existing API | Add tools only as backing commands become implemented |
| Knull | Fixed planning step | Durable, bounded plan/delegation proposals and aggregation |

The proposed v2 API uses operation keys and expected versions for commands. Pause drains work; cancellation invalidates attempts; resume is a validated transition. These are not equivalent to killing an HTTP request. An events endpoint returns committed changes after a cursor; reconnecting clients must not invent state from local animation.

The local [MCP adapter](../../integrations/mcp/README.md) supports stdio and authenticated loopback HTTP. Codex, Claude Code and compatible clients act as MCP clients; Hive exposes the server. This does not mean Hive launches those external coding agents as workers. It also does not make remote hosting, caller isolation or arbitrary tool execution available. See the [MCP review](../reports/hive-mcp-review.md) for the local validation scope.

The proposed console should answer: What is the run trying to do? Who owns each branch? Which tasks are ready or waiting? Why was work blocked? What was reserved and consumed? Which outputs were accepted? Which decision/profile produced a route? It must show partial, stopped, blocked, failed and cancelled outcomes distinctly.

Shared deployment requires HIVE-009 caller identity, authorization and idempotency. HIVE-005 must specify the detailed console/API contract. Both remain backlog; a polished explanatory page does not establish these capabilities.

The [Knull HTML page](knull.html) is an interactive architecture explanation with illustrative scenarios. Its controls alter local explanation state only. It intentionally makes no network requests and does not display real runs.
