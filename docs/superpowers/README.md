# Spec index

Read [the development workflow](../DEVELOPMENT.md) before advancing a spec. Entries below convert the architecture audit into scoped work; all technical choices remain proposals until reviewed.

## Modular hive program

Start with [HIVE-MOD: modular task-based hive](specs/2026-10-19-modular-hive-design.md). It defines the overall flow, delivery boundaries, acceptance gates and rollout sequence. The linked delivery specs below define independently reviewable changes. Read [the problems/fixes register](../reports/problems-and-fixes.md) for actual remediation status.

## Current work

| ID | Work | State | Dependencies | Design / next stage |
|---|---|---|---|---|
| HIVE-001 | Run-scoped evidence isolation | Draft | None | [Written spec](specs/2026-10-19-evidence-isolation-design.md) and [draft planning candidate](plans/2026-10-19-evidence-isolation.md); joint user review pending; native execution recommended |
| HIVE-002 | Attempt fencing, terminal progress, and lease supervision | Draft | None; coordinate store edits with HIVE-001 | [Written spec](specs/2026-10-19-execution-integrity-design.md); user spec review |
| HIVE-003 | Supported final findings and safe report construction | Backlog | HIVE-001 | Write spec against F3; cover headings and empty findings |
| HIVE-004 | Atomic resource reservations and bounded provider calls | Draft | HIVE-002 for integrated execution | [Written spec](specs/2026-10-19-resource-governance-design.md); user spec review |
| HIVE-005 | Live console/API contract | Backlog | None | Write bounded design or spec against F6 after tracing actual response/render path |
| HIVE-006 | Durable run lifecycle, manifests, resume, and Postgres execution | Draft | HIVE-001, HIVE-002, HIVE-004 | [Written spec](specs/2026-10-19-durable-runtime-design.md); user spec review |
| HIVE-007 | Jev decision interface, route qualification, and shadow rollout | Draft | HIVE-004/006 for integration; HIVE-003/010 for claim-acceptance promotion | [Written spec](specs/2026-10-19-jev-decisions-design.md); user spec review |
| HIVE-008 | Role registry and bounded branch hierarchy | Draft | HIVE-002/004/006 for runtime; HIVE-007 for Jev routes | [Written spec](specs/2026-10-19-role-hierarchy-design.md); user spec review |
| HIVE-009 | Caller isolation and request idempotency for shared deployment | Backlog | Before shared deployment; coordinate with HIVE-006 | Write spec against F13; decide actual deployment/caller scope |
| HIVE-010 | Typed model outputs and explicit assessment failure states | Backlog | None; coordinate evidence/API contracts | Write spec against F11; separate unsupported evidence from execution failure |
| HIVE-011 | Reproducible dependency/test environment | Backlog | Needed before full verification of affected paths | Inspect declared/installed versions and lock a supported environment; use dated audit only as starting evidence |
| HIVE-012 | Repo-local skill packages, registry and role binding | Draft | HIVE-008 seam; HIVE-004/006 for governed runtime; HIVE-007 optional selection | [Written spec](specs/2026-10-19-skill-registry-design.md); user spec review |
| HIVE-013 | External clients calling Hive through MCP | Draft; local implementation candidate | Existing lite HTTP API; separate SDK environment. Shared exposure remains gated by HIVE-009. | [Design](specs/2026-10-20-mcp-server-design.md), [implementation ledger](plans/2026-10-20-mcp-server.md), [setup](../../integrations/mcp/README.md). User selected server direction; document review pending. Local protocol verification recorded in plan; no personal host registration/live model call. |

Dependencies specify technical sequencing, not permission to implement. Store/schema work should proceed serially until independent edit surfaces are established. HIVE-005 and HIVE-011 can be scoped while architectural specs are under review.

The audit's capacity, telemetry, evidence invalidation, compatibility and fault-injection requirements travel with each owning spec. No entry claims a load target or quality threshold has already been agreed.

## Working with a spec

1. Find the relevant row and inspect the current implementation.
2. Start with a [design template](templates/spec-template.md); assign stable requirement IDs and measurable acceptance behavior.
3. Follow the review gates in `docs/DEVELOPMENT.md`. Once the spec is approved, create its plan at `docs/superpowers/plans/YYYY-MM-DD-<topic>.md` using the [plan template](templates/plan-template.md).
4. Link the plan in this index when it exists. Update delivery state only from actual review or execution evidence.

HIVE-001 now has a draft planning candidate prepared with fresh diagnosis so the storage/error/migration choices are concrete for review. It does not advance the spec to Approved, select execution, or authorize application changes. Remaining architectural work follows the normal spec-then-plan stages.

## Existing evidence

- [Architecture review](../reviews/hive-modularization-review.md): F1–F13, current/target flows, trade-offs and verification limitations.
- [Offline gap evidence](../reviews/hive-gap-evidence.json): observations from five probes.
- [Probe script](../reviews/reproduce_hive_gaps.py): records defects in the reviewed version; it is not a desired-behavior regression suite.
- [Reviewed source snapshot](../reviews/source-snapshot.sha256): historical source fingerprint, not an assertion that future files retain those hashes.
