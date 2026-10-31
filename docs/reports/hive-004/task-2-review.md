### Spec Compliance

- ✅ **Spec compliant for Task 2's authorized accounting scope.** The frozen six-file package implements the requested internal ResourceStore API, owning-HiveStore access, checked conservation, immutable allocation/call identity, first-transition dispatch authorization, durable uncertainty, receipt replay, one transactional legacy projection, closure, and aggregate inspection (`app/hive/resource_store.py:28`, `:55`, `:114`, `:131`, `:186`, `:225`, `:243`, `:257`, `:268`, `:324`, `:337`; `app/hive/store.py:70`). No blocking missing, extra, or misunderstood Task 2 behavior found.
- ✅ All four original brief files are represented. The two additional files implement the authorized run-identity schema amendment and its directly affected FK/fixture checks (`app/hive/resource_schema.py:12`; `tests/test_hive_resource_migrations.py:165`). The inherited run FK and transactional one-root check implement the approved identity contract without inventing admission data (`app/hive/resource_store.py:114`, `:131`).
- ✅ LED-01/02/07/08 conservation uses checked Python sums, open-child max(grant, used), closed-child used, full uncertain holds, immutable parentage, and permanent root freeze. Tests pin 40/30/70, branch debt 20, overflow rollback, closed replay, and unknown-child closure denial (`app/hive/resource_store.py:55`, `:97`, `:131`, `:268`, `:324`; `tests/test_hive_resources.py:45`, `:59`, `:94`, `:107`, `:169`, `:284`).
- ✅ LED-03–06 and ADM-07 accounting distinguish dispatch authorization, usage completion, and execution termination. Immutable receipt history handles reordered partial replay and cross-call ID reuse; complete usage projects once in the same transaction. Equal call replay checks persisted authority/route/profile/mode/bound before returning (`app/hive/resource_store.py:152`, `:186`, `:225`, `:243`, `:268`; `tests/test_hive_resources.py:73`, `:124`, `:133`, `:157`, `:295`, `:306`, `:319`, `:348`).
- ✅ LED-09 and the Task 3 composition seam use the owning transaction, reject foreign/nontransactional connections, preserve rollback, and return typed contention errors through the accepted transaction helper (`app/hive/resource_store.py:32`, `:182`, `:186`; `tests/test_hive_resources.py:258`, `:367`, `:380`; focused unchanged-contract check `app/hive/transactions.py:40`).
- ⚠️ **Cannot verify from this diff:** actual Caller fingerprint derivation, exact SDK generation-parameter binding, normalized receipt-category semantics, hard-profile qualification, queue fairness/ceilings, atomic integrated permit admission, recovery, or zero hidden provider retries. These remain Tasks 3–8 responsibilities; the ledger's trusted-fingerprint comparison and admission composition seam alone do not establish those runtime guarantees (`app/hive/resource_store.py:152`, `:186`, `:268`; spec LED-03, ADM-01–07, CAL-01–07).
- ⚠️ **Cannot verify from this diff:** public reconciliation inspection of original call IDs and receipt provenance after restart. Task 2 persists receipt history, but its existing ResourceInspection contract exposes run aggregates; later inspection integration must make the retained evidence accessible without presenting unknown usage as settled actuals (`app/hive/resource_store.py:268`, `:337`; unchanged `app/hive/resource_types.py:359`; spec LED-05/06, INT-03).
- ⚠️ **Cannot verify from this diff:** end-to-end HIVE-003 preservation, integrated F3-J cleanup, production migration safety, or full-suite success. The authorized schema change is to never-activated v2; no real-data maintenance or integrated release is established by this review (`app/hive/resource_schema.py:12`; `docs/superpowers/README.md:17`).

### Strengths

- Conservation is centralized in one iterative tree calculation, avoiding SQL aggregate overflow and recursion-depth failure while preserving open-grant authority (`app/hive/resource_store.py:55`). The 369-line new module has one accounting responsibility and explicit admission boundaries rather than hiding scheduling policy inside balance mutations (`app/hive/resource_store.py:1`, `:186`).
- Independent spawned processes use ready/go barriers, bounded joins, and kill cleanup. The crash test signals after committed dispatch, then reopens through a fresh handle; these are meaningful persisted-state tests rather than mocked locking (`tests/test_hive_resources.py:178`, `:187`, `:205`, `:217`, `:235`, `:241`).
- The receipt tests exercise immutable old partial evidence after completion, permit release independent of usage, partial-overrun charging without double-counting, late reconciliation after stop, and atomic projection failure boundaries (`tests/test_hive_resources.py:133`, `:148`, `:295`, `:306`, `:319`, `:329`, `:348`, `:391`).
- All six changed files were reviewed from the complete frozen diff in three bounded passes; no hunk required a separate changed-file read. The sole output mutation is this requested review report. No source, index, HEAD, branch, or Git state was mutated, and no Git recrawl was performed.

### Issues

#### Critical (Must Fix)

- None found in the reviewed Task 2 scope.

#### Important (Should Fix)

- None found in the reviewed Task 2 scope.

#### Minor (Nice to Have)

- **M1 — Dense test setup and process lifecycle code reduce reviewability.** Multiple actions/assertions on one line make failure locations and race-test cleanup harder to scan (`tests/test_hive_resources.py:187`, `:217`, `:241`; `tests/hive_resource_testkit.py:28`, `:43`). Expand the new multi-statement lines and fixture dictionaries when these tests are next edited. The present assertions do exercise real behavior; this is readability, not a correctness blocker.
- **M2 — Existing pytest configuration emits a deprecation warning.** The retained focused log is not pristine: `asyncio_default_fixture_loop_scope` is unset (`docs/reports/hive-004/task-2-green-final.log:1`). Track an explicit compatible fixture scope in the environment/configuration follow-up; do not broaden this accounting task into dependency repair. This warning does not invalidate the 118 observed passes.

### Verification Evidence and Focused Outside-Diff Checks

- Read the exact command/environment/exit receipts in `docs/reports/hive-004/task-2-commands.json` and the retained final log results. Focused acceptance: **118 passed**, exit 0 (`docs/reports/hive-004/task-2-green-final.log:18`). Restricted full run: **490 passed, 11 failed, 3 errors**, exit 1 (`docs/reports/hive-004/task-2-full-final.log`). Separately authorized narrow permitted rerun: **4 passed, 1 failed**, exit 1; the remaining Anthropic failure reports the missing package (`docs/reports/hive-004/task-2-permitted-boundaries.log`). These are separate observed runs, not a synthesized full-suite result. Baseline attribution is the controller/implementer claim supported by the retained error descriptions; no baseline suite was rerun here.
- Named risk: malformed/nullable receipts or mutable return records could undermine settlement and inspection. Focused check of unchanged `app/hive/resource_types.py:243`, `:275`, `:321`, `:359` confirmed PreparedCall validation, complete receipts requiring total_tokens, frozen record contracts, and the existing aggregate inspection shape.
- Named risk: dispatch could authorize a send before commit or ignore an elapsed local deadline. Focused check of unchanged `app/hive/transactions.py:40` confirmed checks before/after the callback, commit before result return, rollback on failure, and BUSY-only translation. Integrated pre-adapter deadline enforcement remains a later-task obligation.
- Read the specific governing LED/ADM/INT requirements and the development/index status to assess scope. No broad code crawl or changed-file reread was needed. No tests were rerun: no concrete unresolved Task 2 doubt warranted a new probe beyond the retained evidence.

### Assessment

**Task quality: Approved.**

**Reasoning:** The reviewed accounting implementation preserves conserved authority and durable uncertainty with meaningful real-SQLite, subprocess, receipt, overflow, and transaction tests. The minor readability/configuration findings do not block Task 2; integrated runtime acceptance and the explicitly listed cross-task checks remain open.
