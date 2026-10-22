# HIVE-003 final fix 2 — reader-blocked COMMIT

Date: 2026-10-21. Governing scope: approved `docs/superpowers/specs/2026-10-20-supported-reports-design.md`, REP-08/12, linked plan's final-review repair, and `final-fix-2-brief.md`. This repairs the remaining original I1. Source is frozen for controller-owned graph refresh and scoped independent re-review; this report does not mark the spec Verified or claim reviewer approval.

## Root cause and repair

The first repair correctly checked absolute process-monotonic task/run deadlines after local mutex and SQLite write-lock waits, and again before the completion write. But default rollback-journal readers can coexist with `BEGIN IMMEDIATE` and hold a SHARED lock until COMMIT needs EXCLUSIVE. That final lock wait happened after the checks, allowing a late completed report even with a live lease.

Deadline-bound `publish_report` now uses `BEGIN EXCLUSIVE`. It acquires the lock required for commit before assignment/deadline/provenance/artifact checks or completion writes. Existing callers without either optional deadline retain `BEGIN IMMEDIATE`. No journal mode, schema, dependency, persisted monotonic timestamp, public API shape, runner clock, or provider boundary changed. In WAL, EXCLUSIVE has the same write-lock behavior as IMMEDIATE and readers do not block commit; a held-reader WAL compatibility test verifies successful atomic publication and the reader's old snapshot.

The transaction's try/except now includes BEGIN. Rollback is conditional on `in_transaction`, avoiding a secondary “no transaction is active” error when BEGIN fails. For deadline-bound calls only, an actual SQLite BUSY primary error (including extended BUSY codes) is converted to `ReportPublicationBusy(RuntimeError)` after rollback and a fresh deadline check. The existing runner classifies RuntimeError as retryable under its existing attempt cap, logical deadline and backoff. If the run/task cutoff elapsed during lock acquisition, the existing `RunDeadlineExceeded` / `TimeoutError` wins instead. Other SQLite errors remain errors. No runner or reporting-module edit was needed.

The connection's `busy_timeout` is never changed. Tests verify its exact configured value after success, validation rollback, stale assignment, BEGIN failure and task/run timeout. This avoids a temporary connection policy and restoration hazards. Stale-assignment rejection remains before caller-content validation after acquiring the transaction. Canonical rendering and selected provenance checks remain in that transaction, with a deadline check immediately before publication writes. No arbitrary caller callback or non-reentrant-lock reacquisition was introduced.

Tradeoff: the short publication transaction blocks new rollback-journal readers while checking/committing its bounded artifact. It contains no provider call or model await. Existing synchronous lock waits can still delay the event loop up to the configured SQLite busy timeout; the repair prevents a report from committing after a deadline crossed during contention rather than promising prompt asynchronous cancellation of those waits. A general asynchronous-store rewrite remains out of scope.

Changed source/test files only:

- `app/hive/store.py`
- `tests/test_hive_report_execution.py`
- `tests/test_hive_report_store.py`

## Behavioral RED and GREEN

Before production edits, the expanded real-lock execution test added a third lock type without removing or weakening the previous mutex/writer assertions. A separate connection begins a read transaction and SELECTs actual task rows in default `delete` journal mode, holding its SHARED lock for 300 ms across a 100 ms logical deadline with a 3-second lease. Both reader variants failed: task timeout returned a nonempty report; run timeout retained a done writer. The transient-reader test also failed because raw SQLite OperationalError exhausted the task instead of retrying. Receipt `red`: **3 failed**, exit 1.

The direct-store policy cases independently reproduced raw lock errors in the busy/task-expired/run-expired variants, with three existing-compatible outcomes passing. Receipt `policy-red`: **3 failed, 3 passed**, exit 1. The failures were behavioral SQLite publication failures, not missing interfaces/imports.

After repair, the focused lock/deadline/clock/policy selection passed **14 tests**, exit 0 (`green`). Final affected-suite and broad-suite runs also include the strengthened exact run-timeout type and additional held-reader WAL compatibility test.

The timeout regressions assert empty run and writer reports, no done writer, distinct task/run timeout metadata, unchanged verified/rejected facts, a live lease, joined/closed holder thread/connection, and no surviving `hive:` tasks. The positive transient-reader case uses a 17 ms configured busy timeout: the first real publication fails while its reader is active, the reader releases before the 1-second deadline, and the second attempt succeeds. It asserts exactly two attempts, one retryable execution error, existing retry backoff, preserved facts, no lingering transaction or child task, and unchanged busy timeout. Six direct-store cases use a separate 19 ms configured value and verify success, invalid artifact, stale assignment, busy BEGIN, task expiry and run expiry. All prior cancellation, stale assignment, provenance, canonical artifact, mutex/writer lock and offset-loop checks remain.

## Executed checks

Exact argv, all environment overrides, cwd, UTC timestamps, exit code and log paths are recorded in [the command receipts](../../../docs/reports/hive-003/final-fix-2-commands.json). Each log is in `docs/reports/hive-003/` with the `final-fix-2-` prefix. Python was `/opt/anaconda3/bin/python`, `DEBUG=false`; Chromium used `/tmp/hive-003-browsers`. Focused/MCP/full checks ran with permitted Chromium/loopback access. No real provider or application database was used.

| Receipt | Actual result |
|---|---|
| `red` | 3 failed before production repair; exit 1. |
| `policy-red` | 3 failed, 3 passed before production repair; exit 1. |
| `green` | 14 passed, 63 deselected; exit 0. |
| `runner-store` | 122 passed across report execution, report store and Hive execution; exit 0. |
| `focused` | 370 passed across the ten required Hive/API files, including actual Chromium rendering; exit 0. |
| `mcp` | 54 successful test indicators, no skips, exit 0. `HIVE_APP_PYTHON` was set and the real stdio → HTTP → SQLite/mock-provider route ran. |
| `full` | 397 passed, 11 failed; exit 1. Failures listed below. |
| `diff-check` | Owned source/test files pass `git diff --check`; exit 0. |

Full-suite failures remain the observed environment cases, not HIVE-003 failures:

- Missing Anthropic SDK: `tests/test_llm_sdk_wiring.py::test_sdk_roundtrip[anthropic-ANTHROPIC_API_KEY-hi-anthropic-tokens1]`.
- Removed `huggingface_hub.HfFolder` imported by the installed embedding stack: `tests/test_semantic_cache.py::TestSemanticCache::test_set_and_get`, `test_semantic_similarity_hit`, `test_cache_miss`, `test_context_key`, `test_invalidate`, `test_stats`; and `tests/test_tools_vectordb.py::TestChromaDB::test_chroma_upsert`, `test_chroma_query`, `test_chroma_upsert_deduplication`, `test_chroma_delete_source`.

Existing pytest-asyncio fixture-loop-scope deprecation warning remains. Unchanged frontend lint/build were not repeated as directed. No commits, pushes, new subagents, dependency installs or paid calls were performed. Controller retains problem-register/spec/plan/status reconciliation, graph refresh and independent re-review ownership.
