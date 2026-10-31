# Task 1 implementation report

Status: DONE_WITH_CONCERNS — implemented foundation; fresh controller review pending. HIVE-004-A remains In progress; this task does not activate governed admission or close integrated acceptance gates.

Governing spec: `docs/superpowers/specs/2026-10-21-resource-ledger-design.md`, LED-09/LED-10. Executed only the extracted Task 1 brief and shared context, without reading the whole implementation plan. Followed project workflow, TDD, and verification-before-completion. No subagents, staging, commits, pushes, dependency installs, paid/live providers, real application migration, or personal-host configuration.

## Changes

- Added `app/hive/resource_types.py`: shared frozen validated records; deep defensive freezing of nested JSON; strict signed-64-bit counts and checked addition; finite timing values and policy relationships; deterministic canonical policy JSON/digest; injected `Clock`/`SystemClock`; classified resource/provider exceptions. `RunRequest` retains runner defaults, including derived heartbeat when a custom lease is supplied; `to_dict()` produces independent serializable JSON without runtime callables.
- Added `app/hive/resource_schema.py`: seven additive resource tables and five queue/lookup indexes. Tables cover policy/profile identity, nested allocations, admission/ownership, logical call metadata/receipts/certainty/permits, fairness cursors, and legacy usage projections. Explicit PK/unique/check/FK constraints cover local scalar invariants. Ledger/allocation state-transition arithmetic belongs to later tasks, rather than SQL triggers here.
- Updated `schema.py`: new empty databases initialize at v2; existing v0/v1 require explicit maintenance. V1 table definitions are byte-for-byte unchanged. Exact validation covers all resource columns, indexes and their full DDL, CHECK/FK semantics, and unexpected tables/indexes/views/triggers. V2 resource FK corruption fails closed on reopen.
- Updated `migrate.py`: positional source/backup API preserved; keyword `target_version=2`, CLI `--target-version {1,2}`. Recognized v0/v1 upgrade only through stopped-writer maintenance, verified private non-overwriting backup, an exclusive transaction and atomic marker. V0→v2 validates/reconciles intermediate v1 inside that same transaction. Backup/source historical snapshots must match before DDL; source changes after backup are refused. No resource reservation/admission backfill. Downgrades refuse.
- Added `transactions.py`: `SQLiteTransactions.write` owns shared lock/connection, validates deadlines, bounds mutex acquisition, checks after SQLite acquisition and before commit, uses EXCLUSIVE for every deadline-bound operation, rolls back only its active transaction, and maps only genuine SQLITE_BUSY-family codes to `ResourceBusy`. Other SQLite/callback errors retain their identity. Async callbacks/returned awaitables refuse. Callbacks are trusted internal synchronous SQL-only operations; this is not a sandbox for arbitrary callbacks.
- Added owned `DatabaseIO`: one private worker; no default thread pool; creating an unused executor starts no thread. Submitted work survives waiter cancellation/timeout and is retained until drain. `aclose()` drains, records detached outcomes in `detached_results`, and surfaces detached failures, including busy failures; caller callback TimeoutError is preserved. Cancelled close can be awaited again.
- Updated `HiveStore` constructor with additive `clock=`; `.transactions` and `.database_io` share that clock, SQLite connection and mutex; FK enforcement enabled; async `.aclose()` drains before closing. No `.resources`/`.admission` stubs. Pre-existing HIVE-003 code from the helpers section onward is byte-identical to the frozen before snapshot.
- Added frozen v1 fixture/validator and dedicated migration/type/transaction tests. Existing migration assertions track current default v2. Controller authorized the sole Task 1 change in `tests/test_hive_report_store.py`: schema version assertion 1→2; no provenance, lease, reader, WAL, deadline, literal-rendering or publication assertion was weakened.

## TDD and verification receipts

Exact pytest argv, explicit environment overrides, exit codes, duration and log paths are in `docs/reports/hive-004/task-1-commands.json`. Test commands used `/opt/anaconda3/bin/python`; no package installation. Logs normalize the checkout/home path; interpreter and browser-cache argv/env remain explicit.

- `task-1-migrations-red.log`: 11 intended behavior failures / 28 legacy passes, before product edits. New-empty stayed v1; v1 opened without maintenance; default upgrades remained v1; target-version argument was missing; interruptions did not exercise v2; old-writer refusal and non-overwriting v1 backup failed. These were actual behavioral failures, not assertion typos.
- `task-1-foundation-red.log`: 14 new type/transaction tests failed because their modules did not yet exist. Subsequent RED cycles below establish concrete invariant failures after those contracts existed.
- `task-1-foundation-green.log`: 14 passed.
- `task-1-edge-red.log`: four observed failures: hard indicator incorrectly treated as count, missing store clock/ownership seam, concurrent change after backup not refused, wildcard-filtered unexpected sqlite-like object not refused. `task-1-edge-green.log`: 106 passed after fixes.
- `task-1-final-fault-red.log`: default deadline write ran its decision under a held reader, and oversized finite-number input leaked OverflowError. `task-1-final-focused.log`: 119 passed after fixes.
- `task-1-self-review-red.log`: callback TimeoutError was incorrectly translated to ResourceBusy, and custom lease lost runner-derived heartbeat. `task-1-self-review-green.log`: 23 passed after fixes.
- `task-1-shape-literal-red.log`: mutated CHECK string literal case/whitespace was accepted; mandatory actual count accepted null. `task-1-shape-literal-green.log`: 126 passed after fixes.
- `task-1-orphan-red.log`: orphan resource rows reopened successfully. `task-1-final-green.log`: 127 passed after FK validation.
- `task-1-detached-busy-red.log`: close reported success after a cancelled worker returned ResourceBusy. `task-1-handoff-focused.log`: 128 passed after preserving/surfacing all detached failures.
- `task-1-expression-index-red.log`: unexpected expression index leaked Python None/string sort TypeError. `task-1-frozen-focused.log`: **130 passed**, including typed refusal of expression/partial indexes, after stable metadata sorting.
- `task-1-migration-reconciliation.log`: **4 passed**, with actual six-table before/after/backup hashes at process-kill barriers after resource DDL, after marker, before commit and after commit. Before commit, recovery retained exact v1 shape/history; after commit it retained exact v2 shape/history. All four recovered integrity_check=ok. Separate injected KeyboardInterrupt tests cover table/index/marker/commit rollback.
- `task-1-static.log`: scoped diff whitespace check; frozen original v1 DDL equals production V1_SCHEMA and the literal fixture; existing HIVE-003 store implementation byte-preserved; report-store test has exactly the authorized version assertion change.

Final full-suite receipt: `task-1-frozen-full-permitted.log`: **452 passed / 11 failed in 21.69s**, exit 1; failure names exactly match the 11-failure preimplementation baseline. The 55 added cases account for 397→452 passes. No setup errors in the comparable permitted run..

Earlier restricted full suite (`task-1-full.log`) was 445 passed / 11 failures / 3 setup errors before final fault additions. That run could not bind localhost for the three SDK test fixtures and lacked the default-cache Playwright browser. Comparable permitted reruns use existing `/tmp/hive-003-browsers`, local fake transports/loopback only, and the exact baseline environment: `DEBUG=false PYTHONDONTWRITEBYTECODE=1 PLAYWRIGHT_BROWSERS_PATH=/tmp/hive-003-browsers`. Earlier permitted run (`task-1-full-permitted.log`) was 449 passed / the same 11 baseline failures. The final frozen full run supersedes earlier counts.

The unchanged baseline dependency failures are:

1. `tests/test_llm_sdk_wiring.py::test_sdk_roundtrip[anthropic-ANTHROPIC_API_KEY-hi-anthropic-tokens1]` — missing `anthropic` package.
2. `tests/test_semantic_cache.py::TestSemanticCache::test_set_and_get` — `HfFolder` import incompatibility.
3. `tests/test_semantic_cache.py::TestSemanticCache::test_semantic_similarity_hit` — same.
4. `tests/test_semantic_cache.py::TestSemanticCache::test_cache_miss` — same.
5. `tests/test_semantic_cache.py::TestSemanticCache::test_context_key` — same.
6. `tests/test_semantic_cache.py::TestSemanticCache::test_invalidate` — same.
7. `tests/test_semantic_cache.py::TestSemanticCache::test_stats` — same.
8. `tests/test_tools_vectordb.py::TestChromaDB::test_chroma_upsert` — same.
9. `tests/test_tools_vectordb.py::TestChromaDB::test_chroma_query` — same.
10. `tests/test_tools_vectordb.py::TestChromaDB::test_chroma_upsert_deduplication` — same.
11. `tests/test_tools_vectordb.py::TestChromaDB::test_chroma_delete_source` — same.

The additional restricted-only failure was `tests/test_hive_reports.py::test_marked_rendering_round_trip` (missing default-cache browser). Restricted-only setup errors were `tests/test_llm_sdk_wiring.py::test_sdk_roundtrip[openai-OPENAI_API_KEY-hi-openai-tokens0]`, `[anthropic-ANTHROPIC_API_KEY-hi-anthropic-tokens1]`, and `[gemini-GEMINI_API_KEY-hi-gemini-tokens2]` (localhost bind PermissionError). The permitted run removes those environment limitations; it does not install or repair dependencies.

## Self-review and handoff contracts

Reviewed Task 1 scope against the extracted requirements and current source: all seven tables, explicit target paths, no historical backfill, interruption rollback, old writer refusal, content/report preservation, lock/deadline/error paths, nested immutability, cancellation and close ownership are covered. Historical data/report bytes and measured ledger values remain unchanged. Foundation checks do not prove future fair admission/accounting/provider behavior. Controller owns independent review, issue register/plan/index updates and any scoped commit.

Three inherited exact-validation defects were repaired within this task: SQL LIKE wildcard hid unexpected sqlite-like names; DDL normalization changed semantic string literals; expression-index NULL metadata caused TypeError during sorting. Literal case/whitespace/escaped-quote changes refuse; harmless known identifier quoting remains accepted. No general SQL parser was added. Full sqlite_master definitions are compared for explicit indexes as well as tables, so CHECK changes, expression text and partial predicates are not inferred solely from PRAGMAs. Resource indexes themselves are ordinary indexes.

Use these exact producer seams in later tasks:

- `HiveStore(clock=...)`, `.transactions`, `.database_io`, `await .aclose()`; shared connection and lock; no second accounting DB.
- `SQLiteTransactions(db, lock, clock=...).write(fn, deadline_monotonic=..., exclusive=...)`, callback receives connection synchronously. A deadline always implies EXCLUSIVE; no-deadline default remains IMMEDIATE.
- `DatabaseIO(clock=...).call(fn, deadline_monotonic=...)`, zero-argument sync callback. The originating event loop owns this executor wrapper; local remaining duration converts into asyncio loop timeout. No monotonic absolute timestamp is persisted.
- `ResourcePolicy.canonical_json`, `.digest`; record `.to_dict()` produces mutable independent JSON copies for serialization. Do not serialize runtime search callables or PreparedCall messages to durable call rows.
- `ResourceInspection.hard_tokens` is `bool | None`: True only qualified hard mode, False estimated, None historical. Historical mode/headroom stay null; actual/reserved/unknown/debt counts remain strict integer values. This is an enforcement indicator, not another token count.
- `UsageReceipt.categories` is defensive deep-frozen JSON in Task 1. Controller pins the normalized Task 4 handoff format to `{'disjoint': {name: int|null}, 'subsets': {name: int|null}}`. Task 4 validates category semantics; top-level complete total is authoritative. Task 1 does not claim category aggregation/double-counting proof.

## Concerns and operating limits

1. Full suite remains red solely for the 11 reproduced baseline dependency failures; no dependency repair was authorized or attempted. Integrated HIVE-004 acceptance remains incomplete until later tasks.
2. Configured SQLite busy timeout is never changed. An in-progress lock acquisition can consume that already-configured finite timeout before the immediate post-acquisition deadline check. This is controller-approved; it is not a hard real-time filesystem/SQLite latency guarantee. Mutex waits are bounded by remaining deadline (or the captured configured local timeout without one), and deadline-bound writes take the reader-conflicting lock before guarded decisions.
3. Database callbacks are internal synchronous SQL-only operations. Do not put providers/network/await/transaction-control work inside them. Their finite SQL busy timeout is what makes cancellation drain finite; arbitrary blocking user callbacks are outside the contract.
4. Operator must stop old/new writers and quiesce outstanding old external requests before applying/activating v2. No live request, real data migration or runtime activation was performed. Historical nonterminal runs have no resource admission row and cannot become governed resumable work merely by migration.
5. Source is frozen for fresh controller review. Fresh review may identify further scoped fixes; this implementer performed no commit.

## Frozen review snapshot

```json
{
  "app/hive/resource_types.py": "afa529c38682e1900160a9b4cd17e4e220b6441f3905a137eed979e3a0cb6c83",
  "app/hive/resource_schema.py": "c448479b84795eafbf8b3967ea289ad89d115dd56fbedaca8036a97ff72611dd",
  "app/hive/transactions.py": "f72e32cabb2d7a66d50aa276964fb59c35265ac05ab9fefbd6e96adc56b57f66",
  "app/hive/schema.py": "5a5c248d49dab6bc994dfd60683377ce24885418bb970b13472f213ccbb0548c",
  "app/hive/migrate.py": "a70cabc8abf9c5da28a6054826273572ac1a16a9bd1e7fcb1f796d3a71d5586d",
  "app/hive/store.py": "073d6ed134c5ac2f80697e25beb368bc250562f882a417ce37f18027e38f7bce",
  "tests/hive_resource_testkit.py": "f06902dbfb4f3fb481678577bd0201a3ae47b3de36e20724e0710777647d726a",
  "tests/test_hive_resource_migrations.py": "7a860aab6efd7fa82fc52537c58fb6fe1b9c3d8703a6e3414217e975118a0e27",
  "tests/test_hive_resource_types.py": "381fd28a7b1bcc038c55b117834fc71b3a1feb13cfc1a56d7771f4177c1944cb",
  "tests/test_hive_transactions.py": "1274e2091d006e1bff0e6d2dcdb36f1ce74b58053c682db55ff31ea763c64afc",
  "tests/test_hive_migrations.py": "2313753170d5cf3ce8a1caa1be7a0bf6d81d567cb0f098f0d68815028b6bbed8",
  "tests/test_hive_report_store.py": "ad70df54f5f7bc9fd4c7f09f9ee5dc16038338137f25a56168ba84e479e5b677"
}
```
