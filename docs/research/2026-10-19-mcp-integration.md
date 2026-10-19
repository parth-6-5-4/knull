# MCP integration research

Date: 2026-10-19. Status: primary-source research; no integration implemented or tested. Direction is a design decision still requiring explicit selection. No dependency installation, provider calls, credentials, or personal host configuration changes were performed.

Follow-up 2026-10-20: user selected external clients → Hive MCP server. This dated research note retains its original evidence limits; implementation, installed SDK verification and current test results are tracked in [HIVE-013's ledger](../superpowers/plans/2026-10-20-mcp-server.md).

## Direction and boundaries

MCP separates the host application, its client connections, and servers exposing tools, resources, and prompts. It does not choose an application's model or agent orchestration. Therefore these are distinct proposals: external GPT/Claude Code/Codex clients call a **Hive MCP server**; Hive becomes an **MCP client** consuming external tools; Hive delegates work to a **coding agent**. Supporting the first does not implement the other two. [Official MCP architecture](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture)

Recommendation, conditional on the user's intended direction: start with a narrow Hive server exposing explicitly permitted registry/run operations, while retaining Hive's deterministic execution authority. Keep any future tool consumption or coding-agent delegation behind separate interfaces and specifications. This is a project recommendation, not an MCP requirement or a claim about existing implementation.

## Current SDK and protocol

- PyPI's current official `mcp` release is **2.3.0**, uploaded October 2, 2026. [Published package](https://pypi.org/project/mcp/2.3.0/)
- The published tag requires Python **>=3.10**. Upstream `main` already requires **>=3.11**, so use release-tagged metadata when choosing a pin. [v2.3.0 metadata](https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/v2.3.0/pyproject.toml), [main metadata](https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/pyproject.toml)
- v2's high-level API is `from mcp.server import MCPServer` and `from mcp import Client`; the SDK supports stdio, Streamable HTTP, and legacy SSE. [Tagged README](https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/v2.3.0/README.md)
- `FastMCP` and `mcp.server.fastmcp` are v1 APIs, renamed in v2. HTTP transport options moved from construction into `run()` or `streamable_http_app()`. Mounted applications must run the session manager in their owning application's lifespan. [Official v1-to-v2 migration](https://py.sdk.modelcontextprotocol.io/migration/)
- Latest protocol resolves to **2026-07-28**. Modern requests carry version/capabilities in per-request metadata and use `server/discover`; they do not require an `initialize` handshake. Revisions **2025-11-25 and earlier** are legacy handshake protocols. A dual-era server can support both; a legacy client cannot automatically fall forward to a modern-only server. [Versioning and compatibility](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning)
- The tagged SDK server registers `server/discover`, reserves `initialize` for its runner, and calls `serve_dual_era_loop`. This is source evidence of an SDK compatibility boundary, not observed compatibility with any installed client. [v2.3.0 server source](https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/v2.3.0/src/mcp/server/lowlevel/server.py)

Standard transports are stdio, using newline-delimited messages on a client-launched process, and Streamable HTTP, using POST to one endpoint with JSON or request-scoped SSE replies. Implement transport/version handling through the selected SDK, then test the specific client versions. [Current transport specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)

## Dependency compatibility with this repository

Inspected local [requirements.txt](../../requirements.txt): FastAPI 0.109.0, Pydantic 2.5.3, httpx 0.26.0, uvicorn 0.27.0, python-multipart 0.0.6, and sse-starlette 1.8.2 are exact pins. `mcp` is absent. This is declared-dependency evidence; installed package versions and a complete resolver result were not collected.

The MCP release's direct metadata establishes these conflicts without installing anything:

| Package | Hive pin | MCP 2.3.0 requirement | Assessment |
|---|---|---|---|
| Pydantic | 2.5.3 | >=2.12.0 | Incompatible |
| python-multipart | 0.0.6 | >=0.0.9 | Incompatible |
| sse-starlette | 1.8.2 | >=3.0.0 | Incompatible |
| uvicorn | 0.27.0 | >=0.31.1 outside Emscripten | Incompatible on normal host platforms |
| Starlette | Transitive through FastAPI | >=0.27 on Python <3.14; >=0.48 on Python >=3.14 | Python-dependent; see below |
| httpx | 0.26.0 | `httpx2>=2.10.0` | Distinct package name; no direct httpx conflict established |

Source: [MCP 2.3.0 dependency metadata](https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/v2.3.0/pyproject.toml). FastAPI 0.109.0 requires Starlette **>=0.35.0,<0.36.0**. Consequently MCP's direct Starlette requirement overlaps on Python <3.14, but conflicts on Python >=3.14. Other transitives can impose additional restrictions; no whole-environment compatibility is claimed. [FastAPI 0.109.0 metadata](https://raw.githubusercontent.com/fastapi/fastapi/0.109.0/pyproject.toml)

Recommendation: put an optional MCP adapter in its own dependency project/environment and process, with a narrow application-service/API boundary. Installing an optional requirements file into the same interpreter does **not** isolate incompatible dependencies. Avoid importing the whole FastAPI application merely to start MCP. If shared-environment mounting is chosen instead, make dependency modernization an explicit reviewed scope with compatibility checks. This recommendation avoids silently broadening HIVE-011; it is not an implemented isolation guarantee.

## Client compatibility and configuration

| Consumer | Verified official integration surface | Configuration boundary |
|---|---|---|
| Claude Code | Local stdio process or remote HTTP; `claude mcp add --transport http hive <URL>` or `claude mcp add hive -- <command> <args>` | Project `.mcp.json` supports shared configuration; project server approval is still required. Do not interpret a successful add as a successful connection. |
| Codex | STDIO and Streamable HTTP; stdio uses `command`/`args`, HTTP uses `url` | `[mcp_servers.hive]` in user `config.toml` or trusted project `.codex/config.toml`; bearer tokens can come from `bearer_token_env_var`. |
| GPT through Responses API | Tool entry `type: "mcp"`, `server_label`, and `server_url`; remote servers may use Streamable HTTP or HTTP/SSE | Public remote endpoint, or separate Secure MCP Tunnel using `tunnel_id` for private/local servers. A local stdio config is not the remote API connection. |

Sources: [Claude Code MCP](https://code.claude.com/docs/en/mcp), [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), [Responses API MCP](https://developers.openai.com/api/docs/guides/tools-connectors-mcp).

Codex's shared host configuration is also used by the ChatGPT desktop app and IDE extension; ChatGPT web uses installed plugins and does not read local Codex configuration files. Therefore “GPT” needs a named product surface in the design. [Codex/ChatGPT configuration boundaries](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

These shapes document supported configuration; none were written to personal files. Exact executable paths, adapter entrypoints, endpoint ownership, authentication, client versions and allowed tools remain implementation choices requiring verification.

## Coding agents exposed as servers

Claude Code documents `claude mcp serve` as a stdio server exposing **Claude Code's tools**. It explicitly makes the calling client responsible for individual tool confirmations. This does not establish delegation to Claude's own reasoning loop. [Claude Code server mode](https://code.claude.com/docs/en/mcp#use-claude-code-as-an-mcp-server)

Current OpenAI documentation says **`codex mcp-server` and `codex-mcp-server` have been removed**. Its replacement app server uses its own JSON-RPC protocol, is not MCP or a drop-in MCP-client replacement, and is experimental and unsupported for production workloads. Codex continues consuming external MCP servers. Old Agents SDK examples are explicitly unsupported. [Official removal notice](https://learn.chatgpt.com/docs/mcp-server)

Inference: if the user intends Hive to use complete Claude/Codex agents as workers, specify that as a separate worker-adapter effort. Do not represent MCP client setup, Claude's tool server, or the removed Codex command as satisfying agent delegation.

## Evidence limits and implementation gates

This note verifies documentation, release-tagged source, and local dependency declarations. It does not verify live host commands, SDK installation/imports, authentication, network reachability, tool execution, cancellation, retries, budget enforcement, evidence isolation, or provider quality. Mutable documentation can change after this date.

Before claiming a connection works, the linked plan should record: selected direction/product surfaces; pinned adapter dependency resolution; modern/legacy version discovery with the actual client versions; tool listing/schema/call results; unauthorized and unknown-tool failures; cancellation/timeout behavior; and confirmation that only authorized Hive operations are exposed. Remote deployment and personal configuration require their own authorized scope. No protocol feature or passing mock should be described as evidence that Hive's application-level guarantees hold.
