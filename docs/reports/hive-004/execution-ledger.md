# HIVE-004-A execution ledger

22 October 2026. [Approved spec revision 2](../../superpowers/specs/2026-10-21-resource-ledger-design.md), [approved implementation plan](../../superpowers/plans/2026-10-21-resource-admission.md).

User spec approval: “Approve revision 2; write the plan.” User plan approval: “Approve plan; start Task 1.” Preserved method: fresh implementer and fresh reviewer per task, sequential execution, then final whole-change review.

## Baseline and isolation

Existing project-owned feature checkout retained; non-main branch. Pre-existing HIVE-003 changes are frozen per task and preserved. Task diffs compare before/after file snapshots rather than including the entire dirty Git diff. Controller owns scoped commits after review. No push, merge, real database migration or runtime deployment performed by starting implementation.

Fresh [full-suite baseline](execution-baseline.log): **397 passed, 11 failed**, exit 1. Ten failures are installed embedding-stack HfFolder imports; one lacks Anthropic SDK. [Command receipt](execution-baseline.json). This is baseline classification, not HIVE-004 acceptance. New provider-control checks still require their own isolated environment in Task 4.

## Progress

| Task | State | Evidence |
|---|---|---|
| 1 — Schema/types/transactions and explicit migration | Verified foundation; fresh review approved | [Review](task-1-review.md): spec compliant, quality approved; 130 focused passed; full452passed/11 unchanged dependency failures; no real data or package changes |
| 2 — Conserved allocations/call accounting | In progress | Fresh implementer; independent review follows |
| 3 — Shared queues/permits/fairness | Pending | No implementation |
| 4 — Provider preparation/single-attempt controls | Pending | No implementation |
| 5 — Async governed Caller | Pending | No implementation |
| 6 — Admitted runtime/lifecycle repair | Pending | No implementation |
| 7 — API/CLI/MCP projections | Pending | No implementation |
| 8 — Load/fault acceptance and final review | Pending | No implementation |

## Controller rulings

- Retain the existing feature checkout and freeze task-owned paths: a fresh worktree would omit uncommitted reviewed HIVE-003 changes. Cost: precise snapshot-based review and staged-scope checks remain necessary.
- Reuse current environment instead of auto-installing root requirements. Existing dependency failures remain visible; required new adapter coverage uses the planned narrow environment. Cost: environment limitations cannot be counted as passes.
- Add dedicated resource-type and transaction test files to Task 1. They exercise existing task requirements without mixing immutable-record and executor behavior into migration tests. Cost: two extra test files, no extra product scope.
- Controller owns commits and prior-change isolation; implementers do not stage or push dirty files. Cost: retain private recovery snapshots until safe scoped publication.

No current cap/fairness/provider-control fix is claimed. F4/F10 remain Scoped until integrated acceptance; F3-J lifecycle repair belongs to Task 6. Parent multi-host and money policies remain separate.

## Task 1 review dispositions

[Fresh review](task-1-review.md) found no Critical/Important issues. Live source hashes match its frozen 12-file package. Real-data maintenance/quiescence remain operator gates; no database activation occurred. Accounting, category normalization, shared permits/fairness and runtime integration remain later-task gates. The inherited pytest fixture-loop warning is deferred to scoped test-configuration work and final-review triage.

Browser reruns regenerated two dated HIVE-003 screenshots. Their original tracked bytes were restored; rerun copies stay in ignored local scratch. Existing dated evidence was not silently replaced. Scoped commits are controller-owned; no push/merge.

## Scoped local checkpoints

- `870ef18` — report publication deadline repair (HIVE-003).
- `4290d88` — report compatibility tests and diagnostics (HIVE-003).
- `2fac99f` — accepted Task1 schema/types/transaction/migration foundation.

Frozen staged hashes were checked against review snapshots; private-path guard passed. No push or merge. Task2 working changes were excluded from Task1 checkpoint. An automatic approval rejection over possible staged-scope overlap was resolved by a fresh exact index path/hash check before retry; no action remains blocked.

Task2 schema ruling: add immutable allocation.run_id FK and inherit it through child grants. The accepted design requires durable root/run identity, while Task3's resource_runs needs an already-created allocation. Keep Task3 request/profile/admission metadata separate and compose enqueue through an internal root-creation callback. Cost: an additional reviewed DDL/migration-test hunk in never-activated v2; no real database upgrade.

Task2 uses trusted internal request_fingerprint identity; Task4 owns canonical hashing of exact messages/generation parameters and must prohibit public supplied hashes. Messages stay local. Cost: mutation/forgery handling at that producer boundary remains a mandatory later acceptance gate.

HIVE-003 closure/evidence/dated graph recorded separately in12415a1. All77committed blobs match the frozen publication manifest;121graph source hashes match source checkpoint4290d88. Raw retained command logs preserve pytest whitespace; staged non-log whitespace checks pass.
