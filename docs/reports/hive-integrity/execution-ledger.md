# Execution ledger — HIVE-001 then HIVE-002

Authorization: user requested completing spec 1 then working on spec 2, 2026-10-20.
Branch: hive-001-002-integrity. Existing MCP/architecture edits retained.
Baseline: existing hive suite 15 passed, Python 3.12.7, SQLite version captured in test evidence.

## Decisions and pre-flight

- Ruling: use a feature branch in the current checkout, retaining prior edits; no separate worktree or commit. Reason: shared pending artifacts and explicit instruction to continue this repo. Cost if wrong: isolation is file-level rather than a second checkout.
- Ruling: repair the plan's stale parent-Git constraint; verified project now owns its Git root. No staging or publishing authorized or performed.
- Task 1 produces versioned evidence schema; Task 2 consumes it. Existing evidence columns/citation IDs retained; composite key is only table-shape change.
- Task 2 publication guard and Task 3 promotion/filtered reads share the transaction seam. Integrity errors roll back whole batches, while stale ownership returns false before provenance validation.
- Task 4 full runs consume all three tasks; old-data fixtures use a frozen schema, not the changing live initializer.

## Progress

- HIVE-001 Task 1: in progress — failing migration/provenance tests next.

- HIVE-001 Tasks 1–3: implemented. Migration + old hive 39 passed; publication/eligibility + migration/hive 56 passed. Schema key regression failed before implementation. New evidence suite: 12 missing-contract/behavior failures before fix, 17 passed after.
- HIVE-001 Task 4: API/CLI/full-flow acceptance 82 passed. API test fixture initially reused cached app settings; isolated both SQLite dependencies and Hive store after unmigrated-store refusal. No real data migrated. Broader suite: 10 embedding import failures, 3 local socket fixture errors; full output retained.
- HIVE-001 final review/graph refresh pending as part of combined delivery. HIVE-002 Task 1 starts after the HIVE-001 acceptance gate.
- Ruling: user explicitly requested implementation, so continue native execution without repeating design/plan approval questions. Cost if wrong: technical choices remain bounded by written specs and recorded interface decisions.

- HIVE-002 Task 1: 14 store tests passed; controlled renewal/expiry and competing handles included. Added barrier-based expiry-vs-renewal test; 36 execution checks passed before review additions.
- HIVE-002 Task 2: runtime RED 19 failed/15 passed, then combined acceptance 121 passed. Interface RED four failures before deadline fields/options were implemented. Router zero-retry case RED then GREEN; Hive disables router-level retry so task retry policy owns attempts.
- Ruling: preserve successful legacy search consumers with opt-in `raise_on_error` in retrieval adapters; Hive uses strict mode. Empty results with backend failures raise execution unavailability; partial results remain usable. Cost if wrong: clients using strict mode may retry otherwise-empty research when only one backend is unavailable.
- Final independent review: three Important findings, all accepted: unknown CHECK/FK/collation loss; swallowed default retrieval errors; synchronous arXiv blocking event-loop timers. Eight regression cases failed before fixes and passed after. No second review requested; whole-suite verification follows the single repair pass.
- External thread limitation: cancelling a task cannot forcibly stop an already-running sync SDK request; its result cannot publish. CLI event-loop shutdown may wait for that thread. Durable external-call reconciliation/global capacity remain HIVE-004/006, not claimed here.
- Final review repairs: 8/8 new regression cases GREEN, 138 focused checks GREEN, MCP real-route/stdio/HTTP fixtures 54/54 GREEN with `HIVE_APP_PYTHON` supplied (initial omitted environment skipped that one case; final run has zero skips).
- Additional lease-loss integration confirms a cancelled search returning late cannot dispatch the old attempt's researcher model call; replacement succeeds with one accepted researcher call. Final focused count increases to 139.
- Broad suite after repairs: 151 passed, 10 unrelated embedding import failures and 3 restricted local-socket fixture errors. Socket-authorized SDK suite: 3 passed, 1 missing Anthropic SDK failure. Full names retained in raw outputs; HIVE-011 owns dependency repair.

- Final acceptance: 140 passed, including fresh-process reopen at six crash boundaries and interrupted-backup cleanup. Broader suite final: 153 passed / 10 unrelated embedding failures / 3 sandbox socket errors. SDK local rerun 3 passed / 1 absent Anthropic SDK; MCP 54 passed, no skips.
- Final graph: 1,271 nodes / 2,890 edges / 75 communities, 110 source fingerprints matched. No missing/dangling endpoints or duplicate edges; one known test-super().execute extraction self-loop retained and disclosed. Chrome accessible tree displayed current counts and community labels; no screenshot/search-quality claim.
- HIVE-001 Tasks 1–4: complete. HIVE-002 Tasks 1–3: complete. Spec/index states updated to Verified within SQLite lite scope. Final exact-source receipt and document checks are in verification.json. No staged changes, commits or real-data migrations.
