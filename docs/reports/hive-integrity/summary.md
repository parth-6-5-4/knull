# HIVE-001 and HIVE-002 delivery evidence

20 October 2026. User explicitly requested completing HIVE-001 then continuing HIVE-002. Both implemented on local branch `hive-001-002-integrity`. Existing unrelated work retained; no commit, push, deployment or real-data migration performed.

## Result

HIVE-001: run-scoped immutable evidence, atomic fact/evidence publication, explicit recoverable schema upgrade and historical provenance eligibility are implemented. Repeated public sources now work across runs, including changed content at the same URL. Historical reports remain unchanged; missing evidence is never borrowed from another run.

HIVE-002: all attempt mutations require current ownership/attempt/fence/lease, expiry is transactional, failed prerequisites block descendants causally, healthy work renews, and run execution is supervised with task/run deadlines and bounded retry. Verifier outage/malformed assessment cannot certify factual rejection. Default retrieval preserves genuine empty results, distinguishes unavailable execution and keeps the event loop responsive during synchronous arXiv work.

## Acceptance map

| Requirement | Observed checks |
|---|---|
| EVI-01 | `test_two_runs_publish_same_evidence_id`; repeated-source file/API/CLI runs |
| EVI-02 | `test_missing_or_foreign_fact_evidence_rolls_back_batch`; existing/same-batch positive case |
| EVI-03 | `test_same_run_conflict_rolls_back_batch` (four content fields + duplicate ID); identical publication |
| EVI-04 | `test_two_runs_preserve_different_source_text`; full-flow changed-source verifier-input capture |
| EVI-05 | stale publication and promotion checks; all-or-nothing batch/result/task assertions |
| EVI-06 | repeated-source API/CLI response/citation checks; existing hive/prompt tests |
| EVI-07 | old-schema preservation, raw-history versus eligible-memory reads, missing-provenance writer/promotion |
| EVI-08 | future/partial/custom-schema refusal; private verified backup; no-op reapply; injected DDL/backup errors; six process-death boundaries with fresh-process reopen |
| EXE-01 | same-worker stale release/exhaustion/renewal/publication, expired-owner mutation, completed-task immutability |
| EXE-02 | separate handles, barrier-controlled expiry-versus-renewal, competing claims |
| EXE-03 | long task renews past one lease; cancelled search returning late cannot make the old attempt's next model call; replacement succeeds |
| EXE-04 | permanent source outage reaches exhausted + causal blocked descendants; independent branch still completes |
| EXE-05 | missing/cross-run/cyclic/unknown-kind graphs rejected; no-progress causal terminal result |
| EXE-06 | cancellation leaves no worker/renewal/watchdog tasks or active claims; supervisor failure records failed cause |
| EXE-07 | invalid inputs rejected before planning/run creation; shared logical task and whole-run deadlines; no router retry backoff after final attempt; API/CLI validation and forwarding |
| EXE-08 | verifier outage preserves proposed facts; malformed verdict is execution error; default tool outage and strict/legacy adapter distinction |

## Commands and environment

Focused app acceptance:

```bash
DEBUG=false PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/test_hive_execution.py tests/test_hive_evidence.py tests/test_hive_migrations.py tests/test_hive_cli.py tests/test_hive.py tests/test_api_research.py tests/test_prompts.py tests/test_tools_arxiv.py -q
```

[Output](combined-acceptance.txt): **140 passed**. Python 3.12.7, SQLite 3.45.3; real disposable SQLite databases and subprocess/fault boundaries; mock model/search providers. No paid calls or live retrieval.

[Post-fix reproduction](../../reviews/2026-10-20-hive-001-post-fix.json): two runs each done with two verified facts and two evidence rows; conflict refused with original text unchanged; foreign-only reference rolled back; orphaned historical facts produce no writer output. Earlier baseline JSON preserved.

[Independent review and three repaired findings](review.md). Eight regressions were observed failing before fixes and passing afterward. Additional integration cases exercise empty/partial retrieval and lease-loss behavior. All important findings addressed in one repair pass; no second review claimed.

[MCP compatibility](mcp-compatibility.txt): 54 passed, no skips, including real Hive HTTP route → disposable SQLite → mock providers, stdio and authenticated HTTP. Required `HIVE_APP_PYTHON=/opt/anaconda3/bin/python` and local fixture socket permission. No personal MCP host setup or live model calls.

[Broader suite](combined-full-suite.txt): **153 passed, 10 failed, 3 socket errors**. It retains ten unrelated failures in `tests/test_semantic_cache.py` and `tests/test_tools_vectordb.py`: installed sentence-transformers imports unavailable `huggingface_hub.HfFolder`. Three SDK roundtrip fixtures cannot bind local sockets under the restricted run. [Socket-authorized SDK rerun](sdk-local-socket.txt): three passed, one failed because the Anthropic SDK is absent. Exact test names and traces are retained. HIVE-011 owns dependency repair; these failures are not reclassified as passes.

## Decisions and limits

- Continued native execution from the direct user instruction rather than repeating approval questions. Scope remains the written specs; no broad modular engine implementation.
- Corrected the old plan's stale parent-Git constraint after verifying project ownership. Created a local feature branch in the existing checkout, retaining pending edits. Isolation is file-level; no separate worktree, staging or commit.
- Strict retrieval is opt-in so legacy consumers retain their documented empty-list behavior. Partial sources remain usable; an empty result with failed backends can trigger a bounded retry.
- Deadlines and cancellation bound coroutine execution and fence late publication. An already-running synchronous SDK thread cannot be forcibly stopped; its late result is discarded, and CLI shutdown may wait for that thread. Durable external-call reconciliation/global resource accounting remains HIVE-004/006.
- No Postgres, crash-resume, role/skill registry, hierarchy or Jev implementation is implied. HIVE-003 sentence/heading support, HIVE-010 complete output schemas and HIVE-011 dependency work remain open.

## Operator action

Existing legacy hive databases need the explicit stopped-writer [maintenance procedure](../../../README.md#hive-storage-upgrade-and-bounded-execution). Do not restart old writers during upgrade. Do not restore a backup over accepted new work. This delivery tested fixtures only; choose and execute real maintenance separately.

## Publication checkpoint — 21 October 2026

User later authorized scoped commits and push. The exact staged HIVE-001/002 source was exported to a disposable checkout and its focused acceptance command above rerun: **140 passed** ([fresh output](publication-focused.txt)). Earlier no-commit statements describe the original execution phase. No real database was migrated. HIVE-003 remains an independently published In progress checkpoint.
