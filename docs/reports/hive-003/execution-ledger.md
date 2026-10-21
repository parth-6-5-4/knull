# SDD ledger — plan: docs/superpowers/plans/2026-10-20-supported-reports.md

User approved spec revision 1 and plan revision 1; selected fresh implementer/reviewer per task, 2026-10-20.
Branch: hive-001-002-integrity. Original execution constraint: no commits/staging/real-data migration. On 2026-10-21 the user explicitly authorized scoped commits and push; real-data migration remains outside this work.

Ruling: Continue in the existing feature checkout, preserving pending HIVE-001/002 and MCP edits — the approved plan explicitly pins that branch and dirty state — cost if wrong: file-level isolation needs careful before/after review rather than separate worktree isolation.
Ruling: Use per-task filesystem snapshots and unified diff packages instead of commit-range review packages; retain ledger/evidence at completion — approved no-commit constraint means empty Git ranges and deleting the sole recovery record would lose evidence — cost if wrong: review provenance relies on captured file hashes rather than commit objects.

## Preflight consistency scan

| Task(s) | Producer / consumer or internal consistency | Finding |
|---|---|---|
| 1 | Frozen snapshots, strict parser and field/message limits | Types/limits/test oracles consistent; no live store required. |
| 2 | Renderer consumes frozen snapshot and selected IDs | Matches exact-claim contract; dependencies must be installed before required DOM check. |
| 3 | Store snapshot/publish and role guards | Coherent read and fenced write are separate; verifier fixture corrected so provenance assertion remains meaningful. |
| 4 | Agents/runner integrate all seams | Gate/count outcomes and typed errors align; route fixtures change with schema. |
| 5 | Surfaces, evidence, review and graph | Compatibility tests can start GREEN; no manufactured RED; controller owns final review/status after task review. |
| 1/2 | reporting.py types/parser → renderer | Shared file; serial work only. |
| 1/3 | snapshot_from_rows / hashes → store | Joined-row schema explicit; matching hashes reused. |
| 1/4 | messages/parser/errors → writer/runner | Exactly one structured selection call per attempt. |
| 1/5 | contract limits → acceptance/evidence | Full matrix included. |
| 2/3 | render_report → publish_report | Recomputed report/gate comparison inside guarded publication. |
| 2/4 | render_report → run_writer tuple | Existing tuple retained; snapshot binding passed separately. |
| 2/5 | Node DOM script → compatibility gates | Required renderer dependency absence cannot pass via skip. |
| 3/4 | report_snapshot/publish_report → executor | Assignment type and function signatures match. |
| 3/5 | durable result/gate → provenance readback | Existing JSON storage; no schema change. |
| 4/5 | shared mock fixtures → API/CLI/MCP | Preserve response shapes and dated diagnostic evidence. |

## Progress

Task 1: dispatched next. Baseline focused suite running; result will be recorded before dependent integration.

Baseline: 128 passed in 5.36s; command/output docs/reports/hive-003/baseline.txt. Existing feature checkout used as approved.

Task 1: complete (no commits authorized; task-1-review.diff snapshot; spec and quality approved). RED 109 failures → GREEN 109 passed.
Task 1: minor (deferred): pre-existing pytest-asyncio loop-scope configuration warning; final review must classify it, not hide it.
Task 2: dispatching fresh implementer after clean task gate.
Frontend prerequisites: locked npm ci succeeded after sandbox DNS failure; Chromium installed under /tmp/hive-003-browsers. No package/lockfile edits.

Ruling: Keep Task 3 writer-publication guards and Task 4 runner integration as separate reviewed tasks; explicitly record intermediate legacy-writer failures rather than weaken guards — Task 3 blocks generic writer completion while the old runner changes only in Task 4 — cost if wrong: the unmerged intermediate checkout cannot complete successful runs until Task 4; final acceptance must restore all existing outcomes.

Task 2 interim visual check: root inspected 390px and 1440px generated-report captures. Literal injection/whitespace and long-token wrapping visible. Detected ordinal-only citation labels [1], requested selected fact-ID labels to preserve existing report/CLI contract before handoff; anchors remain ordinal. Final captures must be regenerated/rechecked after correction.

Task 2: complete (task-2-review.diff snapshot; spec and quality approved). Final 161 passed including 18 browser viewport checks; root viewed corrected 390px/1440px captures with fact-ID labels and literal payloads.
Task 2: minor (deferred): same pre-existing pytest-asyncio configuration warning.
Task 3: dispatching fresh implementer for store snapshot/publication; intermediate writer-integration dependency recorded above.

Task 3: review Important — default publication time captured before lock acquisition; second-connection write lock outlives a 100ms lease, then stale report publication succeeds. Fix round 1/5 started with original implementer; require actual contention RED→GREEN and scoped re-review.

Ruling: Extend Task 3 fix round 1 to reproduced shared lease-checked write races (publish, verifier promotion, heartbeat, release/exhaustion) — expired input-authority mutations or lease revival can undermine report fencing, so restore the already authorized HIVE-002 expiry guarantee rather than leave a parallel bypass — cost if wrong: additional store-method transaction changes require broader focused regression evidence; explicit test clocks and public APIs stay unchanged.

Task 3: fix round 1/5 (original I1 addressed; no new fix-diff findings; 6 contention cases RED→GREEN). Fresh scoped re-review approved.
Task 3: complete (task-3-review.diff + task-3-fix-1-review.diff; no commits). 40 new store tests pass; combined127pass/2 recorded cross-task old-writer failures remain Task4 acceptance obligations.
Task 3: adjacent source-inspected liveness risks: claim samples grant time before lock wait; expire_leases uses early cutoff. These can shorten a new lease or defer reclamation; no expired-mutation permission remains in repaired six paths. Reproduction/repair not claimed; track under capacity/durable-runtime follow-up.
Task 4: dispatched next with obligation to restore both existing integration checks.


## Publication checkpoint — 2026-10-21

Task 4 implementation exists. Recorded checks: 23 execution cases, 301 compatibility cases, 19 API cases and 17 evidence cases passed in their respective runs. Its fresh review could not complete because the reviewer hit the model usage limit; no review approval is claimed. Task 5 remains pending, including diagnostic adapters, compatibility additions, full-suite classification, graph refresh, requirement mapping and final independent review.

User requested scoped commits and push of this checkpoint. Publishing does not advance HIVE-003 beyond In progress. The historical diagnostics still target the retired final_gate/writer format and are not current acceptance commands; preserve dated baseline results. Next: fresh Task 4 review, resolve findings, then Task 5.

Fresh publication checks (2026-10-21):

- `PLAYWRIGHT_BROWSERS_PATH=/tmp/hive-003-browsers DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_hive.py tests/test_hive_migrations.py tests/test_hive_evidence.py tests/test_hive_execution.py tests/test_hive_cli.py tests/test_hive_report_contracts.py tests/test_hive_reports.py tests/test_hive_report_store.py tests/test_hive_report_execution.py tests/test_api_research.py -q`: **351 passed**, including required Chromium renderer checks; [output](publication-focused.txt).
- `HIVE_APP_PYTHON=/opt/anaconda3/bin/python integrations/mcp/.venv/bin/python -m pytest -c integrations/mcp/pyproject.toml integrations/mcp/tests -q`: **54 passed**, local route integration included; [output](publication-mcp.txt).
- Publication signature scan: 265 text files, no matching provider/GitHub/AWS/private-key signatures. Path guards separately exclude ignored local state. This is not a general secret-detection guarantee.

These are checkpoint checks. They do not complete Task 4 review or Task 5 acceptance.
