# Task 5 handoff — compatibility and delivery evidence

21 October 2026. Governing spec: `docs/superpowers/specs/2026-10-20-supported-reports-design.md` (REP-01–12). Governing plan: `docs/superpowers/plans/2026-10-20-supported-reports.md`, Task 5. This is the implementer handoff for fresh whole-change review, not a Verified declaration.

## Result and changed boundary

- `tests/test_hive_cli.py` now checks a generated report's CLI JSON gate (`accepted-claims-v1`), stored writer/run gate and selected claim/source digests; it also checks empty selection yields `blocked`, `(no report)` and no stored report.
- `tests/test_api_research.py` checks historical report bytes on GET, unchanged response keys and absent public top-level gate, plus generated and empty-selection run status, report and stored provenance. The route fixture uses a disposable store and mock provider/search boundary.
- `tests/test_prompts.py` replaces a stale assertion on retired `WRITE_SYSTEM` with a current `run_writer` selection contract check. The original full-suite run exposed that stale test; the six prompt tests subsequently passed.
- `docs/reviews/reproduce_hive_reports.py`, `reproduce_hive_gaps.py` and `reproduce_hive_evidence.py` now probe the structured selection seam. They preserve other gap/evidence probes and use in-memory or disposable SQLite with mock providers. The prior dated baseline JSON files have no working-tree diff.
- No production API, CLI, MCP, reporting, runner or store file changed in Task 5. The six Python files above are frozen for review; no further edit is proposed from this handoff.

## Recorded commands and outcomes

The `task-5-*.log` files capture command output but do not print their full shell argv or an explicit shell-exit receipt. Commands below are the prescribed Task 5 invocations, with the browser path and socket-permitted reruns reflected by their corresponding outputs. Counts and causes are taken from those files; no missing exit code is inferred.

| Check | Command / output | Observed result |
|---|---|---|
| CLI/API compatibility | `DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_hive_cli.py tests/test_api_research.py -q` · `task-5-compatibility.log` | 26 passed; no manufactured RED. |
| Focused acceptance, restricted Chromium | `PLAYWRIGHT_BROWSERS_PATH=/tmp/hive-003-browsers DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_hive.py tests/test_hive_migrations.py tests/test_hive_evidence.py tests/test_hive_execution.py tests/test_hive_cli.py tests/test_hive_report_contracts.py tests/test_hive_reports.py tests/test_hive_report_store.py tests/test_hive_report_execution.py tests/test_api_research.py -q` · `task-5-focused.log` | 1 failed, 354 passed. Chromium Mach rendezvous failed with `Permission denied (1100)` in `test_marked_rendering_round_trip`; this was a process permission failure. |
| Focused acceptance, permitted Chromium | Same test selection and browser path · `task-5-focused-permitted.log` | 355 passed, including the renderer case; no affected failure or skip recorded. |
| MCP, restricted local sockets | `HIVE_APP_PYTHON=/opt/anaconda3/bin/python integrations/mcp/.venv/bin/python -m pytest -c integrations/mcp/pyproject.toml integrations/mcp/tests` · `task-5-mcp.log` | 1 failed, 49 passed, 4 errors. Real-route/transport fixtures could not bind loopback sockets (`PermissionError: [Errno 1] Operation not permitted`). |
| MCP, permitted local sockets | Same suite with `-q` · `task-5-mcp-permitted.log` | 54 passed in 8.56 s, no skips shown. The real-route fixture executed. |
| Prompt compatibility after stale-test repair | `DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_prompts.py -q` · `task-5-prompts-green.log` | 6 passed. |
| Frontend | `npm --prefix web run lint`; `npm --prefix web run build` · `task-5-web-lint.log`, `task-5-web-build.log` | Prior execution reported exit 0 for both; lint output has no findings and build output ends `built in 697ms`. The files themselves do not contain shell exit receipts. |
| Full suite, restricted permissions, before prompt repair | `DEBUG=false /opt/anaconda3/bin/python -m pytest -q` · `task-5-full-suite.log` | 12 failed, 378 passed, 3 errors. This includes the stale prompt assertion and Chromium permission failure, ten embedding import failures and three socket-bound SDK errors. |
| Full suite, permitted permissions, after prompt repair | Same command · `task-5-full-suite-permitted.log` | 11 failed, 382 passed. Six semantic-cache and four Chroma tests fail importing `HfFolder` from installed `huggingface_hub`; one Anthropic SDK roundtrip fails because `anthropic` is not installed. No HIVE report test failed. The full suite remains red. |

The full-suite dependency failures match the earlier HIVE-001/002 delivery's classified embedding and Anthropic environment failures; this handoff does not reclassify them as passes or claim general production readiness. The existing `pytest-asyncio` fixture-loop-scope deprecation warning also appears in Python test logs.

## Diagnostic observations and boundaries

The three script invocations are `DEBUG=false /opt/anaconda3/bin/python docs/reviews/reproduce_hive_reports.py`, `DEBUG=false /opt/anaconda3/bin/python docs/reviews/reproduce_hive_gaps.py` and `DEBUG=false /opt/anaconda3/bin/python docs/reviews/reproduce_hive_evidence.py`, with their stdout saved as the matching `task-5-*-observations.json` files and stderr as `task-5-*-stderr.log`. The files do not contain shell exit receipts; all three JSON files parse and all three stderr files are empty.

`task-5-reports-observations.json` records six prose/heading/HTML/citation payloads rejected as invalid selection JSON, a forged ID rejected as `selection_id_invalid`, one valid selected claim rendered with `accepted-claims-v1` provenance, and an empty selection yielding no report with `no_selected_findings`. The two full-run prose probes ended `blocked`; an HTML objective was escaped as literal report text. `task-5-gaps-observations.json` retains repeated-source, exhausted-dependency and stale-fence probes; unsafe prose is rejected and supported selection renders the accepted claim. The separate HIVE-004 budget gap remains observed at cap 100 / spent 400. `task-5-evidence-observations.json` records two successful repeated-source runs, rejected same-run conflict/unresolved reference, and no report from missing provenance (`no_verified_facts`). These are current offline observations, not acceptance tests or live-provider qualification.

The historical report assertion compares the exact stored string to the returned body, including CRLF, Unicode and raw markup. It establishes fetch compatibility, not safety of arbitrary historical Markdown in the browser. The publication guarantee applies at report-task commit; later fact revocation does not rewrite the artifact. HIVE-005 retains historical UI sanitization, and HIVE-006 retains any post-publication revocation protocol.

## Requirement and self-review handoff

`docs/reports/hive-003/requirements.md` maps REP-01–12 to executable oracles. Task 5 adds REP-09/11 public compatibility and persisted-provenance assertions; its focused suite re-executes the Task 1–4 parser, renderer, store and runner acceptance tests. The reported permitted focused result covers all ten planned test files, while the permitted MCP suite covers the real route. Task 5 did not alter the public projection: HTTP/MCP expose report strings; CLI/direct results expose gate metadata, and run/task storage retains the detailed gate.

Self-review against the brief found no missing Task 5 Python requirement: historical bytes, generated and empty selection, stable response shape, policy/version and provenance, retired diagnostic import removal, dated baseline preservation, focused/MCP/browser execution and broad-suite classification are represented. `tests/test_prompts.py` is the authorized compatibility extension discovered by full-suite RED. Diagnostic scripts do not silently mutate application data. Fresh whole-change independent review, graph refresh/provenance validation, final document/link checks and spec/plan/index/problem-register reconciliation remain controller-owned. Keep HIVE-003 below Verified until those gates and the documented full-suite limitation are assessed.

Draft delivery artifacts: `docs/reports/hive-003/summary.md` and `verification.json`. They are evidence summaries for controller review, not a status change.
