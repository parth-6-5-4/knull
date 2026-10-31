# HIVE-003 Task 3 — scoped re-review, fix round 1

## Verdict

**Original Important finding I1: ADDRESSED.** **No new Critical, Important or Minor findings identified in the fix diff.** The repair is acceptable within this review's scope; this is not integrated HIVE-003 acceptance.

## Original finding and repair

- **I1 — Important, addressed — `app/hive/store.py:262`–`265`.** `publish_report` now obtains `BEGIN IMMEDIATE` before sampling the default clock and checking `_holds`. Waiting for either the Python lock or SQLite write lock therefore cannot preserve the caller's earlier live timestamp. An explicit `now` remains unchanged. Stale rejection still rolls back and returns `False` before task-kind, snapshot or artifact validation.
- The controller-authorized related repair follows the same ordering in generic publication (`app/hive/store.py:173`–`176`) and verifier promotion (`app/hive/store.py:215`–`218`). Heartbeat (`app/hive/store.py:156`–`166`) and shared release/exhaustion transition (`app/hive/store.py:309`–`319`) now acquire a short explicit write transaction before sampling time and performing the guarded update. Both close the transaction on success or exception. No public method nesting, lock reacquisition, schema change or journal-mode change is introduced by this diff.

## Regression evidence assessed

`tests/test_hive_report_store.py:229` uses a separate real file-backed connection holding a write transaction, starts the mutation while its real-time lease remains live, and releases contention after expiry. The report regression at line 261 checks rejection, unchanged claimed status/result and run output, and no open transaction. The five variants at line 270 additionally check unchanged facts/evidence and an expired lease, including heartbeat's inability to renew after the wait.

The recorded round-1 logs substantiate the reported transition: `task-3-fix-1-red-all.log` records all six contention cases failing because the late operation returned `True`; `task-3-fix-1-green.log` records **6 passed, 34 deselected**. `task-3-fix-1-compatibility.log` records **127 passed, 2 failed**, preserving the two explicitly pending old-runner writer-success cases. These are inspected implementation-run results, not newly rerun tests in this review.

## Scope and limitations

Read the original review, Task 3 brief/constraints, implementation report including its fix appendix, and the complete round-1 snapshot diff. Inspected current changed methods, connection autocommit setup, regression helpers/assertions and recorded log summaries. No tests or suites were rerun; no source changes, Git mutations or subagents were used. This report is the only review output written.

Task 4 must still restore the recorded writer integration failures and establish finalization behavior before integrated delivery. Unchanged `claim`, `expire_leases`, advisory `owns`, broader architecture and provider behavior were not reopened in this scoped re-review.
