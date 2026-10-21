"""python -m app.hive.cli "objective" [--workers 3] [--budget 200000]"""
import argparse
import asyncio
import json

from app.hive import run_hive
from app.hive.store import HiveStore


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("objective")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--subtasks", type=int, default=4)
    ap.add_argument("--budget", type=int, default=200_000, help="hard token cap")
    ap.add_argument("--db", default="./app_data/hive.db")
    ap.add_argument("--task-timeout", type=float, default=600, help="logical task deadline in seconds")
    ap.add_argument("--run-timeout", type=float, default=1800, help="whole-run deadline in seconds")
    a = ap.parse_args()
    import os
    os.makedirs(os.path.dirname(a.db) or ".", exist_ok=True)
    store = HiveStore(a.db)
    try:
        r = asyncio.run(run_hive(a.objective, store, workers=a.workers, max_subtasks=a.subtasks,
                                budget_tokens=a.budget, task_timeout_s=a.task_timeout, run_timeout_s=a.run_timeout))
    finally:
        store.db.close()
    print(r.report or "(no report)")
    print(json.dumps({"run_id": r.run_id, "status": r.status, "spent_tokens": r.spent_tokens,
                      "verified": r.facts_verified, "rejected": r.facts_rejected,
                      "gate": {k: v for k, v in r.gate.items() if k != "removed_uncited_or_unverified"},
                      "usage_by_route": r.usage_by_route}, indent=2))


if __name__ == "__main__":
    main()
