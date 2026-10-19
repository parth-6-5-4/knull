# Working in Hive Lite

## Start here

- Before changing behavior, architecture, interfaces, dependencies, or operational configuration, read [the development workflow](docs/DEVELOPMENT.md) and [the spec index](docs/superpowers/README.md). Resume the relevant spec's current stage.
- For domain terms and relationships, read [CONTEXT.md](CONTEXT.md).
- When tracing existing code relationships, use [the knowledge graph guide](docs/knowledge-graph.md) and installed Graphify skill if available. Check snapshot freshness and verify graph-derived claims against current source; the code graph does not encode draft specifications.
- For orchestration, persistence, verification, routing, hierarchy, or scaling work, read [the architecture review](docs/reviews/hive-modularization-review.md). Its findings are evidence and proposals; spec approval establishes the intended behavior.
- When investigating problems, scoping fixes, or changing affected code, maintain [the problems/fixes register](docs/reports/problems-and-fixes.md) using the reporting rules in `docs/DEVELOPMENT.md`.

## Skills

Use the installed Superpowers workflow: `using-superpowers` → `brainstorming` → `writing-plans` → the selected execution skill → `verification-before-completion`. Apply `systematic-debugging` for defects and `test-driven-development` for behavior changes. Load each skill when its stage is reached; do not preload later execution stages.

For module design, use Matt's `codebase-design` and `domain-modeling`. For distributed-state, agent-autonomy, or verification design, use the relevant Stripe skills named in the architecture review. Apply their principles to this project's scale.

Skill discovery and missing-skill handling are documented in `docs/DEVELOPMENT.md`. This repository does not vendor or auto-install third-party skills.

## Project constraints

- Keep run coordination, branch coordination, specialist roles, and worker resources distinct. Parent ownership and task dependencies are separate relationships.
- Keep legal state transitions, leases/fences, permissions, budget accounting, and commits in deterministic code. Jev supplies bounded semantic decisions; generative models supply plans and text.
- Preserve evidence provenance and verifier context isolation. A valid citation ID alone does not establish that a sentence is supported.
- The hive and legacy LangGraph are separate execution paths. Identify which one each change affects and verify the entrypoint actually used.
- Update the governing spec when intended behavior changes. Keep implementation checklists and executed verification evidence in the linked plan.
- Check the actual Git root before worktree, staging, commit, or push operations. Operate on a project-owned checkout; do not stage unrelated parent-directory content.

## Completion

Follow the acceptance criteria and verification requirements in `docs/DEVELOPMENT.md`. Report the linked spec, resulting behavior, checks actually run, and remaining limitations. Keep draft/reviewed/implemented states truthful.
