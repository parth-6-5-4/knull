"""Orchestration loop: Knull plans, symbiote workers claim tasks, watchdog supervises."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from app.hive import agents
from app.hive.store import HiveStore, EvidenceIntegrityError, TaskGraphError
from app.hive.reporting import (
    POLICY_VERSION, ReportInputError, ReportSelectionError, ReportSnapshotChanged, WriterAssignment,
)
from app.hive.watchdog import BudgetGovernor
from app.llm import LLMError


@dataclass
class HiveResult:
    run_id: str
    status: str            # done | stopped | blocked
    report: str
    gate: dict
    spent_tokens: int
    usage_by_route: list = field(default_factory=list)
    facts_verified: int = 0
    facts_rejected: int = 0
    events: list = field(default_factory=list)


class LeaseLost(RuntimeError):
    """The attempt no longer owns authority to dispatch or publish."""


def _positive_number(name, value):
    import math
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive and finite")


async def run_hive(objective: str, store: Optional[HiveStore] = None, *, workers: int = 3,
                   max_subtasks: int = 4, budget_tokens: int = 200_000, lease_s: float = 300,
                   max_attempts: int = 3, search: Optional[agents.SearchFn] = None,
                   tick_s: float = 0.2, run_id: Optional[str] = None,
                   task_timeout_s: float = 600, run_timeout_s: float = 1800,
                   heartbeat_s: Optional[float] = None) -> HiveResult:
    """Bounded lite execution. Persistent restart/resume belongs to HIVE-006."""
    for key, value in (("workers", workers), ("max_subtasks", max_subtasks),
                       ("budget_tokens", budget_tokens), ("max_attempts", max_attempts)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{key} must be a positive integer")
    if workers > 8 or max_subtasks > 8:
        raise ValueError("workers and max_subtasks cannot exceed 8")
    for key, value in (("lease_s", lease_s), ("tick_s", tick_s), ("task_timeout_s", task_timeout_s),
                       ("run_timeout_s", run_timeout_s)):
        _positive_number(key, value)
    heartbeat_s = min(60, lease_s / 5) if heartbeat_s is None else heartbeat_s
    _positive_number("heartbeat_s", heartbeat_s)
    if heartbeat_s >= lease_s:
        raise ValueError("heartbeat_s must be below lease_s")
    owned_store = store is None
    store = store if store is not None else HiveStore(":memory:")
    run_id = run_id or store.create_run(objective, budget_tokens)
    gov = BudgetGovernor(store, run_id, budget_tokens)
    planner_call = agents.Caller(store, run_id, gov)
    search = search or agents.default_search
    stop = asyncio.Event()
    supervised = []
    loop = asyncio.get_running_loop()
    task_deadlines = {}
    retry_at = {}

    def abort(status, code, reason):
        stop.set()
        store.stop_run_tasks(run_id, code, reason)
        store.finish_run(run_id, status, "", {"code": code, "reason": reason})

    async def attempt(task, name):
        tid, att, fence = task["id"], task["attempt"], task["fence"]
        deadline = task_deadlines.setdefault(tid, loop.time() + task_timeout_s)

        def guard():
            if not store.owns(tid, name, att, fence):
                raise LeaseLost("assignment lease lost")
            if loop.time() >= deadline:
                raise TimeoutError("logical task deadline exceeded")
            if stop.is_set():
                raise LeaseLost("run admission closed")

        call = agents.Caller(store, run_id, gov, before_call=guard)

        async def execute():
            token = agents.attempt_guard.set(guard)
            try:
                guard()
                if task["kind"] == "research":
                    async def scoped_search(q, n):
                        guard()
                        result = await search(q, n)
                        guard()
                        return result
                    result, evidence, facts = await agents.run_researcher(task, call, scoped_search)
                    return store.publish(tid, name, att, fence, result, evidence, facts)
                if task["kind"] == "verify":
                    updates = await agents.run_verifier(store, run_id, task["deps"], call)
                    return store.set_fact_status(tid, name, att, fence, updates,
                                                 {"verified": sum(s == "verified" for s, _ in updates.values()),
                                                  "rejected": sum(s == "rejected" for s, _ in updates.values())})
                if task["kind"] == "write":
                    assignment = WriterAssignment(tid, name, att, fence)
                    snapshot = store.report_snapshot(run_id, objective, assignment=assignment)
                    report, gate = await agents.run_writer(store, run_id, objective, call, snapshot=snapshot)
                    guard()  # Cancellation-resistant calls cannot publish after a task deadline.
                    return store.publish_report(tid, name, att, fence, snapshot, report, gate)
                raise TaskGraphError("unknown task kind")
            finally:
                agents.attempt_guard.reset(token)

        async def renew():
            while True:
                await asyncio.sleep(heartbeat_s)
                if not store.heartbeat(tid, name, att, fence, lease_s=lease_s):
                    raise LeaseLost("assignment renewal rejected")

        remaining = deadline - loop.time()
        if remaining <= 0:
            raise TimeoutError("logical task deadline exceeded")
        execution = asyncio.create_task(asyncio.wait_for(execute(), remaining), name=f"hive:execute:{tid}")
        renewal = asyncio.create_task(renew(), name=f"hive:renew:{tid}")
        try:
            done, _ = await asyncio.wait((execution, renewal), return_when=asyncio.FIRST_COMPLETED)
            if execution in done:
                return await execution
            await renewal  # Renewal ends only on loss/failure; cancels execution below.
        finally:
            for child in (execution, renewal):
                if not child.done(): child.cancel()
            await asyncio.gather(execution, renewal, return_exceptions=True)

    async def worker(name):
        while not stop.is_set():
            if gov.exhausted():
                stop.set(); return
            excluded = {tid for tid, after in retry_at.items() if after > loop.time()}
            task = store.claim(run_id, name, lease_s=lease_s, exclude=excluded)
            if not task:
                if store.open_tasks(run_id) == 0: return
                await asyncio.sleep(tick_s); continue
            tid, att, fence = task["id"], task["attempt"], task["fence"]
            store.event(run_id, "claim", task=tid, task_kind=task["kind"], worker=name, attempt=att, fence=fence)
            try:
                if not await attempt(task, name):
                    store.event(run_id, "publish_rejected", task=tid, worker=name, attempt=att, fence=fence)
            except agents.BudgetExceeded:
                stop.set(); return
            except LeaseLost:
                store.event(run_id, "lease_lost", task=tid, worker=name, attempt=att, fence=fence)
            except Exception as exc:
                report_error = isinstance(exc, (ReportInputError, ReportSelectionError, ReportSnapshotChanged))
                code = (exc.code if report_error else "task_timeout" if isinstance(exc, TimeoutError)
                        else "evidence_integrity" if isinstance(exc, EvidenceIntegrityError)
                        else "invalid_output" if isinstance(exc, ValueError) else "execution_error")
                reason = code if report_error else f"{type(exc).__name__}: {exc}"[:300]
                retryable = isinstance(exc, (LLMError, OSError, RuntimeError)) and not isinstance(exc, ValueError)
                retryable = retryable and loop.time() < task_deadlines[tid]
                store.event(run_id, "task_error", task=tid, worker=name, code=code, retryable=retryable, error=reason)
                if not retryable or att >= max_attempts:
                    store.mark_exhausted(tid, reason, worker=name, attempt=att, fence=fence, code=code)
                else:
                    retry_at[tid] = loop.time() + min(tick_s * 2 ** min(att, 8), 1)
                    store.release(tid, name, att, fence, reason, code=code)

    async def watchdog():
        while not stop.is_set():
            for action in store.expire_leases(run_id, max_attempts):
                store.event(run_id, "watchdog", **action)
            if gov.exhausted():
                store.event(run_id, "governor", action="stop", spent=gov.spent(), cap=gov.cap)
                stop.set(); return
            await asyncio.sleep(tick_s)

    async def pipeline():
        subs = await agents.knull_plan(planner_call, objective, max_subtasks)
        store.event(run_id, "plan", subtasks=subs)
        verify_ids = []
        for i, sub in enumerate(subs):
            research = store.add_task(run_id, f"research:{sub['query']}", "research", sub["title"], {"query": sub["query"]})
            verify_ids.append(store.add_task(run_id, f"verify:{i}", "verify", f"Verify: {sub['title']}", {}, [research]))
        store.add_task(run_id, "write", "write", "Write report", {}, verify_ids)
        store.validate_graph(run_id)
        wd = asyncio.create_task(watchdog(), name=f"hive:watchdog:{run_id}")
        active = {asyncio.create_task(worker(f"symbiote-{i + 1}"), name=f"hive:worker:{i+1}") for i in range(workers)}
        supervised.extend([wd, *active])
        while active:
            done, _ = await asyncio.wait([wd, *active], return_when=asyncio.FIRST_COMPLETED)
            if wd in done:
                await wd
                return
            for finished in done:
                active.discard(finished)
                await finished

    try:
        try:
            async with asyncio.timeout(run_timeout_s):
                await pipeline()
        except agents.BudgetExceeded:
            abort("stopped", "budget_exhausted", "budget exhausted before planning")
        except TimeoutError:
            abort("stopped", "run_timeout", "run deadline exceeded")
        except TaskGraphError as exc:
            abort("blocked", "invalid_graph", str(exc))
        except asyncio.CancelledError:
            abort("stopped", "cancelled", "run cancelled; active attempts invalidated")
            raise
        except BaseException as exc:
            abort("failed", "supervisor_failure", type(exc).__name__)
            raise
        finally:
            stop.set()
            for child in supervised:
                if not child.done(): child.cancel()
            await asyncio.gather(*supervised, return_exceptions=True)

        if store.get_run(run_id)["status"] != "running":
            return _result(store, run_id)
        tasks = store.tasks(run_id)
        write = next((t for t in tasks if t["kind"] == "write"), None)
        if gov.exhausted() and not (write and write["status"] == "done"):
            abort("stopped", "budget_exhausted", "token budget exhausted")
        elif write and write["status"] == "done":
            artifact = write["result"]
            report = artifact.get("report") if isinstance(artifact, dict) else None
            gate = artifact.get("gate") if isinstance(artifact, dict) else None
            count = gate.get("finding_count") if isinstance(gate, dict) else None
            valid = (isinstance(gate, dict) and gate.get("policy_version") == POLICY_VERSION
                     and type(count) is int and isinstance(report, str))
            if valid and gate.get("passed") is True and count > 0 and report.strip():
                store.finish_run(run_id, "done", report, gate)
            elif (valid and gate.get("passed") is False and count == 0 and report == ""
                  and gate.get("reason") in {"no_verified_facts", "no_selected_findings"}):
                store.finish_run(run_id, "blocked", "", gate)
            else:
                store.finish_run(run_id, "blocked", "", {"reason": "report_artifact_invalid"})
        else:
            store.block_unsatisfied(run_id)
            store.finish_run(run_id, "blocked", "", {"reason": "no verified facts or required work incomplete",
                                                       "tasks": [f"{t['kind']}:{t['status']}" for t in store.tasks(run_id)]})
        return _result(store, run_id)
    finally:
        if owned_store: store.db.close()


def _result(store: HiveStore, run_id: str) -> HiveResult:
    run = store.get_run(run_id)
    import json
    return HiveResult(
        run_id=run_id, status=run["status"], report=run["report"] or "",
        gate=json.loads(run["gate"] or "{}"), spent_tokens=store.spent(run_id),
        usage_by_route=store.usage_by_route(run_id),
        facts_verified=len(store.facts(run_id, "verified")), facts_rejected=len(store.facts(run_id, "rejected")),
        events=store.events(run_id))
