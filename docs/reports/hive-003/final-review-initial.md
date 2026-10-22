# HIVE-003 independent whole-change review

Date: 2026-10-21. Scope: approved revision 1 of `docs/superpowers/specs/2026-10-20-supported-reports-design.md` and its linked implementation plan, against `whole-change-review.diff` (foundation `0747ac4`, published core plus Task 5 edits). This is a lite reporting readiness review, not a general production-readiness assessment.

## Strengths

- The writer's authority is restricted to ordered IDs. `parse_selection` validates the complete bounded response, rejects duplicate object keys and unknown fields, and rejects the whole selection on forged/duplicate IDs. There is no prose salvage or surviving `final_gate` runtime path (`app/hive/reporting.py:178`, `app/hive/agents.py:194`).
- Accepted claim wording and source metadata are rendered by code. Newline normalization and HTML entity encoding preserve data inside code-owned structure. The actual `marked.parse(..., { async: false })` invocation matches the shipped `ReportView`; the browser harness checks DOM text, headings, references, attribute allowlists, network requests and wrapping (`app/hive/reporting.py:204`, `web/scripts/check-hive-report.mjs:44`, `web/src/components/ReportView.tsx:5`).
- The store coherently reads eligible facts/sources, releases its transaction before model work, rechecks selected source bindings under `BEGIN IMMEDIATE`, recomputes the artifact, and commits result/completion together. Generic writer publication and verifier-path completion bypasses are blocked (`app/hive/store.py:180`, `:222`, `:242`, `:257`). The preceding fix correctly samples lease time after the write-lock wait.
- Execution distinguishes empty valid selection from malformed output, transport errors and changed snapshots, without changing accepted/rejected fact counts. Finalization copies the committed artifact and requires a genuine positive finding count, current policy, literal true gate and nonempty report (`app/hive/runner.py:158`, `:230`).
- Compatibility tests use actual API/CLI paths and disposable storage. Historical report bytes remain untouched, while new stored results carry selected IDs and claim/source digests. The diagnostic adapters preserve their other observations and do not overwrite the dated baselines.

## Issues

### Critical

None identified.

### Important

**I1 — Logical task/run deadlines can expire during publication lock acquisition, yet a successful writer artifact is committed.**

- Location: `app/hive/runner.py:112`–`113`; publication boundary `app/hive/store.py:261`–`265` and `:300`–`301`.
- The post-writer `guard()` checks the logical task deadline before calling synchronous `publish_report`. Acquiring the store lock or SQLite write lock may then block the event-loop thread past that deadline. Publication checks the longer wall-clock lease after acquiring the lock, but it has no logical-deadline input. The asyncio timeout callback cannot run while the synchronous call blocks, and the completed execution can therefore be accepted as successful before the overdue callback rejects it.
- This is observable with a valid, timely selection and an otherwise unchanged snapshot. A second thread held the real store lock for 150 ms after the guard, with `task_timeout_s=0.04` and the normal live lease. The real scheduler/router returned `status="done"`, a nonempty report and writer task `done`, with no task-error event. Measured publication wait was **0.15263954107649624 seconds**. No provider call, persistent database, or application data was used.
- The same named seam also violates the whole-run publication deadline. With `task_timeout_s=5`, `run_timeout_s=0.04` and the same 150 ms contention, the run correctly ends `stopped` with an empty run report and `run_timeout` gate, but the writer task has already committed `done` with a nonempty report after the deadline. Measured wait was **0.15047220804262906 seconds**. The subsequent abort preserves completed task results (`app/hive/store.py:408`), so it does not remove that late artifact. This variant does not falsely claim that the final run itself reports success.
- Impact: a writer can publish success after its configured logical task deadline, violating REP-12 and Task 4's deadline/no-late-publication acceptance behavior. This is distinct from the fixed expired-lease race and the deferred early claim/sweep clock liveness concern. The lease can remain fully valid throughout this failure.
- Required repair: carry both the attempt and whole-run absolute monotonic deadlines to the publication boundary and reject expiry after all blocking lock acquisition, inside the same transaction before completing the task; preserve rollback and the typed timeout outcome. Check immediately before completion as appropriate so deterministic rendering/revalidation cannot cross the deadline unnoticed. Avoid calling the existing `guard()` while holding the non-reentrant store lock, because it calls `store.owns()` and would deadlock. Addressing this publication boundary does not require a general asynchronous-store rewrite.
- Required regression: hold an actual store/SQLite lock across a short task deadline while keeping the lease live, then repeat with a short run deadline and long task deadline. Assert no report/result/completion publication, a timeout execution outcome rather than no-findings, unchanged facts, and no surviving `hive:` children. Retain the existing provider-cancellation and expired-lease cases.

### Minor

No new change-specific Minor finding. Existing pytest-asyncio warning noise is classified below rather than promoted to a reporting blocker.

## Reproduction executed

Executed from the repository root with `PYTHONDONTWRITEBYTECODE=1 DEBUG=false /opt/anaconda3/bin/python -` and the following code. The wrapper only arranges real lock contention at the publication seam; the original publisher, scheduler, selection renderer and mock-router flow execute unchanged.

```python
import asyncio, json, threading, time
from app.hive import run_hive
from app.hive.store import HiveStore
from app.llm import set_router
from tests.test_hive_report_execution import install_writer, select_first
from tests.test_hive import fake_search

async def main():
    store = HiveStore(':memory:')
    install_writer(select_first)
    original = store.publish_report
    timing = {}

    def contended(*args, **kwargs):
        acquired = threading.Event()
        def hold():
            with store._lock:
                acquired.set()
                time.sleep(.15)
        thread = threading.Thread(target=hold)
        thread.start()
        acquired.wait()
        timing['started'] = time.monotonic()
        outcome = original(*args, **kwargs)
        timing['elapsed'] = time.monotonic() - timing['started']
        thread.join()
        return outcome

    store.publish_report = contended
    try:
        result = await run_hive(
            'Attention research', store, workers=1, max_subtasks=1,
            search=fake_search, tick_s=.005, task_timeout_s=.04)
        task = next(t for t in store.tasks(result.run_id) if t['kind'] == 'write')
        print(json.dumps({
            'status': result.status, 'report_present': bool(result.report),
            'writer_status': task['status'], 'publication_wait_s': timing['elapsed'],
            'task_timeout_s': .04,
            'errors': [e for e in result.events if e['kind'] == 'task_error']}))
    finally:
        set_router(None)
        store.db.close()

asyncio.run(main())
```

Observed output (exit 0):

```json
{"status":"done","report_present":true,"writer_status":"done","publication_wait_s":0.15263954107649624,"task_timeout_s":0.04,"errors":[]}
```

The second executed variant used the same command and setup, changed the `run_hive` options to `task_timeout_s=5, run_timeout_s=.04`, and additionally printed `bool((task['result'] or {}).get('report'))` and `result.gate`. Observed output (exit 0):

```json
{"status":"stopped","report_present":false,"writer_status":"done","writer_report_present":true,"publication_wait_s":0.15047220804262906,"task_timeout_s":5,"run_timeout_s":0.04,"gate":{"code":"run_timeout","reason":"run deadline exceeded"},"errors":[]}
```

## Spec alignment and evidence assessed

| Requirements | Assessment |
|---|---|
| REP-01 | Same-run verified joined rows, stable first-32 window, and coherent count/rows read transaction match the contract. File-backed coherence fixture uses a second connection with test-only WAL. |
| REP-02/03 | Strict whole-response JSON, bounded UTF-8 input, exact field/type checks, unique snapshot-owned IDs, maximum 16 selected, explicit empty selection. No material gap found. |
| REP-04/05 | Claims come only from snapshot data. Code owns fixed headings, citation anchors and source structure. Encoding is exercised through the shipped parser and browser DOM. No material gap found in new generated reports. |
| REP-06 | Only selected pinned sources are emitted; unsafe URL syntax remains literal with bounded warnings. Selected fact/source mutation or loss prevents publication. |
| REP-07 | Nonempty valid reports finish `done`; zero candidates/selection produce empty blocked reports; malformed prose exhausts rather than succeeding. |
| REP-08 | Selected acceptance state and full binding equality are checked under the same write transaction as completion, with stale assignment rejection before caller-content validation. Lease expiry after contention is covered; logical deadline is I1. |
| REP-09 | Stored gate carries policy, ordered IDs, counts, assignment, warnings, source identities and content digests; reopening is tested. Raw evidence/quote text is not duplicated in ordinary result payloads. |
| REP-10 | Explicit candidate, per-field, aggregate model input, response, selection-count and rendered-output limits; boundary/one-over tests; no claim truncation. |
| REP-11 | API/MCP retain report-string shapes; CLI/direct gate remains additive; historical byte preservation is covered. Shared tolerant JSON behavior remains for other roles. |
| REP-12 | Typed malformed-input/selection failure, snapshot retries, transport handling and provider cancellation are sound in inspected paths, but I1 leaves late publication possible after a blocking lock wait. |

Read the approved spec and plan, project workflow/index and domain guidance, applicable architecture/graph guidance, runtime reporting/producer/publication/finalization paths, modified tests/diagnostics, task reviews, requirement mapping and evidence records. Focused outside-diff checks covered actual researcher status construction, API and CLI projections, MCP report passthrough, the shipped React parser invocation, and surrounding cancellation/supervision code. Graph capture was navigation only; claims above were checked against source.

Fresh checks in this review:

- SHA-256 verification: **17/17 frozen review files matched** `whole-change-source-hashes.json`; **121/121 graph provenance source files matched** their recorded hashes.
- Executed the two specific in-memory lock/deadline reproductions above. They demonstrate I1 for task and run deadlines; they are not passing acceptance tests.
- Inspected the recorded mobile rendering capture `report-fixture-0-390x844.png`: hostile Markdown/HTML is displayed as literal text and wraps within the report. No new browser run or full-console visual verification was performed.

Previously executed delivery evidence inspected, not rerun by this reviewer: focused **355 passed**, including the actual marked/Chromium fixture; **18 viewport checks** across nine fixtures with no recorded page errors or network requests; CLI/API **26 passed**; MCP **54 passed** with real local route/no shown skips; prompt **6 passed**; reported successful frontend lint/build. The permitted full-suite log remains **382 passed, 11 failed**, comprising ten `HfFolder` embedding import failures and one missing Anthropic SDK test. These failures are not counted as passes and do not explain or invalidate I1. Existing passing task reviews do not substitute for this whole-change finding.

No implementation/index/branch mutation, commit, push, nested reviewer or broad-suite rerun was performed. This review file is the only checkout output written.

## Declined to judge

- Original verifier semantic accuracy or truth of accepted claims: HIVE-003 preserves accepted text; it is not a model-quality/entailment qualification and no live provider evaluation was authorized.
- Rewriting/revoking an already committed report when facts change later: explicitly owned by HIVE-006; this contract ends at report-task publication.
- Sanitizing arbitrary saved or historical Markdown in `ReportView`: F3-D/HIVE-005; the new renderer and fixture do not secure the entire historical consumer.
- Full-console layout, keyboard/accessibility behavior, browser coverage beyond recorded Chromium fixtures, and a frontend redesign: no application UI implementation changed; current evidence is report-only, with Impeccable hardening and Emil readability principles applied to that boundary.
- Global token admission, concurrent budget overspend, provider response memory limits before the report parser, and distributed capacity: HIVE-004/006; report-local byte/count bounds are assessed here, global accounting is not.
- Early `claim`/`expire_leases` clock sampling and resulting liveness: separately tracked F3-F; it does not excuse I1's new report-publication deadline gap.
- Unchanged trusted-controller powers (`finish_run`, direct SQLite access, caller-created snapshots, generic research seeding of verified rows): these are not untrusted external/model mutation APIs in this lite path. The actual researcher constructs `status="proposed"`; the verifier changes it; the report executor uses store-produced snapshots. I assessed supported writer completion bypasses, not an adversarial Python process with the connection or controller authority.
- Protection against arbitrary tampering with task-result JSON after publication: outside the publication-time contract. Finalization's shape checks are fail-closed consistency defenses, not an integrity proof against a malicious database writer.
- HTTP links to private/local addresses and destination reputation: renderer never fetches URLs; the approved URL policy validates absolute HTTP(S) structure and inert unsafe syntax, not destination trust or SSRF protection for a separate fetcher.
- Durable restart/resume, multi-controller lifecycle authority, manifests and post-publication run cancellation races: HIVE-006. Inspected current writer cancellation/cleanup only; no broader durable-runtime claim.
- Legacy LangGraph semantics, separate HIVE-001/002 foundation changes, licensing, MCP hardening and architecture-artifact changes outside the frozen HIVE-003 scope: independent changes; only concrete reporting producer/consumer seams were inspected.
- Installed embedding/Anthropic dependency failures and pytest-asyncio warning cleanup: HIVE-011/environment maintenance. Recorded full-suite failures remain visible; no unrelated dependency repair is requested by this review.
- Source-graph extraction completeness and the known migration-fixture static self-loop: graph is an undirected navigation aid, not correctness evidence; current hashes were checked, no semantic graph calls or graph-quality audit performed.
- Final document/status reconciliation and publication handoff: controller-owned completion work, explicitly pending at dispatch. Current draft/In progress status is appropriate until I1 is resolved and the delivery records are reconciled.

## Assessment

**Ready to merge this lite reporting change? With fixes — I1 is a blocking Important finding.**

The strict selection, deterministic rendering, selected-provenance recheck and compatibility changes are well aligned with the approved contract. Repair and independently re-review the logical-deadline publication gap with a meaningful contention regression; then reconcile delivery documents and requirement evidence. This recommendation makes no general production-readiness claim.
