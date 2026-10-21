# HIVE-003 diagnosis and proposed fixes

2026-10-20. Delivery state: **Spec revision 1 approved; implementation plan in review; no product fix implemented**.

Governing [design, revision 1](../superpowers/specs/2026-10-20-supported-reports-design.md). The [problem register](problems-and-fixes.md) remains the cross-project issue ledger.

## Observed baseline

Executed:

```bash
DEBUG=false /opt/anaconda3/bin/python docs/reviews/reproduce_hive_reports.py
```

Exit 0. [Recorded output and source fingerprints](../reviews/2026-10-20-hive-003-baseline.json). In-memory SQLite, mocked models/search, no network and no real application data. This is a defect reproduction, not an acceptance pass.

| Probe | Actual result | Required future behavior |
|---|---|---|
| Changed number/relation with valid fact ID | Unsupported prose retained; gate passes. | Model cannot author findings; selected claim is rendered verbatim. |
| Unsupported heading | Retained; gate passes with zero sentences. | Headings fixed by code; arbitrary writer prose rejected. |
| Empty body | Gate passes with zero sentences. | No successful report without a finding. |
| Citation alone | Gate passes as one sentence. | Finding must contain a nonempty accepted claim. |
| Unrelated prose with two valid IDs | Retained; gate passes. | Multiple IDs cannot authorize new prose. |
| HTML heading | Raw HTML retained; gate passes. | Untrusted content encoded as literal text. |
| Full heading-only run | `done`, zero checked sentences, two appended sources. | No supported findings means `blocked`. |
| Full empty-body run | `done`, zero checked sentences, two appended sources. | Same; source wrappers do not establish a finding. |
| Full run with HTML objective | Raw HTML survives in report; run finishes `done`. | Objective is literal data under code-owned structure. |

## Root causes and remedy ownership

The current gate receives only accepted IDs, so it cannot compare the writer's wording to the original claim. Skipping all headings bypasses even ID checks. Appending objective/source wrappers after the gate and finalizing on string truthiness creates the empty-report success path. Direct Markdown interpolation gives untrusted fields structural authority.

HIVE-003 proposes a narrow `reporting` module: strict ID selection, exact accepted claims, fixed headings, safe data encoding, matching references and explicit nonempty findings. Store publication must preserve existing fencing and atomically recheck the selected snapshot. Runner completion must inspect the resulting contract rather than report length.

The report consumer also passes parsed Markdown to `dangerouslySetInnerHTML` without an explicit sanitizer. This is a source-inspection finding; no browser exploit or visual assessment was performed. Historical/arbitrary report sanitization belongs to F3-D under HIVE-005, coordinated with HIVE-009 before shared exposure. Backend-safe construction does not clear that issue.

## Fixes actually completed

- Saved a reusable, isolated diagnosis script and dated evidence with source hashes.
- Wrote the HIVE-003 design and 12 falsifiable requirements, including negative/failure checks.
- Updated spec status, issue ownership and beginner architecture handoff links.

No application behavior, database, dependency, browser UI or provider configuration changed. Runtime F3 issues remain **Scoped**. Spec approval permits implementation planning under the repository workflow; acceptance tests and implementation follow the approved plan.

User approved revision 1 on 2026-10-20: “Approve revision 1; write the plan.” [Five-task implementation plan](../superpowers/plans/2026-10-20-supported-reports.md) and [review handoff](hive-003-plan-review.md) now exist; plan approval and execution-method selection remain pending.

## Evidence boundaries

Mock runs prove the present gate/finalization defect. They do not measure verifier accuracy, provider quality, production capacity, browser exploitability or the proposed fix. Planned tests are listed in the design; no RED/GREEN implementation evidence exists for HIVE-003 yet. HIVE-001/002 acceptance results remain separate.

Document verification: five documents checked for local-link targets, 12 unique requirement declarations checked, probe Python syntax parsed, and the diagnosis repeated successfully with matching runtime-source fingerprints. [Check counts and limitations](hive-003-scoping-verification.json). The repeated run confirms the defects remain reproducible; it is not evidence that they are fixed.
