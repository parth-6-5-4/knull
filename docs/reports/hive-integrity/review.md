# Independent HIVE-001 / HIVE-002 review and repairs

20 October 2026. Fresh-context read-only reviewer inspected the named implementation, specs, plans and disposable acceptance cases. No real application data or live providers were used. Review preceded the final repair pass; no second independent review is claimed.

| Finding | Reproduction before repair | Repair | Observed regression evidence |
|---|---|---|---|
| P1: default arXiv blocked the event loop | Offline sync SDK fixture took 150 ms; configured 30 ms run deadline returned after 161 ms with zero renewals. | Offload sync retrieval to `asyncio.to_thread`; cancelled attempts cannot publish. Underlying thread cannot be forcibly cancelled and CLI shutdown may wait for it. | `test_arxiv_fetch_does_not_block_event_loop`: fetch-start → tick → fetch-end. Failed before, passes after. |
| P2: unknown constraints silently removed | Legacy evidence table with custom CHECK accepted and migrated; CHECK disappeared. | Recognize complete normalized table DDL as well as columns/indexes; reject unsupported constraints before backup or DDL. | `test_custom_constraints_are_refused_without_discarding_semantics`: CHECK, FK and collation cases all failed before, pass after; source unchanged and no backup created. |
| P2: default retrieval hid execution outages | All three providers raised OSError; research completed with no sources on attempt one, zero task_error events. | Opt-in strict adapter errors for Hive; genuine empty results remain successful, partial sources remain usable; empty results with backend errors raise unavailability and bounded retry. | `test_default_search_outage_retries_and_records_execution_failure` plus three real-adapter strict/legacy tests. Failed before, pass after. |

[Eight failing regressions](review-regressions-red.txt) → [eight passing regressions](review-regressions-green.txt). [Final focused acceptance](combined-acceptance.txt): 140 passed. [Full-suite output](combined-full-suite.txt) retains unrelated failures by exact test name. [MCP compatibility](mcp-compatibility.txt): 54 passed under local fixture socket permission.

No other important findings identified by the reviewer. HIVE-004 resource conservation/global admission, HIVE-006 crash recovery and HIVE-010 complete typed assessment output remain separate work. This review does not establish those capabilities.
