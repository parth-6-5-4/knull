"""Offline audit probes. Run from project root; no provider keys or network used.

These probes report current defects, rather than assert desired future behavior.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

os.environ["DEBUG"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.hive import run_hive
from app.hive.agents import Caller, final_gate
from app.hive.store import HiveStore
from app.hive.watchdog import BudgetGovernor
from app.llm import LLMConfig, LLMRouter, ModelSpec, set_router
from tests.test_hive import fake_search, make_handler, routed_config


async def main():
    findings = {}
    set_router(LLMRouter(routed_config(), mock_handler=make_handler()))
    store = HiveStore()
    first = await run_hive("Attention and caching", store, workers=2, search=fake_search, tick_s=0.001)
    second = await run_hive("Attention and caching", store, workers=2, search=fake_search, tick_s=0.001)
    findings["cross_run_source_collision"] = {
        "first": {"status": first.status, "verified": first.facts_verified},
        "second": {"status": second.status, "verified": second.facts_verified,
                   "rejected": second.facts_rejected},
        "second_evidence_rows": len(store.evidence(second.run_id)),
    }

    store = HiveStore()
    rid = store.create_run("Permanent failure", 200000)

    async def unavailable_search(query, count):
        raise RuntimeError("permanent tool outage")

    before = asyncio.all_tasks()
    try:
        await asyncio.wait_for(run_hive("Permanent failure", store, run_id=rid, workers=1,
                                       search=unavailable_search, tick_s=0.001), timeout=0.25)
        timed_out = False
    except asyncio.TimeoutError:
        timed_out = True
    finally:
        leaked = asyncio.all_tasks() - before
        for task in leaked:
            task.cancel()
        await asyncio.gather(*leaked, return_exceptions=True)
    findings["exhausted_dependency_hang"] = {
        "timed_out": timed_out, "run_status": store.get_run(rid)["status"],
        "tasks": [{"kind": t["kind"], "status": t["status"], "attempt": t["attempt"]}
                  for t in store.tasks(rid)],
    }

    body, gate = final_gate("## Findings\nCaching increases calls by 900% [F-aaaaaaaa].",
                            {"F-aaaaaaaa"})
    findings["citation_laundering"] = {
        "known_fact": "Caching reduces calls by 40%.", "retained": body, "gate": gate,
    }

    async def expensive_response(spec, messages):
        await asyncio.sleep(0.01)
        return "x" * 800

    model = ModelSpec(provider="mock", model="budget-probe")
    set_router(LLMRouter(LLMConfig(default=model), mock_handler=expensive_response))
    store = HiveStore()
    rid = store.create_run("Budget", 100)
    caller = Caller(store, rid, BudgetGovernor(store, rid, 100))
    await asyncio.gather(*(caller("workers", "researcher", "s", "u", max_tokens=200)
                           for _ in range(2)))
    findings["concurrent_budget_overshoot"] = {"cap": 100, "spent": store.spent(rid)}

    store = HiveStore()
    rid = store.create_run("Stale failure", 1000)
    tid = store.add_task(rid, "r", "research", "t", {})
    old = store.claim(rid, "old", lease_s=1, now=0)
    store.expire_leases(rid, now=2)
    current = store.claim(rid, "current", lease_s=10, now=3)
    store.publish(tid, "current", current["attempt"], current["fence"], {"ok": True}, now=4)
    store.mark_exhausted(tid, "late failure from old attempt")
    findings["unfenced_exhaustion"] = {
        "old_fence": old["fence"], "current_fence": current["fence"],
        "status_after_success_then_stale_failure": store.get_task(tid)["status"],
    }
    set_router(None)
    print(json.dumps(findings, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
