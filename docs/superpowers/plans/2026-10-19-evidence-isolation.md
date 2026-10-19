# Run-scoped evidence isolation implementation plan

> **For agentic workers:** Read the linked spec and this plan. After review, use `superpowers:executing-plans` for native execution or `superpowers:subagent-driven-development` if selected by the maintainer. Track actual completion with the checkboxes below.

**Goal:** Allow repeated sources across runs while preventing facts from using missing or substituted evidence.
**Architecture:** Keep provenance rules behind the `HiveStore` interface. A focused schema module owns SQLite initialization/version detection; an explicit maintenance command owns old-database upgrade and backup. Callers retain local evidence/citation IDs. Eligibility checks prevent historical missing provenance from entering new reports.
**Tech Stack:** Existing Python 3.12, stdlib sqlite3, pytest/pytest-asyncio, mock LLMRouter/search, existing FastAPI TestClient.
**Spec:** [HIVE-001](../specs/2026-10-19-evidence-isolation-design.md), EVI-01–08.
**Status:** Draft for joint spec/plan review; not executable approval.
**Approval:** Pending. User asked to start step 1; this authorizes investigation/preparation and is not recorded as approval of this newly written plan.
**Execution method:** Native recommended; not selected. Tasks share one storage seam and should execute serially.

This review candidate makes the storage/error/recovery decisions concrete before requesting implementation approval. Neither the spec nor this plan is represented as approved. No application implementation or acceptance-test changes have been made.

## Global constraints

- Repair the existing SQLite hive only. Postgres, crash-resume, Jev, hierarchy, and general claim-entailment/report construction remain separate work.
- Preserve `evidence(run_id, evidence_id=None)` and `publish(...) -> bool`: lost lease returns `False`; provenance conflict is an explicit error, with full publication rollback.
- Preserve `E-...` and `F-...` representations. Evidence uniqueness becomes `(run_id, id)`; IDs embedded in prompts remain unchanged.
- Compare persisted source ID, title, URL and text for same-run immutability. Identical re-publication can succeed through a newly claimed task; a completed task's stale publication remains refused.
- Never copy another run's evidence to repair a missing historical reference. Historical reports remain unchanged.
- Use disposable databases and mock model/search responses. Do not open, migrate, or restore real `app_data` during implementation tests.
- Do not mutate the legacy `app.db` workflow or introduce dependencies. Use serial store edits; no unrelated HIVE-002 repairs.
- Existing runner failure propagation (F2) can leave dependents pending after repeated integrity errors exhaust a task. HIVE-001 must expose/rollback the error correctly; HIVE-002 owns terminal propagation. Keep this residual rollout risk explicit; HIVE-001 success is not production readiness.
- Git root is `/Users/parthsdambhare`, not this project. No staging, commits, worktrees, or pushes from that parent checkout. File-level verification remains available.

## Current evidence and review focus

[Baseline JSON](../../reviews/2026-10-19-hive-001-baseline.json) and [probe](../../reviews/reproduce_hive_evidence.py) establish current behavior on Python 3.12.7 / SQLite 3.45.3:

- First file-backed run: done, two evidence records/two verified facts. Second: blocked, zero evidence/verified facts, two rejected facts.
- Same-run changed evidence: accepted; task done; original text silently retained.
- Fact referencing only another run's evidence: publication accepted, fact and unrelated evidence committed, task done.
- Missing provenance with stored `verified` status: writer returns a nonempty report and passing gate without a matching source reference.
- Existing hive suite: 15 passed. These tests do not cover the failures above.

Five review risks, each assigned a test below:

1. Partial batches: one valid evidence record followed by conflict/missing reference must leave no partial evidence, fact, result, or task completion (Task 2).
2. Old data and future schemas: supported old rows survive; unknown schema/version/custom objects fail before writes (Task 1).
3. Upgrade interruption: error or process death between copy/drop/rename/version changes must reopen as legacy or complete v1, never mixed writable state (Task 1).
4. Cached trust: historical `verified` status and attempted promotion cannot bypass missing-provenance checks; stored reports stay unchanged (Task 3).
5. Citation compatibility and changed source text: repeated/changed sources verify against their own run; API and CLI preserve existing forms (Task 4).

## Chosen interfaces and migration contract

Create `app/hive/schema.py`:

- `HIVE_SCHEMA_VERSION = 1`.
- `HiveSchemaError(RuntimeError)` and subclass `HiveMigrationRequired`.
- `initialize_hive_schema(db: sqlite3.Connection) -> None`: create fresh v1 or accept recognized v1. Recognized legacy raises `HiveMigrationRequired` with the explicit maintenance command; unknown/future/partial schemas raise `HiveSchemaError`. Close the new connection if store initialization fails.
- `inspect_hive_schema(db: sqlite3.Connection) -> dict`: version/shape, evidence count, and unresolved fact counts by run; no source text, claims or credentials in diagnostics. Caller obtains a read-only connection for `--check`.
- Fresh/current schema uses `PRIMARY KEY(run_id, id)` with both columns `NOT NULL`. Other tables and citation fields retain existing shapes. Do not enable a blanket foreign-key mode that would invalidate historical facts outside this migration.

Create `app/hive/migrate.py`:

- `upgrade_hive_database(db_path: str, backup_path: str) -> dict` and `main() -> None`.
- `python -m app.hive.migrate --db PATH --check`: inspect existing file read-only, report missing provenance; exit 0 for a recognized readable shape, nonzero for unsupported input. Never create a missing file.
- `python -m app.hive.migrate --db PATH --apply --backup BACKUP`: explicit stopped-writer maintenance operation. Refuse in-memory targets, missing DB, same source/destination and existing backup destination. Require service/CLI writers stopped; this change promises no online or mixed-version operation.
- Inspect schema before modifying it. `user_version=0` plus the exact original hive table/column/key shape is the only legacy input. Version 1 must have the expected shape. Reject unknown versions, partial schemas, unexpected evidence indexes/triggers/views, and legacy NULL run/ID keys before mutation; do not silently drop custom objects or invent keys.
- Take a consistent SQLite backup, with exclusive creation/private permissions, before destructive operations; verify `PRAGMA integrity_check` on the backup. Backup failure aborts before DDL. Preserve a successfully created backup even if migration later fails; never overwrite an earlier backup. Partial backup is not reported as valid.
- After recognizing legacy input and completing backup, in one `BEGIN IMMEDIATE` transaction create `evidence_v1`, copy original columns verbatim, verify row count/content, drop old evidence, rename replacement, set `PRAGMA user_version=1`, and commit. Roll back on any error; close failed connections. Preserve other tables and all historical statuses/reports verbatim. No cross-run backfill.
- Use individual `execute` calls inside that transaction, not `executescript`, whose legacy transaction behavior can commit a pending transaction. Reopen and validate final shape/content before reporting success. Recognized version 1 re-apply returns a no-op before backup creation/existence checks, with no new destructive transition or backup; it never overwrites the supplied backup path.

SQLite's documented [table-rebuild procedure](https://www.sqlite.org/lang_altertable.html#otheralter) supports create/copy/drop/rename inside a transaction. Use [SQLite backup](https://www.sqlite.org/backup.html), not a raw main-file copy, for a consistent database snapshot. Python's [sqlite3 transaction and backup documentation](https://docs.python.org/3.12/library/sqlite3.html) governs the concrete connection behavior. These are implementation constraints; fault tests remain required.

Keep errors in `app/hive/store.py`:

- `EvidenceIntegrityError(ValueError)`: conflicting evidence, unresolved fact reference, or attempted `verified` promotion without run-owned evidence. Message identifies safe run/evidence IDs and reason; never dumps source text.
- `publish(...)` checks lease first, inserts/compares evidence under its task's run, validates all incoming fact evidence under that same run including evidence in the current batch, then commits facts/result/task status together. No global fallback. Compare duplicate evidence IDs within the incoming batch too.
- `facts(run_id, status='verified')` returns only rows whose evidence exists for that run. `facts(run_id)` and other status views retain raw historical rows for diagnosis; they do not rewrite state on read. Thus raw API facts can show historical status, while new report/result eligibility excludes missing provenance. Preserve old reports as historical artifacts.
- `set_fact_status(...)` validates any proposed `verified` update against the task's run and run-owned evidence in its existing fenced transaction. Unresolvable promotion raises `EvidenceIntegrityError` with no partial updates/completion. Do not broaden this into HIVE-002's general mutation/fence redesign.

## Requirement coverage

| Requirement | Task | Acceptance oracle |
|---|---|---|
| EVI-01 | 1, 2, 4 | Same evidence ID stored twice under separate runs; both full runs finish with verified facts. |
| EVI-02 | 2 | Missing/cross-run reference throws integrity error; full publication batch rolled back. |
| EVI-03 | 2 | Identical evidence accepted; each changed metadata/text field refused with original content unchanged. |
| EVI-04 | 2, 4 | Two runs retain different text at one URL; captured verifier inputs contain only their own text. |
| EVI-05 | 2, 3 | Stale attempt returns false; valid publication and verifier update remain atomic. |
| EVI-06 | 4 | Existing tests plus repeated-source API and CLI checks retain response/citation forms. |
| EVI-07 | 1, 3 | Legacy evidence retained only under original run; missing evidence remains inspectable but ineligible. |
| EVI-08 | 1 | Backup/failure/crash/reopen/future-schema tests; only complete v1 opens writable. |

## Task 1: Versioned initialization and recoverable offline upgrade

**Files:** Create `app/hive/schema.py`, `app/hive/migrate.py`, `tests/test_hive_migrations.py`; modify `app/hive/store.py` initialization only.
**Interfaces:** Schema/migration functions above; keep `HiveStore(path=':memory:')`. Tests embed a frozen literal of the original schema rather than importing the changing live `SCHEMA` as their legacy fixture.

- [ ] Add file-backed tests `test_fresh_schema_has_run_scoped_evidence_key`, `test_old_schema_requires_explicit_upgrade_without_writes`, `test_upgrade_preserves_original_evidence_and_other_tables`, `test_upgrade_reopen_and_reapply_are_idempotent`, and `test_check_is_read_only_and_reports_missing_references`. Assert keys, version, full row preservation, missing provenance count and unchanged historical report/status.
- [ ] Add `test_unknown_or_partial_schema_refused_before_writes` parameterized over future version, wrong v1 key, partial tables, NULL legacy run/ID, and unexpected evidence trigger/index/view. Compare schema/data snapshots before/after.
- [ ] Add `test_backup_failure_leaves_original_unchanged` and `test_migration_error_rolls_back` (inject SQLite failure at copy/drop/rename/version update using a test connection/SQLite authorizer). Assert legacy reopens unchanged; verified backup opens independently with original rows. No production failpoint flag.
- [ ] Add `test_process_death_during_migration_recovers_old_or_new_schema`: child process wraps the real connection at the internal test seam; parent terminates after copy/drop/rename and around commit, with explicit pipe barriers. Reopen in a fresh process; assert full old or full new schema, matching rows, and clear migration-required error for old. Test timeout kills/reaps child; never wall-clock guessing.
- [ ] Run `DEBUG=false python -m pytest tests/test_hive_migrations.py -q`; confirm failures reflect missing new behavior, not fixture/import errors.
- [ ] Implement the chosen schema and explicit upgrade contract, using real SQLite. Complete backups before starting DDL; do not call same-connection backup from inside the migration's write transaction.
- [ ] Rerun migration tests and `DEBUG=false python -m pytest tests/test_hive.py -q`; record actual results. Review source diff; no commit in the parent checkout.

## Task 2: Atomic provenance publication and immutable run evidence

**Files:** Modify `app/hive/store.py`; create `tests/test_hive_evidence.py`.
**Interfaces:** Existing `publish(...) -> bool`, `evidence(run_id, evidence_id=None)`; produce `EvidenceIntegrityError` contract above. All tests use file-backed stores and public store operations; direct SQL only to inspect atomic persistence state.

- [ ] Add `test_two_runs_publish_same_evidence_id` and `test_two_runs_preserve_different_source_text`: each run retrieves only its own record; v1 has two rows with the same local ID.
- [ ] Add `test_same_run_identical_evidence_is_idempotent` through distinct claimed tasks. Add `test_same_run_conflict_rolls_back_batch`, parameterized over source ID/title/URL/text and duplicate IDs within one batch. Include an earlier valid new evidence/fact before conflict; assert earlier records unchanged, new records absent, task still claimed, result absent.
- [ ] Add `test_missing_or_foreign_fact_evidence_rolls_back_batch`, parameterized over missing ID, NULL/empty reference and foreign-only evidence; assert no facts/evidence/result/task completion. Add positive test for facts resolving evidence already present in this run or newly supplied in the same batch.
- [ ] Add `test_stale_publication_writes_no_provenance`: stale same-worker attempt after reclaim supplies evidence/facts; assert false and no mutations. Also assert valid replacement commits result/evidence/facts together.
- [ ] Run `DEBUG=false python -m pytest tests/test_hive_evidence.py -q`; confirm intended failures, then implement task-scoped evidence comparisons and reference validation inside the existing transaction. Do not catch and suppress integrity errors.
- [ ] Rerun evidence tests plus existing lease/fence/dependency cases in `tests/test_hive.py`; review the diff.

## Task 3: Reject missing historical provenance during new assessment/reporting

**Files:** Modify `app/hive/store.py`; extend `tests/test_hive_evidence.py`. Change `app/hive/agents.py` only if store-interface enforcement cannot satisfy the tests; any extra behavior must remain EVI-07.
**Interfaces:** `facts(run_id, 'verified')` is eligible verified memory; unfiltered reads remain historical diagnostics. Existing `run_writer(...) -> tuple[str, dict]` and `set_fact_status(...) -> bool` retain signatures.

- [ ] Add `test_legacy_verified_fact_without_evidence_is_ineligible`: upgrade a literal old database with one valid and one foreign-only verified reference. Assert raw facts/status/report preserved, filtered verified facts include only the valid row, and no foreign evidence copied.
- [ ] Add `test_writer_never_receives_missing_provenance_fact`: capture writer input; only eligible facts appear, every emitted reference resolves in the same run. When all facts are ineligible, writer receives no model call and returns empty report with `no verified facts` gate reason. Existing stored report remains byte-identical.
- [ ] Add `test_verified_promotion_with_missing_evidence_rolls_back`: verifier update batch includes one valid and one unresolved fact; assert explicit error, no status/note/result/task-completion change. Include stale verifier attempt returning false before validation.
- [ ] Run focused tests, demonstrate expected failures, implement eligibility/promotion checks at the store seam, then rerun `DEBUG=false python -m pytest tests/test_hive_evidence.py tests/test_hive_migrations.py tests/test_hive.py -q`.
- [ ] Review results/counts/API implications: eligible verified counts may decrease for damaged historical data; raw historical statuses and stored reports are intentionally retained. No claim of re-verification or historical recovery.

## Task 4: End-to-end compatibility and operator handoff

**Files:** Extend `tests/test_hive.py`, `tests/test_api_research.py`; add `tests/test_hive_cli.py`; update `README.md`, spec/index/plan/register and graph artifacts only after acceptance. Retain dated diagnostic JSON as historical evidence.
**Interfaces:** Existing mock handler/search; real file-backed HiveStore; `/v1/hive/runs` 202 request and polling response; existing CLI arguments/citation forms. No new server endpoint.

- [ ] Add `test_repeated_source_runs_share_file_store` and `test_changed_source_content_isolated_per_run` in `tests/test_hive.py`. Two successive runs both finish with two verified facts, their evidence is resolvable, and reports cite `F-` IDs. Capture per-run verifier input for changed text at one URL and assert no other run's text substituted.
- [ ] Add `TestHiveAPI.test_repeated_source_runs_preserve_contract`: two POSTs share a disposable file store and identical source fixtures; both return 202 and distinct run IDs, polling returns done, verified facts and reports. Preserve existing response field names. Mock provider only; restore router/store globals in fixture cleanup.
- [ ] Add `test_cli_repeated_sources_preserve_output` using `cli.main` with controlled argv and injected mock router/search, one temporary `--db` path for both invocations. Assert report/citation syntax and both emitted JSON summaries show verified success. Add subprocess `--help`/migration-check smoke checks without provider calls; do not start Ollama or cloud models.
- [ ] Run `DEBUG=false python -m pytest tests/test_hive_migrations.py tests/test_hive_evidence.py tests/test_hive_cli.py tests/test_hive.py tests/test_api_research.py tests/test_prompts.py -q`. Expected all pass; record counts/output. No frontend behavior changed, so no browser/build requirement for this repair.
- [ ] Run `DEBUG=false python -m pytest -q` once for broader compatibility. Record and classify every failure; unrelated environment failures do not become passes, and any affected-path failure blocks verification. If local socket fixtures need sandbox permission, request only that capability; no live provider test or broad dependency install.
- [ ] Rerun `DEBUG=false python docs/reviews/reproduce_hive_evidence.py` into a new **post-fix** artifact. Update the probe to capture expected integrity errors and seed historical damage through the frozen legacy fixture rather than public publication, which should now refuse it. Preserve baseline JSON and the broad five-gap audit; do not mark other defects repaired.
- [ ] Document stopped-writer backup/check/apply/start commands, backup location and failure recovery in README. Reconcile evidence counts/keys and unresolved references before/after on fixtures; startup must fail clearly for unmigrated/unsupported stores. No automatic restore. Rollback requires writers stopped and independent confirmation that no accepted post-upgrade writes would be discarded; otherwise forward repair and preserve upgraded data.
- [ ] Update F1 and its subfindings only from observed acceptance results. Map EVI-01–08 to recorded passing checks, request whole-change review per Superpowers, then refresh the code graph and its provenance because source has changed. Mark Verified only after required evidence/review; no staging/commit in the unrelated parent repository.

## Verification record

| Date/environment | Command | Observed result | Meaning/limits |
|---|---|---|---|
| 2026-10-19; Python 3.12.7 / SQLite 3.45.3 | `DEBUG=false PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/test_hive.py -q` | 15 passed in 0.35s | Existing baseline only; no EVI acceptance claim. |
| Same; mock providers/disposable SQLite | `DEBUG=false PYTHONDONTWRITEBYTECODE=1 python docs/reviews/reproduce_hive_evidence.py` | Repeated-source failure, ignored same-run conflict, unresolved publication and writer eligibility gap reproduced | [Saved observations](../../reviews/2026-10-19-hive-001-baseline.json). No real app data opened. |
| Same | Graphify query `evidence publish facts verifier writer` | 161 nodes found; 60 shown under budget | Navigation only; eight relevant source hashes match graph snapshot; direct source read confirmed behavior. |

## Handoff

Self-review: all eight requirements mapped; five review risks assigned tests; signatures and commands consistent; baseline distinguished from future acceptance. Native serial execution recommended because migration, publication and eligibility share the same store. Written spec and this candidate await maintainer review/execution selection. No implementation task is checked complete. No real storage migration has been run.
