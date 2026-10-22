# HIVE-004-A controller rulings

Execution decisions within approved revision2; chronological, including costs and remaining gates.

- Ruling: Retain existing project-owned non-main feature checkout with frozen task-file snapshots — plan explicitly permits it and carries uncommitted HIVE-003 baseline; a new worktree would omit that reviewed authority — cost if wrong: need precise per-task diff isolation and later scoped staging.

- Ruling: Reuse existing tested interpreter/dependencies; do not auto-install root requirements — approved plan limits dependencies and previous suite classified embedding/SDK failures — cost if wrong: required new checks may need isolated environment at their owning task.

- Ruling: Controller owns commits after review; implementers do not stage dirty files — user requires scoped commits and current store baseline includes separate HIVE-003 fixes — cost if wrong: delayed integration checkpoints require retained snapshots.

- Ruling: Add dedicated resource-types and transaction tests to Task1 file scope — shared immutable records and executor/lock semantics need real validation without mixing concerns into migration tests — cost if wrong: two extra test files in review; no new product behavior.

- Ruling: Preserve finite configured SQLite busy_timeout, validate deadline after lock acquisition and before commit, and bound mutex acquisition by remaining deadline — prevents late guarded decisions without changing connection policy — cost if wrong: synchronous SQLite wait may outlast requested response deadline before refusing; no hard real-time response claim.

- Ruling: Allow Task1 to change only the expected schema_version assertion in test_report_provenance_survives_reopen from1 to2 — explicit v2 migration requires version expectation update; report/provenance behavior stays intact — cost if wrong: one compatibility-test hunk; private before snapshot preserves HIVE-003 changes.

- Ruling: Historical ResourceInspection fields may be null for unknown governed policy; hard_tokens is bool-or-null, not a count — old measured usage must not acquire invented reservation semantics — cost if wrong: downstream projections must preserve explicit nullable handling.

- Ruling: Foundation uses HiveStore.transactions / database_io and async aclose with a shared injected Clock; unused executor is lazy — gives later tasks one ownership path and preserves old raw-db-close fixtures without new threads — cost if wrong: downstream service must consistently await aclose for started work.

- Ruling: Every transaction-helper write with deadline_monotonic uses effective BEGIN EXCLUSIVE even when exclusive=True is omitted — admission must not reopen the reproduced reader-blocked COMMIT race — cost if wrong: stricter rollback-journal reader concurrency; WAL semantics unchanged, no throughput promise. Require default-call held-reader regression.

- Task1 self-review found inherited SQL DDL normalization loses quoted CHECK-literal semantics. Ruling: lexical literal-preserving normalization is required within LED-10 exact-shape authority — new enum constraints cannot be accepted under altered meaning — cost if wrong: more schema canonicalization cases; preserve frozen v0/v1 compatibility and avoid a general SQL parser. Require RED→GREEN and explicit task-review attention.

- Ruling: Generic UsageReceipt categories remain defensive immutable JSON in Task1; Task4 owns normalized category semantics using disjoint/subsets count maps, with complete total authoritative — avoids inventing provider arithmetic in the schema foundation — cost if wrong: Task4 must validate completeness, numeric category counts and subset separation before any complete settlement.

- Ruling: Keep dated HIVE-003 screenshot baselines unchanged; full browser reruns overwrote two tracked fixtures, so preserve regenerated copies in ignored .local-only/hive-004-renderer-reruns and restore original HEAD bytes — avoids presenting nondeterministic reruns as revised historical evidence — cost if wrong: current rerun visuals remain local only; explicit future visual-baseline refresh must be separately reviewed.

- Ruling: Add immutable run_id FK to resource_allocations in Task2, inherited by child grants; create_root requires legacy run and binds allocation/run/limit. Existing schema had no durable root/run identity until Task3 metadata, causing circular construction. Keep request/profile/admission metadata Task3-owned; expose _create_root_in_transaction for its atomic composition. Amend never-activated v2 DDL and affected tests within approved LED02/03 — cost if wrong: one additional schema hunk needs focused migration/reopen review; no real database/version upgrade.

- Ruling: Task2 trusts internal PreparedCall.request_fingerprint as canonical Task4 producer identity and compares persisted identity/route/profile/mode/bound/authority. No request-message persistence or duplicate hashing in SQL ledger — messages explicitly stay in originating coroutine. Task4 computes exact message/generation-parameter hash and public facade never accepts an externally supplied fingerprint — cost if wrong: arbitrary in-process forged records are outside this trust boundary; later mutation tests remain mandatory.

- Ruling: Root may stage frozen reviewed blobs while Task2 modifies working files; every staged blob hash must equal reviewed manifest and index scopes remain serial — preserves task isolation without interrupting source work — cost if wrong: commit ordering must retain before/after receipts; never use blanket staging.

- Ruling: Preserve retained command logs byte-for-byte, including pytest traceback trailing whitespace; apply staged whitespace check to non-log content separately — raw failure evidence should not be silently cleaned — cost if wrong: full git diff --check reports log-only whitespace; product/docs checks remain strict.
