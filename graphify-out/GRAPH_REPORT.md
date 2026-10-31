> Scope: code-only static extraction; zero LLM tokens. INFERRED means static heuristics in this snapshot, including where generated report wording says model-reasoned. Source hashes and limitations: provenance.json.

# Graph Report - hive-lite-v5  (2026-10-21)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1459 nodes · 3598 edges · 72 communities (51 shown, 21 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 452 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e36f7e01`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- App.tsx
- LLMConfig
- agents.py
- core/config.py
- HiveStore
- KnowledgeGraph
- test_tools_vectordb.py
- TraceRepository
- SemanticCache
- RunRepository
- db/__init__.py
- test_hive.py
- tools/__init__.py
- test_tools_arxiv.py
- routes_export.py
- agent/__init__.py
- routes_feedback.py
- logging.py
- fetch.py
- compilerOptions
- run_hive
- ResearchState
- components.json
- json
- ollama_client.py
- compilerOptions
- tracer.py
- package.json
- main.py
- routes_hive.py
- graph.py
- routes_research.py
- dependencies
- extract_concepts_from_text
- devDependencies
- detect_trends
- TestResearchAPI
- chroma_reset
- TestFeedbackAPI
- decide_next_agent
- TestRunStatus
- TestExportAPI
- main.tsx
- vite.config.ts
- scripts
- Convert to dictionary.
- tsconfig.json
- tests/__init__.py
- app/__init__.py
- TestFeedbackAPI
- arxiv.py
- prompts.py
- TestRunStatus
- TestExportAPI
- main.tsx
- vite.config.ts
- TestHealthEndpoints
- scripts
- Convert to dictionary.
- generate_chunk_id
- WikipediaSource
- test_strict_search_adapters_preserve_errors_and_legacy_empty_contract
- scripts
- hive-lite-mcp

## God Nodes (most connected - your core abstractions)
1. `HiveStore` - 96 edges
2. `run_hive()` - 45 edges
3. `routed_config()` - 32 edges
4. `LLMRouter` - 31 edges
5. `cn()` - 28 edges
6. `main()` - 28 edges
7. `make_handler()` - 28 edges
8. `App()` - 25 edges
9. `get_logger()` - 24 edges
10. `set_router()` - 24 edges

## Surprising Connections (you probably didn't know these)
- `scholar()` --calls--> `Source`  [INFERRED]
  tests/test_hive_execution.py → app/agent/state.py
- `main()` --calls--> `LLMConfig`  [INFERRED]
  docs/reviews/reproduce_hive_gaps.py → app/llm/config.py
- `main()` --calls--> `ModelSpec`  [INFERRED]
  docs/reviews/reproduce_hive_gaps.py → app/llm/config.py
- `handler()` --calls--> `LLMError`  [INFERRED]
  tests/test_hive_execution.py → app/llm/router.py
- `down()` --calls--> `LLMError`  [INFERRED]
  tests/test_hive_execution.py → app/llm/router.py

## Import Cycles
- None detected.

## Communities (72 total, 21 thin omitted)

### Community 0 - "App.tsx"
Cohesion: 0.07
Nodes (62): lucide-react, motion, react, App(), SidebarNav(), View, VIEWS, BudgetGauge() (+54 more)

### Community 1 - "LLMConfig"
Cohesion: 0.05
Nodes (29): BudgetExceeded, default_config(), LLMConfig, load_llm_config(), ModelSpec, ProviderSettings, _call_anthropic(), _call_gemini() (+21 more)

### Community 2 - "agents.py"
Cohesion: 0.07
Nodes (29): _connect_existing(), main(), upgrade_hive_database(), _expected(), HiveMigrationRequired, HiveSchemaError, initialize_hive_schema(), inspect_hive_schema() (+21 more)

### Community 3 - "core/config.py"
Cohesion: 0.06
Nodes (16): chunk_by_sentences(), create_chunk_metadata(), cosine_similarity(), embed_single(), embed_texts(), get_embedding_dimension(), _get_model(), chroma_delete_source() (+8 more)

### Community 4 - "HiveStore"
Cohesion: 0.07
Nodes (22): default_search(), setup_task(), test_arxiv_fetch_does_not_block_event_loop(), test_cancellation_cleans_workers_watchdog_and_assignments(), test_default_search_outage_retries_and_records_execution_failure(), test_expiry_transaction_excludes_concurrent_renewal(), test_failed_dependency_blocks_descendants_but_preserves_independent_branch(), test_invalid_dependency_graph_rejected_before_execution() (+14 more)

### Community 5 - "KnowledgeGraph"
Cohesion: 0.11
Nodes (7): evidence_id(), main(), claimed(), publish(), main(), load_golden_prompts(), run_evaluation()

### Community 6 - "test_tools_vectordb.py"
Cohesion: 0.10
Nodes (17): build_research_graph(), critic_node(), emit_event(), finalizer_node(), _generate_fallback_report(), intake_node(), planner_node(), reader_node() (+9 more)

### Community 7 - "TraceRepository"
Cohesion: 0.15
Nodes (24): LLMRouter, set_router(), main(), probe_run(), main(), fake_search(), handler(), test_cli_deadline_options_control_actual_run() (+16 more)

### Community 8 - "SemanticCache"
Cohesion: 0.11
Nodes (22): run_writer(), _active_source_url(), _compact(), _display(), _literal(), parse_selection(), _reject_constant(), render_report() (+14 more)

### Community 9 - "RunRepository"
Cohesion: 0.09
Nodes (13): knull_plan(), _check_patterns(), classify_query(), _extract_terms(), generate_sub_queries(), _get_recommendations(), QueryClassification, QueryType (+5 more)

### Community 11 - "test_hive.py"
Cohesion: 0.15
Nodes (25): assert_facts_preserved(), assert_no_hive_tasks(), execute(), install_writer(), handler(), select_first(), test_direct_writer_rejects_mismatched_snapshot_before_dispatch(), test_empty_selection_blocks_run() (+17 more)

### Community 12 - "tools/__init__.py"
Cohesion: 0.17
Nodes (20): reporting(), row(), snapshot(), test_raw_source_changes_invalidate_binding(), test_report_rejects_duplicate_or_missing_candidate_identity(), test_report_rejects_empty_claim(), test_report_rejects_foreign_or_unverified_rows(), test_report_rejects_nonstring_or_unrepresentable_fields() (+12 more)

### Community 13 - "test_tools_arxiv.py"
Cohesion: 0.10
Nodes (3): get_cache(), SemanticCache, TestSemanticCache

### Community 14 - "routes_export.py"
Cohesion: 0.11
Nodes (11): run_research(), Chunk, create_initial_state(), Critique, get_max_loops(), get_max_sources(), Plan, Source (+3 more)

### Community 15 - "agent/__init__.py"
Cohesion: 0.11
Nodes (7): Base, Feedback, TraceSpan, get_database_url(), get_db(), get_db_context(), init_db()

### Community 16 - "routes_feedback.py"
Cohesion: 0.10
Nodes (7): HiveResult, _result(), HiveStore, main(), store(), test_expired_owner_cannot_mutate_without_reclaim(), store()

### Community 17 - "logging.py"
Cohesion: 0.09
Nodes (3): TraceRepository, LocalTracer, Span

### Community 18 - "fetch.py"
Cohesion: 0.19
Nodes (19): assert_unpublished(), prepared(), publish(), store(), test_changed_snapshot_publication_is_atomic(), test_deadline_publication_preserves_busy_timeout_and_transaction_state(), test_deadline_publication_with_wal_reader_keeps_report_atomic(), test_existing_mutation_rechecks_lease_after_database_contention() (+11 more)

### Community 19 - "compilerOptions"
Cohesion: 0.11
Nodes (7): FeedbackRequest, FeedbackResponse, FeedbackStatsResponse, get_feedback_stats(), get_run_feedback(), submit_feedback(), FeedbackRepository

### Community 20 - "run_hive"
Cohesion: 0.15
Nodes (8): get_run(), get_trace(), list_runs(), RunListResponse, RunStatusResponse, stream_run(), Run, RunRepository

### Community 21 - "ResearchState"
Cohesion: 0.11
Nodes (10): ArxivSource, format_arxiv_for_context(), search_arxiv(), fetch(), test_format_arxiv_for_context(), test_format_arxiv_for_context_empty(), test_search_arxiv_handles_empty_query(), test_search_arxiv_respects_max_results() (+2 more)

### Community 22 - "components.json"
Cohesion: 0.17
Nodes (15): factory(), make_server(), test_deep_json_is_rejected_inside_safe_api_error_boundary(), test_discovery_and_forwarding_preserve_hive_contract(), upstream(), test_encoded_response_is_rejected_before_decompression(), test_invalid_read_payload_is_not_returned_as_success(), test_invalid_run_id_never_reaches_upstream() (+7 more)

### Community 23 - "json"
Cohesion: 0.10
Nodes (11): Caller, _norm(), run_researcher(), run_verifier(), BudgetGovernor, is_looping(), similarity(), _tokens() (+3 more)

### Community 24 - "ollama_client.py"
Cohesion: 0.15
Nodes (7): export_run(), _count_by_type(), export_bibtex(), export_html(), export_json(), export_markdown(), export_pdf()

### Community 25 - "compilerOptions"
Cohesion: 0.21
Nodes (15): EvidenceIntegrityError, claimed(), migrated(), publish(), store(), test_fact_evidence_may_be_existing_or_same_batch(), test_legacy_verified_fact_without_evidence_is_ineligible(), test_missing_or_foreign_fact_evidence_rolls_back_batch() (+7 more)

### Community 26 - "tracer.py"
Cohesion: 0.15
Nodes (9): real_hive(), test_submit_and_poll_real_hive_through_stdio(), serving(), test_cli_entrypoint_exists_and_explains_transport_options(), test_http_auth_rejects_before_any_upstream_request(), test_http_launch_refuses_untrusted_binding_or_weak_token(), test_real_http_authenticated_discovery_and_tool_call(), test_real_stdio_discovers_tools_and_calls_health() (+1 more)

### Community 28 - "main.py"
Cohesion: 0.13
Nodes (3): event_stream(), SSEBroadcaster, SSEEvent

### Community 29 - "routes_hive.py"
Cohesion: 0.10
Nodes (20): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection (+12 more)

### Community 30 - "graph.py"
Cohesion: 0.11
Nodes (8): get_hive(), get_store(), HiveRequest, start_hive(), test_hive_deadline_validation_before_submission(), test_hive_deadlines_forwarded_to_runner(), TestHiveAPI, TestHiveEvidenceCompatibility

### Community 31 - "routes_research.py"
Cohesion: 0.12
Nodes (16): clsx, @fontsource-variable/geist, @fontsource-variable/geist-mono, oxlint, react-dom, tailwind-merge, tailwindcss, @types/marked (+8 more)

### Community 32 - "dependencies"
Cohesion: 0.35
Nodes (16): render(), row(), snapshot(), test_citation_labels_preserve_fact_ids_with_ordinal_anchors(), test_direct_renderer_revalidates_selection(), test_empty_report_has_no_supporting_artifact(), test_escaping_expansion_cannot_bypass_output_cap(), test_malformed_bracketed_authority_is_inert() (+8 more)

### Community 33 - "extract_concepts_from_text"
Cohesion: 0.12
Nodes (5): ReportSnapshotChanged, check_deadlines(), ReportPublicationBusy, RunDeadlineExceeded, TaskGraphError

### Community 34 - "devDependencies"
Cohesion: 0.11
Nodes (17): aliases, components, hooks, lib, ui, utils, registries, @aceternity (+9 more)

### Community 35 - "detect_trends"
Cohesion: 0.12
Nodes (16): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+8 more)

### Community 36 - "TestResearchAPI"
Cohesion: 0.13
Nodes (3): get_settings(), Settings, Config

### Community 37 - "chroma_reset"
Cohesion: 0.19
Nodes (4): ColoredFormatter, get_logger(), JSONFormatter, setup_logging()

### Community 38 - "TestFeedbackAPI"
Cohesion: 0.19
Nodes (4): _failure(), HiveAPI, failure(), _valid_structure()

### Community 39 - "decide_next_agent"
Cohesion: 0.19
Nodes (4): execute_research(), ResearchRequest, ResearchResponse, start_research()

### Community 40 - "TestRunStatus"
Cohesion: 0.18
Nodes (3): main(), BearerGate, create_http_app()

### Community 41 - "TestExportAPI"
Cohesion: 0.19
Nodes (4): _extract_html_text(), fetch_arxiv_abstract(), safe_fetch_text(), get_wikipedia_content()

### Community 42 - "main.tsx"
Cohesion: 0.18
Nodes (8): _positive_number(), run_hive(), pipeline(), watchdog(), worker(), test_invalid_limits_rejected_before_run_creation(), test_run_deadline_includes_planning_and_records_stop(), test_worker_crash_is_requeued_and_run_completes()

### Community 43 - "vite.config.ts"
Cohesion: 0.17
Nodes (7): marked, playwright, evidenceDir, fixtures, results, root, tokens

### Community 44 - "scripts"
Cohesion: 0.17
Nodes (12): dependencies, clsx, @fontsource-variable/geist, @fontsource-variable/geist-mono, lucide-react, marked, motion, react (+4 more)

### Community 45 - "Convert to dictionary."
Cohesion: 0.24
Nodes (9): WriterAssignment, LeaseLost, attempt(), execute(), scoped_search(), guard(), renew(), probe_writer() (+1 more)

### Community 46 - "tsconfig.json"
Cohesion: 0.18
Nodes (5): extract_concepts_from_text(), detect_trends(), _extract_concepts_from_sources(), format_trend_summary(), TrendAnalysis

### Community 48 - "app/__init__.py"
Cohesion: 0.20
Nodes (10): devDependencies, oxlint, playwright, @types/marked, @types/node, @types/react, @types/react-dom, typescript (+2 more)

### Community 50 - "arxiv.py"
Cohesion: 0.29
Nodes (4): get_paper_by_id(), _rate_limit(), search_semantic_scholar(), SemanticScholarSource

### Community 52 - "TestRunStatus"
Cohesion: 0.29
Nodes (3): after_database_contention(), test_snapshot_read_is_coherent(), trace()

### Community 54 - "main.tsx"
Cohesion: 0.33
Nodes (3): check_citations_present(), check_sections_present(), evaluate_report()

### Community 58 - "Convert to dictionary."
Cohesion: 0.40
Nodes (3): @tailwindcss/vite, vite, @vitejs/plugin-react

### Community 60 - "WikipediaSource"
Cohesion: 0.40
Nodes (5): scripts, build, dev, lint, preview

## Knowledge Gaps
- **8 isolated node(s):** `oxlint`, `tailwindcss`, `@types/marked`, `@types/node`, `@types/react` (+3 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 608 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `HiveStore` connect `routes_feedback.py` to `extract_concepts_from_text`, `agents.py`, `HiveStore`, `KnowledgeGraph`, `TraceRepository`, `SemanticCache`, `RunRepository`, `main.tsx`, `test_hive.py`, `Convert to dictionary.`, `fetch.py`, `TestRunStatus`, `TestExportAPI`, `json`, `compilerOptions`, `graph.py`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `HiveStore` (e.g. with `Caller` and `run_verifier()`) actually correct?**
  _`HiveStore` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `oxlint`, `tailwindcss`, `@types/marked` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `App.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.07226738934056007 - nodes in this community are weakly interconnected._
- **Why does `run_hive()` connect `main.tsx` to `extract_concepts_from_text`, `HiveStore`, `KnowledgeGraph`, `test_tools_vectordb.py`, `TraceRepository`, `test_hive.py`, `Convert to dictionary.`, `routes_feedback.py`, `json`, `compilerOptions`, `graph.py`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `run_hive()` (e.g. with `start_hive()` and `main()`) actually correct?**
  _`run_hive()` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Should `LLMConfig` be split into smaller, more focused modules?**
  _Cohesion score 0.050616050616050616 - nodes in this community are weakly interconnected._