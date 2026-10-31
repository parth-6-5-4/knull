# HIVE-003 implementation-plan handoff

2026-10-20. **Spec and plan revision 1 approved; subagent-driven implementation underway.**

User approval: “Approve revision 1; write the plan.” Approval recorded in the [design](../superpowers/specs/2026-10-20-supported-reports-design.md). [Implementation plan](../superpowers/plans/2026-10-20-supported-reports.md) now defines five tasks and maps all 12 REP requirements to named acceptance checks.

| Task | Deliverable | Main failure prevented |
|---|---|---|
| 1 | Strict bounded selection contract and immutable report inputs | Malformed/forged IDs or oversized input becoming report content. |
| 2 | Deterministic literal-text renderer with source/provenance metadata | Accepted wording changed, hostile markup interpreted, unused references appended. |
| 3 | Coherent SQLite snapshot and fenced atomic publication | Selected claim/source changes or alternative task-completion paths bypassing acceptance. |
| 4 | Writer/runner integration with explicit terminal outcomes | Zero-findings success, factual rejection fabricated from execution errors, stale retry output published. |
| 5 | API/CLI/MCP compatibility, final review and delivery evidence | New contract delivered without actual consumer and historical-data checks. |

## Planning discoveries

- HTTP/MCP currently project report strings, but do not expose run `gate` as a public top-level field. Plan preserves those shapes; stored result/run JSON and CLI/direct results provide provenance inspection. No extra API projection is silently added.
- Historical fixtures include `F-good`; membership must not be replaced with a new hex-only ID constraint.
- Existing verifier-promotion test helper creates research tasks even when named `verify`. Plan corrects that fixture's role so enforcing writer-publication ownership does not mask its provenance regression.
- Removing `final_gate` also affects two audit scripts and old sentence-stripping tests. Plan explicitly updates those call sites, preserving dated defect JSON.
- Frontend dependencies are absent locally; renderer/DOM checks remain required at execution. No package was installed and no browser rendering was verified while writing this plan.

## Rendering guidance

Impeccable context loaded successfully for the report consumer; no product/design context file was present, so the existing source is the scope constraint. Impeccable `harden` and Emil guidance were applied to the proposed rendering contract only.

| Before | Proposed after | Why |
|---|---|---|
| Untrusted Markdown/HTML interpolation | Escaped data inside code-owned report structure | Preserve literal claims without giving data structural authority. |
| No defined multiline/long-token behavior | Whitespace-preserving text spans and wrapping, checked at 390 and 1,440 pixels | Keep claims readable without deleting text or introducing horizontal overflow. |
| Report-string truthiness can show success with zero findings | Explicit zero-finding blocked outcome | Prevent an apparently supported empty report. |

No React/CSS source change, UI redesign or historical report sanitizer is included. F3-D stays under HIVE-005; generated-report fixture verification cannot establish end-to-end historical browser safety.

## Review and remaining work

Self-review checked REP-01–12 coverage, consistent signatures/types across tasks, exact byte/count limits, bounded errors, same-run provenance, publication transaction boundaries, alternative completion paths, failure versus no-findings distinction, legacy fixtures and five explicit failure classes. No independent code reviewer was dispatched for this documentation-only stage; final implementation review is required by Task 5.

Recommend native execution because tasks share one reporting contract and store transaction seam. Implement tasks serially, then use one fresh whole-change reviewer. Subagent-driven execution remains available if the user selects it.

User subsequently approved this concrete plan and selected subagent-driven execution on 2026-10-20. Source: repository `docs/DEVELOPMENT.md` step 5 and Superpowers `writing-plans` execution handoff. No new approval is being sought for the already approved design.

Planning checks and source fingerprints are recorded in [the verification receipt](hive-003-plan-verification.json). The planning receipt is historical. Current executed checks and per-task reviews are recorded under `hive-003/` and in its execution ledger. Application F3/F3-A/B/C issues remain Scoped; no issue is marked fixed by this plan.
