# Codebase knowledge graph

Open [the interactive map](../graphify-out/graph.html), [Graphify's report](../graphify-out/GRAPH_REPORT.md), or [the graph JSON](../graphify-out/graph.json). Refreshed 2026-10-21 after HIVE-003 reporting and compatibility changes: **1,459 nodes, 3,598 edges, 72 communities**. This maps source/tests/configuration, including migration, assignment integrity, supported-report construction and the optional MCP adapter. Proposed modular architecture remains in [the spec index](superpowers/README.md). Current accepted foundation: [implementation evidence](reports/hive-integrity/summary.md).

**Snapshot boundary:** source hashes bind the HIVE-003 working implementation, including its compatibility tests. The Git stamp alone does not include uncommitted changes. Architecture diagrams retain their original dated source snapshots.

## Installation and provenance

Installed the [official Graphify project](https://github.com/Graphify-Labs/graphify/tree/86c57be8204673c2a1b9849a3292a7dd3ab373d8), package **graphifyy 0.9.92**, from commit `86c57be8204673c2a1b9849a3292a7dd3ab373d8`. Its Codex skill lives at `~/.codex/skills/graphify/SKILL.md`; CLI at `~/.local/bin/graphify`. Isolated uv tool environment; application dependencies unchanged. Restart Codex or start a new session to refresh installed-skill discovery.

[Provenance](../graphify-out/provenance.json) records SHA256 hashes for all 121 detected code/config files (115 represented by nodes) and extraction limitations. A project-owned Git checkout appeared during the 2026-10-20 work; the current graph's commit stamp identifies its HEAD, while uncommitted review fixes require the source hashes to reproduce the actual snapshot. Earlier extraction had inherited an unrelated parent-repository stamp; it was removed at that time. Always verify the actual Git root before trusting a stamp.

## Coverage and interpretation

- Local AST/structured-file extraction only; zero LLM input/output tokens. Deterministic hub names label communities. No semantic document pass or external model calls.
- Current detector classified 121 files as code/config and 37 as documents. Documents were skipped; ten unclassified files were also skipped, including the Codex TOML examples. `.graphifyignore` excludes maintenance reports, generated graph/cache data, dependencies, build outputs, runtime data and lockfiles.
- Incremental extraction reuses unchanged cached entries, so cached warnings are not a fresh whole-tree symbol audit. Module/import nodes can still exist. Three dated review JSON files, two Claude config JSON examples and `eval/golden.json` have no represented nodes (the six paths are listed in provenance). Detection does not imply full semantic coverage.
- 3,146 edges are marked EXTRACTED; 452 INFERRED by static heuristics. These are navigation clues, not verified runtime dependencies or entailment evidence.
- Graph is **undirected**. Query/explain output may display relationship arrows; do not treat them as an authoritative execution order. Follow source for call direction, dynamic dispatch, provider selection, runtime state, and security boundaries.
- Community membership expresses topology, not approved module ownership. Generic names such as `compilerOptions` may recur. Use node IDs and source paths to disambiguate.
- HTML embeds graph data and loads `vis-network@9.1.6` from unpkg.com. It needs network access when that library is uncached. JSON/report/CLI queries work locally.

## Explore

Run from this project directory, with `~/.local/bin` on PATH:

```bash
GRAPHIFY_QUERY_LOG_DISABLE=1 graphify query 'run_writer report_snapshot publish_report parse_selection render_report' --budget 1200
GRAPHIFY_QUERY_LOG_DISABLE=1 graphify explain report_snapshot
GRAPHIFY_QUERY_LOG_DISABLE=1 graphify path run_hive HiveStore
```

The captured query follows supported-report construction. The refreshed [captured query](../graphify-out/query-smoke.txt) uses a 1,000-token budget and retains source references; omitted nodes are reported. Broad token matches can include unrelated modules. Increase budget or narrow the symbol/path before concluding something is absent. [Snapshot explanation](../graphify-out/explain-smoke.txt) retains source references. Useful entry points include `HiveAPI`, `HiveStore`, `run_hive`, `BudgetGovernor`, `LLMConfig`, `routes_hive.py`, and `App.tsx`.

In the HTML, search `HiveStore` or `HiveAPI`, select a result, then inspect source and neighbors. Community checkboxes narrow the view. Initial browser verification on 2026-10-19 confirmed rendering, search and HiveStore details. The 2026-10-21 Chromium smoke checked canvas loading, current counts, report_snapshot search, selection and details with zero page errors or failed requests; [receipt](reports/hive-003/final-fix-2-graph-browser.json). No new visual-quality approval is claimed.

## Refresh and verify

From the project root:

```bash
export GRAPHIFY_QUERY_LOG_DISABLE=1
export PYTHONDONTWRITEBYTECODE=1
export GRAPHIFY_OUT=graphify-out
# Prevent inheritance of the unrelated parent Git repository.
export GIT_CEILING_DIRECTORIES="$(dirname "$PWD")"
graphify extract . --code-only
graphify cluster-only . --no-label
graphify diagnose multigraph --graph graphify-out/graph.json --json > graphify-out/health.json
```

`--no-label` prevents model-based labeling; existing valid labels are reused and changed groups can receive deterministic hub labels. On a fresh output directory, generic community names are acceptable; use Graphify's local `label_communities_by_hub` helper for richer names without a model. This snapshot used that helper. Do not add `--directed` to this version's `extract` command: it does not parse that flag.

After refresh, update provenance hashes/counts and captured queries; inspect the rendered HTML again. Refresh when source changes; graph queries do not update extraction automatically. Keep graph JSON, HTML, report and provenance together. Internal caches, local interpreter hints and dated tool backups are ignored.

[Post-build health](../graphify-out/health.json) found zero missing/dangling endpoints or duplicates. Two self-loops are static extractor resolution errors: the migration fixture's `super().execute` and the offset event-loop fixture's `super().time` resolve back to their wrappers. Source shows delegation, not actual recursion. This checks exported graph integrity; it cannot recover relationships suppressed before serialization or prove complete source coverage. Graph generation itself does not validate runtime behavior; HIVE-001/002 acceptance and [HIVE-003 acceptance](reports/hive-003/summary.md) are linked separately.

Publication metadata uses portable home-relative tool locations; personal absolute host paths were removed without changing graph structure or source hashes.

This refresh used local code-only extraction and deterministic labeling: zero LLM input/output tokens. The generated report template sometimes calls INFERRED edges model-reasoned; this snapshot uses static heuristics, as its report preface and provenance clarify. Graph health retains two known extractor self-loops, with no missing/dangling endpoints or duplicate edges.

HIVE-004-A execution started 2026-10-22. This dated graph still binds the HIVE-003 source snapshot; evolving resource/schema code is not included until Task 8 refresh. Verify current source when following those paths.
