# Hive MCP implementation review and fixes

Date: 2026-10-20. Scope: `integrations/mcp`, HIVE-013 design/plan, host examples and documentation. Fresh read-only reviewer used the Superpowers code-review workflow; no independent review of unrelated application repairs, real host accounts, public hosting or research quality was claimed.

## Review findings and repairs

| ID | Finding and reproduced effect | Repair | Observed verification |
|---|---|---|---|
| MCP-R1 | HTTPX inactivity timeout allowed a continuously trickling request to succeed after 10.53 seconds, exceeding the documented deadline. | Total asyncio deadline wraps request/body/validation, retaining read failure versus ambiguous submission semantics. | `test_total_deadline_stops_a_continuously_trickling_response` failed for GET/POST before repair, then passed. |
| MCP-R2 | Roughly 3 KB of deeply nested accepted JSON escaped API validation and failed SDK serialization with a generic submission error. | Catch parser recursion failure and reject nesting beyond 32 inside the safe API error boundary. Non-finite numeric values also reject before output. | `test_deep_json_is_rejected_inside_safe_api_error_boundary`, GET/POST at depths 64/1200: four failures before repair, then passes with correct error class. |
| MCP-R3 | HTTPX decompressed before the byte guard: an 8,175-byte gzip response expanded to 8 MiB, with about 22 MiB traced peak in reviewer's probe. | Request identity encoding; reject other encodings before reading; cap raw chunks before JSON parsing. | `test_encoded_response_is_rejected_before_decompression`, GET/POST: both failed before repair; now assert body never consumed and identity requested. |
| MCP-R4 | Initial contract test found SDK silently ignored extra tool arguments. | Public tool seam forbids unknown arguments and publishes `additionalProperties: false`. | `test_invalid_submission_never_reaches_upstream` demonstrated the unwanted API call; all input cases now pass. |

Reviewer severity: three P2 findings, treated as Important. One repair pass completed; no second review is represented as performed. Eight targeted regression cases failed before the three repairs and passed afterward; final whole adapter suite passed 54/54 in the locked environment.

Review found no bearer bypass, automatic submission retry, caller-selected upstream host/path, or unrelated app mutation. This is scoped code-review evidence, not a security certification.

## Behavior considered outside this review

- F1/F2/F4/F13 lite-engine repairs and production research quality: existing separate work; adapter does not close those findings.
- Public ingress, OAuth and shared callers: outside local single-operator build; enabling them needs the HIVE-009 scope.
- Actual Codex/Claude/GPT account registration: examples only; no personal configuration or paid model test.
- Parent-executed socket/application tests: reviewer did not independently reproduce them. Their exact commands/results remain in [the execution ledger](../superpowers/plans/2026-10-20-mcp-server.md).

These exclusions do not weaken the adapter's request/response/auth bounds. No unresolved Important adapter finding remains after the recorded tests. Maintainer document review remains distinct from implementation verification.
