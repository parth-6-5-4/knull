### Spec Compliance

- ❌ Issues found: REP-08 active-assignment fencing is violated when lock acquisition crosses lease expiry: `app/hive/store.py:255` captures the default clock before both the connection lock and `BEGIN IMMEDIATE`. See Important finding I1.
- ✅ Remaining task-local requirements are implemented: coherent same-run candidate capture (`app/hive/store.py:236`), writer-only atomic publication and deterministic output recomputation (`app/hive/store.py:251`), generic/verifier bypass guards (`app/hive/store.py:175`, `app/hive/store.py:217`), and the verifier fixture correction preserving the missing-provenance assertion (`tests/test_hive_evidence.py:134`).
- ⚠️ Cross-task integration remains unverified and currently failing: `app/hive/runner.py:107` still completes writers through generic `publish`; `docs/reports/hive-003/task-3-compatibility.log:37` records **121 passed, 2 failed**, specifically execution tests at lines 150 and 398. The explicit ruling at `.superpowers/sdd/2026-10-20-supported-reports/progress.md:40` is consistent with the task's required guard and Task 4 ownership; it does not establish integrated compatibility. Task 4 must restore both cases through bound `publish_report` and verify finalization copies the committed artifact.
- ⚠️ Actual model-dispatch transaction release, no-findings run status, route/accounting compatibility, and public delivery remain Task 4/5 checks. `tests/test_hive_report_store.py:129` proves the snapshot method releases its transaction before a separate mock await; it does not exercise the real writer route. `tests/test_hive_report_store.py:306` verifies stored failure metadata, while run finalization remains outside this diff.

### Strengths

- `app/hive/store.py:236`: count and bounded stable candidate query share one explicit read transaction, with immutable construction after commit. The barrier-controlled second-connection test at `tests/test_hive_report_store.py:91` tests genuine SQLite snapshot coherence and restricts WAL to the fixture.
- `app/hive/store.py:281`: selected rows are rebuilt using the same binding builder; full fact equality checks display metadata as well as hashes. Missing, revoked, foreign and malformed current rows fail atomically with snapshot-change classification. The mutation matrix at `tests/test_hive_report_store.py:148` exercises those cases using file-backed storage.
- `app/hive/store.py:272`, `app/hive/store.py:288`, `app/hive/store.py:294`: publication recomputes the artifact, compares canonical JSON rather than loose Python equality, and persists only recomputed values through a transaction-local helper. No public publication method is nested or non-reentrant lock reacquired.
- `tests/test_hive_report_store.py:208`, `tests/test_hive_report_store.py:277`: stale identity/replay rejection and persisted provenance readback are substantive behavior tests; reopening checks exact metadata, digest retention, raw-text nonduplication, and unchanged schema version.

### Issues

#### Critical (Must Fix)

- None.

#### Important (Should Fix)

- **I1 — Expired assignment can publish after waiting for a database lock.** `app/hive/store.py:255` obtains `time.time()` before acquiring `_lock` and before the potentially blocking `BEGIN IMMEDIATE` at line 257. `_holds` then compares lease expiry against that stale timestamp, although publication has only just obtained its transaction. A caller whose lease expires while waiting is allowed to complete and persist its result, violating REP-08's active-assignment check. This remains a defect even though older generic publication uses a similar clock pattern.
  - Focused probe run with `DEBUG=false /opt/anaconda3/bin/python`: temporary file-backed database, a writer claimed with a 0.10-second lease, second connection holding `BEGIN IMMEDIATE`, worker thread calling `publish_report` with default `now`, lock released after 0.25 seconds. Observed `{'expired_before_lock_release': True, 'published': True, 'status': 'done'}`. The empty-selection artifact was otherwise valid; lease rejection must precede artifact validation for every selection.
  - Resolve default `now` only after successfully acquiring the write transaction, immediately before `_holds`, while preserving an explicitly supplied test clock. Add a controlled lock-wait regression asserting `False`, unchanged claimed task/result, and no open transaction when the lease expires before publication obtains the transaction.

#### Minor (Nice to Have)

- `docs/reports/hive-003/task-3-green.log:1`: existing `pytest-asyncio` unset `asyncio_default_fixture_loop_scope` warning means test output is not pristine. This is a pre-existing configuration issue, not a new Task 3 regression; retain its explicit deferred classification.

### Assessment

**Task quality:** Needs fixes.

**Reasoning:** The snapshot and atomic provenance implementation is otherwise coherent and appropriately scoped, but the reproduced lock-wait lease defect must be fixed before Task 3 is trusted. The two recorded writer integration failures belong to the explicit Task 4 dependency and must remain visible until restored.

**Review checks:** Read the task-local snapshot diff once; inspected unchanged builder/renderer contracts for the concrete revalidation and canonical-gate risks (`app/hive/reporting.py:96`, `app/hive/reporting.py:248`), unchanged connection setup and `_holds` for transaction/clock semantics (`app/hive/store.py:44`, `app/hive/store.py:145`), and runner publication/finalization call sites for the explicit cross-task guard dependency (`app/hive/runner.py:107`, `app/hive/runner.py:224`). Read the governing publication contract and recorded green/compatibility logs. Ran only the focused lock-wait probe above; no suites rerun, source changes, Git mutations, or subagents.
