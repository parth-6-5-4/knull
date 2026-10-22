# HIVE-004 scoping and problem report

2026-10-21. Started after [HIVE-003 verified delivery](../hive-003/summary.md). Read-only diagnosis and specification work; no resource-governance product code yet.

## Existing flow

`run_hive` constructs `BudgetGovernor` and `Caller`. Caller checks already-recorded usage, invokes `LLMRouter.complete(retries=0)`, then inserts successful reported input/output usage. There is no pre-dispatch hold, failed-call identity or durable unknown state. Concurrent calls can all observe available budget before any usage insert. Existing API text calls the allowance a hard cap, which overstates this behavior.

Source: [Caller](../../../app/hive/agents.py), [governor](../../../app/hive/watchdog.py), [usage store](../../../app/hive/store.py), [router](../../../app/llm/router.py), [API](../../../app/api/routes_hive.py). Latest preserved [offline probe](../hive-003/task-5-gaps-observations.json): cap 100, spent 400. Diagnostic evidence, not a passing budget test.

## Problems and proposed remedies

| ID | Observed gap | Proposed remedy | Current state |
|---|---|---|---|
| F4 / RES-01–04,10 | Check-then-call race; only successful receipts counted | Transactional bound reservation; retained ambiguous external spend; immutable call identity | HIVE-004-A revision 2 approved; integrated admission acceptance pending |
| RES-02 | No inherited child authority ledger | Conserved parent grants with exact nested accounting | Proposed LED-02/07/08 |
| RES-05 | Outer retries=0 leaves SDK retries uncontrolled | Runner-owned bounded task retries, zero hidden dispatcher/SDK retries and per-attempt identity | Included in revision 2; runtime unchanged |
| RES-08 | Current usage pair may omit other charge categories; no monetary policy | Qualified complete bounds/receipts and independently versioned money policy | Hard token qualification included; monetary accounting separate; no current hard-provider-cost guarantee |
| F10 / RES-06/07 | Each API request creates its own worker pool | Shared global/run/provider permits and bounded fair admission | Shared run/call queues and permits included in revision 2; not implemented |
| F3-J | Separate reader can defeat unchanged watchdog/abort commits | Deadline-aware lifecycle contention recovery with independent-reader end-to-end test | HIVE-004-A INT-04 explicitly includes the required local lifecycle repair; not implemented |

## Current-source research

Official [OpenAI Python retry documentation](https://github.com/openai/openai-python#retries) describes two retries by default and explicit max_retries control. The current adapter does not configure that control; outer retries=0 therefore does not prove a single transport attempt. Installed OpenAI 2.14.0 was inspected locally; Anthropic SDK is absent, so no local Anthropic transport verification is claimed. Official [Anthropic Python SDK documentation](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python#retries) likewise exposes retry controls.

Google's [token guide](https://ai.google.dev/gemini-api/docs/tokens) separates input counting from response usage, including thinking/cache/tool categories. Design inference: character heuristics or visible output alone cannot establish a complete bound for every route. Provider/model/version profiles must qualify bounds and full receipt categories before hard mode activation. No provider calls or paid evaluation performed.

Google's [official SDK types](https://github.com/googleapis/python-genai/blob/main/google/genai/types.py) define retry attempts as including the original request; attempts 0 or 1 disable retries, and timeout units are milliseconds. This differs from max_retries-style SDK settings. Revision 2 requires installed-version transport fixtures rather than copying one provider's control values into another adapter. Upstream source was researched; that does not qualify an installed production route.

## Revised integrated delivery

The user rejected standalone-only scope and selected both shared concurrency/queues and immediate Caller/provider integration. [HIVE-004-A revision 2](../../superpowers/specs/2026-10-21-resource-ledger-design.md) therefore delivers one integrated local-host change: inherited accounting, every Hive role, SDK single-attempt controls, qualified hard/explicit estimated modes, shared run/call permits, bounded fair queues, observable overload, contention-safe lifecycle and schema migration. A library-only intermediate task does not close this delivery.

Multiple API/CLI/direct processes must share the same canonical Hive database and persisted policy. Global limits cover governed Hive work there; the legacy LangGraph path and unrelated provider clients are outside those ceilings. Postgres/multi-host scheduling and exact monetary policy remain parent HIVE-004/HIVE-006 work.

## Consumer and migration findings

- MCP currently rejects a start response whose status differs from running. Revision 2 preserves that field and adds admission state. New budget_mode is additive; hard mode rejects unqualified routes instead of silently estimating. Queue-full rejection uses 429, temporary admission-store busy 503 and unsupported hard profile/config 422. Timed-out submission remains ambiguous; no automatic POST replay.
- Current Hive schema validator accepts an exact v1 shape. New resource tables cannot be silently installed alongside it. Revision 2 chooses explicit stopped-writer v2 migration, private verified backup, historical content reconciliation and old-writer refusal. No separate ledger file or cross-file transaction claim.
- Existing soft budget descriptions and usage projections must change with integration: actual normalized totals, held unknowns and estimates stay distinct. Historical measured usage is preserved, with no invented reservations.
- F3-J is now inside the required local integration repair. A permanently unavailable database cannot promise persisted cleanup; failure must be explicit and new dispatch stopped.

## Verification state

Revision 2 approved by user 2026-10-21: “Approve revision 2; write the plan.” [Integrated eight-task plan](../../superpowers/plans/2026-10-21-resource-admission.md) approved 2026-10-22: “Approve plan; start Task 1.” Task1 foundation independently reviewed and locally committed as2fac99f;130focusedchecks passed, full suite452passed/11unchanged baseline dependency failures. Task2 accounting underway. Queue fairness, provider controls and integrated spend guarantees remain open acceptance gates. No live external calls, dependency installs or real database activation. The dated HIVE-003 graph remains separate until Task8 refresh. [Execution evidence](execution-ledger.md).
