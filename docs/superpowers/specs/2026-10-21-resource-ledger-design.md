# Integrated resource admission, token ledger and shared queues

**Spec ID:** HIVE-004-A
**Status:** Spec approved, revision 2
**Date:** 2026-10-21
**Owner:** Project maintainer
**Approval:** Revision 2 approved by user on 2026-10-21: “Approve revision 2; write the plan.” Revision 1 was not approved.
**Depends on:** HIVE-001/002/003; implements the local integrated portion of HIVE-004
**Plan:** [Integrated implementation plan](../plans/2026-10-21-resource-admission.md), approved 2026-10-22; execution in progress

## Intent and scope revision

Prevent task-based agents from multiplying model calls, queues or spending authority. A run receives a token allocation. Every planner/researcher/verifier/writer call waits for shared capacity, reserves allowance and records dispatch intent before contacting its provider. Unknown external work stays charged. Branch allocations divide authority rather than creating it.

The user requested both changes after reviewing revision 1: “Broaden to shared concurrency limits and queues” and “Include current Caller/provider integration immediately.” Therefore the first delivery now includes the ledger, live Hive integration, existing provider adapters, shared run/call admission, bounded fair queues and required SQLite lifecycle repairs. No library-only delivery counts as completion. The filename remains stable to preserve existing review links; this revision replaces the standalone-only scope.

**Deployment boundary:** one trusted local host, multiple API/CLI/worker processes sharing one canonical Hive SQLite file and one persisted resource-policy identity. `global` means all governed Hive work in that deployment. Separate databases are separate deployments. Network-filesystem SQLite, multi-host execution, account-wide limits across unrelated applications and the legacy LangGraph path are excluded. Postgres execution/resume remains HIVE-006. Financial pricing, caller authentication, hierarchy creation and Jev selection remain their owning specs.

## Existing flow and evidence

[Scoping report](../../reports/hive-004/scoping.md) traces `run_hive → Caller → LLMRouter → provider → record_usage`. Caller tests past successful usage; it does not reserve before dispatch. Preserved offline evidence: allowance 100, spent 400. API creates a new BackgroundTasks run per request. Router retries=0 leaves SDK-internal policies uncontrolled. A separate SQLite reader can defeat existing watchdog/abort commits (F3-J).

[Current MCP adapter](../../../integrations/mcp/src/hive_mcp/api.py) requires POST status `running`; existing GET/CLI reports and HIVE-003 publication contracts must remain compatible. [Schema v1](../../../app/hive/schema.py) validates an exact database shape, so additional resource tables require an explicit schema v2 upgrade, not silent startup DDL or an unrelated side database.

## Approaches and decision

| Approach | Benefit | Rejection / trade-off |
|---|---|---|
| Process semaphores and post-call usage | Minimal edits | Processes do not share limits; no conserved inherited allowance or crash accounting |
| Integrated local admission module in the existing Hive database | One ACID authority for runs, reservations, permits and usage; exercises real Caller/provider seams now | Explicit v2 maintenance migration, more compatibility tests, local-host scope |
| Full Postgres scheduler and distributed runtime immediately | Cross-host coordination | Pulls HIVE-006 resume/manifest infrastructure into this delivery without a requested cross-host target |

Choose integrated local admission. Apply Matt's deep-module design: callers learn a small async submission/completion interface; allocation arithmetic, permit ordering, retry classification and transactional state remain local to the resource module. Apply Stripe-inspired invariant and failure testing without claiming current Stripe internals.

## Modules and execution flow

| Module / proposed seam | Responsibility | Consumers and real dependencies |
|---|---|---|
| Resource store, under `app/hive/` | Versioned allocations, call states, permits, FIFO sequence and fairness cursors; immutable policy/profile snapshots | Shared Hive SQLite transactions; no provider I/O or await inside transactions |
| Admission service, under `app/hive/` | `submit_run`, `wait_run`, `complete_call`, `inspect`; bounded waiting, scheduling and supervision | API, CLI, direct Hive runner and Caller; injected clock/adapter for tests |
| Governed provider dispatch, at `app/llm/` seam | Resolve pinned route, prepare/fingerprint request, enforce SDK single attempt, normalize all charge categories and outcome certainty | Existing OpenAI/Anthropic/Gemini/Ollama/mock adapters; legacy ungoverned entrypoint compatibility |
| Existing runner/store | Task execution and fenced facts/report publication; bounded contention-safe lifecycle writes | Admission ticket and run ownership; HIVE-003 report logic retained |
| API/MCP/CLI projections | Queue/admission status, actual vs held usage and typed overload outcomes | Existing HTTP report contracts, MCP client validation and CLI JSON |

Exact new file names and task grouping belong in the implementation plan. Do not introduce an adapter framework for hypothetical providers.

1. Validate request, policy identity and pinned route-profile eligibility. In one transaction create the run, root allocation and queued admission row. Queue-full rejection creates none of these.
2. A lifespan-managed scheduler claims a queued run when a shared active-run slot is available. Other processes contend on the same state; one run receives one coordinator fence. No worker pool is created while queued. Direct run_hive without an injected store uses the deployment database, matching API/CLI; explicit temporary/in-memory stores are isolated test/development deployments and cannot claim shared production limits.
3. The runner calls the existing Caller interface. Caller supplies run/role/task-attempt identity and its live guard to `complete_call`; the planner has its own run-scoped identity/deadline. All current Hive model roles use this seam.
4. Prepare the exact request, pin provider/model/profile and output cap, validate context/bound/mode, then enqueue metadata. No token hold or call permit is consumed while merely waiting.
5. Fair admission atomically reserves tokens and all global/run/provider permits. Revalidate live run/task authority and deadlines before committing dispatch intent, then recheck the local monotonic deadline immediately before invoking the adapter. Admission never holds a database transaction across network work.
6. A complete receipt atomically settles usage, releases terminal permits and projects known usage once. A timeout/cancellation or incomplete receipt preserves the relevant unknown charge and, when external termination is unproved, its permits. Late receipts update the original identity; they cannot publish stale task/report output.
7. Run termination cancels queued/undispatched work and releases only proven unused authority. Remaining external uncertainty remains visible after the run is terminal.

## Ledger requirements

| ID | Observable contract | Acceptance oracle |
|---|---|---|
| LED-01 | Positive integer limits/bounds; nonnegative integer actuals; explicit nonempty IDs. Reject bools, invalid references and overflow before mutation. | Invalid inputs and signed-64-bit aggregate boundaries leave all balances unchanged; no float promotion. |
| LED-02 | Roots/grants are idempotent by identity and immutable input. Child grants partition parent allowance; hierarchy cannot cycle or cross roots. | Separate processes contend for grants; accepted total never exceeds available parent authority; changed replay conflicts. |
| LED-03 | A unique transport-attempt call ID binds allocation, run/task attempt and fence, exact request fingerprint and pinned route/profile/mode. Fingerprints cover canonical messages and generation parameters, excluding credential values. Reserve before every provider send. | Concurrent full Caller calls cannot exceed admitted bound; changed identity replay conflicts; no unreserved send. |
| LED-04 | Legal states: queued → reserved → dispatched → settled/unknown; queued → cancelled/expired; reserved → released; unknown → settled. No release after dispatch. | State/race matrix including release vs dispatch; only first dispatch transition authorizes send. |
| LED-05 | Dispatched/unknown holds survive timeout, cancellation, process death and reopen. Task/run lease expiry never manufactures headroom. | Kill/reopen with pending external work; new admissions remain charged; inspect original identity. |
| LED-06 | Complete normalized usage and receipt provenance settle exactly once. Equal replay is harmless; conflicting replay is explicit. Missing categories remain unknown rather than zero. | Late/duplicate/reordered receipts preserve exact totals and one legacy usage projection. |
| LED-07 | Usage below bound returns unused allowance. Overrun records the full measured total, exposes debt and freezes new grants/calls throughout the root. | Child/sibling admissions stop after overrun; existing calls may still reconcile; estimates never replace actuals. |
| LED-08 | Close allocations only without held calls/open children; retain spent cost, return only genuinely unused grant; never reopen closed authority. | Nested close/replay and unknown-child tests preserve conservation. |
| LED-09 | Finite contention waits return typed busy errors without partial mutation; other storage errors stay distinct. Retry whole idempotent operation within remaining deadline. | Real reader/writer locks, retry and rollback checks; no invalid ROLLBACK or changed connection timeout. |
| LED-10 | Schema v2 stores admission and accounting in the same authoritative Hive database. Historical evidence/facts/reports/events/usage remain unchanged. | Explicit stopped-writer migration, interruption rollback, schema validation/reopen and byte/count reconciliation. |

For allocation `a`, `own(a)` sums reserved/dispatched/unknown bounds and settled actual usage; released/cancelled/expired calls contribute zero. `used(a) = own(a) + sum(contribution(child))`. An open child contributes `max(child.limit, used(child))`; a closed child contributes `used(child)`. `available(a) = max(0, a.limit - used(a))`; `debt(a) = max(0, used(a) - a.limit)`. Queued calls have no hold. All relevant decisions serialize in one transaction. Overrun freezes the root for this version; no automatic unfreeze or mutable billing correction.

Example: root 100 grants branch 60, leaving 40 at root. Branch holds 50, leaving 10 within that grant; parent still charges 60. Receipt 30 frees 20 inside branch. Closing branch returns its remaining unused 30, leaving root 70 available and 30 spent. A receipt 80 against bound 50 retains actual 80, exposes branch debt 20 and freezes the root.

## Shared capacity and queue requirements

| ID | Observable contract | Acceptance oracle |
|---|---|---|
| ADM-01 | All API, CLI and direct Hive runs in one deployment share persisted active-run/global/run/provider ceilings. Every Hive model role is included, including planner. | Simultaneous entrypoints in separate processes observe maxima no greater than each configured ceiling. |
| ADM-02 | Run queue is durable and bounded, separate from active-run slots. Accepted requests do not create workers until activation. | Saturate active slots and pending capacity; next submission is rejected with no orphan run/allocation or background task. |
| ADM-03 | Call queues are bounded globally and per run; admission acquires every needed permit and token hold atomically or none. | Flooded run receives typed queue-full result; no partial permit acquisition/deadlock or pre-queue token hoarding. |
| ADM-04 | Run activation uses FIFO acceptance sequence. Call admission rotates eligible runs, then eligible allocations within a run, with FIFO among eligible calls in each allocation. Fresh arrivals cannot jump waiting eligible work. | Barrier-based multi-run/branch tests: with N continuously eligible run queues, each receives a turn within N successful grants; analogous bound within each run. |
| ADM-05 | Provider-blocked work cannot block eligible work for another provider. Token-exhausted/expired/stale work is rejected rather than queued indefinitely. | Outage/saturation of provider A leaves B dispatchable; expired or insufficient-budget head entries cannot stall peers. |
| ADM-06 | Queue wait has a finite deadline bounded by caller/run/task deadline. Cancellation before dispatch removes queue entry/releases only undispatched holds. | Controlled time plus actual cancellation; zero provider sends for expired/cancelled queued work. |
| ADM-07 | Ownership expiry can reclaim queued/undispatched work, but dispatched permit occupancy persists until terminal external evidence. Usage certainty and execution certainty are separate. | Dead owner/new fence cannot reuse an uncertain call's permits. Terminal response with unknown usage frees capacity but retains token hold. |
| ADM-08 | Finite run-owner heartbeat/fence prevents duplicate coordinator launch and stale new admission. Restart can launch never-started queued runs with persisted replayable inputs; active interrupted runs are stopped, not replanned/resumed. | Two schedulers claim one run once; kill owner; stop/reconcile active run, preserve unknown calls, continue eligible queued runs. |
| ADM-09 | One immutable deployment policy identifies ceilings/profile versions. Processes with a different policy or unsupported SDK version fail admission explicitly. | Competing configuration hashes cannot create independent permit pools or silently raise ceilings. |

Queued runs persist the exact serializable invocation options and original expiry. An injected nonserializable dependency (for example a direct-call search callable) binds the request to its originating process; loss of that owner stops it explicitly instead of substituting a different adapter. No callable serialization framework enters this scope.

The shared store holds admission sequence/cursors and permit occupancy. Queue waiters may poll boundedly with jitter; polling itself is not admission. A transaction may grant only the next eligible identity. Waiter heartbeats/expiry prevent a dead head from blocking indefinitely. No requirement promises wall-clock fairness while SQLite is unavailable or permits remain externally uncertain; saturation and unknown-held capacity are observable outcomes.

`global_active_calls` measures provider requests, not idle Python workers or retrieval requests. Active-run and per-run worker limits separately bound spawned Hive workers. All keys needed by a request are acquired together; no hold-and-wait across provider/global/run permit pools.

## Caller/provider and budget-mode requirements

| ID | Observable contract | Acceptance oracle |
|---|---|---|
| CAL-01 | Existing Hive Caller always uses governed completion; API, CLI and direct run_hive cannot bypass it. No caller-specific independent semaphore or post-call-only fallback. | Planner/researcher/verifier/writer integration traces show queued → reserved → dispatched and identical admission authority. |
| CAL-02 | `hard` token mode requires a versioned qualified upper bound for exact prepared input plus every bounded output/charge category, and complete receipt normalization. Unknown/unsupported profile denies before dispatch. | Boundary/missing-profile/context/output tests produce zero sends; mocked qualified profile demonstrates cap conservation. |
| CAL-03 | Explicit `estimated` mode can use conservative heuristics but is labelled soft in every admission/inspection result. It still shares queues/permits and reserves estimates. Never silently downgrade hard mode. | Unqualified route runs only with explicit estimated selection; overrun freezes root, no hard-token claim. |
| CAL-04 | Governed adapter invocation has exactly one transport attempt: disable SDK/router retries and automatic request replay/redirect as required. Existing runner owns bounded task retries with backoff/jitter; each actual retry has a new charged call identity. Planner gets one attempt. | Fake transports count requests under 429/5xx/timeout; no multiplication of task/router/SDK retries; total task attempts remain existing max_attempts. |
| CAL-05 | OpenAI, Anthropic, Gemini, Ollama and mock seams receive explicit output cap and remaining call timeout; normalize route/category/request provenance. Unsupported controls/profile versions fail closed. | Provider transport fixtures plus pinned SDK configuration checks; timeout units/zero-retry semantics verified per SDK. |
| CAL-06 | Pre-dispatch validation failure releases only proven unsent work. Sent-but-ambiguous work retains token/permit debt as appropriate; cancellation never implies remote cancellation. | Timeout/connection reset/cancellation/crash/late response cases preserve original reservation and prevent stale output publication. |
| CAL-07 | Admission errors remain typed operational outcomes, distinct from factual rejection and empty findings. Budget/queue/profile failure cannot trigger an ungoverned planner fallback. | No false fact rejection or report success on denied dispatch; existing lease/deadline/report gate behavior preserved. |

A route profile pins provider endpoint identity, model/version, SDK/control version, tokenizer/counting method, request/context/output limits, normalized charge categories and qualification evidence. Bounds are computed without ungoverned network preflight calls: a profile must supply a local qualified counting/bounding method. An approximate character count cannot qualify hard mode. No real provider is declared qualified merely because an SDK field exists. Hard mode defaults on; local development can explicitly choose estimated mode in API/CLI/MCP/direct-call options. Existing requests retain their shape but may now be denied for an unqualified route; setup and tests must document this intentional behavioral tightening. The first live call remains an explicit user/operator action, not a validation side effect.

Calls awaiting a permit have no network-side effect. Once dispatch intent commits, crash-before-send remains conservatively uncertain; no exactly-once remote execution promise. A local timeout is not a remote termination receipt. Without qualified terminal evidence, hold the permit indefinitely and expose degraded capacity; do not invent a safe quarantine duration from the SDK timeout. A late complete receipt may release holds after the run is terminal. This can favor safety over availability and must remain visible.

For task retries, the runner remains the sole transport-retry owner. An adapter/dispatcher performs zero hidden retries. Retryable outcomes and jittered backoff are bounded by remaining run/task deadline and existing max_attempts; queue exhaustion/configuration errors are not network retries. Semantic verifier iterations are distinct call identities within the same task allowance, not invisible transport retries. No task or model can increase its allocation or configured limits.

## Public contracts and integration requirements

| ID | Observable contract | Acceptance oracle |
|---|---|---|
| INT-01 | POST remains 202 with existing `run_id` and `status: running`; additive `admission.state` distinguishes queued/active. GET keeps report/facts/tasks/events and adds admission/resource inspection. | Existing MCP start validation and historical report byte-read checks pass; queued runs are visible with no worker/task creation. |
| INT-02 | Immediate queue-full uses HTTP 429 with Retry-After and stable `resource_queue_full`; transient admission-store busy uses 503. Unsupported hard profile/config uses 422. No accepted-run claim before atomic enqueue commit. | HTTP/MCP/CLI tests distinguish rejected vs ambiguous submission; no automatic POST replay. Request idempotency remains HIVE-009. |
| INT-03 | Known actual tokens, reserved/unknown tokens, remaining allowance, debt, mode, occupancy and queue state are distinct. For governed runs authoritative actual totals include all normalized categories, not only visible output. Historical usage remains measured history. | CLI JSON/GET/event/projection replay tests agree with resource store; no fabricated backfill or duplicate legacy usage row. |
| INT-04 | Repair F3-J across integrated lifecycle writes: bounded deadline-aware contention handling; successful cleanup when a transient reader releases; fail closed on unresolved storage outage. | Independent reader survives publication retry, blocks watchdog/abort, then releases: truthful terminal state eventually persists and child tasks join. Permanent lock gives explicit persistence failure, never claimed persisted cleanup. |
| INT-05 | Shared scheduler/transport supervision is lifespan-managed and bounded. Shutdown stops admission, cancels queued/undispatched work, joins local children and retains external unknowns. | API startup/shutdown, direct/CLI cancellation and repeated runs leave no local orphan tasks/threads; unknown accounting survives reopen. |

POST `running` retains its current nonterminal lifecycle meaning; it does not assert that a queued run owns an execution slot. Resource projections expose admission state explicitly. Queue-full responses identify a rejection; a timed-out POST remains an ambiguous submission and must not be replayed automatically. New request option `budget_mode` defaults to hard. MCP adds an optional `budget_mode` parameter with the same default and forwards it; CLI adds an explicit mode flag; direct run_hive gains the same keyword. Existing parameter names remain valid. No UI redesign is needed for these backend contracts; frontend type/fixture adjustments and lint/build checks enter the plan if required. Legacy LangGraph usage is outside these Hive ceilings; it must not be marketed as governed.

Admission-store actual usage is authoritative for new governed runs. The old input/output ledger remains a once-per-call compatibility projection; category totals can be additive. Historic ungoverned runs use their unchanged old ledger. The API must expose accounting kind rather than imply old rows had reservations. No shadow real provider dispatch for comparison.

## Proposed initial local policy

| Limit | Initial value / meaning |
|---|---|
| Run token allowance | Existing request value, default 200,000; inherited grants partition it |
| Active runs / queued runs | 4 / 20, independently bounded |
| Provider calls active | Global 8; per run 3; per provider 2 |
| Pending provider calls | Global 128; per run 16 |
| Workers | Existing 1–8 per active run; idle workers do not consume call permits |
| Queue wait | At most 60 seconds and remaining run/task deadline |
| Call duration | At most 120 seconds locally and remaining run/task deadline; no implied remote terminal proof |
| Run/task deadlines | Existing request defaults 1,800 / 600 seconds; run deadline includes run-queue wait |
| Task retries | Existing max_attempts default 3; zero dispatcher/router/SDK retries on governed calls |
| Run ownership / waiter freshness | Heartbeat 3 seconds, ownership lease 15 seconds; waiter expiry 5 seconds, refresh at most 1 second |

These are reviewed starting proposals, not measured throughput or price promises. Values are pinned to the deployment policy; a process cannot raise them ad hoc. Queued run/call deadlines use persisted UTC expiry for cross-process eligibility; live owners also keep monotonic deadlines in their own clock domain. Assumption: one trusted host with an adequately synchronized clock; discontinuity detection fails admission closed rather than extending work. At run activation, timers use the original accepted expiry, not a fresh full run_timeout_s. No process-local monotonic timestamp is interpreted in another process/loop epoch.

## Schema migration, restart and rollback

Choose a coordinated stopped-writer v1 → v2 cutover. Current exact-shape validation and a new shared accounting authority make mixed old/new writers unsafe. Extend the existing maintenance command with versioned check/apply and verified private backup. Retain the existing v0 → v1 path; any multi-step upgrade must identify the actual target and reconcile each step. No automatic writable upgrade at API/import startup. No real application database is modified during implementation tests.

| Stage | Preconditions / authority | Completion / recovery |
|---|---|---|
| Prepare | Maintainer stops all writers and confirms no old external requests remain active; read-only inspect and exclusive private backup | Backup integrity, old row counts/content hashes and sufficient local disk checked; otherwise stop |
| Upgrade | One exclusive transaction adds v2 resource/config/ownership tables and version marker; historical data remains authoritative history | Schema/foreign-key checks, row reconciliation and read-only reopen; interruption rolls back and source remains usable at old version |
| Activate | All processes use supported v2 code and identical policy/SDK identities | Health/config check before admission; fake-transport integrated acceptance and bounded local load pass before claiming release readiness |
| Recover | Queued never-started runs may be claimed; active lost-owner runs become stopped/interrupted without replanning; dispatched unknown holds remain | No task crash-resume claim; reconciliation inspection retains source/call IDs and debt, including previous process occupancy |
| Roll back | Stop new admission and reconcile/drain active requests; preserve v2 history | After first governed call, no in-place downgrade/backup restore that erases accounting. Roll forward or run read-only inspection; old code must refuse v2 |

Corrupt/unsupported storage fails closed. No deletion, permit TTL or new task fence restores uncertain resources. A permanent database outage can prevent terminal persistence; return/report persistence failure and stop new dispatch rather than falsely claiming cleanup. F3-J repair does not promise progress while the database never becomes writable.

## Acceptance and evidence

| Requirements | Proposed falsifiable checks | Environment / owner / tier |
|---|---|---|
| LED-01/02/07/08 | Exact integer/nested conservation, overrun/freeze/close, ID replay/conflict | Resource module owner; temporary SQLite + pure tables; every ledger change |
| LED-03–06, CAL-01/06/07 | Concurrent real Caller invocations, release/dispatch race, kill/reopen, cancellation, late/conflicting receipts | Fake providers + file-backed SQLite and subprocesses; every governed-dispatch change |
| ADM-01–09 | Separate API/direct/CLI processes share ceilings; one flood/outage cannot starve eligible peers; bounded queues/expiry/owner loss | Deterministic barriers/controlled clock plus real SQLite/processes; every admission change |
| CAL-02–05 | Profile/bound/context/output denial, exact SDK transport attempt counts, deadline units and complete-category normalization | Official SDK fixtures in reproducible environments; no real credentials; every adapter/profile change |
| INT-01–05 | 202/429/503/422, MCP read/start compatibility, queue visibility, unique usage projections, reader-contention cleanup, lifespan shutdown | HTTP/CLI/MCP integration, independent reader and local processes; every API/lifecycle change |
| LED-10 | v0/v1/v2 exact-shape/backup/refusal/reopen/interruption tests; old content unchanged | Disposable migration fixtures; every schema change |
| Compatibility | HIVE-001/002/003 focused acceptance, legacy router fixtures, MCP real-local route, full-suite classification; frontend checks if consumer code changes | Existing test environments; affected failures block delivery |
| Local capacity | More than eight fake-provider contenders across at least three runs and two providers; queue/peak counts/denial/cleanup recorded, no leaked holds except deliberate uncertainty | Isolated repeatable local load/fault test, no paid calls; pre-release and limit changes |

All checks above are proposed, not executed passes. Deterministic failures block delivery; no silent flaky-test quarantine. Missing SDK/dependency environments must be repaired in an isolated reproducible test setup or recorded as unresolved required gates; earlier HIVE-003 full-suite classification does not waive new adapter tests. No live provider quality eval or distributed load claim.

HIVE-004-A is Verified only when integrated ledger, Caller/provider controls, shared limits/queues and required lifecycle/migration/consumer checks all pass. Intermediate module tasks may land together under the eventual approved plan, but standalone ledger completion cannot close F4 or this spec. Covers local RES-01–07/09/10 and token side of RES-08; monetary policy and cross-host authority remain explicitly incomplete in parent HIVE-004.

## Review record and next stage

- Revision 1 proposed an isolated library; user chose “Revise scope before planning.” No approval or implementation is claimed for it.
- User selected shared concurrency/queues plus immediate Caller/provider integration. This establishes revised scope, not approval of this newly written revision.
- 2026-10-21 revision 2 self-review: checked shared authority across entrypoints, exact-schema migration, additive MCP compatibility, nested accounting, fair queue ordering, independent execution/usage certainty, owner loss, SDK retries, hard-vs-estimated claims, permanent lock behavior and HIVE-003 publication compatibility. No technical placeholder remains.
- 2026-10-21 user written-spec approval: “Approve revision 2; write the plan.” Approval covers revision 2 above. The linked integrated implementation plan was approved 2026-10-22: “Approve plan; start Task 1.” Subagent-driven execution started; no new dependencies or real-data upgrade authorized by that stage.

## Execution clarifications within approved revision 2

2026-10-22: Persist immutable run ownership on each allocation, inherited through grants. Root allocation creation binds an existing run before admission metadata is composed in the same transaction. This implements LED-02/03 identity and does not expand deployment scope or authorize real-data migration. Request bodies stay in the originating coroutine; the trusted internal preparation module computes canonical request fingerprints, and the ledger compares their persisted identity. Task4 must verify that boundary.
