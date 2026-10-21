# Graph Report - hive-lite-v5  (2026-10-20)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1271 nodes · 2890 edges · 75 communities (54 shown, 21 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 343 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f4f54133`
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
- .setup
- tsconfig.json
- test_strict_search_adapters_preserve_errors_and_legacy_empty_contract
- TestHealthEndpoints
- scripts
- encrypted-text.tsx
- generate_chunk_id
- tsconfig.json
- hive-lite-mcp

## God Nodes (most connected - your core abstractions)
1. `HiveStore` - 76 edges
2. `run_hive()` - 40 edges
3. `cn()` - 28 edges
4. `main()` - 28 edges
5. `LLMRouter` - 27 edges
6. `routed_config()` - 26 edges
7. `App()` - 25 edges
8. `get_logger()` - 24 edges
9. `RunRepository` - 23 edges
10. `make_handler()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `LLMConfig`  [INFERRED]
  docs/reviews/reproduce_hive_gaps.py → app/llm/config.py
- `main()` --calls--> `ModelSpec`  [INFERRED]
  docs/reviews/reproduce_hive_gaps.py → app/llm/config.py
- `handler()` --calls--> `LLMError`  [INFERRED]
  tests/test_hive_execution.py → app/llm/router.py
- `down()` --calls--> `LLMError`  [INFERRED]
  tests/test_hive_execution.py → app/llm/router.py
- `client()` --uses--> `HiveStore`  [INFERRED]
  tests/test_api_research.py → app/hive/store.py

## Import Cycles
- None detected.

## Communities (75 total, 21 thin omitted)

### Community 0 - "App.tsx"
Cohesion: 0.06
Nodes (3): KnowledgeGraph, TestConceptExtraction, TestKnowledgeGraph

### Community 1 - "LLMConfig"
Cohesion: 0.10
Nodes (20): default_config(), LLMConfig, load_llm_config(), ModelSpec, ProviderSettings, _call_anthropic(), _call_gemini(), _call_ollama() (+12 more)

### Community 2 - "agents.py"
Cohesion: 0.10
Nodes (18): build_research_graph(), critic_node(), emit_event(), finalizer_node(), _generate_fallback_report(), intake_node(), planner_node(), reader_node() (+10 more)

### Community 3 - "core/config.py"
Cohesion: 0.09
Nodes (5): ColoredFormatter, get_logger(), JSONFormatter, setup_logging(), EventType

### Community 4 - "HiveStore"
Cohesion: 0.09
Nodes (12): default_search(), ArxivSource, format_arxiv_for_context(), search_arxiv(), fetch(), test_default_search_preserves_empty_success_and_partial_sources(), test_format_arxiv_for_context(), test_format_arxiv_for_context_empty() (+4 more)

### Community 5 - "KnowledgeGraph"
Cohesion: 0.09
Nodes (5): TraceSpan, TraceRepository, get_db_context(), LocalTracer, Span

### Community 6 - "test_tools_vectordb.py"
Cohesion: 0.11
Nodes (13): evidence_id(), final_gate(), _norm(), run_researcher(), run_verifier(), is_looping(), similarity(), _tokens() (+5 more)

### Community 7 - "TraceRepository"
Cohesion: 0.12
Nodes (8): main(), HiveResult, _positive_number(), run_hive(), TaskGraphError, claimed(), main(), publish()

### Community 8 - "SemanticCache"
Cohesion: 0.09
Nodes (12): extract_concepts_from_text(), _check_patterns(), classify_query(), _extract_terms(), generate_sub_queries(), _get_recommendations(), QueryClassification, QueryType (+4 more)

### Community 9 - "RunRepository"
Cohesion: 0.18
Nodes (19): LLMRouter, set_router(), main(), main(), fake_search(), test_cli_deadline_options_control_actual_run(), test_cli_repeated_sources_preserve_output(), mock_router() (+11 more)

### Community 10 - "db/__init__.py"
Cohesion: 0.10
Nodes (6): _result(), HiveStore, store(), test_expired_owner_cannot_mutate_without_reclaim(), test_expiry_transaction_excludes_concurrent_renewal(), test_fresh_schema_has_run_scoped_evidence_key()

### Community 11 - "test_hive.py"
Cohesion: 0.15
Nodes (20): lucide-react, marked, View, VIEWS, BudgetGauge(), FactsPanel(), LaunchForm(), ReportView() (+12 more)

### Community 12 - "tools/__init__.py"
Cohesion: 0.13
Nodes (10): setup_task(), test_cancellation_cleans_workers_watchdog_and_assignments(), test_failed_dependency_blocks_descendants_but_preserves_independent_branch(), test_invalid_dependency_graph_rejected_before_execution(), test_no_progress_blocking_is_transactional_and_causal(), test_old_attempt_cannot_mutate_replacement_or_completion(), test_separate_handle_renewal_expiry_and_competing_claims(), test_dependencies_gate_claims() (+2 more)

### Community 13 - "test_tools_arxiv.py"
Cohesion: 0.14
Nodes (9): execute_research(), get_run(), get_trace(), list_runs(), RunListResponse, RunStatusResponse, stream_run(), Run (+1 more)

### Community 14 - "routes_export.py"
Cohesion: 0.09
Nodes (13): store(), test_arxiv_fetch_does_not_block_event_loop(), test_default_search_outage_retries_and_records_execution_failure(), test_invalid_limits_rejected_before_run_creation(), test_lease_loss_cancels_execution_and_blocks_its_next_subcall(), test_long_running_task_renews_without_duplicate_attempt(), heartbeat(), search() (+5 more)

### Community 15 - "agent/__init__.py"
Cohesion: 0.17
Nodes (15): factory(), make_server(), test_deep_json_is_rejected_inside_safe_api_error_boundary(), test_discovery_and_forwarding_preserve_hive_contract(), upstream(), test_encoded_response_is_rejected_before_decompression(), test_invalid_read_payload_is_not_returned_as_success(), test_invalid_run_id_never_reaches_upstream() (+7 more)

### Community 16 - "routes_feedback.py"
Cohesion: 0.12
Nodes (10): Chunk, create_initial_state(), Critique, get_max_loops(), get_max_sources(), Plan, Source, decide_next_agent() (+2 more)

### Community 17 - "logging.py"
Cohesion: 0.17
Nodes (15): legacy_database(), snapshot(), _interrupt_migration(), execute(), test_backup_failure_leaves_original_unchanged(), test_check_is_read_only_and_reports_missing_references(), test_custom_constraints_are_refused_without_discarding_semantics(), test_interrupted_backup_is_not_reported_as_valid() (+7 more)

### Community 18 - "fetch.py"
Cohesion: 0.15
Nodes (7): export_run(), _count_by_type(), export_bibtex(), export_html(), export_json(), export_markdown(), export_pdf()

### Community 19 - "compilerOptions"
Cohesion: 0.23
Nodes (15): run_writer(), EvidenceIntegrityError, claimed(), migrated(), publish(), test_fact_evidence_may_be_existing_or_same_batch(), test_legacy_verified_fact_without_evidence_is_ineligible(), test_missing_or_foreign_fact_evidence_rolls_back_batch() (+7 more)

### Community 20 - "run_hive"
Cohesion: 0.10
Nodes (19): @fontsource-variable/geist, @fontsource-variable/geist-mono, oxlint, playwright, react, react-dom, tailwindcss, @tailwindcss/vite (+11 more)

### Community 21 - "ResearchState"
Cohesion: 0.15
Nodes (8): cosine_similarity(), embed_single(), embed_texts(), get_embedding_dimension(), _get_model(), chroma_delete_source(), chroma_query(), _get_collection()

### Community 22 - "components.json"
Cohesion: 0.12
Nodes (4): get_feedback_stats(), get_run_feedback(), submit_feedback(), FeedbackRepository

### Community 23 - "json"
Cohesion: 0.13
Nodes (3): event_stream(), SSEBroadcaster, SSEEvent

### Community 24 - "ollama_client.py"
Cohesion: 0.21
Nodes (15): motion, App(), BentoGrid(), CollapsibleNavbar(), DOTS, EmptyState(), GlowingEffect, GlowingEffectProps (+7 more)

### Community 25 - "compilerOptions"
Cohesion: 0.10
Nodes (20): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection (+12 more)

### Community 26 - "tracer.py"
Cohesion: 0.14
Nodes (4): create_chunk_metadata(), chroma_stats(), chroma_upsert(), TestChromaDB

### Community 27 - "package.json"
Cohesion: 0.18
Nodes (4): Base, Feedback, get_database_url(), init_db()

### Community 28 - "main.py"
Cohesion: 0.13
Nodes (13): BudgetExceeded, Caller, knull_plan(), LeaseLost, attempt(), execute(), scoped_search(), guard() (+5 more)

### Community 29 - "routes_hive.py"
Cohesion: 0.22
Nodes (9): _connect_existing(), main(), upgrade_hive_database(), _expected(), HiveMigrationRequired, HiveSchemaError, initialize_hive_schema(), inspect_hive_schema() (+1 more)

### Community 30 - "graph.py"
Cohesion: 0.16
Nodes (4): FeedbackRequest, FeedbackResponse, FeedbackStatsResponse, get_db()

### Community 32 - "dependencies"
Cohesion: 0.17
Nodes (8): serving(), test_cli_entrypoint_exists_and_explains_transport_options(), test_http_auth_rejects_before_any_upstream_request(), test_http_launch_refuses_untrusted_binding_or_weak_token(), test_real_http_authenticated_discovery_and_tool_call(), test_real_stdio_discovers_tools_and_calls_health(), upstream(), server()

### Community 33 - "extract_concepts_from_text"
Cohesion: 0.11
Nodes (17): aliases, components, hooks, lib, ui, utils, registries, @aceternity (+9 more)

### Community 35 - "detect_trends"
Cohesion: 0.14
Nodes (6): _extract_html_text(), fetch_arxiv_abstract(), safe_fetch_text(), get_wikipedia_content(), search_wikipedia(), WikipediaSource

### Community 36 - "TestResearchAPI"
Cohesion: 0.12
Nodes (16): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+8 more)

### Community 37 - "chroma_reset"
Cohesion: 0.17
Nodes (7): run_research(), check_citations_present(), check_sections_present(), evaluate_report(), load_golden_prompts(), run_evaluation(), run_single_eval()

### Community 38 - "TestFeedbackAPI"
Cohesion: 0.19
Nodes (4): _failure(), HiveAPI, failure(), _valid_structure()

### Community 39 - "decide_next_agent"
Cohesion: 0.16
Nodes (5): parse_json(), test_parse_json_tolerant(), _json_skeletons(), test_graph_prompts_have_valid_json_skeletons(), test_parse_json_tolerates_wrappers()

### Community 40 - "TestRunStatus"
Cohesion: 0.18
Nodes (3): main(), BearerGate, create_http_app()

### Community 41 - "TestExportAPI"
Cohesion: 0.16
Nodes (3): ollama_chat(), OllamaClient, OllamaError

### Community 42 - "main.tsx"
Cohesion: 0.21
Nodes (3): ResearchRequest, ResearchResponse, start_research()

### Community 43 - "vite.config.ts"
Cohesion: 0.26
Nodes (12): SidebarNav(), DesktopSidebar(), MobileSidebar(), Sidebar(), SidebarBody(), SidebarContext, SidebarContextProps, SidebarLink() (+4 more)

### Community 44 - "scripts"
Cohesion: 0.18
Nodes (3): get_settings(), Settings, Config

### Community 45 - "Convert to dictionary."
Cohesion: 0.24
Nodes (5): health(), lifespan(), llm_status(), root(), check_ollama()

### Community 46 - "tsconfig.json"
Cohesion: 0.17
Nodes (12): dependencies, clsx, @fontsource-variable/geist, @fontsource-variable/geist-mono, lucide-react, marked, motion, react (+4 more)

### Community 47 - "tests/__init__.py"
Cohesion: 0.18
Nodes (6): get_hive(), get_store(), HiveRequest, start_hive(), test_hive_deadline_validation_before_submission(), get()

### Community 50 - "arxiv.py"
Cohesion: 0.20
Nodes (10): devDependencies, oxlint, playwright, @types/marked, @types/node, @types/react, @types/react-dom, typescript (+2 more)

### Community 51 - "prompts.py"
Cohesion: 0.25
Nodes (3): BudgetGovernor, test_caller_rechecks_lease_before_each_model_call(), handler()

### Community 54 - "main.tsx"
Cohesion: 0.25
Nodes (3): test_hive_deadlines_forwarded_to_runner(), TestHiveAPI, TestHiveEvidenceCompatibility

### Community 55 - "vite.config.ts"
Cohesion: 0.29
Nodes (6): clsx, tailwind-merge, describe(), EventLog(), KIND_TONE, HiveEvent

### Community 57 - "scripts"
Cohesion: 0.36
Nodes (7): clip(), COL_X, DagView(), Placed, STATUS_COLOR, titleLines(), HiveTask

### Community 59 - "generate_chunk_id"
Cohesion: 0.33
Nodes (3): get_paper_by_id(), _rate_limit(), SemanticScholarSource

### Community 65 - "scripts"
Cohesion: 0.40
Nodes (5): scripts, build, dev, lint, preview

### Community 66 - "encrypted-text.tsx"
Cohesion: 0.70
Nodes (4): EncryptedText(), EncryptedTextProps, generateGibberishPreservingSpaces(), generateRandomCharacter()

## Knowledge Gaps
- **9 isolated node(s):** `oxlint`, `playwright`, `tailwindcss`, `@types/marked`, `@types/node` (+4 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 560 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `HiveStore` connect `db/__init__.py` to `test_tools_vectordb.py`, `TraceRepository`, `RunRepository`, `tools/__init__.py`, `routes_export.py`, `tests/__init__.py`, `logging.py`, `compilerOptions`, `main.tsx`, `Convert to dictionary.`, `main.py`, `graph.py`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `HiveStore` (e.g. with `Caller` and `run_verifier()`) actually correct?**
  _`HiveStore` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `oxlint`, `playwright`, `tailwindcss` to the rest of the system?**
  _9 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `App.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.05735430157261795 - nodes in this community are weakly interconnected._
- **Why does `SemanticCache` connect `devDependencies` to `SemanticCache`, `app/__init__.py`, `scripts`, `routes_research.py`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `run_hive()` (e.g. with `start_hive()` and `main()`) actually correct?**
  _`run_hive()` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Should `LLMConfig` be split into smaller, more focused modules?**
  _Cohesion score 0.09565217391304348 - nodes in this community are weakly interconnected._