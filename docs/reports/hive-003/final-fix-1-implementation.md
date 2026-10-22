# HIVE-003 final fix 1 — publication deadlines

Date: 2026-10-21. Governing contract: approved `docs/superpowers/specs/2026-10-20-supported-reports-design.md`, REP-08/12, and the final-repair section of `docs/superpowers/plans/2026-10-20-supported-reports.md`. Source is frozen for the controller's scoped re-review and graph refresh. This report does not mark the spec Verified or the review approved.

## Cause and change

The runner checked the logical task deadline before synchronous `publish_report`, but the call could then wait on the local mutex or SQLite `BEGIN IMMEDIATE` until that deadline passed. The store checked the wall-clock lease after waiting and had no logical deadline, so a live lease could still publish a late artifact. The independent reviewer reproduced this with a 40 ms deadline and 150 ms local-lock wait: task timeout yielded a completed run/report; run timeout stopped the run but left a completed writer report.

`run_hive` now passes absolute task and whole-run monotonic deadlines to `HiveStore.publish_report`. The store checks them after the local and SQLite lock waits, following the existing stale-assignment/lease check, and again immediately before the report task completion write. An expired task deadline raises `TimeoutError`, yielding the existing `task_timeout` exhausted-task semantics. An expired run deadline raises `RunDeadlineExceeded`, which propagates through the worker to the existing `run_timeout` stop/abort path. The transaction rolls back on either exception. No runner guard or caller callback runs under the store's non-reentrant lock; selection, provenance and canonical-artifact checks remain inside the same transaction. Direct store callers can omit both optional deadline keywords, and no persisted schema/public API shape changed.

The store uses `time.monotonic()` only for logical deadlines and `time.time()` only for the lease. The asyncio timer uses an independently derived `loop.time()` deadline. The initial implementation mistakenly passed the monotonic store timestamp to `asyncio.timeout_at`; the real MCP/Uvicorn loop exposed the different clock origin and immediately stopped a run. A real offset-loop regression now fails against that mixed-clock line and passes with the corrected timer.

## Behavioral evidence

The new scheduler/router/store test runs valid selection against disposable file-backed SQLite, with mocked providers and a 3-second live lease. A second thread holds either the actual store mutex or an actual SQLite `BEGIN IMMEDIATE` write lock for 300 ms across a 100 ms task or run deadline. Four cases failed before the production repair: both task cases returned a nonempty completed report; both run cases retained a completed writer artifact. All four pass after repair, asserting the separate `task_timeout` and `run_timeout` outcomes, empty run/writer reports, no completed writer, unchanged one verified/one rejected fact, and no surviving `hive:` tasks. The direct-store stale-assignment test also passes an expired deadline with malformed content and still receives `False`, preserving precedence.

The clock-origin test uses a real `asyncio.SelectorEventLoop` with an offset `time()` origin and a real successful writer run. It failed with `status='stopped'` against the initial mixed-clock line, then passed after correction. The first MCP run independently failed 1/54 (real route stopped at research claim); the retained disposable database showed `run_timeout`. Final MCP passes 54/54.

Machine-readable exact argv, environment overrides, cwd, log paths, timestamps where captured, and exit codes are in `final-fix-1-commands.json` in this directory. All test logs are under `docs/reports/hive-003/`. The four-case RED log is `final-fix-1-red.log` (exit 1); its focused GREEN is `final-fix-1-green-focused.log` (exit 0). Clock RED/GREEN are `final-fix-1-offset-red.log` (exit 1) and `final-fix-1-offset-green.log` (exit 0). The intermediate failing MCP log is retained as `final-fix-1-mcp-pre-clock-fix.log` (exit 1).

Final checks after the source fix:

| Receipt key | Actual result |
|---|---|
| `runner_store` | 112 passed, exit 0. |
| `focused` | 360 passed across the ten named Hive files, including Chromium rendering, exit 0. |
| `mcp` | 54 passed through the real route, exit 0. |
| `full` | 387 passed, 11 failed, exit 1. Ten failures import removed `HfFolder` through the installed embedding stack; one lacks the Anthropic SDK. No HIVE-003 test failed. |

`git diff --check` on the four owned source/test files passed. The existing pytest-asyncio fixture-loop-scope deprecation warning remains. Frontend lint/build were not repeated because this repair changes no UI or dependency. No real provider or application data was used. Controller owns spec/status/graph reconciliation and scoped independent re-review.
