# <Feature> Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Select the execution method during user plan review, subject to host permissions. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** <One sentence>
**Architecture:** <Selected approach and module responsibilities>
**Tech Stack:** <Actual project technologies>
**Spec:** <Relative link to approved design and its ID>
**Status:** Plan review
**Approval:** Pending user review
**Execution method:** Not selected

This is a template. Create a feature plan only after written-spec approval, and replace all placeholders before plan review.

## Global Constraints

<Copy exact project-wide constraints from the approved spec.>

## Review Focus

<Identify up to five high-risk input/failure classes that need explicit tests. Add each test to its owning task. State if fewer apply.>

## Requirement Coverage

| Spec requirement | Task | Acceptance test / oracle |
|---|---|---|
| <ID> | <Task number> | <Exact test and asserted outcome> |

## Task 1: <Independently verifiable deliverable>

**Files:** <Exact create/modify/test paths>
**Interfaces:** <Consumed and produced names, signatures, invariants>
**Requirements:** <IDs>

- [ ] Write the behavior test with the spec's exact assertions.
- [ ] Run `<focused command>` and confirm failure for the intended reason.
- [ ] Implement `<exact interface and chosen behavior>`.
- [ ] Run `<focused command>` and confirm acceptance assertions pass.
- [ ] Run `<required compatibility checks>`.
- [ ] Review the diff and commit scoped files in a valid project checkout when authorized.

Repeat tasks only for independently reviewable deliverables; do not create tasks for empty scaffolding.

## Verification Record

| Date / environment | Command | Observed result | Requirement IDs / limitations |
|---|---|---|---|
| <Actual execution only> | <Command> | <Actual output/status> | <Coverage and gaps> |

## Handoff

<Spec/plan review evidence, chosen execution method, remaining checks, rollout/recovery state. Do not mark Verified with unresolved required acceptance checks.>
