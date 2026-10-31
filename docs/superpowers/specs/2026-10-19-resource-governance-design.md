# Resource admission and inherited budgets design

**Spec ID:** HIVE-004
**Status:** Draft
**Date:** 2026-10-19
**Owner:** Project maintainer
**Approval:** Pending user review
**Depends on:** HIVE-002 for integrated lease-aware execution
**Plan:** Not written; requires spec approval

## Intent and current evidence

Task spinning must not multiply concurrent calls or spend beyond admitted allowances. Current `Caller` checks past usage then dispatches, recording successful usage afterward; concurrent calls can overshoot and failed/ambiguous calls may go unrecorded. API starts a new worker pool for every request. [Audit F4/F10](../../reviews/hive-modularization-review.md).

## Scope and choice

Introduce one resource module for allocations, call reservations and global/provider/run admission. Use transactional reservations, not a process-local semaphore alone: a semaphore bounds one process but cannot conserve resources across worker hosts. Keep control arithmetic deterministic. Exact billing reconciliation is limited by provider receipts; the system must expose that uncertainty.

## Requirements

| ID | Required behavior | Acceptance oracle |
|---|---|---|
| RES-01 | Reserve a conservative input/output upper bound before any generative or decision call. | Simultaneous callers cannot admit reservations exceeding run allowance, including planner/Jev/verifier/writer. |
| RES-02 | Resource allocation is inherited and conserved. | A branch cannot allocate more than available parent allowance or count the same grant twice; outstanding child reservations remain charged upstream. |
| RES-03 | Every dispatch attempt has a durable unique call identity and state. | Crash before dispatch, after dispatch and before receipt leaves a distinguishable reservation; duplicate settlement is harmless. |
| RES-04 | Unknown usage retains conservative allowance until resolved. | Timeout/crash never resets spend headroom; unresolved calls appear in inspection and can block further admission. |
| RES-05 | One policy owns all retries. | SDK retries are disabled or fully accounted; 429/5xx/timeout retry chain obeys one shared attempt/deadline limit and jittered backoff. |
| RES-06 | Bound concurrency across processes, providers, runs and branches. | Multiple runs/hosts cannot exceed shared permit counts; stale ownership cannot release/reuse an active external call's permit prematurely. |
| RES-07 | Requests are fairly admitted and queue growth is bounded. | A flooding run cannot starve another admitted run; excess admission returns an explicit queue-full/retryable response. |
| RES-08 | Token and monetary policies are distinct. | Exact decimal/integer cost accounting uses versioned price/usage category; missing pricing or trustworthy token bound prevents a claimed hard-money/hard-token route. |
| RES-09 | Deadline, context, output and task-count limits are validated before work. | Oversized context, expired deadline or exhausted allocation denies before provider dispatch; models cannot raise limits. |
| RES-10 | Cancelling/reclaiming a task does not erase possible external spend. | Late receipt settles original call; new attempt cannot inherit uncertain reservation as free allowance. |

## Interface and accounting

Resource policy exposes `allocate(parent, request)`, `reserve(call_spec, allocation)`, and `settle(call_id, receipt_or_unknown)` as logical operations. These are one module interface with explicit accepted/denied/unknown results; persistence and permit renewal are internal. HIVE-006 owns durable transaction infrastructure and assignment identity.

Call states are reserved → dispatched → settled, with released-before-dispatch and unknown-after-dispatch branches. Reserved means no network dispatch has occurred. Release is legal only with proof of no dispatch. Settled outcomes retain actual usage, requested/resolved model, input/price version, retry identity, latency and receipt provenance. Provider/billing reconciliation can increase known cost beyond estimates; expose overrun and stop new admissions rather than rewriting history.

Allocation accounting avoids double counting: parent grants partition spend authority; reserving a child call consumes that grant, not another independent full parent budget. Sum of unused grants, pending reservations and settled usage must reconcile to the original authority after returning genuinely unused grants.

An SDK without a trustworthy upper bound cannot satisfy hard-token admission; either disable the route in hard mode or label policy as soft and require explicit selection. Do not turn an estimate into a guarantee. In-flight permit expiry requires provider cancellation/terminal receipt or a conservative quarantine interval defined by that provider's maximum call duration; a new task lease alone is insufficient evidence that the old request stopped.

## Initial configuration proposal

For trusted local research: per-run token allowance 200,000; global active specialist invocations 8; per-run 3; per-provider in-flight requests 2; accepted queued runs 20; run wall-clock deadline 1,800 seconds; task deadline 600 seconds; one provider call deadline 120 seconds; at most three transport attempts including initial call. These are safe starting proposals for review, not measured capacity or price promises. Effective per-run concurrency cannot exceed global/provider ceilings. Runtime manifests pin values; increasing them is an explicit configuration change.

Context/output bounds are role-specific and recorded in role profiles. Unsupported provider retry/duration semantics fail closed in hard mode. A signed-in account or human provisioning of a new provider is outside this spec.

## Rollout, recovery and verification

Introduce admission around existing provider seams, first with deterministic fake providers and file-backed state. Multi-process guarantees require real Postgres integration before enabling distributed execution. Preserve historical usage as measured usage; do not manufacture reservations retroactively. Rollback stops new admission and drains/reconciles outstanding reservations; deletion is not a recovery mechanism.

| Requirements | Required checks |
|---|---|
| RES-01/02/08/09 | Concurrent allocation/reservation and monetary precision/property checks; missing bound/pricing denied; parent conservation |
| RES-03/04/05/10 | Crash/timeout/late receipt, duplicate settlement, SDK retry accounting and cancellation tests |
| RES-06/07 | Multi-process permits, provider outage, queue overload and starvation/fairness tests with real database |

Observe reservation debt, settlement lag, unknown calls, denied work, provider saturation, queue age and admitted versus actual spend. None of these checks have been executed. Self-reviewed 2026-10-19; proposed configuration awaits review; live capacity remains unmeasured.

## First integrated delivery — 2026-10-21

[HIVE-004-A revision 2](2026-10-21-resource-ledger-design.md) now includes the token ledger, current Caller/provider integration, shared active-run/global/run/provider limits, bounded fair run/call queues, required lifecycle contention repair and explicit SQLite v2 migration. This replaces revision 1's standalone-library proposal after the user requested both shared queues and immediate integration. [Scoping/problem report](../../reports/hive-004/scoping.md) records the current flow and outstanding fixes.

Shared means all governed Hive API/CLI/direct processes on one trusted host using one canonical Hive database and persisted policy. One transaction authority covers admission, reservations and usage; no cross-file dual-write accounting. Postgres/multi-host execution and monetary policy remain outside this local delivery. They remain parent RES obligations, not silently satisfied by HIVE-004-A.

HIVE-004-A revision 2 approved 2026-10-21; its [integrated plan](../plans/2026-10-21-resource-admission.md) approved 2026-10-22. Tasks1–2 schema/transaction and accounting foundations are implemented and independently task-reviewed; shared queues/provider/Caller integration remain unfinished. Parent monetary/cross-host scope remains Draft; local slice approval does not approve those deferred contracts. Integrated runtime overshoot, provider controls and capacity remain unverified.
