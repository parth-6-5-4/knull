# Local-only files and publication rules

Reviewed 2026-10-21 before publishing to `https://github.com/parth-6-5-4/knull.git`.

Keep these files on the developer's machine. The repository `.gitignore` excludes them; do not force-add them or move their contents into tracked files.

| Local material | Reason |
|---|---|
| `.local-only/` | Unapproved drafts, local publication manifests, private setup notes and scratch data. |
| `.superpowers/` | Agent task briefs, filesystem baselines, temporary review packages and recovery workspaces. Shared results belong in reviewed reports, not the entire agent workspace. |
| `.archify/` | Duplicate generated candidates, browser captures and intermediate diagram checks. Publish curated `docs/architecture/` deliverables instead. |
| `.codex/`, `.agents/`, `.mcp.json` | Personal agent/host configuration. Share generic templates under `integrations/mcp/examples/`. |
| `.env`, `.env.*`, private key files | Credentials and machine settings. Explicit `.env.example`/`.env.sample` templates must contain placeholders only. |
| `app_data/`, `chroma_data/`, database files | Real run data, user records and backups. |
| Virtualenvs, `node_modules/`, build outputs and test caches | Rebuild locally from declared dependencies. |
| `graphify-out/cache/`, `.graphify*`, dated build folders, `.vocab.txt`, `memory/`, `reflections/` | Machine state, query history and agent learning; not the shared source map. |
| HIVE-003 dependency/browser installation logs | Machine setup output; not behavioral acceptance evidence. |

Shareable material includes source/tests, specifications/plans, curated architecture HTML, the static graph export with dated provenance, and selected mock-data test/review evidence. Historical test logs may contain interpreter paths; these are environment evidence, not reusable setup configuration. Never include real tokens, `.env` content, private datasets or run databases in reports.

Before every commit/push:

1. Check `git status --short` and the exact remote URL.
2. Stage explicit scopes; inspect `git diff --cached --name-status` and the staged diff. Avoid blanket staging before this review.
3. Check staged content for credentials and local-only paths. Ignoring a file does not untrack an already tracked file; remove only its index entry when converting it to local-only, preserving the local copy.
4. Run the relevant verification and record incomplete work accurately. Do not label an interrupted review or unfinished spec Verified.
5. Push the intended branch without force, merge, history rewriting or unrelated changes.

`python3 scripts/check_publication.py` checks the index against ignore rules, including files force-added despite those rules. This checkout installs the shared pre-commit/pre-push hooks through `git config core.hooksPath .githooks`; fresh clones can run that command to enable the same guard. Existing unrelated hook configuration should be integrated rather than overwritten. Hooks can be bypassed deliberately, so the explicit review remains necessary. The guard checks paths, not the contents of every possible secret format.

On 2026-10-21, tracked Graphify query-memory/reflection/vocabulary artifacts were designated local-only and removed from the index while keeping local copies. Earlier Git history may still contain those artifacts; this task does not rewrite published history. No credential was identified in them by the publication scan.
