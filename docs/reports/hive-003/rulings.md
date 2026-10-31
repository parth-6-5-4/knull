# HIVE-003 decisions and deferred review scope

Controller record, 2026-10-21. Requirements remain revision 1. These decisions explain execution choices and every behavior explicitly set aside by whole-change review; they do not silently approve other specs.

## Execution decisions

| Decision | Reason | Cost if wrong |
|---|---|---|
| Continue the existing feature checkout and preserve preceding HIVE-001/002/MCP edits. | Approved plan pins this branch and existing work; later publication established a clean checkpoint. | File-level isolation needs careful scoped diffs instead of a separate worktree. |
| Use frozen filesystem baselines for task reviews; preserve the ignored recovery workspace until new work is safely published. | Original execution had no commit authorization, and original snapshots are unique review/recovery evidence. | More local disk; provenance depends on file hashes as well as commits. |
| Keep store publication guards and runner integration separate; retain intermediate old-writer failures honestly. | Guard correctness should not be weakened for an unintegrated consumer. | Intermediate checkout cannot complete reports until the runner task; final acceptance must restore success. |
| Repair the reproduced cached-time race in six shared lease-checked write paths. | An expired mutation or revived lease could undermine report authority through another path. | Broader store change needs real contention and regression evidence. |
| Extend Task 5 to the stale writer contract test in test_prompts.py. | Full-suite RED exposed access to retired WRITE_SYSTEM after policy replacement. | Could regress shared prompts; preserve other role checks and require prompt GREEN. |
| Repair whole-change I1 for both task and run deadlines at publication. | Real lock contention showed successful report artifacts after logical deadline with an otherwise live lease. | Additional runtime deadline propagation/store checks require real contention RED/GREEN and scoped re-review. |

| Continue one bounded repair after the first final re-review left I1 open. | Actual readers blocked SQLite COMMIT after the first repair; a concrete lock-first fix exists, so stopping or claiming completion would leave a material requirement broken. | Additional testing/review time; short exclusive report transactions block new readers until publication finishes. |

## Explicit review exclusions and disposition

| Considered behavior | Ruling / owner | Cost or residual limitation |
|---|---|---|
| Original verifier semantic accuracy and universal truth | Defer to model/verification qualification, HIVE-007/010. | Accepted claim can still be mistaken; this spec preserves wording/provenance only. |
| Later revocation or rewriting a committed report | Defer to HIVE-006 dependency invalidation. | Stored artifact remains a publication-time snapshot. |
| Arbitrary historical Markdown sanitization | Keep F3-D scoped to HIVE-005. | Historical consumer remains unsafe by source inspection. |
| Full-console layout/accessibility, other browsers, redesign | Outside unchanged application UI; report-only parser/Chromium evidence accepted. | No whole-console or cross-browser qualification. |
| Global token/spend admission, provider response memory bounds and distributed capacity | Defer to HIVE-004/006; keep report-local limits assessed here. | Existing budget overshoot persists until integrated resource work. |
| Early claim/sweep clocks | Keep F3-F admission/recovery follow-up. | Liveness may shorten leases or delay reclaim; repaired authority checks do not establish capacity. |
| Trusted controller/direct SQLite powers and caller-created in-process data | Preserve trusted-local-controller assumption; HIVE-009 owns shared-caller isolation. | Malicious code with the connection is outside this report authorization guarantee. |
| Tampering with committed task-result JSON | Outside publication-time contract; shape checks remain consistency defenses. | No integrity protection against a malicious database writer. |
| Private/local HTTP destinations and source reputation | Preserve approved URL syntax policy; renderer never fetches URLs. | A displayed HTTP URL is not a destination-trust or fetcher SSRF guarantee. |
| Durable lifecycle, multi-controller authority and post-publication cancellation races | Defer to HIVE-006; current writer cancellation is checked. | No crash-resume/distributed-lifecycle claim. |
| Legacy LangGraph, prior foundation, license and independent MCP hardening | Separate published scopes; inspect concrete report consumer seams only. | HIVE-003 review does not requalify unrelated changes. |
| Embedding/Anthropic dependencies and pytest-asyncio warning | Retain exact environment failures; HIVE-011 owns repair. | Full suite remains red; affected report checks must still pass. |
| Graph completeness and migration fixture self-loop | Treat graph as source-hashed navigation; retain extraction warning. | Graph topology is not runtime proof or complete dependency coverage. |
| Final docs/status/publication handoff | Controller owns reconciliation after I1 repair and scoped review. | Do not mark Verified while material review findings or required evidence remain open. |


## Additional scoped observation

F3-J: accept the re-review's out-of-scope classification for unchanged watchdog/abort writes under an independently held SQLite reader and very short busy timeout. Track it as a HIVE-004 integration gate/HIVE-006 lifecycle follow-up. Cost: a database contention failure can leave lite run state unfinished; current report-publication safety and publication-only retry tests do not establish global recovery or production readiness.
