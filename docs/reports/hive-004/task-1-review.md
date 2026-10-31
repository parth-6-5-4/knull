### Spec Compliance

- ✅ **Spec compliant for Task 1.** All eleven requested paths have corresponding changes, plus the explicitly authorized schema-version-only change in `tests/test_hive_report_store.py:377`. The reviewed artifact is the 12-file before/after snapshot, not the dirty branch diff. No later-task admission facade or empty resource accessors were added (`app/hive/store.py:55`).
- ✅ The seven additive tables and five indexes cover the requested durable foundation, including policy/profile identity, allocation hierarchy, run ownership, calls/receipts/permits, cursors and usage projection (`app/hive/resource_schema.py:3`). The original six table definitions remain intact (`app/hive/schema.py:11`); v0/v1 opening requires explicit maintenance (`app/hive/schema.py:108`).
- ✅ The positional maintenance API remains compatible, defaults to target v2, supports explicit target v1, and refuses downgrades (`app/hive/migrate.py:27`). Backup creation is exclusive/private and verified before mutation; the exclusive transaction rechecks source content, validates the intermediate v1 shape/content, and commits the v2 marker atomically (`app/hive/migrate.py:39`, `app/hive/migrate.py:65`). No historical resource admissions are fabricated.
- ✅ The shared records expose the specified field names, preserve runner defaults, validate integer/finite-number boundaries and freeze nested JSON defensively (`app/hive/resource_types.py:48`, `app/hive/resource_types.py:87`, `app/hive/resource_types.py:163`). The clock seam is shared by the store, transaction coordinator and owned executor (`app/hive/store.py:55`).
- ✅ Transactions preserve the configured SQLite timeout, bound mutex acquisition, revalidate before/after acquisition and before commit, use EXCLUSIVE for every deadline-bound call, and classify only SQLITE_BUSY-family errors (`app/hive/transactions.py:40`). Cancellation detaches rather than cancels submitted work; close drains and exposes detached values/errors (`app/hive/transactions.py:88`, `app/hive/transactions.py:120`).
- ⚠️ **Cannot verify from this task:** actual operator quiescence, outstanding old provider requests, or activation on a real database. The controller must retain those maintenance gates. The absence of resource rows for historical runs is implemented; governed resume rejection belongs to later admission integration (`app/hive/resource_schema.py:20`, `tests/test_hive_resource_migrations.py:23`).
- ⚠️ **Cannot verify from this task:** call-ID derivation/conflict handling, receipt category normalization and accounting, fairness, provider ceilings, retries and integrated admission behavior. `PreparedCall`/`UsageReceipt` provide the types; future producers must enforce those semantics (`app/hive/resource_types.py:240`, `app/hive/resource_types.py:276`). These are later-task gates, not Task 1 omissions.
- ⚠️ **Cannot verify from this frozen review artifact:** whether the live checkout still matches the supplied hash manifest when the controller stages/commits. Recheck identity against `task-1-after.json` before committing; no Git command or changed-source reread was performed here.

### Strengths

- Literal-sensitive DDL comparison preserves single-quoted case, spaces and escaped quotes while allowing known identifier quoting. Full explicit-index definitions and stable sorting of nullable expression-index metadata avoid accepting changed predicates or leaking Python comparison errors (`app/hive/schema.py:41`, `app/hive/schema.py:60`). The associated tests exercise literal changes, quoted identifiers, expression/partial indexes, extra objects and orphan rows (`tests/test_hive_resource_migrations.py:145`, `tests/test_hive_resource_migrations.py:197`).
- Maintenance tests use literal historical DDL and the frozen old validator rather than redefining history through current SCHEMA (`tests/hive_resource_testkit.py:6`, `tests/hive_resource_testkit.py:25`). Six-table reconciliation, backup mode/non-overwrite checks, injected exceptions and real subprocess termination test durable behavior (`tests/test_hive_resource_migrations.py:23`, `tests/test_hive_resource_migrations.py:122`).
- The deadline tests exercise real SQLite readers and writers, including the default deadline-bound write path, not only mocks (`tests/test_hive_transactions.py:55`, `tests/test_hive_transactions.py:160`). Existing publication tests retain their meaning; the sole report-store test change is its version expectation (`tests/test_hive_report_store.py:377`).
- Executor tests cover queued expiry, cancellation after work starts, detached success/error retention, one-worker ownership, interrupted close, and callback TimeoutError identity (`tests/test_hive_transactions.py:82`, `tests/test_hive_transactions.py:174`). Private executor ownership avoids the default global pool (`app/hive/transactions.py:76`).

### Issues

#### Critical (Must Fix)

- None found in Task 1 scope.

#### Important (Should Fix)

- None found in Task 1 scope.

#### Minor (Nice to Have)

- **Inherited test-output warning:** `docs/reports/hive-004/task-1-frozen-focused.log:1` reports unset `asyncio_default_fixture_loop_scope`. The same warning exists in `docs/reports/hive-004/execution-baseline.log:1`, so it is not a Task 1 regression and does not block this foundation. Track a scoped test-configuration follow-up to choose the intended fixture loop scope explicitly; the output is not pristine.

### Scoped Checks and Evidence

- Read the task brief first, then shared constraints, implementation report/hash manifest and the frozen diff. The initial large diff output was truncated in its schema/executor/testkit section; reread only that missing range from the diff. No changed source file was read separately, no Git command ran, no suite was rerun, no subagent was dispatched, and no checkout content was modified except this review.
- Checked the concrete risk of inflated or incomplete verification claims by reading `docs/reports/hive-004/task-1-commands.json`, final focused/full logs, baseline failure names, migration RED summaries, reconciliation output and static receipts. Final focused evidence is **130 passed** (`docs/reports/hive-004/task-1-frozen-focused.log:20`); full evidence is **452 passed / 11 failures**, with the same failure names as baseline (missing Anthropic dependency and HfFolder incompatibility). This is evidence review, not an independent test rerun.
- Checked interruption/history claims against the tests and four saved process-kill receipts: pre-commit recovery is v1; post-commit recovery is v2; all six before/after/backup table digests agree at every barrier (`docs/reports/hive-004/task-1-migration-reconciliation.log:13`). Static receipts also report unchanged frozen v1 DDL, unchanged HIVE-003 store helpers onward and the single authorized report test edit (`docs/reports/hive-004/task-1-static.log:2`).
- No narrow runtime probe was needed: the concrete lock/deadline, error-identity, literal-shape and detached-outcome doubts were addressed by the diff and existing targeted tests. This review does not claim full-suite green or integrated HIVE-004 acceptance.

### Assessment

**Task quality: Approved.**

**Reasoning:** The schema/migration foundation is additive and fail-closed, with meaningful real-database and interruption evidence. The transaction and executor seams match the task contract; the known baseline dependency failures and inherited fixture warning remain explicit, and future admission/provider/accounting gates remain open.
