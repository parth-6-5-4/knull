# GPT-6.1 Sol: custom-skill instruction cleanup

Research and local review date: 2026-10-19. Target remains GPT-6.1 Sol. The user authorized editing only 14 `stripe-*` skills and three writing skills, and explicitly excluded third-party installations. This changes local instruction files, not model capabilities, API defaults or reasoning settings.

## Research findings

Official documentation positions GPT-6.1 Sol for complex coding, computer use and professional work. The family prompting section explicitly says its observations are primarily about Astra and must be evaluated with the selected model/workload. That supports auditing Sol prompts, not asserting that every Astra behavior is inherent or identical in Sol. [Exact model/family guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6.1-sol).

OpenAI's skill cleanup article recommends precise short descriptions, relevant reference loading and less rigid procedural coaching. Broad triggers can load unrelated skills, while long descriptions consume discovery context. Its examples of native testing thoroughness concern Astra; they do not justify deleting Sol's domain-specific integrity tests. [Skill and prompt guidance](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra).

Official skill-authoring guidance keeps workflow/tool conventions, policies and useful resources in skills, with larger detail in references. Names/descriptions are discovery metadata; supporting files are loaded when relevant. Local `skill-creator` likewise recommends retaining only guidance that changes decisions, while preserving user intent, risk controls and non-obvious operational invariants. [Build skills](https://developers.openai.com/plugins/build/skills).

## What qualifies for removal

| Category | Decision | Reason |
|---|---|---|
| Generic competence coaching | Shorten/remove repeated “inspect, reason, write clearly, test, report” itineraries and motivational framing. | Adds little task-specific knowledge; skill need not reteach ordinary professional work. |
| Overlong trigger catalogs | Replace with recognizable user goal plus actual routing distinction. | Avoids attracting routine unrelated changes and reduces discovery text. |
| Rigid universal output recipes | Keep the evidence/deliverable contract; allow task-appropriate shape and scope. | A simple edit should not trigger a full organizational or production audit. |
| Domain invariants | Retain idempotency, fences, unknown outcomes, conservation, privacy, source provenance, replay isolation, retirement/rollback and hiring fairness. | These are consequential task constraints, not redundant proof that a model can reason. |
| User writing preferences | Retain evidence-backed claims, project-advice outreach, platform differences, exact limits, confirmed links/attachments and drafting-only authority. | Preferences are not supplied by model competence. |
| Public-source attribution | Retain Stripe reference routing and historical/adaptation/current boundaries. | General model capability does not establish a private/current Stripe fact. |
| Activation/permissions | Preserve existing invocation metadata and authority boundaries. | Prompt cleanup does not grant broader permission or opt skills out of discovery. |

No unconditional model-specific “skip tests” rule, additional global skill router, forced model default or third-party override is introduced.

## Scope and preservation

Eligible custom skills: `stripe-agentic-delivery`, `stripe-api-review`, `stripe-behavioral-replay`, `stripe-codebase-migrations`, `stripe-engineering`, `stripe-hiring-system`, `stripe-incident-response`, `stripe-interview-prep`, `stripe-invariant-recovery`, `stripe-production-readiness`, `stripe-safe-migrations`, `stripe-security-review`, `stripe-staff-engineering`, `stripe-testing-rigor`, `write-human-social-posts`, `write-job-outreach-dms`, `write-recruiter-emails`.

Only each skill's `SKILL.md` is in the edit set. Supporting references/scripts/assets and `agents/openai.yaml` remain intact. Backups, source hashes, candidate copies and validation live outside the project in a temporary maintenance workspace. Superpowers, Matt, gstack, Archify, HyperFrames, system/plugin skills and `hatch-pet` are excluded from edits. The skill lock file and third-party provenance were inspected before selecting the user-confirmed allowlist.

## Validation and limits

Initial structural validation caught an unquoted colon in a candidate YAML description. Descriptions were safely quoted and all 17 then passed built-in `quick_validate.py` and relative-reference checks. This was a staged-document error; it was never installed.

Independent preservation review compares originals/candidates for lost domain requirements. Independent forward checks apply one realistic small scenario to each candidate. These are qualitative checks, not repeated randomized A/B evaluation, a no-guidance control, or proof of equal/better Sol accuracy. Structural validation alone cannot establish behavioral quality. No paid API benchmark or task-cost/latency measurement is claimed.

Final outcome: all 17 custom entrypoints installed and validated, 47,977 → 27,360 characters (42.97% shorter). Four domain-preservation issue groups were restored and re-reviewed. A synthetic sender-name error prompted an identity rule; its targeted rerun omitted the unsupported name. Supporting resources and 1,818 protected existing files were hash-unchanged.

See [installation metrics/hashes](../reports/custom-skill-cleanup-evidence.json), [preservation review](../reports/custom-skill-preservation-review.md), [actual forward scenarios and rerun](../reports/custom-skill-forward-checks.md), and [problem/fix status](../reports/problems-and-fixes.md). Original custom skills are backed up at `/Users/parthsdambhare/.codex/skill-backups/hive-custom-skills-0sz2j6sz`. Newly discovered sessions can load the revised files; this task does not rewrite the host's already-loaded instruction snapshot.
