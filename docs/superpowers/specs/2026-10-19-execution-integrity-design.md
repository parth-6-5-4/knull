# Attempt integrity and terminal progress design

**Spec ID:** HIVE-002
**Status:** Draft
**Date:** 2026-10-19
**Owner:** Project maintainer
**Approval:** Pending user review
**Depends on:** None; coordinate persistence edits with HIVE-001
**Plan:** Not written; requires spec approval

## Intent and evidence

Accepted work must not be overwritten by a late worker, and a permanently failed prerequisite must not leave a run polling forever. The current store fences `publish()`/`set_fact_status()` but not `mark_exhausted()`; expiry/renewal contain unguarded read-then-write operations. Runner never calls heartbeat. Exhausted tasks leave pending descendants counted as open. [Audit F2/F5/F8](../../reviews/hive-modularization-review.md), [probe observations](../../reviews/hive-gap-evidence.json).

## Scope and choice

Harden execution invariants behind the store/runner seam, usable by the existing single-process engine and later Postgres implementation. Keep SQLite for this initial repair. Adding a queue alone is rejected because it does not make stale mutations or dependency propagation correct. Cross-process Postgres guarantees and new lifecycle names belong to HIVE-006.

## Requirements

| ID | Required behavior | Acceptance oracle |
|---|---|---|
| EXE-01 | Every attempt-owned mutation checks task, owner, attempt, fence, valid status and lease where relevant in one DB transaction/conditional write. | Late success, rejection, failure, release and renewal cannot alter a newer or completed attempt. |
| EXE-02 | Expiry reclaim compares the observed lease/fence and cannot overwrite a concurrent renewal/completion. | Controlled-time interleavings preserve valid current ownership; exactly one successor may claim. |
| EXE-03 | Healthy long-running work renews ownership; lease loss stops new subcalls and excludes subsequent publication. | Task lasting longer than one lease completes while renewing; killed worker is reclaimed; delayed result is rejected. |
| EXE-04 | Final failure blocks descendants that require success; independent branches may finish. | Permanent tool failure reaches a finite terminal outcome after configured attempts; descendants show causal prerequisite IDs. |
| EXE-05 | No-progress and impossible dependency graphs terminate visibly. | Missing/cyclic dependency is rejected before execution; zero runnable/in-flight work with unsatisfied prerequisites finalizes blocked. |
| EXE-06 | Worker/watchdog/renewal tasks are supervised and cleaned up. | Cancellation, unexpected exception and run completion leave no orphan background loops or active leases without recovery metadata. |
| EXE-07 | Attempts, task deadlines and arguments are bounded consistently across API/CLI/direct invocation. | Nonpositive workers/lease/deadline and invalid limits reject before planning; permanent error does not spin without backoff. |
| EXE-08 | Transient tool/model failure remains distinguishable from unsupported evidence. | Execution failure records retryable/unavailable cause; it does not certify that a source contradicts a claim. |

## Interfaces and state ownership

The store owns atomic claim/renew/commit/fail/reclaim semantics. Runner supplies an immutable assignment identity and receives accepted/stale/terminal outcome. Error result includes a machine-readable reason and safe text, not unstructured exception matching. Exact Python signatures belong to the reviewed implementation plan; all mutation paths must use the same ownership predicate.

Attempt identity changes on retry; task identity and accepted predecessor evidence remain stable. Completion and attempt failure are different operations. Successful tasks are immutable unless an explicit versioned invalidation protocol replaces them. HIVE-006 maps existing `done/claimed/exhausted` names to its new lifecycle without changing this invariant.

Use DB time for lease predicates in the Postgres successor. SQLite tests use one injected clock per store operation; scheduler intervals use monotonic elapsed time. Initial policy proposal: 300-second lease, renewal every 60 seconds, three attempt limit. Renewal interval must be strictly below lease duration. Task/run deadlines come from resource policy and dominate renewal.

## Failures, compatibility and recovery

Keep existing successful lite API/CLI behavior. Add explicit causal blocked outcomes rather than reporting success with missing required work. Retry only classified transient failures within configured caps; malformed task kinds fail closed. Cancellation must stop admission immediately; outstanding external-call outcomes remain uncertain until settled/reconciled under HIVE-004.

Deploy to the lite executor first behind focused tests. No active task schema is destructively rewritten without a recoverable migration. On failure, stop new admissions, retain task/attempt records, and repair from durable ownership; do not reopen completed tasks to simplify rollback.

## Verification and review

| Requirements | Required checks |
|---|---|
| EXE-01/02/03 | Store-interface stale-fence tests with separate DB handles, deterministic time and publication/expiry/renewal interleavings; long task and lost lease runner tests |
| EXE-04/05/07 | Permanent outage, invalid arguments, missing/cyclic dependencies, mixed successful/failed branches and no-progress termination |
| EXE-06/08 | Async cancellation/leak checks; unavailable verifier remains an execution outcome |

Existing probes are historical observations, not these acceptance tests. No new acceptance checks executed. Self-reviewed 2026-10-19; review pending. Proposed timing values require review, but every configured value must obey the stated invariants.
