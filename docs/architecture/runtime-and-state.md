# Runtime and durable state

[Main guide](../../ARCHITECTURE.md) · [Visual atlas](index.html)

**Mixed delivery:** HIVE-002 lite SQLite ownership/supervision is verified; the PostgreSQL durable runtime and resource ledger remain proposed. See [delivered foundation](implemented-foundation.md). Governing specs: [execution integrity](../superpowers/specs/2026-10-19-execution-integrity-design.md), [resource governance](../superpowers/specs/2026-10-19-resource-governance-design.md), [durable runtime](../superpowers/specs/2026-10-19-durable-runtime-design.md).

Think of the runtime as a dispatcher, a ledger and a recovery supervisor. The dispatcher chooses eligible work. The ledger remembers authoritative state. The supervisor deals with workers that disappear.

| Part | Input → output | Responsibility |
|---|---|---|
| Contracts | Validated request → RunSpec / TaskSpec | Stable IDs, versions, dependencies, criteria and limits |
| Scheduler | Ready tasks + available capacity → assignment request | Eligibility and fairness; no model calls under database locks |
| Resource ledger | Requested call + allocation → reservation / denial | Concurrency, token allowance, deadlines and retry limits |
| Store | Guarded mutation → state + event | Atomic transitions, leases, fences and result publication |
| Executor | Assignment + context → CandidateResult | Run a pinned handler using allowed tools |
| Recovery | Expired lease → retry or terminal cause | Reclaim orphaned attempts and reject stale writes |
| RunView | Committed state → consistent read model | Parent links, dependencies, attempts, findings and resource use |

The suggested code seams are `app/orchestration/contracts.py`, `runtime.py`, `scheduler.py` and `execution.py`. The store owns state changes; callers do not update task rows opportunistically. PostgreSQL uses database time and short locking transactions. Network calls happen after those transactions end.

The core task path is `pending → ready → leased → succeeded`. A coordinator may move to `waiting_children` and release its lease. Retry returns a task to ready only within its remaining policy and deadline. Failed, blocked and cancelled dependencies must lead to an explicit downstream outcome rather than an endless wait. [Task lifecycle diagram](diagrams/07-task-lifecycle.html) shows these relationships.

A lease alone is insufficient. Suppose worker A stalls, its lease expires, and worker B receives the task. A later response from A must fail the attempt/fence check even if its content looks correct. Every authoritative mutation needs the guard, including failure, heartbeat and final publication.

Resource accounting belongs before execution. Reserve under the parent's allocation; settle a known receipt; retain a conservative charge when the provider outcome is unknown. A retry must not receive unlimited fresh budget. Proposed concurrency defaults are design values, not measured capacity. Four workers passing a test does not qualify thirty-two workers.

Persist authoritative state and transactional events together. Recovery rebuilds scheduling decisions from that state and uses events for explanation and reconciliation. This is not a requirement to reconstruct the whole database from an event stream or repeat paid calls.

Acceptance evidence must include real PostgreSQL competition, stale attempts, cancellation during execution, process loss, unknown provider usage and dependency failure propagation. Unit tests cannot establish database lock behavior. Start after the preceding evidence/integrity specifications and plans have reached their required approval stages.
