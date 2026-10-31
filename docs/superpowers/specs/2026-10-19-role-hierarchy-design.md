# Task-based roles and bounded hierarchy design

**Spec ID:** HIVE-008
**Status:** Draft
**Date:** 2026-10-19
**Owner:** Project maintainer
**Approval:** Pending user review
**Depends on:** HIVE-002/004/006 for authoritative execution; HIVE-007 for Jev-based profile selection
**Plan:** Not written; requires spec approval

## Intent and current behavior

Spin specialist invocations from task demand, with optional branch coordination and explicit authority. Today the lite runner has explicit fixed research/verify/write handlers; HIVE-002 rejects unknown kinds. There is no role registry, parent link, branch aggregation or delegated allowance. [Audit F9/F11](../../reviews/hive-modularization-review.md).

“Spin an agent” means create a task-scoped invocation with a pinned role/context/tool manifest on an admitted worker. It does not mean launch an unbounded process, self-install a skill or give an LLM the root coordinator's entire authority. [Domain vocabulary](../../../CONTEXT.md).

## Scope and alternatives

Choose a code-owned registry and three logical levels maximum: Knull, optional lieutenant, specialist. Start with existing research capabilities plus branch coordination. Registry handlers can be ordinary deterministic functions, bounded generative invocations or decision-policy calls.

Keeping fixed dispatch is simpler but blocks extension. Arbitrary recursive agent factories increase authority/spend ambiguity. A class/plugin hierarchy for every agent is unnecessary; a small explicit registry interface hides role-specific behavior while keeping the scheduler generic.

## Role and invocation contract

`RoleProfile`: immutable ID/version, supported task kinds/capabilities, input/result schemas, entrypoint handler, tool allowlist, context builder/version, approved generator/decision policy references, input/output/time/retry limits and delegation permissions. Credentials are referenced through a scoped execution service; they are never copied into model prompts or child payloads.

Registry exposes `resolve(task_kind, capability, profile_version)` and produces an executable profile or a typed unknown/ineligible error. Executor consumes HIVE-006 Assignment and returns CandidateResult. Task input/results/evidence schemas must validate before publication. Adding a profile does not require editing scheduler kind branches; unknown kinds never fall through to writer.

[HIVE-012](2026-10-19-skill-registry-design.md) separately defines user-authored instruction packages and skill bindings. A RoleProfile may bind approved skill snapshots; skill prose does not register an executable handler or enlarge the profile's tool/delegation grants. The role registry and skill registry retain separate identities and interfaces.

Initial roles: root planner, academic researcher, claim verifier, report writer, branch coordinator. Preserve independent verifier context: claim + authorized evidence + policy only, without researcher conversation/rationale. Writer receives only eligible supported findings. Profiles implement typed output limits instead of relying only on prompt promises. Assessment outages remain unresolved execution outcomes under HIVE-010.

## Hierarchy and delegation

Root planner proposes independently assessable branches or a flat DAG. A lieutenant owns one bounded branch and proposes children using inherited capabilities, completion criteria and allocation. The scheduler validates the entire child proposal and commits it atomically. Waiting for children releases the coordinator's worker lease; a version-checked aggregate reschedules the next bounded coordinator attempt.

Parent links express accountability; dependency edges express readiness. A task has at most one parent, but can depend on authorized tasks from multiple branches in the same run. Branch outcome includes required criteria satisfied, unresolved criteria, accepted evidence/result references and consumed resources. A child saying “done” cannot complete a branch without aggregation policy.

Initial policy proposal: root depth 0, optional lieutenant depth 1, specialists at depth 1 for flat work or depth 2 for delegated work; maximum four children per coordination task and 64 total tasks per run, counting coordinators/verifiers/writers/retries as follows: retries reuse task ID and do not increase task count, but consume attempt/call limits. A branch coordinator cannot create another branch coordinator. Roles may lower limits; children may not raise them. These are testable starting ceilings for review, not evidence of optimal topology.

Follow-up work requires one explicit unmet criterion, fresh input evidence reference, a new stable operation key, remaining task/attempt/time/allocation and allowed depth. Repeating unchanged proposals or unsupported criteria defers/blocks; it cannot silently enlarge the run.

## Requirements

| ID | Required behavior | Acceptance oracle |
|---|---|---|
| ROLE-01 | Registry owns task-kind dispatch and explicit eligibility. | Existing specialists plus a newly registered typed fixture run without scheduler edits; unknown/ineligible kind rejects before tools. |
| ROLE-02 | Invocations get minimal role-scoped context and tools. | Verifier excludes researcher history; child role cannot call an unlisted tool or see unrelated branch material. |
| ROLE-03 | Parent/dependency validation enforces run identity and acyclic work. | Cross-run parent/edge, duplicate conflicting task key, cycle or nonexistent node rejects complete proposal. |
| ROLE-04 | Depth, fan-out, total tasks and delegation capability are code-enforced. | Fifth child, task 65, depth 3 or nested lieutenant is denied under initial policy before any new provider call. |
| ROLE-05 | Children inherit bounded authority and resources. | Requested tools, deadline, profiles or allocation outside parent grant reject; cancellation closes descendant admission. |
| ROLE-06 | Waiting coordinators consume no specialist slot or active lease. | Multiple branches wait for children while remaining worker capacity executes ready specialists; no capacity deadlock. |
| ROLE-07 | Branch completion aggregates required results and unresolved criteria. | One failed required child blocks branch; optional failure produces partial only when explicitly allowed; empty findings cannot imply success. |
| ROLE-08 | Delegation and follow-up proposals are idempotent/versioned. | Coordinator retry creates no duplicate children; stale aggregate or changed criterion version cannot commit. |
| ROLE-09 | Jev selects only eligible profiles; deterministic fallback remains. | Singleton candidate skips model call; uncertainty/unavailable decision defers or uses qualified profile; no arbitrary profile generated. |
| ROLE-10 | Capacity comes from bounded resource admission, not number of logical agents. | Many ready tasks never exceed global/run/provider active limits; slow branch cannot monopolize all admitted work. |
| ROLE-11 | Role manifests and result schemas remain reproducible. | Restart invokes pinned profile/context/schema version; incompatible result fails without facts/task completion. |
| ROLE-12 | Hierarchy is observable through authoritative state. | API/CLI show parent/deps, current role/attempt, delegation limit, branch outcome and causal failure; last-claim events are insufficient. |

## Failure model, rollout and recovery

Treat all task/source text as untrusted data. A task payload cannot add tools, mutate registry definitions, raise budgets or claim a different principal. Deny by profile/capability checks before execution. Tool-provider outages and invalid outputs follow HIVE-002/004 retry/deadline policy; a lieutenant cannot reset attempts by renaming the same task.

Enable registry dispatch for flat research first, preserving existing successful role behavior. Branch execution is initially disabled. After runtime/resource/decision fixtures pass, enable optional branches for explicit runs, then compare completion, accepted-fact coverage, deferrals, latency and spend against flat execution. Do not assume more branches improve quality.

Rollback disables new branch proposals and routes new runs to flat registered execution. Drain or pause existing branch runs under their pinned manifest; keep child outcomes and resource accounting. A changed role manifest creates a new version rather than mutating a running task's meaning.

## Verification and review

ROLE-01/02/09/11: registry/executor/decision contract tests with explicit denied-tool and independent-context assertions. ROLE-03/04/05/08: generated graph/delegation fixtures and atomic proposal tests. ROLE-06/07/10/12: real-runtime branch aggregation, cancellation, queue saturation, restart and API projection tests. A whole-flow comparison objective must work both flat and branched under fixed mocked evidence; live quality/cost comparison follows separately.

No acceptance tests or hierarchy implementation executed. Self-reviewed 2026-10-19. Open before promotion: reviewed hierarchy/resource ceilings and task-family expansion beyond research. Existing allowed research scope is sufficient to implement the proposed contracts after spec/plan review.
