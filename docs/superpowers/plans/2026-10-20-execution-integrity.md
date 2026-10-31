# Execution integrity implementation plan

> **For agentic workers:** Use `superpowers:executing-plans`; serial store/runtime edits, then one fresh whole-change reviewer.

**Goal:** Reject stale mutations and make every bounded lite run reach an inspectable outcome.
**Architecture:** SQLite transactions own assignment changes and dependency propagation. The runner supervises execution/renewal/watchdog tasks, enforces deadlines and checks authority before provider calls. Keep successful v1 output/citation shapes.
**Tech Stack:** Existing Python 3.12 asyncio/sqlite3/pytest; no new dependencies.
**Spec:** [HIVE-002](../specs/2026-10-19-execution-integrity-design.md), EXE-01–08.
**Status:** Verified, 2026-10-20.
**Authorization:** Direct user instruction 2026-10-20 to complete HIVE-001 then work on HIVE-002. Native serial execution continues on `hive-001-002-integrity`; no commit, push, deployment or real database maintenance.

## Global constraints and interface decisions

- HIVE-001 schema/key/eligibility behavior remains intact. No additional schema version for this slice.
- Lite task states retain pending/claimed/done/exhausted/failed and add explicit blocked. Do not implement HIVE-006 crash-resume or new modular engine.
- `heartbeat`, `release` and `mark_exhausted` require current worker/attempt/fence/lease in one transaction or conditional update, returning accepted/stale boolean. `mark_exhausted(task_id, reason, *, worker, attempt, fence, now=None, code='execution_error')` replaces unsafe ID-only internal use.
- `expire_leases` selects and transitions under `BEGIN IMMEDIATE`; separate handles cannot interleave a newer claim/renewal across its update.
- `validate_graph(run_id)` rejects missing/cross-run/cyclic dependencies and unknown kinds before execution. `block_unsatisfied(run_id)` records causal prerequisite IDs; independent work can continue. No-progress detection is transactional.
- `stop_run_tasks(run_id, code, reason)` is the local controller cleanup operation. It preserves accepted tasks and invalidates active assignments; pending work becomes blocked. No distributed coordinator claim is made.
- `run_hive` validates arguments before creating/planning a run. Positive finite task/run deadlines default to 600/1800 seconds; `heartbeat_s` defaults to `min(60, lease_s/5)` and must be below lease length. Workers/subtasks match API ceiling 8. Attempts are positive bounded integers supplied by configuration; default three.
- Logical task deadlines use one monotonic deadline across retries in this lite process. Persistent deadline/restart semantics belong to HIVE-006.
- Caller accepts optional `before_call` authority callback. Attempt contexts check ownership before each model dispatch. Running work is cancelled and awaited on lease loss; the store remains final publication authority.
- Transient tool/runtime/LLM failures retry within limits and backoff; schema/provenance/unknown-kind/invalid-output errors are terminal. Verifier outage raises execution failure, preserving proposed facts. Unsupported verdict remains a factual rejection. Full typed output redesign belongs to HIVE-010.
- API/CLI expose task/run timeouts with the same runner validation. Cancellation propagates to caller after recording stopped/cancelled cause and cleaning owned tasks. Unexpected supervisor failure records failed cause then propagates.

## Review focus

1. Same worker name reclaims, then old failure/release/heartbeat arrives: no mutation (Task 1).
2. Renewal competes with expiry on separate SQLite handles: valid owner survives or exactly one successor wins (Task 1).
3. Required failure coexists with independent work: descendants block, independent result survives (Task 1/2).
4. Provider operation outlives lease or parent cancellation: no new model subcall/late commit; no leaked loops (Task 2).
5. Verifier outage or malformed response: never falsely mark proposed evidence rejected (Task 2).

## Task 1: Store-owned assignment and dependency integrity

**Files:** `app/hive/store.py`, new `tests/test_hive_execution.py`; update diagnostic caller using removed unsafe exhaustion signature.
**Consumes:** HIVE-001 initialization/publication/eligibility seam.
**Produces:** guarded mutation signatures and graph/cleanup operations above.

- [x] Add stale success/failure/release/renewal tests, including expired same identity and completed tasks.
- [x] Add separate-handle renewal/expiry/claim tests with controlled clocks; competing claim test permits exactly one owner.
- [x] Add failed-dependency cascade, independent completion, missing/cross-run/cyclic graph and no-progress cases.
- [x] Run new tests RED; implement transactional operations; rerun store/migration/hive suites GREEN.

## Task 2: Supervised bounded execution

**Files:** `app/hive/runner.py`, `app/hive/agents.py`, `app/hive/cli.py`, `app/api/routes_hive.py`; extend execution/API/CLI tests.
**Consumes:** Task 1 mutation/graph contracts.
**Produces:** bounded `run_hive` and consistent timeout inputs, independent factual/execution outcomes.

- [x] Add permanent/transient failures, unhealthy supervisor, renewal past one lease, lease loss between subcalls, task/run deadline, cancellation and invalid-input tests. Use explicit events/barriers and real store; use short elapsed deadlines only for the timeout contract itself.
- [x] Run tests RED; implement bounded retry/renewal/supervision and caller guard. Preserve unsupported-verdict behavior, propagate outage/malformed assessment as execution errors.
- [x] Add API/CLI timeout argument validation and successful compatibility checks. Run focused tests GREEN; full suite once, name unrelated failures; authorized local socket rerun when necessary.

## Task 3: Review and delivery evidence

- [x] One independent whole-change review covering HIVE-001 and HIVE-002; repair important findings with RED→GREEN regression cases.
- [x] Map EVI-01–08 and EXE-01–08 to observed tests; update plans/index/register/architecture status truthfully. Refresh Graphify source map/provenance, preserving original diagnosis artifacts and source-pinned architecture diagrams.
- [x] Report migration commands and remaining environment limits. Do not migrate user data or claim Postgres/capacity/Jev readiness.

## Completed execution — 2026-10-20

All tasks completed in native serial execution following the direct user instruction. [Execution ledger](../../reports/hive-integrity/execution-ledger.md), [requirement map and commands](../../reports/hive-integrity/summary.md), [independent review and repairs](../../reports/hive-integrity/review.md). Focused acceptance includes real SQLite process-death/reopen and concurrency barriers, historical provenance, API/CLI and lease-loss cases. Full-suite environment failures remain named in the evidence and are not claimed as passes. No real-data maintenance, staging, commit or push. Source graph refreshed; source-pinned architecture diagrams remain historical artifacts.

Earlier pending-review/no-implementation statements in dated baseline sections describe their original state and are superseded by this completion record. Full modular architecture remains unimplemented.
