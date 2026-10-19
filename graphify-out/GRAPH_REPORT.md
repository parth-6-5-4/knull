# Graph Report - hive-lite-v5  (2026-10-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 999 nodes · 2136 edges · 49 communities (38 shown, 11 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 161 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

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
- tsconfig.json

## God Nodes (most connected - your core abstractions)
1. `HiveStore` - 44 edges
2. `cn()` - 28 edges
3. `main()` - 27 edges
4. `run_hive()` - 26 edges
5. `App()` - 25 edges
6. `LLMConfig` - 24 edges
7. `get_logger()` - 24 edges
8. `RunRepository` - 23 edges
9. `LLMRouter` - 21 edges
10. `ResearchState` - 19 edges

## Surprising Connections (you probably didn't know these)
- `test_parse_json_tolerant()` --calls--> `parse_json()`  [INFERRED]
  tests/test_hive.py → app/llm/parsing.py
- `main()` --calls--> `ModelSpec`  [INFERRED]
  docs/reviews/reproduce_hive_gaps.py → app/llm/config.py
- `test_default_config_is_ollama()` --calls--> `load_llm_config()`  [EXTRACTED]
  tests/test_hive.py → app/llm/config.py
- `main()` --indirect_call--> `fake_search()`  [INFERRED]
  docs/reviews/reproduce_hive_gaps.py → tests/test_hive.py
- `main()` --calls--> `LLMConfig`  [EXTRACTED]
  docs/reviews/reproduce_hive_gaps.py → app/llm/config.py

## Import Cycles
- None detected.

## Communities (49 total, 11 thin omitted)

### Community 0 - "App.tsx"
Cohesion: 0.07
Nodes (62): lucide-react, motion, react, App(), SidebarNav(), View, VIEWS, BudgetGauge() (+54 more)

### Community 1 - "LLMConfig"
Cohesion: 0.06
Nodes (25): default_config(), LLMConfig, load_llm_config(), ModelSpec, ProviderSettings, _call_anthropic(), _call_gemini(), _call_ollama() (+17 more)

### Community 2 - "agents.py"
Cohesion: 0.06
Nodes (20): BudgetExceeded, Caller, evidence_id(), knull_plan(), _norm(), run_researcher(), run_verifier(), run_writer() (+12 more)

### Community 3 - "core/config.py"
Cohesion: 0.07
Nodes (7): get_settings(), Settings, Config, event_stream(), EventType, SSEBroadcaster, SSEEvent

### Community 4 - "HiveStore"
Cohesion: 0.11
Nodes (6): _result(), HiveStore, main(), test_dependencies_gate_claims(), test_expired_lease_cannot_publish_and_attempts_cap(), test_lease_fence_blocks_stale_worker()

### Community 6 - "test_tools_vectordb.py"
Cohesion: 0.09
Nodes (7): create_chunk_metadata(), chroma_delete_source(), chroma_stats(), chroma_upsert(), generate_chunk_id(), _get_collection(), TestChromaDB

### Community 7 - "TraceRepository"
Cohesion: 0.08
Nodes (4): TraceRepository, get_db_context(), LocalTracer, Span

### Community 8 - "SemanticCache"
Cohesion: 0.10
Nodes (3): get_cache(), SemanticCache, TestSemanticCache

### Community 9 - "RunRepository"
Cohesion: 0.14
Nodes (9): execute_research(), get_run(), get_trace(), list_runs(), RunListResponse, RunStatusResponse, stream_run(), Run (+1 more)

### Community 10 - "db/__init__.py"
Cohesion: 0.12
Nodes (7): Base, Feedback, TraceSpan, FeedbackRepository, get_database_url(), get_db(), init_db()

### Community 11 - "test_hive.py"
Cohesion: 0.15
Nodes (19): final_gate(), is_looping(), similarity(), _tokens(), set_router(), fake_search(), make_handler(), routed_config() (+11 more)

### Community 12 - "tools/__init__.py"
Cohesion: 0.12
Nodes (8): chunk_by_sentences(), chunk_text(), cosine_similarity(), embed_single(), embed_texts(), get_embedding_dimension(), _get_model(), chroma_query()

### Community 13 - "test_tools_arxiv.py"
Cohesion: 0.11
Nodes (9): ArxivSource, format_arxiv_for_context(), search_arxiv(), test_format_arxiv_for_context(), test_format_arxiv_for_context_empty(), test_search_arxiv_handles_empty_query(), test_search_arxiv_respects_max_results(), test_search_arxiv_returns_list() (+1 more)

### Community 14 - "routes_export.py"
Cohesion: 0.15
Nodes (7): export_run(), _count_by_type(), export_bibtex(), export_html(), export_json(), export_markdown(), export_pdf()

### Community 15 - "agent/__init__.py"
Cohesion: 0.14
Nodes (8): Chunk, create_initial_state(), Critique, get_max_loops(), get_max_sources(), Plan, Source, should_continue()

### Community 16 - "routes_feedback.py"
Cohesion: 0.13
Nodes (6): FeedbackRequest, FeedbackResponse, FeedbackStatsResponse, get_feedback_stats(), get_run_feedback(), submit_feedback()

### Community 17 - "logging.py"
Cohesion: 0.14
Nodes (4): ColoredFormatter, get_logger(), JSONFormatter, setup_logging()

### Community 18 - "fetch.py"
Cohesion: 0.12
Nodes (7): default_search(), _extract_html_text(), fetch_arxiv_abstract(), safe_fetch_text(), get_wikipedia_content(), search_wikipedia(), WikipediaSource

### Community 19 - "compilerOptions"
Cohesion: 0.10
Nodes (20): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection (+12 more)

### Community 20 - "run_hive"
Cohesion: 0.15
Nodes (5): main(), HiveResult, run_hive(), BudgetGovernor, test_worker_crash_is_requeued_and_run_completes()

### Community 21 - "ResearchState"
Cohesion: 0.20
Nodes (9): build_research_graph(), critic_node(), emit_event(), finalizer_node(), intake_node(), planner_node(), reader_node(), retriever_node() (+1 more)

### Community 22 - "components.json"
Cohesion: 0.11
Nodes (17): aliases, components, hooks, lib, ui, utils, registries, @aceternity (+9 more)

### Community 23 - "json"
Cohesion: 0.18
Nodes (7): run_research(), check_citations_present(), check_sections_present(), evaluate_report(), load_golden_prompts(), run_evaluation(), run_single_eval()

### Community 24 - "ollama_client.py"
Cohesion: 0.15
Nodes (3): ollama_chat(), OllamaClient, OllamaError

### Community 25 - "compilerOptions"
Cohesion: 0.12
Nodes (16): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+8 more)

### Community 26 - "tracer.py"
Cohesion: 0.17
Nodes (4): get_paper_by_id(), _rate_limit(), search_semantic_scholar(), SemanticScholarSource

### Community 27 - "package.json"
Cohesion: 0.12
Nodes (15): clsx, marked, oxlint, playwright, tailwind-merge, tailwindcss, @types/marked, @types/node (+7 more)

### Community 28 - "main.py"
Cohesion: 0.19
Nodes (5): health(), lifespan(), llm_status(), root(), check_ollama()

### Community 29 - "routes_hive.py"
Cohesion: 0.18
Nodes (4): get_hive(), get_store(), HiveRequest, start_hive()

### Community 30 - "graph.py"
Cohesion: 0.22
Nodes (4): _generate_fallback_report(), synthesizer_node(), format_chunks_for_prompt(), format_sources_for_prompt()

### Community 31 - "routes_research.py"
Cohesion: 0.21
Nodes (3): ResearchRequest, ResearchResponse, start_research()

### Community 32 - "dependencies"
Cohesion: 0.17
Nodes (12): dependencies, clsx, @fontsource-variable/geist, @fontsource-variable/geist-mono, lucide-react, marked, motion, react (+4 more)

### Community 34 - "devDependencies"
Cohesion: 0.20
Nodes (10): devDependencies, oxlint, playwright, @types/marked, @types/node, @types/react, @types/react-dom, typescript (+2 more)

### Community 35 - "detect_trends"
Cohesion: 0.22
Nodes (4): detect_trends(), _extract_concepts_from_sources(), format_trend_summary(), TrendAnalysis

### Community 39 - "decide_next_agent"
Cohesion: 0.29
Nodes (3): route_next(), decide_next_agent(), get_agent_description()

### Community 42 - "main.tsx"
Cohesion: 0.40
Nodes (3): @fontsource-variable/geist, @fontsource-variable/geist-mono, react-dom

### Community 43 - "vite.config.ts"
Cohesion: 0.40
Nodes (3): @tailwindcss/vite, vite, @vitejs/plugin-react

### Community 44 - "scripts"
Cohesion: 0.40
Nodes (5): scripts, build, dev, lint, preview

## Knowledge Gaps
- **8 isolated node(s):** `oxlint`, `playwright`, `tailwindcss`, `@types/marked`, `@types/node` (+3 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 467 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `KnowledgeGraph` connect `KnowledgeGraph` to `logging.py`, `agents.py`, `graph.py`, `LLMConfig`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `HiveStore` (e.g. with `Caller` and `run_verifier()`) actually correct?**
  _`HiveStore` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `oxlint`, `playwright`, `tailwindcss` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `App.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.07226738934056007 - nodes in this community are weakly interconnected._
- **Why does `HiveStore` connect `HiveStore` to `agents.py`, `test_hive.py`, `run_hive`, `routes_hive.py`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `main()` (e.g. with `.add_task()` and `.claim()`) actually correct?**
  _`main()` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Should `LLMConfig` be split into smaller, more focused modules?**
  _Cohesion score 0.058018018018018015 - nodes in this community are weakly interconnected._