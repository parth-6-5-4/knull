# Delivery phases and agent handoff

[Main guide](../../ARCHITECTURE.md) · [Visual atlas](index.html)

**Delivery update:** phases 0/1 are verified for the lite SQLite engine under HIVE-001/002. See [the delivered foundation](implemented-foundation.md). Remaining phases are proposed. This is a dependency guide, not approval of every phase. Follow [the development workflow](../DEVELOPMENT.md), the [spec index](../superpowers/README.md), and each version's actual approval/plan status.

| Phase | Buildable slice | Gate before advancing |
|---|---|---|
| 0. Establish contracts | Reproduce affected defects; review HIVE-001/002 and the first bounded plan | Agreed invariant, regression case, review evidence |
| 1. Integrity foundation | Run-owned evidence; guarded transitions; terminal dependency propagation | Concurrent/repeated-run and stale-attempt evidence |
| 2. Durable governed runtime | HIVE-004/006 reservations, PostgreSQL leases, restart and reconciliation | Real database/process-loss checks; no duplicate accepted results or free unknown spend |
| 3. Role and skill seams | HIVE-008/012 typed dispatch, pinned contexts and bounded bundles | Registry failures, permission intersections and context isolation |
| 4. Qualified decisions | HIVE-007 adapter, fixtures, real transport and shadow evaluation | Explicit held-out thresholds and promotion decision; otherwise stay shadow |
| 5. Bounded hierarchy | Enable branch coordination on the durable role/runtime contracts | Wait/join, child ceilings, cancellation, retry and branch-criteria tests |
| 6. Product and scale qualification | HIVE-003/005/009/010/011 contracts and implementation; fault/load and provider evaluation | Supported reports, truthful clients, authorization, reproducibility and measured capacity |

Hierarchy contracts can be designed with phase 3; enabling delegated execution waits for the integrity and resource gates. Load runs at 4/8/16/32 workers are test configurations, not announced capacity. The local MCP adapter already exists; its presence does not advance the modular engine's state.

## Handoff for the next human or coding agent

1. Read `ARCHITECTURE.md`, `CONTEXT.md`, `AGENTS.md`, the governing spec and its linked plan.
2. Check repository root, current source and worktree changes. Do not replace another task's edits.
3. Identify one slice and its stable requirement IDs. Verify spec/plan approval and selected execution method before runtime implementation.
4. Reproduce the relevant issue from the problem register. Add evidence if the current behavior differs.
5. Write or update the implementation plan with exact files, migration/rollback, failure states and observed acceptance commands.
6. Implement and verify the slice under the agreed workflow. Use real database/browser/provider/load checks when the invariant requires them; distinguish fixtures from those checks.
7. Update requirement traceability, spec/index state, problem/fix entry and this architecture explanation when the resulting behavior changes.

The [evidence-isolation plan](../superpowers/plans/2026-10-19-evidence-isolation.md) and execution-integrity plan are complete. Next runtime work belongs to HIVE-004/006 after their own review and planning; do not begin by implementing the whole proposed swarm.

## What this documentation task resolves

The project had distributed design documents without a beginner reading path or a single explanation of model versus platform authority. This guide adds that path, module handoffs, a phased dependency map and source-linked diagrams. Runtime defects remain open/scoped until their behavioral fixes and acceptance evidence exist.
