# Development checkpoint — 1 November 2026

This branch is an unfinished development checkpoint of Knull's lite research hive. Publishing it preserves working modules, tests and plans; it does not mark the modular platform complete or production-ready.

## What exists

The current Hive path plans a research/verify/write task DAG, coordinates leased and fenced work in SQLite, retains run-owned evidence and facts, and renders selected accepted claims into reports. The legacy LangGraph research path remains separate.

| Area | Current state | Evidence / remaining boundary |
|---|---|---|
| HIVE-001 — evidence isolation | Verified lite scope | Run-scoped provenance and explicit maintenance; [acceptance](hive-integrity/summary.md). |
| HIVE-002 — execution integrity | Verified lite scope | Attempt fencing, terminal progress and supervision; distributed restart remains separate. |
| HIVE-003 — supported reports | Verified lite scope | Literal accepted-claim rendering, fenced publication and deadline repair; [acceptance](hive-003/summary.md). Historical Markdown consumer safety and broader lifecycle contention remain open. |
| HIVE-004-A Task1 — schema foundation | Implemented and task-reviewed | SQLite v2, explicit backup/migration, immutable types, transaction/executor ownership; [review](hive-004/task-1-review.md). No real database activated. |
| HIVE-004-A Task2 — accounting | Implemented and task-reviewed | Conserved grants, durable holds, receipt replay, overrun freeze and inspection; [review](hive-004/task-2-review.md). Internal accounting is not integrated shared admission. |
| HIVE-004-A Tasks3–8 | Not implemented | Shared queues/permits, provider controls, Caller integration, lifecycle repair, public projections and load/fault acceptance remain. |
| HIVE-013 — MCP | Local implementation candidate | Optional adapter and retained protocol checks; [ledger](../superpowers/plans/2026-10-20-mcp-server.md). Document review/shared exposure gates remain open. |
| Durable hierarchy, Jev and skill registry | Draft designs | HIVE-006/007/008/012 in the [spec index](../superpowers/README.md); no modular hierarchy, Jev routing or user skill execution claimed. |

## Verification

Fresh publication check: **118 passed** across resource accounting, resource migration and report-store compatibility. [Command, environment and source hashes](hive-004/publication-focused-2026-11-01.json), [output](hive-004/publication-focused-2026-11-01.log). The inherited pytest fixture-loop deprecation warning remains. No application behavior was edited during publication.

Historical October Task2 evidence: full restricted run **490 passed / 11 failed / 3 errors**; a separate permitted browser/local-transport rerun recorded **4 passed / 1 failed**. Its remaining dependency failures are the embedding stack's HfFolder incompatibility and absent Anthropic SDK. Those runs are retained independently; the full suite was not rerun for this November publication and is not claimed green. [Exact historical receipts](hive-004/task-2-commands.json).

Task2's complete written independent review records spec compliance and quality approval with no blocking findings. Its agent turn hit a usage limit after writing the report. Minor test readability and fixture configuration notes remain recorded; integrated requirements are still open.

## Next implementation step

Resume [Task3 of the approved plan](../superpowers/plans/2026-10-21-resource-admission.md): implement shared run/call queues, fair scheduling and atomic capacity permits on the same database. Continue fresh implementer/reviewer per task, then complete Tasks4–8 before declaring HIVE-004-A verified. Include original call identity and receipt-provenance inspection in Task7.

Existing v0/v1 data requires explicit stopped-writer maintenance. Unpublished v2 shape changed during accounting work; earlier temporary v2 fixtures are not a supported deployed-data baseline. No real database migration or activation was performed.

## Publication boundaries

Only project source, tests, plans, status documents and curated mock-data evidence are intended for GitHub. [Local-only rules](../LOCAL_ONLY.md) exclude agent recovery workspaces, host configuration, credentials, databases, dependency environments, caches and regenerated screenshot scratch. The current knowledge graph remains the dated HIVE003 snapshot; resource modules are not represented until the planned refresh. No merge into main, deployment or new feature implementation is part of this publication.
