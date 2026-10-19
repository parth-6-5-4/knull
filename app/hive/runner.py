"""Orchestration loop: Knull plans, symbiote workers claim tasks, watchdog supervises."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from app.core.config import settings
from app.hive import agents
from app.hive.store import HiveStore
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


async def run_hive(objective: str, store: Optional[HiveStore] = None, *, workers: int = 3,
                   max_subtasks: int = 4, budget_tokens: int = 200_000, lease_s: float = 300,
                   max_attempts: int = 3, search: Optional[agents.SearchFn] = None,
                   tick_s: float = 0.2, run_id: Optional[str] = None) -> HiveResult:
    store = store or HiveStore(":memory:")
    run_id = run_id or store.create_run(objective, budget_tokens)
    gov = BudgetGovernor(store, run_id, budget_tokens)
    call = agents.Caller(store, run_id, gov)
    search = search or agents.default_search
    stop = asyncio.Event()

    # 1. Knull plans the DAG: research_i -> verify_i, all verify_i -> write
    try:
        subs = await agents.knull_plan(call, objective, max_subtasks)
    except agents.BudgetExceeded:
        store.finish_run(run_id, "stopped", "", {"reason": "budget exhausted before planning"})
        return _result(store, run_id)
    store.event(run_id, "plan", subtasks=subs)
    verify_ids = []
    for i, s in enumerate(subs):
        r = store.add_task(run_id, f"research:{s['query']}", "research", s["title"], {"query": s["query"]})
        v = store.add_task(run_id, f"verify:{i}", "verify", f"Verify: {s['title']}", {}, [r])
        verify_ids.append(v)
    store.add_task(run_id, "write", "write", "Write report", {}, verify_ids)

    async def worker(name: str):
        while not stop.is_set():
            if gov.exhausted():
                return
            task = store.claim(run_id, name, lease_s=lease_s)
            if not task:
                if store.open_tasks(run_id) == 0:
                    return
                await asyncio.sleep(tick_s)
                continue
            t_id, att, fence = task["id"], task["attempt"], task["fence"]
            store.event(run_id, "claim", task=t_id, task_kind=task["kind"], worker=name, attempt=att, fence=fence)
            try:
                if task["kind"] == "research":
                    result, ev, facts = await agents.run_researcher(task, call, search)
                    ok = store.publish(t_id, name, att, fence, result, ev, facts)
                elif task["kind"] == "verify":
                    updates = await agents.run_verifier(store, run_id, task["deps"], call)
                    ok = store.set_fact_status(t_id, name, att, fence, updates,
                                               {"verified": sum(1 for s, _ in updates.values() if s == "verified"),
                                                "rejected": sum(1 for s, _ in updates.values() if s == "rejected")})
                else:
                    report, gate = await agents.run_writer(store, run_id, objective, call)
                    ok = store.publish(t_id, name, att, fence, {"report": report, "gate": gate})
                if not ok:
                    store.event(run_id, "publish_rejected", task=t_id, worker=name, attempt=att, fence=fence)
            except agents.BudgetExceeded:
                store.release(t_id, name, att, fence, "budget exhausted")
                return
            except (LLMError, Exception) as e:  # noqa: BLE001 - worker failures requeue, watchdog caps attempts
                store.event(run_id, "task_error", task=t_id, worker=name, error=str(e)[:300])
                if att >= max_attempts:
                    store.mark_exhausted(t_id, str(e)[:300])
                else:
                    store.release(t_id, name, att, fence, str(e)[:300])

    async def watchdog():
        while not stop.is_set():
            for act in store.expire_leases(run_id, max_attempts):
                store.event(run_id, "watchdog", **act)
            if gov.exhausted():
                store.event(run_id, "governor", action="stop", spent=gov.spent(), cap=gov.cap)
                stop.set()
                return
            await asyncio.sleep(tick_s)

    wd = asyncio.create_task(watchdog())
    await asyncio.gather(*(worker(f"symbiote-{i + 1}") for i in range(workers)))
    stop.set()
    await wd

    # 2. Close-out: do not report "done" when budget ran out or the gate found nothing
    tasks = store.tasks(run_id)
    write = next((t for t in tasks if t["kind"] == "write"), None)
    if gov.exhausted() and not (write and write["status"] == "done"):
        store.finish_run(run_id, "stopped", "", {"reason": "token budget exhausted", "spent": gov.spent()})
    elif write and write["status"] == "done" and write["result"]["report"]:
        status = "done" if write["result"]["gate"].get("passed") else "done_with_removals"
        store.finish_run(run_id, status, write["result"]["report"], write["result"]["gate"])
    else:
        store.finish_run(run_id, "blocked", "", {"reason": "no verified facts or write task incomplete",
                                                 "tasks": [f"{t['kind']}:{t['status']}" for t in tasks]})
    return _result(store, run_id)


def _result(store: HiveStore, run_id: str) -> HiveResult:
    run = store.get_run(run_id)
    import json
    return HiveResult(
        run_id=run_id, status=run["status"], report=run["report"] or "",
        gate=json.loads(run["gate"] or "{}"), spent_tokens=store.spent(run_id),
        usage_by_route=store.usage_by_route(run_id),
        facts_verified=len(store.facts(run_id, "verified")), facts_rejected=len(store.facts(run_id, "rejected")),
        events=store.events(run_id))
