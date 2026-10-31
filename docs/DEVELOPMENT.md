# Spec-driven development

Hive Lite uses Superpowers to move changes from intent through reviewed specifications, implementation plans, behavior tests, and verified results. This workflow is adopted by the maintainer's request on 2026-10-19. Adoption does not approve the technical proposals in the existing architecture review or draft feature specs.

## Authoritative documents

| Document                                                    | Responsibility                                                                            |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| [AGENTS.md](../AGENTS.md)                                    | Agent entry point, conditional context pointers, project constraints                      |
| [CONTEXT.md](../CONTEXT.md)                                  | Domain vocabulary                                                                         |
| This file                                                   | Development stages, review gates, and completion criteria                                 |
| [Spec index](superpowers/README.md)                         | Current work, status, dependencies, and next stage                                        |
| `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`     | Intended behavior, scope, invariants, interfaces, acceptance criteria, and trade-offs     |
| ` docs/superpowers/plans/YYYY-MM-DD-<topic>.md`           | Implementation steps, requirement coverage, execution progress, and verification evidence |
| [Architecture review](reviews/hive-modularization-review.md) | Dated observations, reproduced defects,   3e  proposed fixes, and migration context    |

Specs define what must hold. Plans define how a specific change will establish it. Tests supply executable evidence. Current source establishes what exists today; an unimplemented spec must not be described as current behavior.

## Scope the work

Use Superpowers `brainstorming` to classify each request.

| Class                                | Required artifact                                                                              | Before implementation                                                             |
| ------------------------------------ | ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Read-only investigation              | Findings with source evidence                                                                  | No product implementation                                                         |
| Spike                                | One question and a bounded probe, recorded in discussion                                       | User approves probe; output stays throwaway                                       |
| Bounded behavior change              | Short design with explicit expected behavior and acceptance checks in discussion, issue, or PR | User approves that design; no separate implementation-plan file required          |
| Architectural or multi-module change | Written design spec, then a linked implementation plan                                         | User reviews spec; then reviews plan and selects execution method                 |
| Documentation/formatting only        | Describe intent and verify links/content or formatting                                         | Existing task authorization suffices; no product tests or feature spec for a typo |

The bounded design is the specification for a small change. Promote to a full file if interfaces, persistence, concurrency, permissions, spend, or scope introduce architectural uncertainty. Split large programs into independently reviewable specs; do not write one implementation plan for the entire modular hive.

## Workflow

1. **Understand.** Read current entrypoints, relevant tests, the governing spec, and domain vocabulary. Reproduce defects before proposing fixes. Distinguish observed behavior from assumptions and desired behavior.
2. **Specify.** Use `brainstorming`. Compare viable approaches, choose a small scope, and write requirements with stable IDs, failure behavior, and falsifiable acceptance criteria. Use the [design template](superpowers/templates/spec-template.md). Every persistent-state change must cover compatibility, recovery, migration, and rollback.
3. **Review spec.** Self-review for ambiguity, contradictory requirements, placeholders, and scope. Present the written spec for user review. Record actual approval evidence; a draft or the agent's self-review is not user approval. Spec approval permits planning, not implementation.
4. **Plan.** After spec approval, use `writing-plans` and the [plan template](superpowers/templates/plan-template.md). Map every requirement to tasks and acceptance tests. Name actual files, interfaces, commands, and expected results. Include uncovered failure classes in review focus. Self-review before presenting the plan.
5. **Choose execution.** User reviews the plan and selects native execution or subagent-driven execution. Honor a method already supplied. Use `executing-plans` or `subagent-driven-development` accordingly; load `using-git-worktrees` when isolation is needed. Delegation follows the active host's permissions and available capabilities.
6. **Implement.** Follow the approved plan in small independently verifiable changes. For behavior changes, demonstrate a meaningful failing test, make the smallest implementation, then verify. Test externally observable invariants rather than prompt wording or implementation structure.
7. **Review and verify.** Use `requesting-code-review` as applicable and `verification-before-completion`. Run focused acceptance checks and required compatibility checks. Record exact commands, results, and environment limitations in the plan. Planned tests, mocked transports, live provider calls, browser tests, and distributed load tests are different evidence classes.
8. **Close.** Complete requirement traceability, update spec/index status, and summarize delivered behavior and residual risk. Commit only in a valid project checkout; deployment/merge follow the user's authorized scope.

For a bounded change, use understand → short design/approval → implement → review/verify → close. Do not invent a formal plan just to fill the directory.

When scope changes, update the spec before continuing dependent work. A change within already approved scope does not need repeated approval. Material changes to contracts, authority, cost, or acceptance behavior return to review. Keep the approval history attached to the version it actually covers.

## Spec state

Use these index states consistently:

| State         | Meaning / required evidence                                                   |
| ------------- | ----------------------------------------------------------------------------- |
| Backlog       | Work identified; no written spec yet                                          |
| Draft         | Written design exists; user approval pending                                  |
| Spec approved | User approved a particular design revision; planning may begin                |
| Plan review   | Plan exists and self-review is complete; user review/execution choice pending |
| Ready         | Plan approved and execution method recorded                                   |
| In progress   | Approved implementation underway                                              |
| Verified      | Acceptance criteria and required checks completed with recorded evidence      |
| Superseded    | Another spec replaces this one; link replacement and explain compatibility    |

Spec header records spec status/approval. Index records overall delivery state. Plan header records plan review/execution method; plan checklist records actual task progress. Never advance a state from elapsed time, silence, a tool's success message, or an assumption of approval.

## Verification and completion

Use the cheapest trustworthy test for each risk: pure validation tests for rules; API/module contracts for interfaces; actual database integration for locking/restart; browser checks for console behavior; held-out evaluation for model decisions; load/fault testing for capacity. A passing mock test does not establish semantic model accuracy or production readiness.

Typical current commands, from the repository root:

```bash
# Hive behavior tests; explicit boolean avoids an inherited DEBUG=release value.
DEBUG=false python -m pytest tests/test_hive.py -q

# API contracts and provider transport fixtures.
DEBUG=false python -m pytest tests/test_api_research.py tests/test_llm_sdk_wiring.py -q

# Full suite when the change needs broad compatibility checks.
DEBUG=false python -m pytest -q

# Frontend checks, after installing the project's declared frontend dependencies.
npm --prefix web run lint
npm --prefix web run build
```

Choose commands for the actual change; do not run paid evaluations or install broad dependencies as a hidden side effect of a documentation edit. Existing `eval/run_eval.py` exercises the legacy research graph; it is not a hive/Jev qualification suite. The [dated audit](reviews/hive-modularization-review.md) describes the environment limitations observed during review; recheck them before relying on its test results.

Before declaring a feature verified:

- Each requirement ID maps to an implemented task and observed acceptance result.
- Failure, retry, stale-state, and compatibility behavior relevant to the change are covered.
- Spec, plan, domain terms, API/client contract, and resulting behavior agree.
- Commands/results are recorded; unresolved required checks keep status below Verified.
- New operational controls have observable failure states and a recovery path.

## Superpowers availability

Superpowers is already available in the current agent environment; its skills were read when adopting this workflow. Skills remain installed in the host environment rather than copied into this repository. Other contributors must verify skill discovery in their own host.

Use the host's skill catalog first. If a required skill is missing, inspect the configured Claude/agent skill locations, then use a trusted upstream installation through the host's skill installer. The upstream project is [obra/superpowers](https://github.com/obra/superpowers). Read the installed skill instructions before invocation. Do not claim an uninstalled workflow is active, auto-install at application startup, or execute downloaded shell scripts without inspection. This workflow documentation remains usable by human contributors without agent skills.

## Pull requests

Use the [PR template](../.github/pull_request_template.md). Link the governing spec or bounded design, plan when required, requirement coverage, observed verification, and migration/rollback notes. Keep code claims and evidence specific. Documentation-only changes may state that product tests are not applicable and identify the content/link checks performed.

## Problem and fix tracking

Maintain [the problems/fixes register](reports/problems-and-fixes.md) while discovering issues, scoping remedies and implementing changes. Each entry needs stable issue ID, observed problem and evidence, owning spec/requirement, planned remedy, actual changes, executed verification and current status. Add new issues when discovered; update the same entry when the remedy changes.

Use Open, Scoped, In progress, Implemented/unverified, Verified, or Deferred with an explicit reason. Writing a spec changes an issue to Scoped; it does not fix the application. Implemented/unverified means a change exists but required behavioral evidence is incomplete. Only observed acceptance results permit Verified. Retain historical reproduction evidence and record the check/environment/date that established the new behavior; do not silently rewrite old results into current passes.
