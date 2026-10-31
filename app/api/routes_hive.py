"""
Hive endpoints (lite Knull + symbiotes, Book 1 ch. 15).

POST /v1/hive/runs        start a hive run in the background
GET  /v1/hive/runs/{id}   status, report, verified/rejected facts, usage per (layer, agent, provider, model)
"""
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.hive import run_hive
from app.hive.store import HiveStore

router = APIRouter(prefix="/v1", tags=["hive"])
_store: Optional[HiveStore] = None


def get_store() -> HiveStore:
    global _store
    if _store is None:
        p = Path(settings.sqlite_path).with_name("hive.db")
        p.parent.mkdir(parents=True, exist_ok=True)
        _store = HiveStore(str(p))
    return _store


class HiveRequest(BaseModel):
    objective: str = Field(..., min_length=5)
    workers: int = Field(3, ge=1, le=8)
    subtasks: int = Field(4, ge=1, le=8)
    budget_tokens: int = Field(200_000, ge=1_000, description="hard token cap for the whole run")
    task_timeout_s: float = Field(600, gt=0, allow_inf_nan=False)
    run_timeout_s: float = Field(1800, gt=0, allow_inf_nan=False)


@router.post("/hive/runs", status_code=202)
async def start_hive(req: HiveRequest, bg: BackgroundTasks):
    store = get_store()
    run_id = store.create_run(req.objective, req.budget_tokens)
    bg.add_task(run_hive, req.objective, store, workers=req.workers, max_subtasks=req.subtasks,
                budget_tokens=req.budget_tokens, run_id=run_id,
                task_timeout_s=req.task_timeout_s, run_timeout_s=req.run_timeout_s)
    return {"run_id": run_id, "status": "running"}


@router.get("/hive/runs/{run_id}")
async def get_hive(run_id: str):
    store = get_store()
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return {
        "run_id": run_id, "objective": run["objective"], "status": run["status"],
        "report": run["report"], "spent_tokens": store.spent(run_id), "budget_tokens": run["budget_tokens"],
        "tasks": [{"id": t["id"], "kind": t["kind"], "title": t["title"], "status": t["status"],
                   "attempt": t["attempt"]} for t in store.tasks(run_id)],
        "facts": [{"id": f["id"], "claim": f["claim"], "status": f["status"], "note": f["note"]}
                  for f in store.facts(run_id)],
        "usage_by_route": store.usage_by_route(run_id),
        "events": store.events(run_id)[-50:],
    }
