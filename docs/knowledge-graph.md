# Codebase knowledge graph

Open [the interactive map](../graphify-out/graph.html), [Graphify's report](../graphify-out/GRAPH_REPORT.md), or [the graph JSON](../graphify-out/graph.json). Snapshot: 2026-10-19; 999 nodes, 2,136 edges, 49 communities. This maps current source, tests, and configuration. Proposed modular architecture remains in [the spec index](superpowers/README.md).

## Installation and provenance

Installed the [official Graphify project](https://github.com/Graphify-Labs/graphify/tree/86c57be8204673c2a1b9849a3292a7dd3ab373d8), package **graphifyy 0.9.92**, from commit `86c57be8204673c2a1b9849a3292a7dd3ab373d8`. Its Codex skill lives at `/Users/parthsdambhare/.codex/skills/graphify/SKILL.md`; CLI at `/Users/parthsdambhare/.local/bin/graphify`. Isolated uv tool environment; application dependencies unchanged. Restart Codex or start a new session to refresh installed-skill discovery.

[Provenance](../graphify-out/provenance.json) records SHA256 hashes for all 88 detected code/config files and extraction limitations. No project-owned Git checkout exists here: the parent repository's commit is not a source snapshot. Its automatically inherited stamp was removed. Ignore any stamp copied from an older cached graph; compare the source hashes instead.

## Coverage and interpretation

- Local AST/structured-file extraction only; zero LLM input/output tokens. Deterministic hub names label communities. No semantic document pass or external model calls.
- Detector classified 88 files as code/config and 22 as documents. The documents were skipped. Eight unclassified files were also skipped. `.graphifyignore` excludes maintenance reports, generated graph/cache data, dependencies, build outputs and runtime data.
- Six files yielded no symbols; warning examples include `app/__init__.py`, `app/api/__init__.py`, `app/core/__init__.py`, `web/src/lib/utils.ts`, and `web/src/main.tsx`. Module/import nodes can still exist. `eval/golden.json` has no represented node. Detection does not imply full semantic coverage.
- 1,975 edges are marked EXTRACTED; 161 INFERRED by static heuristics. These are navigation clues, not verified runtime dependencies or entailment evidence.
- Graph is **undirected**. Query/explain output may display relationship arrows; do not treat them as an authoritative execution order. Follow source for call direction, dynamic dispatch, provider selection, runtime state, and security boundaries.
- Community membership expresses topology, not approved module ownership. Generic names such as `compilerOptions` may recur. Use node IDs and source paths to disambiguate.
- HTML embeds graph data and loads `vis-network@9.1.6` from unpkg.com. It needs network access when that library is uncached. JSON/report/CLI queries work locally.

## Explore

Run from this project directory, with `~/.local/bin` on PATH:

```bash
GRAPHIFY_QUERY_LOG_DISABLE=1 graphify query 'run_hive HiveStore claim publish BudgetGovernor' --budget 1200
GRAPHIFY_QUERY_LOG_DISABLE=1 graphify explain HiveStore
GRAPHIFY_QUERY_LOG_DISABLE=1 graphify path run_hive HiveStore
```

First query found 187 nodes and returned 49 within its budget; omitted nodes were explicitly reported. Increase the budget or narrow the symbols before concluding something is absent. [Captured query](../graphify-out/query-smoke.txt) and [explanation](../graphify-out/explain-smoke.txt) retain source references. Useful entry points: `HiveStore` (44 connections), `run_hive`, `BudgetGovernor`, `LLMConfig`, `routes_hive.py`, and `App.tsx`.

In the HTML, search `HiveStore`, select its result, then inspect source and neighbors. Community checkboxes narrow the view. Browser verification confirmed rendering, community controls, search, and selected-node details showing `app/hive/store.py` with degree 44.

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

[Post-build health](../graphify-out/health.json) found zero missing/dangling endpoints, duplicates and self-loops. This checks exported graph integrity; it cannot recover relationships suppressed before serialization or prove complete source coverage. No runtime application behavior was changed or validated by graph generation.
