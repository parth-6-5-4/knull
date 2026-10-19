# Jev decision policy and routing design

**Spec ID:** HIVE-007
**Status:** Draft
**Date:** 2026-10-19
**Owner:** Project maintainer
**Approval:** Pending user review
**Depends on:** HIVE-004/006 for authoritative integration; HIVE-003/010 before model-assisted claim acceptance promotion
**Plan:** Not written; requires spec approval

## Intent and evidence

Use TypeSafe AI's Jev for narrow semantic decisions inside code-controlled orchestration. Current provider router only maps agent/layer/default to a generative model. It has no candidate eligibility, uncertainty policy, Jev adapter or held-out decision evaluation. [Audit F12](../../reviews/hive-modularization-review.md).

Official contract checked 2026-10-19: state plus named typed questions; Choice selects a supplied option; Score rates a rubric; Noul returns yes probability. Generation remains a separate interface. [Introduction](https://docs.typesafe.ai/introduction), [API schema](https://api.typesafe.ai/openapi.json).

## Scope and alternatives

Create a distinct decision-policy module with a real TypeSafe adapter and recorded/fake adapter. Preserve `app/llm` for generative calls. Initial Jev uses: select among eligible research role profiles; score retrieved evidence relevance; assess one explicit completion criterion. Claim support assessment can run in shadow but cannot independently mark facts verified until report/assessment gates qualify it.

Static routing remains an evaluated baseline and outage fallback. An arbitrary JSON chat-judge implementation under the same Jev confidence thresholds is rejected: different semantics and calibration require separate qualification. Fully autonomous planner/routing/commit via Jev is rejected because it changes authority and asks open-ended generation from a bounded decision model.

## Contracts and flow

`DecisionRequest`: decision/task/run identity and version, purpose, minimal immutable state references/hash, eligible candidate IDs/descriptions, question schema/version, model version, policy version, allocation and deadline. `DecisionOutcome`: selected action or defer, probabilities, question-specific confidence when provided, resolved model, usage/call ID, reason code and input/version identity.

Flow: deterministic candidate eligibility → singleton bypass or typed decision call → validate response → apply question-specific gate → persist decision → revalidate current task/plan/candidate/resource versions → commit permitted action. No candidate means defer; one candidate means deterministic route. Jev cannot invent a role, tool, task kind, resource grant or permission.

Proposed modules: `app/decisions/policy.py` owns eligibility/gates/fallback; `app/decisions/typesafe.py` owns authenticated HTTP/SDK contract; `app/decisions/contracts.py` owns typed request/outcome. Keep model transport errors separate from semantic insufficient-evidence outcomes. One shared retry/resource policy comes from HIVE-004.

## Requirements

| ID | Required behavior | Acceptance oracle |
|---|---|---|
| JEV-01 | Semantic questions are atomic and their answer space is code-defined. | Registered question fixtures have explicit criteria; compound permissions/budget questions never dispatch. |
| JEV-02 | Eligibility and committed action stay within deterministic authority. | Disallowed/removed role, unknown result key or stale candidate set yields defer/reject, not execution. |
| JEV-03 | Typed answers retain probabilities and correct uncertainty meaning. | Choice/Score use their confidence/distribution; Noul near 0.5 defers; no assumed `confidence` property on Noul. |
| JEV-04 | Version every question, policy, input and resolved model. | Replay identifies exact candidate ordering/descriptions and evidence snapshot; moving aliases cannot silently change active policy. |
| JEV-05 | Stale decisions have no effect. | Cancelled task, changed plan/evidence/policy or expired resource authority rejects before action commit. |
| JEV-06 | Timeout/rate-limit/unavailable/malformed response has bounded fallback. | Deadline and retry cap produce explicit evaluated fallback or defer; unknown usage remains reserved. |
| JEV-07 | Shadow mode cannot create authoritative side effects. | Shadow outcomes cannot spawn tasks, verify facts, consume production allocations or cause duplicated work; separate shadow allowance accounts for its paid calls. |
| JEV-08 | Automatic action requires a qualified policy manifest. | Missing evaluation/promotional thresholds, unsupported model version or unqualified fallback leaves action disabled. |
| JEV-09 | Context is minimal, scoped and untrusted. | Source instructions cannot grant tools; oversized/missing evidence defers; unrelated branch history is excluded. |
| JEV-10 | Outcome quality is measured per purpose/model/profile, including deferrals. | Held-out comparison reports incorrect actions, coverage, calibration, latency, spend and fallback behavior separately. |
| JEV-11 | Semantic routing and generative provider selection compose explicitly. | Jev chooses eligible profile; profile maps to pinned approved generator/tool manifest; it cannot choose an arbitrary model/account. |
| JEV-12 | Decision inspection is actionable without invented explanations. | View contains reason code, selected candidate, distribution and evidence/input references; no fabricated free-text rationale attributed to Jev. |

## Questions and control ownership

| Purpose | Question form | Code response |
|---|---|---|
| Role profile | Choice over currently eligible profiles plus `defer` | Gate then bind registered profile; tools remain manifest-scoped |
| Evidence relevance | Score against ordered explicit semantic relevance levels | Sort/filter by approved threshold within context limits; preserve rejected candidate provenance |
| Completion gap | Noul about one named criterion and supplied branch results | If unmet/uncertain, allow a bounded follow-up proposal or defer; depth/task/spend checks still apply |
| Citation support, shadow initially | Choice supported/contradicted/insufficient with local passage context | Mechanical quote/span validation first; no auto-verification until separately qualified |

Do not ask Jev to count tasks, compare dates, allocate numeric budgets or decide permissions. TypeSafe documents numeric, indirection, adversarial-state and option-order weaknesses for 1.13; include these as version-specific regression hypotheses rather than assuming a newer version fixed them. [Known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13).

Choice/Score confidence derives from the returned distribution; it is not independent observed accuracy. Noul exposes a probability instead of a separate confidence field. Thresholds must be purpose/risk-specific. [Confidence documentation](https://docs.typesafe.ai/confidence).

## Model versions and qualification

Official docs currently list 1.13.0 and 1.14.0 and moving aliases. Start qualification with explicit `jev-1.13.0` and `jev-1.14.0`; production selects the version that meets project criteria. Log resolved version and reject unexpected alias resolution for an active policy. Do not enable experimental image/long-context features for this text-only release. [Models](https://docs.typesafe.ai/models).

Promotion manifest must supply purpose, eligible profile versions, model/question/policy versions, human-adjudicated fixture version, minimum labeled sample count, maximum incorrect-action rate, minimum automatic coverage, p95 latency ceiling, mean decision-cost ceiling, uncertainty gate and separately qualified fallback. These are required typed values; owner-selected operational values are not supplied by this spec. Therefore live auto-routing remains off until review supplies them. Offline contract implementation and shadow evaluation may proceed under explicit finite fixture/budget limits.

Fixtures cover ambiguity/defer, negation, same entities/different numbers, incomplete evidence, option permutation, distractor context, injected instructions, unfamiliar task type, changing candidate eligibility, transport errors and stale results. Keep held-out data separate from threshold tuning. Multiple questions in one request do not provide verifier independence; high-impact agreement policy must measure correlated failures.

## Rollout, rollback and verification

Use fake/recorded contract tests first; require actual TypeSafe transport qualification before shadow live calls. Shadow logs compare outcomes with deterministic baseline and reviewed labels. Authoritative rollout starts with reversible research profile routing; a kill switch routes new decisions to evaluated baseline or defer. Existing committed decisions keep their provenance; rollback does not erase history or reinterpret old thresholds.

JEV-01/02/03/05/09/11: policy-interface fixtures. JEV-04/06/07/12: transport, durable record, stale-version and resource tests. JEV-08/10: held-out evaluation and promotion-manifest rejection tests. Live latency/cost/quality are unmeasured. Self-reviewed 2026-10-19; no acceptance tests or live Jev calls executed; approval pending.
