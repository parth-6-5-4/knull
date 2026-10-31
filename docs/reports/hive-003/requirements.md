# HIVE-003 requirement coverage

Revision 1, resumed 2026-10-21. This maps executable checks to the approved contract; final commands/results and review verdicts live in summary.md and verification.json. All required lite acceptance gates completed; delivery is Verified. Latest focused suite: 370 passed; MCP: 54 passed. Full-suite dependency failures remain classified in the delivery summary.

| Requirement | Executable oracle | Evidence class |
|---|---|---|
| REP-01 | `test_snapshot_excludes_unaccepted_or_foreign_provenance`, `test_snapshot_read_is_coherent` | Disposable file-backed SQLite, second connection/WAL coherence fixture |
| REP-02 | `test_selection_rejects_noncontract_json`, raw-response UTF-8 cases | Pure strict JSON parser; full-response rejection |
| REP-03 | `test_selection_rejects_duplicate_unknown_or_excess_ids`, `test_selection_empty_and_sixteen_preserve_order` | Pure selection membership/count/order |
| REP-04 | `test_render_uses_only_selected_claims`, `test_writer_prose_cannot_be_salvaged`, `test_valid_selection_finishes_with_exact_claim` | Renderer and full mock-provider runs |
| REP-05 | `test_marked_rendering_round_trip` | Locked marked parser plus Chromium DOM and 390/1440px viewports |
| REP-06 | `test_sources_match_selected_findings`, `test_unsafe_url_is_inert`, source mutation publication cases | Renderer URL/text rules and pinned SQLite provenance |
| REP-07 | `test_empty_selection_blocks_run`, `test_no_candidates_skips_writer`, `test_empty_report_has_no_supporting_artifact` | Empty report/gate/status, no-model dispatch, unchanged facts |
| REP-08 | `test_changed_snapshot_publication_is_atomic`, `test_stale_report_attempt_cannot_publish`, lock-contention cases | Separate SQLite handles; all-or-nothing completion/result and live lease guards |
| REP-09 | `test_report_provenance_survives_reopen`, valid API/CLI stored-artifact cases | Reopen persisted metadata and compare pinned accepted claim/source digests |
| REP-10 | `test_report_utf8_boundaries*`, `test_candidate_window_is_stable`, output cap exact/over cases | UTF-8 byte limits; no truncation and stable omissions |
| REP-11 | Task 5 API/CLI historical/valid/empty-selection checks plus existing MCP suite | Real local surfaces with disposable data; response-string compatibility |
| REP-12 | `test_writer_error_classification_preserves_facts`, snapshot retry and cancellation cases | Distinct execution/no-findings outcomes; bounded attempts, cleanup, real mutex/writer/reader deadline contention and distinct-loop-clock regression |

Task 3 review found a live-time race after SQLite lock waits; six contention regressions failed before repair and pass afterward. Existing HIVE-001/002 guards remain obligations, not bypasses for report construction.

Guarantee ends at report-task publication. Later fact revocation does not rewrite a committed artifact (HIVE-006 owns that protocol). Preserving accepted claims does not establish semantic verifier accuracy. Historical arbitrary Markdown UI sanitization remains F3-D/HIVE-005. No live-provider quality evaluation, distributed load test or production-readiness claim.
