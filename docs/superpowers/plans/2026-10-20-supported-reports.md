# Supported Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task after plan review. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish only nonempty findings that preserve run-owned accepted claims, with auditable sources and no writer-authored factual prose.
**Architecture:** A pure reporting module validates ID selection and renders an artifact from a bounded input snapshot. The store captures that snapshot coherently and rechecks it with the assignment fence when publishing; the runner finalizes from the validated finding count.
**Tech Stack:** Existing Python/pytest/SQLite and standard-library JSON, dataclasses, hashing, HTML encoding and URL parsing; existing Node/marked/Playwright development dependencies for renderer verification. No new production dependency or schema.
**Spec:** [HIVE-003 revision 1](../specs/2026-10-20-supported-reports-design.md)
**Status:** In progress
**Plan revision:** 1
**Spec approval:** User, 2026-10-20: “Approve revision 1; write the plan.”
**Plan approval:** User, 2026-10-20: “Approve plan; subagent-driven execution—fresh implementer and reviewer for each task.”
**Execution method:** Subagent-driven; fresh implementer and reviewer for each task, then fresh whole-change review

## Global Constraints

- Policy version: `accepted-claims-v1`. The model selects IDs and order; code owns accepted-claim wording, headings, citations and sources. No prose salvage or ID-only fallback.
- Candidate facts: first **32** eligible rows in stable fact-ID order; record additional eligible rows as omitted. Selection: **16** unique IDs maximum, all from that snapshot.
- UTF-8 limits: claim **4 KiB**, source title **2 KiB**, source URL **4 KiB**, objective **4 KiB**; full serialized model input **64 KiB**, raw selection response **4 KiB**, rendered Markdown **128 KiB**. KiB means 1,024 bytes. Enforce the aggregate limits as well as the per-field limits.
- Empty/whitespace-only claims fail input validation. Normalize CRLF/CR to LF for display only; preserve other claim text. Never truncate a claim, synthesize a conclusion or mutate fact status to recover a report.
- Successful reports require at least one finding. Empty candidates skip the model call; empty selection is a no-findings result. Both finish `blocked`, without a report.
- Exactly `{"fact_ids": [...]}` is accepted. Reject duplicate JSON keys, extra fields, wrong types, duplicate/unknown IDs, code fences and trailing prose. Invalid selection rejects the whole response.
- One writer call per attempt through existing `workers`/`writer` routing and usage accounting; task-level bounded retries remain possible. No new entailment call or claim of model accuracy.
- Never hold a SQLite transaction across a model call. Publication rechecks the active assignment and selected claim/source snapshot atomically with result/completion.
- Same-run provenance only. Historical report bytes, legacy LangGraph and public report-string delivery stay compatible. `done_with_removals` remains readable historically, but this policy never produces it.
- No real-data migration, schema change, UI redesign, historical-report sanitizer, provider qualification, global reservation, Postgres, hierarchy or Jev implementation.
- Preserve existing dirty edits and branch `hive-001-002-integrity`. No staging, commits, pushes or deployments under this plan's current authorization. Obtain separate authorization before such actions.

## Review Focus

1. A claim containing `</span>`, fake citations, repeated whitespace, CRLF, RTL/CJK/emoji or a long unbroken token must remain literal and readable. Task 2 pins parser/DOM round trips and 390/1,440-pixel rendering checks.
2. A source revoked, rebound or corrupted between writer selection and publication must leave no result or completion behind. Task 3 uses separate file-backed SQLite handles and controlled mutation, including source metadata and quote changes.
3. Old helper calls must not bypass the reporting contract. Task 3 rejects generic writer publication; Tasks 4–5 retire `final_gate` and adapt diagnostic scripts without rewriting historical evidence.
4. Zero-findings or malformed output must not be confused with provider outages, factual rejection or candidate-window omission. Task 4 asserts distinct terminal gates, bounded retries and unchanged facts.
5. A renderer that passes Python string tests can still be interpreted differently by the shipped Markdown parser. Task 2 uses the locked `marked` package and browser DOM; missing dependencies are a required-check limitation, never a skip counted as success.

## Requirement Coverage

| Requirement | Tasks | Named acceptance oracle |
|---|---|---|
| REP-01 | 1, 3 | `test_snapshot_excludes_unaccepted_or_foreign_provenance`; candidate rows and count captured in one read transaction. |
| REP-02 | 1 | `test_selection_rejects_noncontract_json`; strict whole-response failures. |
| REP-03 | 1 | `test_selection_rejects_duplicate_unknown_or_excess_ids`; no partial salvage. |
| REP-04 | 2, 4 | `test_render_uses_only_selected_claims`; adversarial writer prose never appears in a successful run. |
| REP-05 | 2 | `test_marked_rendering_round_trip`; three fixed headings and exact literal claim text, with no injected elements. |
| REP-06 | 2, 3 | `test_sources_match_selected_findings`; `test_unsafe_url_is_inert`; pinned same-run source metadata. |
| REP-07 | 2, 4 | `test_empty_selection_blocks_run`; no report and zero findings, despite available sources. |
| REP-08 | 3 | `test_changed_snapshot_publication_is_atomic`; `test_stale_report_attempt_cannot_publish`. |
| REP-09 | 2, 3, 5 | `test_report_provenance_survives_reopen`; selected claim/source metadata and hashes persisted without raw source text. |
| REP-10 | 1, 2, 3 | `test_report_utf8_boundaries`; `test_candidate_window_is_stable`; aggregate input/output caps. |
| REP-11 | 4, 5 | Existing API/CLI/MCP suites plus `test_historical_report_read_is_unchanged`. |
| REP-12 | 4 | `test_writer_error_classification_preserves_facts`; execution failure is not a factual rejection or no-findings assessment. |

## Task 1: Strict report inputs and selection

**Create:** `app/hive/reporting.py`, `tests/test_hive_report_contracts.py`.
**Requirements:** REP-01–03, REP-10.

**Interfaces produced in `reporting.py`:**

- Frozen `WriterAssignment(task_id: str, worker: str, attempt: int, fence: int)`.
- Frozen `ReportFact(id: str, claim: str, evidence_id: str, source_id: str, title: str, url: str, claim_sha256: str, quote_sha256: str, evidence_sha256: str, binding_sha256: str)`.
- Frozen `ReportSnapshot(run_id: str, objective: str, candidates: tuple[ReportFact, ...], eligible_count: int, assignment: WriterAssignment | None = None)`.
- `ReportInputError(ValueError)`, code `report_input_invalid`; `ReportSelectionError(ValueError)`, code `report_selection_invalid`; `ReportSnapshotChanged(RuntimeError)`, code `report_snapshot_changed`. Error messages contain bounded reason codes, not raw input/model/evidence text.
- `snapshot_from_rows(run_id: str, objective: str, rows: list[dict], eligible_count: int, assignment: WriterAssignment | None = None) -> ReportSnapshot`. Each joined row has `id`, `run_id`, `status`, `claim`, `evidence_id`, `quote`, `evidence_run_id`, `source_id`, `title`, `url`, `text`. Both run IDs must match the argument and status must be `verified`; source text is hashed here and not retained in the snapshot.
- `writer_messages(snapshot: ReportSnapshot) -> tuple[str, str]`: system and user strings, with a JSON user object containing objective and `candidates: [{"id": ..., "claim": ...}]`. Measure the UTF-8 bytes of compact JSON serialization of the complete two-message array, including roles/content, against 65,536 bytes.
- `parse_selection(raw: str, snapshot: ReportSnapshot) -> tuple[str, ...]`: strict response validation, selection order preserved.

Constants copy the approved byte/count limits exactly. Candidate IDs are validated by exact snapshot membership, not a new hex-only rule: historical fixtures contain IDs such as `F-good`. Reject non-string or duplicate candidate identities. Snapshot `eligible_count` must be at least the candidate count, which cannot exceed 32. An empty candidate list is allowed.

Compute hashes from original UTF-8 bytes before display normalization. `binding_sha256` hashes compact, key-sorted JSON containing run ID, fact ID, raw claim, evidence ID, raw quote, evidence source ID/title/URL and evidence-text digest. The same function is used for publication rechecks. No `default=str` coercion. Reject fields that cannot be faithfully represented as UTF-8, including unpaired surrogates and NUL; reject non-string fields instead of converting `None` to text.

- [x] **RED:** Add `test_selection_rejects_noncontract_json` and `test_selection_rejects_duplicate_unknown_or_excess_ids` as parametrized tests. Assert the typed exception for fenced/trailing prose, duplicate object keys, arrays/scalars/null, `fact_ids` as a string, bool/non-string IDs, extra keys, valid-plus-forged IDs, duplicates and 17 IDs. Assert `parse_selection('{"fact_ids":[]}', snapshot) == ()`; 16 valid unique IDs retain order. Each test module constructs its snapshots through `snapshot_from_rows` using explicit joined-row fixtures, rather than reproducing hash logic in tests.
- [x] **RED:** Add `test_report_utf8_boundaries`: use multibyte strings to prove byte rather than character limits; test exact-limit and one-byte-over values for each field/response, plus 32 candidates versus 33 and a combined message array above 65,536 bytes. Input errors must occur before any caller dispatch. Add empty/whitespace-only claim and unsupported Unicode fixtures.
- [x] Run `DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_hive_report_contracts.py -q`; record failures for the missing contract, not fixture/import-environment problems.
- [x] Implement the frozen types, deterministic hash/input builder and strict parser. Use `json.loads` with duplicate-key rejection and nonstandard-constant rejection; do not reuse tolerant `app.llm.parsing.parse_json` or change its other consumers.
- [x] Run the same command; require all contract cases green. Review this module's interface before adding rendering.

## Task 2: Deterministic literal-text renderer and provenance

**Modify:** `app/hive/reporting.py`.
**Create:** `tests/test_hive_reports.py`, `web/scripts/check-hive-report.mjs`.
**Requirements:** REP-04–07, REP-09/10.

**Consumes:** Task 1's types, selection validator, hashes and limits.
**Produces:** `render_report(snapshot: ReportSnapshot, fact_ids: tuple[str, ...]) -> tuple[str, dict]`. Revalidate selection membership/count here as well; direct callers cannot bypass parser validation. No input mutation or network access.

Use fixed Markdown headings `# Research report`, `## Findings`, `## Sources`. For data-bearing content, emit code-owned HTML list/paragraph wrappers inside Markdown, with `html.escape(value, quote=True)` for every textual field and URL attribute. Literal claim spans use static `white-space: pre-wrap; overflow-wrap: anywhere` styling, preserving spaces/newlines while allowing narrow-screen wrapping. No untrusted value enters tag names, attribute names, styles or structure. This retains ordinary paragraph/list typography, without code-block formatting or frontend stylesheet changes.

Each selected finding uses one literal claim span and a code-owned citation link. Use ordinal anchors `hive-source-1`, `hive-source-2`, etc.; never interpolate a fact ID into an HTML attribute. Source labels/citation text are escaped. Selected order controls findings and references; distinct claims sharing evidence still get distinct reference entries. Show the objective in a labeled literal-text paragraph.

For active source links, require absolute `http`/`https`, a valid nonempty hostname and valid port, no credentials, whitespace/control characters, backslashes or percent-encoded controls. Invalid URLs are displayed in escaped literal spans with one `unsafe_source_url` warning per selected fact; no dereferencing. Do not add external-link target behavior.

Gate fields: `policy_version`, `passed`, `finding_count`, `selected_fact_ids`, `candidate_count`, `eligible_count`, `omitted_count`, `warnings`, `provenance`, `writer_assignment`, compatibility `sentences` and `removed_uncited_or_unverified`. `provenance` contains selected IDs, raw accepted claim, evidence ID, source ID/title/URL and the four Task 1 digests. No raw quote or evidence text. Warnings are code/fact-ID objects, bounded to 16 entries; never raw model output. Candidate omissions equal `eligible_count - candidate_count` and are not removals.

Empty candidates return `("", gate)` with `reason="no_verified_facts"`; nonempty candidates and empty selection return the analogous `no_selected_findings`. Both have `passed=false`, zero counts, empty references/provenance. Nonempty valid selection sets `passed=true`, `sentences=finding_count`, `removed_uncited_or_unverified=[]`; no success reason is needed. Enforce the 131,072-byte output cap after full escaping/assembly, without truncation.

- [x] **RED:** Add `test_render_uses_only_selected_claims` and `test_sources_match_selected_findings`. Given accepted “Caching cut calls by 40%.” and an unselected second claim, assert the exact first claim and only its citation/source occur; no reversed number, inferred sentence, extra heading or unused source. Assert `gate["finding_count"] == gate["sentences"] == 1`, `gate["selected_fact_ids"] == [selected_id]`, and `gate["removed_uncited_or_unverified"] == []`. Add shared-evidence and legacy-ID cases.
- [x] **RED:** Add `test_unsafe_url_is_inert` and output-bound tests. Exercise script/data/file/protocol-relative URLs, credentials, controls, quotes, malformed ports/hosts and backslashes; valid HTTP(S) links remain links, unsafe strings remain data with warnings. Test escaping expansion above 128 KiB even when every raw field passes its own limit.
- [x] Run `DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_hive_reports.py -q`; capture intended RED results, then implement `render_report` and require pure rendering cases green.
- [x] Add `test_marked_rendering_round_trip` invoking `node web/scripts/check-hive-report.mjs` via subprocess with JSON on stdin. The script imports the project's `marked` and `playwright`, parses each generated report and loads that output in a network-blocked Chromium page. Assert claim span `textContent` equals the original after CRLF/CR normalization; headings are exactly the three fixed labels; only expected citation/source anchors exist; no attacker-supplied image/script/style/event attributes exist. Verify fake citations, HTML closing tags, Markdown links/headings, ampersand entities, leading/trailing/repeated whitespace, CJK/RTL/emoji and long tokens. Handler errors and network requests fail the check.
- [x] Install only locked frontend dependencies when executing, if needed: `npm --prefix web ci --ignore-scripts`. Current planning environment has no `web/node_modules`. If Chromium is absent, provision the locked Playwright Chromium for these tests or record this required check as blocked; do not count it as a passing skip. No installation occurs during plan authoring.
- [x] Run `DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_hive_report_contracts.py tests/test_hive_reports.py -q`; require parser/DOM cases to run. In the script also inspect rendered findings at 390×844 and 1,440×900, verify no horizontal overflow and capture representative screenshots under `docs/reports/hive-003/`. Review captures before claiming rendering verified. These are generated-report fixture checks, not whole-console or historical-sanitizer verification.

## Task 3: Coherent snapshot and atomic report publication

**Modify:** `app/hive/store.py`, `tests/test_hive_evidence.py`.
**Create:** `tests/test_hive_report_store.py`.
**Use unchanged:** `tests/hive_testkit.py` frozen legacy fixture and existing HIVE-001/002 fencing tests.
**Requirements:** REP-01, REP-06, REP-08–10.

**Consumes:** Task 1 snapshot builder/types/digest rules; Task 2 renderer.
**Produces on `HiveStore`:**

- `report_snapshot(run_id: str, objective: str, *, assignment: WriterAssignment | None = None) -> ReportSnapshot`.
- `publish_report(task_id: str, worker: str, attempt: int, fence: int, snapshot: ReportSnapshot, report: str, gate: dict, *, now: float | None = None) -> bool`.

Snapshot capture uses the existing connection lock and a short read transaction: count eligible same-run verified facts with same-run evidence, then fetch the first 32 joined fact/source rows ordered by fact ID. Commit the read before model dispatch. Build immutable values/hashes outside the transaction. Assignment may be absent for direct read-only `run_writer` consumers; actual publication requires a complete matching `WriterAssignment`.

Publication uses `BEGIN IMMEDIATE`. First apply existing `_holds`; stale assignment returns false before validating caller content. Require task kind `write`, matching run and assignment identity. Recheck each selected fact is still verified and its binding digest matches current same-run joined rows. Missing/mutated rows raise `ReportSnapshotChanged` and roll back. Unselected facts changing do not invalidate selected findings; candidate-window metadata records the original capture. Do not claim future revocation handling after publication.

Recompute the deterministic renderer from the captured snapshot and selected IDs, and compare supplied report/gate to its output. Mismatches raise `ReportInputError`; persist only recomputed output in the existing result JSON. Within the same transaction, complete the task or roll back everything. `publish` must reject attempts to complete `write` tasks through its generic path after applying the stale-assignment check; `set_fact_status` must remain limited to verifier tasks so it cannot become an alternate writer completion path. Wrong-kind publication raises existing `TaskGraphError`. Malformed current rows during snapshot recheck are classified as `ReportSnapshotChanged`, rather than masking the mutation as a new model-input failure. Extract a small internal transaction-local completion helper if necessary; never nest public publication methods or reacquire the non-reentrant lock.

- [x] **RED:** Add `test_snapshot_excludes_unaccepted_or_foreign_provenance`, `test_candidate_window_is_stable` and `test_snapshot_read_is_coherent`. Use file-backed databases, distinct runs and a barrier-controlled second connection. Enable WAL only in the temporary coherence fixture so a second connection can commit during the first read without a lock/barrier deadlock; no runtime journal-mode change is proposed. Assert count/candidates come from one SQLite read snapshot, 33 eligible rows produce 32 stable candidates plus one omission, and missing/foreign/proposed/rejected rows never enter the candidate set. Assert no open transaction remains before a mocked model awaits.
- [x] **RED:** Add `test_changed_snapshot_publication_is_atomic`, parametrized for changed claim, quote, evidence binding/content/title/URL, revoked status, removed selected fact/source and mismatched run/assignment. Raw SQL mutation is test-only fault injection. Assert typed failure and no new result, completion or report writes. Add `test_unselected_fact_change_does_not_block_report`.
- [x] **RED:** Add `test_stale_report_attempt_cannot_publish`, `test_generic_publication_cannot_complete_writer`, `test_verifier_publication_cannot_complete_writer`, `test_forged_report_body_is_rejected` and `test_report_provenance_survives_reopen`. Assert stale publication returns false without side effects; a fresh valid assignment publishes once; replay cannot overwrite; reopening shows exact selected metadata/hashes and no duplicated raw source text. On rejected live publication assert `store.get_task(task_id)["status"] == "claimed"` and `store.get_task(task_id)["result"] is None`. Current schema version must remain unchanged.
- [x] Run `DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_hive_report_store.py -q`; capture meaningful failures before implementing the store methods/guards.
- [x] Implement snapshot capture, fenced revalidation and publication as above. Catch exceptions to roll back all writes, preserving the HIVE-001/002 transactional behavior. Update the test-only `claimed` helper in `tests/test_hive_evidence.py` to accept `kind="research"`; its verifier-promotion test must explicitly pass `kind="verify"`. Preserve the existing missing-provenance rollback assertion so the new role guard cannot mask it.
- [x] Run `DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_hive_report_store.py tests/test_hive_evidence.py tests/test_hive_execution.py tests/test_hive_migrations.py -q`. Require store tests green. Execution ruling: the strict generic-writer guard intentionally precedes Task 4 runner integration, so record any intermediate old-writer success failures explicitly (anticipated renewal/lease-loss full-run cases); never classify them as passing. Task 4 must restore them before integrated acceptance. Preserve orphan exclusion/historical-byte checks and research/verifier publication behavior.

## Task 4: Writer/runner integration and explicit outcomes

**Modify:** `app/hive/agents.py`, `app/hive/runner.py`, `tests/test_hive.py`, `tests/test_hive_evidence.py`, `tests/test_api_research.py`.
**Create:** `tests/test_hive_report_execution.py`.
**Requirements:** REP-04, REP-07–09, REP-11/12.

**Consumes:** Tasks 1–3 contracts.
**Produces:**

- `run_writer(store: HiveStore, run_id: str, objective: str, call: Caller, *, snapshot: ReportSnapshot | None = None) -> tuple[str, dict]`. Preserve positional callers; use the provided snapshot or capture a read-only one. Reject a provided snapshot with mismatched run/objective. Empty candidates return the renderer's no-findings result without dispatch. Otherwise call existing `workers`/`writer` route with `writer_messages`, `max_tokens=512`, then strict parse/render.
- Executor captures `WriterAssignment(tid, name, att, fence)`, obtains a bound snapshot, calls `run_writer(..., snapshot=snapshot)` and commits with `publish_report`. No generic writer completion call remains.
- Runner recognizes typed report error codes. Input/selection errors are nonretryable invalid output; snapshot changes use existing bounded retry policy; transport errors retain existing classification. Never log raw failing selection/source content in exception strings/events.

Replace writer instructions with the strict selection schema, keeping the `writer symbiote` identity for existing routing fixtures. Remove `_CITE`/`final_gate`; no semantic safety API taking only an ID set remains. Keep shared tolerant `parse_json` behavior for other roles/legacy consumers.

Update `make_handler` in `tests/test_hive.py` to parse the JSON writer user payload and return selected IDs. Replace the `uncited` behavior case with explicitly malformed writer output; preserve coverage that unsupported prose cannot appear. Update the API's local mock handler similarly. Update the migrated `F-good` direct writer fixture and assert additive no-findings metadata without deleting its original evidence-eligibility assertions.

Finalization copies only the committed artifact. Valid policy + `passed=true` + positive integer finding count + nonempty report finishes `done`. A committed no-findings gate finishes `blocked` with empty report and preserves `no_verified_facts`/`no_selected_findings`. Any inconsistent artifact fails closed with `report_artifact_invalid`. Exhausted writer execution remains causally blocked under HIVE-002; its typed task error must remain inspectable. Never emit new `done_with_removals` results.

- [ ] **RED:** Add `test_empty_selection_blocks_run`, `test_no_candidates_skips_writer`, `test_writer_prose_cannot_be_salvaged` and `test_valid_selection_finishes_with_exact_claim`. Empty selection must assert `result.status == "blocked"`, `result.report == ""`, `result.gate["finding_count"] == 0`, `result.gate["reason"] == "no_selected_findings"`. Also assert writer-route call count and unchanged verified/rejected fact counts. Parametrize prose rejection with unsupported heading, changed entity/number/relation, citation-only text and valid JSON plus trailing text.
- [ ] **RED:** Add `test_writer_error_classification_preserves_facts`: malformed response exhausts once as `report_selection_invalid`; transport outage retries within `max_attempts`; deadline stops within configured bounds; late output cannot publish. Add `test_snapshot_change_retries_with_fresh_inputs`, invalid committed-artifact defense and cancellation cleanup checks with no surviving `hive:` tasks.
- [ ] Run the full mock execution cases against the old path before switching the implementation: `DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_hive_report_execution.py -q`. Record behavioral RED evidence separately from tests requiring new interfaces.
- [ ] Integrate `run_writer`, assignment-bound publication, typed error classification and finalization. Update the enumerated fixtures; retain original fact/evidence and route-selection assertions. Replace the old sentence-stripping test with a whole-selection-rejection assertion.
- [ ] Run `DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_hive.py tests/test_hive_evidence.py tests/test_hive_execution.py tests/test_hive_report_contracts.py tests/test_hive_reports.py tests/test_hive_report_store.py tests/test_hive_report_execution.py -q`. Require all affected checks green; do not loosen assertions to accept zero-finding success.

## Task 5: Surface compatibility, review and delivery evidence

**Modify:** `tests/test_hive_cli.py`, `tests/test_api_research.py`, `docs/reviews/reproduce_hive_reports.py`, `docs/reviews/reproduce_hive_gaps.py`, `docs/reviews/reproduce_hive_evidence.py`; integration fixture files only if fresh checks identify a dependency on the old writer format.
**Create:** `docs/reports/hive-003/summary.md`, `verification.json`, `review.md`, `execution-ledger.md` and exact command-output logs within that directory.
**Update on delivery:** this plan; HIVE-003 spec/index; `docs/reports/problems-and-fixes.md`, `docs/reports/hive-003-scoping.md`, `ARCHITECTURE.md`, `docs/architecture/implemented-foundation.md`; source graph/provenance under `graphify-out/` and `docs/knowledge-graph.md` following their existing refresh procedure.
**Requirements:** REP-09/11 and complete REP-01–12 traceability.

Public compatibility boundary: HTTP and MCP currently expose report strings but do not project run `gate` as a public top-level field; CLI and direct `HiveResult` do expose gate metadata. Preserve existing surface shapes; verify new provenance by stored run/task JSON and direct/CLI results. Do not quietly add a new API projection as part of report construction. Historical gate/report values remain fetchable as before.

- [ ] Extend API/CLI compatibility tests with `test_historical_report_read_is_unchanged`, empty-selection `blocked`/empty report and valid generated report cases. Assert existing response keys/citation/source behavior, CLI JSON summary/gate, stored policy/provenance and exact historical bytes: `body["report"] == historical_report` and `summary["gate"]["policy_version"] == "accepted-claims-v1"` for a new successful CLI run. Route fixtures keep disposable stores and mock boundaries; never open `app_data`.
- [ ] Run `DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_hive_cli.py tests/test_api_research.py -q`; require compatibility GREEN. These checks may already pass after Task 4; do not manufacture a RED result. If a defect is found, capture its failing assertion before the smallest fixture/adapter repair and verify GREEN. No production API/CLI/MCP change is expected; any contract change returns to spec review.
- [ ] Adapt diagnostic scripts to the new public seam: report current unsafe-payload rejection and supported rendering through `run_writer`/reporting rather than importing retired `final_gate`. The gaps script must preserve its other probes. Update the evidence probe's mock selection response. Preserve the dated baseline JSON byte-for-byte; put new observations in `docs/reports/hive-003/`, clearly separated from acceptance tests.
- [ ] Run focused acceptance: `DEBUG=false /opt/anaconda3/bin/python -m pytest tests/test_hive.py tests/test_hive_migrations.py tests/test_hive_evidence.py tests/test_hive_execution.py tests/test_hive_cli.py tests/test_hive_report_contracts.py tests/test_hive_reports.py tests/test_hive_report_store.py tests/test_hive_report_execution.py tests/test_api_research.py -q`. Require zero affected failures and required renderer cases executed.
- [ ] Run MCP compatibility: `HIVE_APP_PYTHON=/opt/anaconda3/bin/python integrations/mcp/.venv/bin/python -m pytest -c integrations/mcp/pyproject.toml integrations/mcp/tests`. Require the real-route fixture to run, not skip; classify any loopback permission failure separately and rerun with permitted local sockets if needed.
- [ ] Run `npm --prefix web run lint`, `npm --prefix web run build` and `DEBUG=false /opt/anaconda3/bin/python -m pytest -q`. Record actual results. Previously recorded embedding import incompatibility, absent Anthropic SDK and socket restrictions are starting clues, not assumed current outcomes; affected-path failures block delivery. Do not hide full-suite failures or claim production readiness.
- [ ] Invoke `requesting-code-review` for one fresh whole-change reviewer after focused acceptance. Supply approved spec/plan, existing-dirty-change boundaries, failure matrix and command evidence. Fix accepted material findings with their own meaningful RED/GREEN regressions; repeat only checks justified by resulting changes. Do not stage unrelated prior work. Native execution includes this independent final review; no per-task delegation is required.
- [ ] Refresh the installed Graphify code-only snapshot after final source changes; load its skill, follow `docs/knowledge-graph.md`, regenerate provenance/query/health outputs and inspect the graph HTML. No semantic labeling/model calls. Treat graph relationships as navigation, not proof of report safety; keep archived architecture diagrams explicitly source-pinned unless separately updated.
- [ ] Complete evidence ledger and REP-01–12 mapping, check document links and runtime fingerprints, then update statuses only from observed results. F3/F3-A/B/C can become Verified when their owning checks pass; F3-D remains Scoped under HIVE-005. Record publication-time guarantee and post-publication-revocation exclusion. No HIVE-003 Verified claim with a missing required parser/store/execution/compatibility check.

## Verification Record

| Date / environment | Check | Observed result | Limitations |
|---|---|---|---|
| 2026-10-20, plan authoring | Current source, spec, fixture and consumer inspection | Identified exact writer/store/runner seams; HTTP/MCP gate projection distinction; legacy `F-good` fixture and old helper imports. | Read-only; no HIVE-003 implementation or acceptance run. |
| 2026-10-20, plan authoring | Dependency-path check | `web/node_modules` absent; existing MCP virtualenv present. | Parser/browser checks require declared frontend dependencies at execution; no packages installed now. |

Planned commands above have not been executed as HIVE-003 acceptance checks. Existing [diagnosis](../../reports/hive-003-scoping.md) proves defects, not fixes. Planning verification and self-review receipts are recorded in [the handoff report](../../reports/hive-003-plan-review.md).

## Handoff

Spec revision 1 approved on 2026-10-20 by the explicit reply quoted in the header. Plan revision 1 approved on 2026-10-20; user selected subagent-driven execution. Implementation now follows the task gates below. No design behavior changed during planning; interfaces and encoding are implementation choices within the approved literal-text and bounded-selection contract.

Self-review covers all 12 requirements, matching type/function names across five tasks, count/byte limits, transaction scope, zero-findings finalization, current fixture compatibility and the five Review Focus failure classes. UI skills applied only to the rendering contract: Impeccable `harden` and Emil guidance favor readable wrapping, literal text and no truncation; no interface redesign was performed.

Original recommendation was **native execution**: tasks share one reporting interface and one transaction seam, so serial implementation avoids concurrent edits; one fresh final reviewer checks the completed change. User may instead select subagent-driven execution with a fresh implementer/reviewer per task, subject to host permissions. Plan review and method selection are required before implementation by the repository workflow and Superpowers `writing-plans` handoff.

Execution update: user selected subagent-driven execution after reviewing this plan. That choice supersedes the recommendation; no task implementation may replace its fresh task review with implementer self-review.


### Publication checkpoint — 2026-10-21

Tasks 1–3 completed their task reviews; Task 4 implementation and focused checks exist but its independent review hit the model usage limit. Task 5 has not been completed. The detailed [execution ledger](../../reports/hive-003/execution-ledger.md) records observed task evidence. User subsequently authorized scoped commits and push. This publishes an In progress checkpoint, not verified delivery; task checkboxes above remain conservative until final reconciliation.
