# HIVE-004-A Task 2 implementation report

Status: DONE_WITH_CONCERNS; source frozen, focused acceptance GREEN; unrelated baseline dependency failures and restricted full-suite limitations retained. No implementer commits, staging, pushes, installs, real database maintenance, live providers, or delegated review.

Governing scope: `docs/superpowers/specs/2026-10-21-resource-ledger-design.md` revision 2, LED-01–09, INT-03 accounting, ADM-07 certainty separation; dispatched Task 2 brief and accepted Task 1 interfaces. Runtime admission and provider integration remain later-task acceptance.

## Changes and files

- Created `app/hive/resource_store.py`: internal ResourceStore, root/grant conservation, immutable identity replay, allocation closure, durable call state transitions, receipt history, atomic legacy projection, inspection and permanent root freeze after overrun.
- Modified `app/hive/store.py`: owning `HiveStore.resources` accessor alongside existing transaction/database-I/O owners. No changes to legacy execution behavior.
- Modified `app/hive/resource_schema.py`: controller-approved immutable `resource_allocations.run_id TEXT NOT NULL REFERENCES runs(id)` binding. Child rows inherit the parent run; roots require an existing legacy run. One root per run is enforced transactionally. The unpublished v2 foundation is amended; no production migration/version transition or real database change was performed.
- Modified `tests/test_hive_resource_migrations.py`: seven-column allocation fixtures and missing-run foreign-key assertion. Existing stopped-writer migration/reopen tests remain meaningful.
- Created `tests/test_hive_resources.py`: 41 parameterized real-SQLite accounting/transition/identity/receipt/overflow/contention/crash cases.
- Modified `tests/hive_resource_testkit.py`: controlled PreparedCall/UsageReceipt and admission-row fixtures. Fake provider metadata only; all accounting/locking/process tests use actual SQLite.
- Added task-specific logs/receipts under `docs/reports/hive-004/`; this public copy preserves the original task handoff evidence. Controller owns plan, problem-register and review status updates.

## Resulting behavior and composition seams

`used(a)` sums own settled actuals, max(bound, known partial lower bound) for held calls, open-child max(grant, used), and closed-child used. Queued calls contribute zero. Checked Python signed-64-bit sums validate prospective changes before SQL storage; transaction rollback also protects every error. Root 100 → child 60 → hold 50 → receipt 30 gives root 40 before close, child 30 available, root 70 after child close. Actual 80 against bound 50 retains measured cost, exposes child debt 20, freezes the entire root, and never automatically unfreezes.

`_create_root_in_transaction(db, allocation_id, run_id, limit_tokens)` enables Task 3 to atomically create legacy run/root/admission metadata without fabricating policy/request data. `_reserve_in_transaction(connection, prepared, *, now_utc, deadline_monotonic)` composes accounting/permit intent into Task 3's one transaction, without opening a nested transaction. Both require the owning HiveStore connection already in transaction. `_reserve_in_transaction` is an internal accounting seam; it does not implement fairness, ceilings or independent permission to send. Only `mark_dispatched(...) == True` after commit authorizes the first send; repeated/released transitions return false. Admission must supply the surrounding shared queue/permit policy.

Reserve/dispatch compare persisted authority, allocation, fingerprint, provider/model/endpoint/profile/SDK/mode/bound; dispatch rechecks active run fence/lease/expiry and task assignment fence/lease, as applicable. Closed/frozen authority rejects new work. Released calls cannot settle or become unknown; dispatched/unknown calls cannot release unsent holds. Usage-complete and execution-terminal flags remain independent. Complete nonterminal usage can still hold permits; terminal partial evidence frees capacity while preserving the token hold and known counts. Late complete receipts after run stop reconcile the original call.

Every accepted receipt remains in immutable receipt_json history, including prior partial identities after completion. Equal replay (including reordered older partial receipts) returns the current immutable record; changed identity replay or cross-call reuse conflicts. Complete receipts create exactly one legacy ledger row plus one projection link in the same transaction. Legacy input/output remain nullable when unknown; authoritative governed totals come from ResourceInspection, not the old pair. Receipt total is authoritative when complete; partial total or known input/output sum is a lower bound, never added to an already full hold twice. Receipt categories/provenance are retained unchanged.

Historical runs without a root return historical-measured totals without invented mode, hard cap or allowance. A root without admission metadata cannot claim hard mode; inspection conflicts until metadata is attached atomically by Task 3. Inspection exposes separate actual/reserved/unknown/debt/headroom, queue and occupancy counts.

## TDD and executed verification

Exact argv, explicit environment overrides, working directory, exit, timestamp and log receipts are retained in `docs/reports/hive-004/task-2-commands.json`.

1. Initial required RED: `DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_hive_resources.py -q` → exit 1, 2 failed/30 setup errors, all because ResourceStore did not exist (`task-2-red.log`). This initial absence probe included two generation-param cases subsequently removed under the controller's canonical-fingerprint trust-boundary ruling; they belong to Task 4 producer tests, not Task 2 metadata comparisons.
2. First implementation focused iteration: three-file command → exit 1, 104 passed/3 failed (`task-2-green-1.log`). Failures exposed two fixture mistakes (reused authority ordinal; trying to create a new call after overrun freeze) and one affected seven-column migration fixture. Fixtures corrected without weakening conservation assertions.
3. Meaningful receipt RED before fix: resource command → exit 1, 37 passed/2 failed (`task-2-receipt-red.log`): old equal partial replay incorrectly conflicted after completion; old partial receipt ID reuse on another call was accepted. Both drove immutable retained receipt history.
4. Intermediate focused GREEN: three-file command → exit 0, 116 passed (`task-2-green-2.log`).
5. Self-review RED before fixes: `DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_hive_resources.py -q -k 'internal_composition or complete_receipt_pair_overflow'` → exit 1, 2 failed/39 deselected (`task-2-self-review-red.log`). Composition outside the owning transaction and complete pair overflow were incorrectly accepted. Guards and checked arithmetic added.
6. Final required focused GREEN: `DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_hive_resources.py tests/test_hive_resource_migrations.py tests/test_hive_report_store.py -q` → exit 0, **118 passed**, 4.10s (`task-2-green-final.log`).
7. Required full suite run once: `DEBUG=false PLAYWRIGHT_BROWSERS_PATH=/tmp/hive-003-browsers /opt/anaconda3/bin/python -m pytest -q` → exit 1, **490 passed, 11 failed, 3 errors**, 22.40s (`task-2-full-final.log`). All 41 resource cases passed. Sandbox restrictions blocked the Chromium fixture and localhost SDK setup; the dependency failures were not repaired.
8. Authorized narrow permitted boundary rerun (no second full suite): `DEBUG=false PLAYWRIGHT_BROWSERS_PATH=/tmp/hive-003-browsers /opt/anaconda3/bin/python -m pytest tests/test_hive_reports.py::test_marked_rendering_round_trip tests/test_llm_sdk_wiring.py -q` with `require_escalated` local process/socket access → exit 1, **4 passed, 1 failed**, 4.71s (`task-2-permitted-boundaries.log`). Browser rendering and OpenAI/Gemini local transports passed; Anthropic reached its existing missing-package failure after socket setup succeeded. These are separate observed runs, not a synthesized full-suite pass count.
9. `git diff --check --` scoped source/test paths → exit 0, no output (`task-2-diff-check.log`). New files were also self-reviewed directly. No source edits after final focused GREEN/full run.

Full restricted failure/error IDs:

- `tests/test_hive_reports.py::test_marked_rendering_round_trip`: Chromium MachPort bootstrap permission denied by sandbox; passed in permitted narrow rerun.
- `tests/test_semantic_cache.py::TestSemanticCache::test_set_and_get`
- `tests/test_semantic_cache.py::TestSemanticCache::test_semantic_similarity_hit`
- `tests/test_semantic_cache.py::TestSemanticCache::test_cache_miss`
- `tests/test_semantic_cache.py::TestSemanticCache::test_context_key`
- `tests/test_semantic_cache.py::TestSemanticCache::test_invalidate`
- `tests/test_semantic_cache.py::TestSemanticCache::test_stats`
- `tests/test_tools_vectordb.py::TestChromaDB::test_chroma_upsert`
- `tests/test_tools_vectordb.py::TestChromaDB::test_chroma_query`
- `tests/test_tools_vectordb.py::TestChromaDB::test_chroma_upsert_deduplication`
- `tests/test_tools_vectordb.py::TestChromaDB::test_chroma_delete_source`
- Setup error `tests/test_llm_sdk_wiring.py::test_sdk_roundtrip[openai-OPENAI_API_KEY-hi-openai-tokens0]`: localhost bind sandbox denial; passed in permitted narrow rerun.
- Setup error `tests/test_llm_sdk_wiring.py::test_sdk_roundtrip[anthropic-ANTHROPIC_API_KEY-hi-anthropic-tokens1]`: localhost bind sandbox denial; permitted rerun reached baseline `No module named anthropic` failure.
- Setup error `tests/test_llm_sdk_wiring.py::test_sdk_roundtrip[gemini-GEMINI_API_KEY-hi-gemini-tokens2]`: localhost bind sandbox denial; passed in permitted narrow rerun.

All ten semantic-cache/vector failures have the existing `sentence_transformers` → `huggingface_hub.HfFolder` ImportError. Together with the permitted Anthropic missing-package failure, these identify the controller's eleven existing dependency failures. In the restricted full run, the Anthropic failure was masked by earlier socket setup failure and the browser restriction supplied the eleventh failure; the three setup errors are reported separately.

Known warning in focused logs: existing pytest-asyncio unset default fixture-loop-scope deprecation; no dependency/config changes performed.

## Evidence and self-review

Process tests use `multiprocessing` spawn, each opening its own HiveStore/SQLite connection. Explicit ready/go barriers precede competing grants and release/dispatch; every join is bounded, with kill cleanup. Crash test signals `dispatched-committed` only after reserve and dispatch methods return from their commits, then parent terminates that exact process and a fresh handle confirms hold/permit/headroom survive. Reader and writer contention use independent real SQLite handles, a 17ms busy timeout, rollback assertions, and whole-operation idempotent retries; connection timeout remains 17ms. No inherited SQLite handles or sleep-based race oracle.

Self-review checked each mutation/return against LED-01–09: immutable root/run/grant identity; no branch multiplication/cycles/reparenting; checked nested totals; no SQL aggregate overflow; first-dispatch authorization; one winner against unsent release; conservative external uncertainty; replayed receipts/legacy projection; complete usage independent of terminal execution; retained partial lower bound; no unfreeze; unused-only return on close; transaction ownership/composition; busy rollback and distinct storage errors. Report-store compatibility stayed green.

## Concerns and boundaries

- Task 2 is internal accounting only. Shared active/queued run/call ceilings, fair scheduling, policy/SDK qualification, actual governed Caller/provider dispatch, cleanup/recovery and end-to-end F3-J repair remain later tasks; this is not an integrated admission release claim.
- Canonical request_fingerprint is trusted from Task 4's internal producer. Task 2 compares persisted identity; it does not defend against forged unchanged fingerprints with different local messages/generation parameters. Task 4 must derive the fingerprint from canonical messages/temperature/output/route and must not expose caller-supplied fingerprints through the public facade. Controller explicitly confirmed this boundary.
- Receipt category semantics/bound qualification are Task 4-owned normalization. Store preserves JSON, trusts complete authoritative totals, uses normalized input/output or supplied partial total as known lower bound, and checks count arithmetic. It does not sum informational subset categories.
- Receipt history uniqueness currently scans retained call histories within the serialized transaction. This favors exact replay correctness for the bounded local version; no large-history throughput claim was measured.
- Unpublished schema v2 changed in this task; all earlier temporary v2 fixtures must be recreated. Real application data was neither activated nor modified.
- The permitted browser check regenerated two tracked HIVE-003 screenshots (`report-fixture-4-1440x900.png`, `report-fixture-4-390x844.png`). These are test side effects outside Task 2; controller was notified to restore baseline bytes.
- Fresh independent review and controller-owned commit are the next gates. No reviewer dispatched by implementer.
