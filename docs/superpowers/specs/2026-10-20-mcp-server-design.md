# External clients calling the Hive MCP server

**Spec ID:** HIVE-013
**Status:** Draft implementation contract
**Date:** 2026-10-20
**Owner:** Project maintainer
**Authorization:** User requested an MCP connection, then explicitly selected “Expose Hive tools through an MCP server for Codex, Claude Code and compatible GPT clients.” This records direction/build authorization, not a separate approval of this newly written document.
**Plan:** [Implementation and verification ledger](../plans/2026-10-20-mcp-server.md)

## Outcome and scope

Provide a runnable optional MCP server over the **existing lite Hive HTTP API**. Codex/Claude Code can launch it through stdio; compatible clients can use authenticated local Streamable HTTP. Supply host configuration examples without editing personal settings. GPT API access requires a reachable authenticated endpoint/private tunnel; creating public ingress or making a paid model call is outside this local build.

Hive consuming external MCP servers and delegating reasoning to external coding agents are separate future integrations. HIVE-012 skills and HIVE-008 hierarchy remain designs; this adapter must not advertise them as implemented. It must not introduce shell, arbitrary URL, SQL, filesystem, registry-edit or provider-configuration tools.

## Architecture and alternatives

Choose a separate `integrations/mcp` Python project/process that speaks to a configured loopback Hive API. Modern MCP dependencies conflict with exact app pins; a separate requirements file installed into the app environment would not isolate them. [Release/source research](../../research/2026-10-19-mcp-integration.md). Keep existing application code and dependency declarations unchanged.

Directly mounting the SDK into the old FastAPI app would require dependency migration. Duplicating run execution/storage in the MCP process would create competing authorities. A narrow HTTP adapter preserves the existing API seam and keeps SDK/protocol details local.

Tool surface:

| Tool | API | Semantics |
|---|---|---|
| `hive_health` | `GET /health` | Read health/routing information, no provider/model completion. Existing health implementation may probe local dependencies. |
| `hive_start_run` | `POST /v1/hive/runs` | Submit objective and return accepted run ID; does not claim completion. Mutation, not idempotent. |
| `hive_get_run` | `GET /v1/hive/runs/{run_id}` | Read current lite status/report/facts/tasks/events/usage; never fabricate new-engine fields. |

Inputs: objective 5–10,000 characters; strict integers workers/subtasks 1–8, requested budget 1,000–200,000; run ID exactly 12 lowercase hex characters. These bound adapter inputs; they do not repair the known engine budget race. Defaults match current API: workers 3, subtasks 4, requested budget 200,000.

## Requirements

| ID | Required behavior | Acceptance oracle |
|---|---|---|
| MCP-01 | Runnable isolated server exposes only the three documented tools. | Official SDK client lists exact names and validates input/output schemas. |
| MCP-02 | Tools forward validated requests to the existing Hive API. | Fake HTTP service and real lite route fixture receive correct method/path/body; accepted ID can be polled. |
| MCP-03 | Mutation never auto-retries or claims success after ambiguous delivery. | Timeout/connection/5xx or malformed accepted response yields `submission_outcome_unknown`; request count stays one. |
| MCP-04 | Inputs cannot choose an upstream host/path or exceed admitted payload limits. | Invalid IDs/ranges/extra arguments reject; base URL is operator-selected HTTP loopback origin without credentials/path/query/fragment. Redirects are not followed; proxy environment is ignored. |
| MCP-05 | Responses and waits are bounded with safe errors. | Upstream timeout, oversized/non-JSON/error response produces typed tool failure without leaking response text, tokens or objective; response limit 1 MiB and request timeout 10 seconds. |
| MCP-06 | Both stdio and local Streamable HTTP work through SDK protocol handling. | Real subprocess stdio discovery/calls and real local HTTP discovery/calls; no protocol logs corrupt stdout. Test modern and legacy client modes where supported by the pinned SDK. |
| MCP-07 | HTTP requires bearer authentication and loopback binding. | Missing/wrong token rejected before tools; token at least 32 characters; non-loopback bind refused. Token supplied through environment, never config literals or logs. |
| MCP-08 | Host examples respect product/config boundaries. | Parse example JSON/TOML; CLI help and documented launch entrypoint work. Do not claim real Codex/Claude/GPT session connectivity from examples alone. |
| MCP-09 | Existing Hive paths/dependencies remain intact. | Original application hashes unchanged; existing hive tests pass; adapter's independent environment passes its suite. |
| MCP-10 | Underlying failure limits stay visible. | Documentation explains lite engine F1/F2/F4/F13 remain unresolved, POST non-idempotency, cancellation/disconnect not run cancellation, no skill registry yet, no shared-tenant guarantee. |

## Failure, authority and compatibility

The MCP server inherits one trusted local operator's access to the configured Hive API. Static bearer authentication is a private single-principal gate, not OAuth, per-run authorization or multi-tenant isolation. Anyone granted that token can read runs and submit research under the service's configured providers. Do not expose publicly; shared deployment requires HIVE-009 and reviewed ingress/authentication.

Allow only HTTP loopback upstream origins and no redirects. IDs cannot become path traversal. Use a dedicated HTTP client with `trust_env=False`. Stream responses to enforce the byte cap before decoding; validate expected response shapes before reporting success. Emit safe protocol errors; do not return raw upstream exceptions/bodies. Cancellation propagates to the pending HTTP call but cannot undo a submission already accepted by Hive.

Read GET failures can be retried explicitly by the caller. POST is sent once: timeout or uncertain server failure can mean a run exists, so the caller must inspect local Hive state before resubmitting. No fake idempotency guarantee or in-memory “durable” deduplication. Do not expose a stop/resume operation absent from the current API.

Existing successful response fields remain JSON objects. Annotate reads as read-only/idempotent and submission as non-idempotent; annotations inform clients but do not grant permissions. Use SDK transport/version support rather than hand-writing JSON-RPC. Pin and lock adapter dependencies separately; test actual installed SDK APIs.

## Rollout, recovery and evidence

Start Hive separately, then launch the adapter. Disconnecting/stopping the adapter leaves accepted Hive jobs under Hive's existing lifecycle. Rollback removes client registration or stops adapter process; no database migration. HTTP server listens only on loopback; public TLS/tunnel operation and real host account registration are not performed by this task.

Use mock HTTP transport for deterministic failure oracles, plus subprocess/socket tests for actual transport/framing/auth. A separate process with existing app dependencies exercises real Hive routes using mock models and disposable database. No paid provider requests or real application databases. Record exact commands and limitations in the linked plan; full product/model quality and distributed readiness are not established by MCP success.

Self-review: narrow API seam, mutation ambiguity, authentication, protocol compatibility, dependency isolation, and capability honesty covered. Document review status is distinct from observed implementation verification. New security/hosting authority requires separate user authorization; ordinary local build/test continues within the selected request.
