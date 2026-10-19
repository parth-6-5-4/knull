# <Feature> design

**Spec ID:** <stable ID>
**Status:** Draft
**Date:** <YYYY-MM-DD>
**Owner:** <responsible maintainer>
**Approval:** Pending user review
**Depends on:** <spec IDs, or None>
**Plan:** Not written; requires spec approval

This is a template. Replace all angle-bracket placeholders before submitting an actual spec for review.

## Intent

<Who needs this, what problem they encounter, and the user-visible outcome. Separate requested constraints from assumptions.>

## Current behavior and evidence

<Trace the current entrypoint and relevant state/tool boundaries. Link source paths and dated reproductions. State what has and has not been tested.>

## Scope and non-goals

<Define one independently deliverable change. Name adjacent work that belongs to another spec.>

## Approaches and chosen design

<Compare realistic options and explain the selected trade-off. State reversibility and migration cost.>

## Requirements and invariants

| ID | Required observable behavior | Acceptance oracle |
|---|---|---|
| <PREFIX>-01 | <Precise behavior including failure response> | <Given/when/then result> |

## Interfaces and data flow

<Callers, inputs, outputs, ownership, ordering, errors, dependencies and module seam. For persistence: identity, versioning, legal transitions and transaction scope. Use a small diagram when it clarifies the flow.>

## Failure and resource model

<Relevant retries, duplicate/concurrent/stale work, partial results, crash/restart, dependency outages, permission limits, timeouts and budgets. Mark risks outside scope explicitly.>

## Compatibility, rollout and recovery

<Existing callers/data affected, schema/API migration, initial enablement, observability, abort criteria, and rollback or roll-forward.>

## Verification strategy

<Map requirement IDs to the cheapest trustworthy test layer and required environment. Distinguish proposed checks from observed evidence.>

## Open decisions

<List decisions that genuinely block planning, or state None. Never invent a user decision or approval.>

## Review record

<Self-review date/findings; actual user approval and revision covered when received. A self-review cannot approve the spec.>
