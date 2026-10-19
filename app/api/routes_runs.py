"""
Run status and streaming endpoints.
GET /v1/runs/{run_id} - Get run status
GET /v1/runs/{run_id}/stream - SSE stream
"""
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db, RunRepository
from app.core.sse import event_stream, broadcaster
from app.traces import tracer
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/runs", tags=["runs"])


class RunStatusResponse(BaseModel):
    """Response for run status."""
    id: str
    status: str
    objective: str
    depth: str
    plan: Optional[dict] = None
    sources: Optional[list] = None
    final_report: Optional[str] = None
    timings: Optional[dict] = None
    errors: Optional[list] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RunListResponse(BaseModel):
    """Response for listing runs."""
    runs: list[RunStatusResponse]
    total: int


@router.get("", response_model=RunListResponse)
async def list_runs(
    limit: int = 20,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List recent research runs."""
    repo = RunRepository(db)
    
    if session_id:
        runs = repo.get_by_session(session_id, limit=limit)
    else:
        runs = repo.list_recent(limit=limit)
    
    return RunListResponse(
        runs=[
            RunStatusResponse(
                id=r.id,
                status=r.status,
                objective=r.objective,
                depth=r.depth,
                plan=r.plan,
                sources=r.sources,
                final_report=r.final_report,
                timings=r.timings,
                errors=r.errors,
                created_at=r.created_at.isoformat() if r.created_at else None,
                updated_at=r.updated_at.isoformat() if r.updated_at else None,
            )
            for r in runs
        ],
        total=len(runs),
    )


@router.get("/{run_id}", response_model=RunStatusResponse)
async def get_run(run_id: str, db: Session = Depends(get_db)):
    """Get the status and results of a research run."""
    repo = RunRepository(db)
    run = repo.get(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return RunStatusResponse(
        id=run.id,
        status=run.status,
        objective=run.objective,
        depth=run.depth,
        plan=run.plan,
        sources=run.sources,
        final_report=run.final_report,
        timings=run.timings,
        errors=run.errors,
        created_at=run.created_at.isoformat() if run.created_at else None,
        updated_at=run.updated_at.isoformat() if run.updated_at else None,
    )


@router.get("/{run_id}/stream")
async def stream_run(run_id: str, db: Session = Depends(get_db)):
    """
    Stream real-time updates for a research run via SSE.
    
    Events:
    - node_started: A node in the workflow started
    - node_finished: A node completed
    - tool_called: A tool was invoked
    - source_found: A source was discovered
    - partial_report: Draft report update
    - final_report: Research complete
    - error: An error occurred
    - heartbeat: Connection keep-alive
    """
    repo = RunRepository(db)
    run = repo.get(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return StreamingResponse(
        event_stream(broadcaster, run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/{run_id}/trace")
async def get_trace(run_id: str, db: Session = Depends(get_db)):
    """
    Get execution trace for a run.
    Shows timing and status for each step.
    """
    repo = RunRepository(db)
    run = repo.get(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    spans = tracer.get_trace(run_id)
    formatted = tracer.format_trace(run_id)
    
    return {
        "run_id": run_id,
        "spans": spans,
        "formatted": formatted,
        "summary": {
            "total_spans": len(spans),
            "total_duration_ms": sum(s.get("duration_ms", 0) or 0 for s in spans),
            "errors": [s for s in spans if s.get("error")],
        }
    }
