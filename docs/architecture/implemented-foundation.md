# Implemented lite foundation — 20 October 2026

[Main architecture guide](../../ARCHITECTURE.md) · [Evidence](../reports/hive-integrity/summary.md)

HIVE-001 and HIVE-002 are verified for the SQLite lite engine. Earlier diagrams are source-pinned historical explanations; their proposed modular/Postgres system remains a design target.

| Part | Delivered behavior | Remaining modular work |
|---|---|---|
| Provenance | Evidence keyed by run and local ID; immutable same-run content; atomic rejection of unresolved references | Shared snapshots/authorization and long-term memory |
| Historical data | Explicit stopped-writer migration, consistent private backup, refusal of unsupported/custom shapes | Postgres store-authority cutover |
| Assessment | Missing provenance excluded from new verified memory/reports; verifier outages remain execution failures | Complete typed assessment schemas and calibrated final-report support |
| Ownership | Guarded publish/fail/release/renew; transactional expiry and causal dependency blocking | Durable distributed coordinator authority |
| Execution | Supervised worker/watchdog/renewal tasks; cancellation fences late work; bounded retry and logical task/run deadlines | Crash-resume, global/provider admission and conservative unknown-call settlement |
| Retrieval | Strict Hive outage reporting, legacy adapter compatibility, responsive event loop during arXiv work | Capacity and external-call reconciliation; active sync threads cannot be forcibly stopped |

The graph remains fixed research → verify → write. There is no role/skill registry, delegated hierarchy or Jev runtime yet. HIVE-003/004/006/007/008/010/011/012 retain their own status and acceptance gates.

Before using an existing old hive database, follow the [operator maintenance procedure](../../README.md#hive-storage-upgrade-and-bounded-execution). No real database was upgraded by the implementation task.

## Reporting checkpoint — 21 October 2026

HIVE-003 now delivers strict fact-ID selection, literal accepted-claim rendering and fenced report publication. All five tasks and final repairs reviewed; [acceptance evidence](../reports/hive-003/summary.md): 370 focused + 54 MCP passed. Full-suite dependency failures, pre-existing lifecycle contention and historical arbitrary Markdown remain separately tracked. Architecture diagrams retain their stated earlier source pins; the code-only graph has a refreshed 2026-10-21 source-hash snapshot.
