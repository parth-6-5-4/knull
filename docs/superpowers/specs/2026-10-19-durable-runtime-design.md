# Durable modular execution runtime design

**Spec ID:** HIVE-006
**Status:** Draft
**Date:** 2026-10-19
**Owner:** Project maintainer
**Approval:** Pending user review
**Depends on:** HIVE-001, HIVE-002, HIVE-004 for authoritative integration
**Plan:** Not written; requires spec approval

## Intent, current behavior and alternatives

API acceptance must survive web-process death; tasks resume from committed state rather than regenerate their plan. Today SQLite stores data, but `BackgroundTasks` owns execution and invoking `run_hive(run_id=...)` plans again. Diagnostic events do not contain every atomic transition. [Audit F7](../../reviews/hive-modularization-review.md).

Choose one modular application with Postgres-backed task state and bounded worker processes. SQLite-only remains appropriate for lite compatibility; a separate broker/workflow platform is deferred until actual timer/workflow requirements justify its cost. Choose state tables plus append-only transaction events. Full event sourcing is outside scope: recovery reads committed authoritative state rather than replaying paid calls.

## Canonical contracts

These are the shared contracts for the new engine. Physical schema and exact Python types belong in its implementation plan; consumers must preserve these field meanings.

| Contract | Required data / ownership |
|---|---|
| RunSpec | Objective, engine version, immutable plan/version, deadline, limits, policy/config/prompt/model/tool manifest references, principal scope, request key/hash |
| TaskSpec | Stable task ID, run ID, parent task ID, kind, required capability, input references, dependency IDs, completion criteria, limits/allocation reference, plan version |
| Assignment | Task ID/version, unique attempt ID, increasing fence, worker ID, lease expiry, pinned role profile and scoped context/tool manifest |
| CandidateResult | Task/attempt identity, typed result reference, evidence/fact references, execution status; accepted only by guarded commit |
| RunView | Run and task versions/states, parent/dependency relationships, current attempts/leases, findings, decisions, resource state, causal failures, event cursor |

`RoleProfile` and delegation policy are owned by HIVE-008. `DecisionRequest/Outcome` by HIVE-007. Resource grant/reservation records by HIVE-004. Content/provenance requirements remain HIVE-001 and assessment/report specifications.

## State model

Task states: pending → ready → leased → succeeded. A coordinating task may transition leased → waiting_children, releasing its worker lease; a version-checked child aggregate can make it ready for a new attempt or succeeded. Leased attempt failure may return task to ready only within attempt/deadline policy. Failed, blocked and cancelled are terminal task outcomes. Pending dependencies must resolve before ready. Required failed/blocked/cancelled predecessors cause blocked descendants, not infinite pending.

Run states: queued → planning → running; running may enter pausing → paused or waiting_review. Resume is allowed from paused/waiting_review after the recorded condition is resolved within existing authority/deadline. Completed, partial, blocked, stopped, failed and cancelled are terminal. Crash recovery of a running/planning/pausing run is not a new user resume command and does not regenerate its plan. A terminal run requires a new linked continuation run for additional work.

Pause stops new claims/calls and drains active work to recorded outcomes; it becomes paused only after no active assignments remain. Cancel fences outstanding assignments and closes admission; external spend may remain unknown. Completed requires all required outcomes and report gates; partial requires an explicit accepted partial-results policy, otherwise unmet required work is blocked. Budget/deadline exhaustion yields stopped, not completed.

## Requirements

| ID | Required behavior | Acceptance oracle |
|---|---|---|
| RUN-01 | Submission atomically persists accepted run and planning task before returning. | Kill web process immediately after 202; independent scheduler finds run and continues. |
| RUN-02 | Stable operation identity deduplicates submissions within caller scope. | Same key/hash returns same run; key with different canonical request returns 409; in-flight duplicate cannot create a second plan. |
| RUN-03 | Plan creation and child scheduling are atomic, versioned and idempotent. | Kill mid-plan yields no half-visible graph; retry cannot attach old dependency positions to new generated queries. |
| RUN-04 | Every transition appends an event in the same transaction. | Failed transaction leaves neither partial state nor standalone success event; events have monotonic per-run sequence and unique operation ID. |
| RUN-05 | Recovery preserves manifests, accepted results, evidence and budgets. | Restart scheduler/workers after claim, call, result and finalization boundaries; no accepted result rewrites or automatic generation replay. |
| RUN-06 | Claims and coordinator authority are safe across hosts. | Short guarded Postgres claim transactions and coordinator leases/version checks prevent concurrent authoritative scheduling/finalization. |
| RUN-07 | Controls are idempotent and version-aware. | Repeated pause/resume/cancel with command identity is harmless; stale expected version returns 409 without effects. |
| RUN-08 | Dependencies, parent links and task kinds are validated before publication. | Cross-run edge, missing node, cycle, unknown registered kind or invalid parent rejects entire proposed graph. |
| RUN-09 | Inspection reflects committed state, not reconstructed recent events. | Current lease/parent/dependency state is present even after event pagination/history truncation; unknown usage remains visible. |
| RUN-10 | New and legacy execution remain pinned and distinguishable. | v1 continues lite behavior; modular-v1 cannot be resumed by lite code; legacy stored runs are not silently imported as resumable. |
| RUN-11 | Read/event volume is bounded and cursor-based. | Pagination yields stable increasing event IDs without duplicate side effects or loading all history for a page. |
| RUN-12 | Unexpected process exceptions leave a recoverable condition and observable cause. | Worker/scheduler kill or DB outage never requires erasing records; readiness distinguishes unavailable DB from healthy idle engine. |

## Modules and interfaces

Proposed seams: `app/orchestration/runtime.py` for `submit/control/inspect`; `app/orchestration/contracts.py` for canonical contracts; `app/orchestration/scheduler.py` for durable readiness and claims; `app/orchestration/execution.py` for scoped assignments; store implementation behind guarded claim/renew/commit/transition operations. API/CLI call lifecycle interface; they do not create their own worker loops.

Postgres owns transactions, constraints, DB lease time and ordering. Use indexed ready-task claims with `FOR UPDATE SKIP LOCKED`, guarded updates and short transactions; do not hold locks over network work. Readiness/finalization uses an authoritative transaction rather than interpreting skipped rows as proof that no work remains. A test adapter supports behavior fixtures; actual Postgres tests establish locking semantics.

Evidence snapshots/run links, assessments, immutable manifests and per-run transitions are durable. Unknown calls are reconciled through HIVE-004. Long-lived workers hold no authoritative conversation state; assignments reconstruct minimal context from immutable references.

## API and compatibility

New engine uses `POST /v2/hive/runs`, `GET /v2/hive/runs/{id}`, `POST /v2/hive/runs/{id}/commands` and `GET /v2/hive/runs/{id}/events?after=<sequence>&limit=<count>`. Submission and control require operation keys; commands carry expected run version. Initial trusted local principal is `local`; binding beyond trusted local use requires HIVE-009 authentication/authorization. Inspecting by ID is not authentication.

RunView tasks must contain `deps`, parent ID, kind/profile, status, version and current assignment identity. Current worker ownership comes from task/attempt state, not the last claim event. Existing v1 endpoints retain their shapes/status vocabulary and lite engine; HIVE-005 repairs their known missing-dependency contract separately. CLI gains explicit `--engine modular-v1`; its default stays lite until reviewed promotion. Advanced console steering is deferred to HIVE-005; API/CLI provide complete controls first.

## Migration, rollout and recovery

Provision versioned Postgres schema for new runs, retain SQLite history in its legacy path and drain old live runs. Do not transfer active leases or treat legacy rows without manifests as new-engine resumable work. Historical import, if later required, must use a separate restartable provenance-checked migration.

Enable new engine for explicit local submissions, then fault tests, then small live canary. Rollback disables new admissions and drains/pauses new-engine work; retain new state/history and reconcile outstanding calls. Reverting code cannot discard accepted new facts or translate in-flight state into an incompatible older engine.

## Verification and observability

RUN-01–05/12: process-kill matrix around durable boundaries, actual Postgres transaction failures and deterministic provider receipts. RUN-06–08: multi-process competing claims, stale coordinator and graph-validation tests. RUN-09–11: actual API contract tests, cursor pagination and lite compatibility. Every requirement needs an independently named acceptance case in its implementation plan.

Load matrix uses 4/8/16/32 worker processes with fake variable-latency providers, multiple runs, 429s, DB outages and worker loss; higher levels are explicit test configurations, not production defaults. Record queue-age percentiles, recovery time, stale commits, duplicates, resource conservation, unfinished work and provider-call count. A live bounded canary follows synthetic load. No target throughput/SLO or live capacity is claimed.

Self-reviewed 2026-10-19. No runtime code, DB migration or new acceptance tests executed. Open before production promotion: workload/SLO and shared-deployment scope. Offline implementation can enforce all invariants with explicit configuration and trusted-local scope.
