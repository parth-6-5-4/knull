"""
Research API endpoints.
POST /v1/research - Start a new research run
"""
import uuid
import asyncio
from typing import Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db, RunRepository
from app.agent import run_research
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["research"])


class ResearchRequest(BaseModel):
    """Request body for starting research."""
    topic: str = Field(..., min_length=3, max_length=500, description="Research topic/objective")
    constraints: Optional[str] = Field(None, max_length=500, description="Optional constraints")
    depth: str = Field("normal", pattern="^(quick|normal|deep)$", description="Research depth")
    session_id: Optional[str] = Field(None, description="Optional session ID for grouping runs")


class ResearchResponse(BaseModel):
    """Response for starting research."""
    run_id: str
    status: str
    message: str


async def execute_research(
    run_id: str,
    topic: str,
    depth: str,
    constraints: Optional[str],
    session_id: Optional[str],
    db: Session,
):
    """Background task to execute research."""
    repo = RunRepository(db)
    
    try:
        # Update status to running
        repo.update_status(run_id, "running")
        
        # Run the research workflow
        final_state = await run_research(
            objective=topic,
            run_id=run_id,
            depth=depth,
            constraints=constraints,
            session_id=session_id,
        )
        
        # Update with results
        repo.update_results(
            run_id=run_id,
            plan=final_state.get("plan"),
            sources=final_state.get("sources"),
            final_report=final_state.get("final_report"),
            timings=final_state.get("timings"),
            errors=final_state.get("errors"),
        )
        repo.update_status(run_id, "completed")
        
        logger.info(f"Research run {run_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Research run {run_id} failed: {e}")
        repo.update_status(run_id, "failed")
        repo.update_results(run_id, errors=[str(e)])


@router.post("/research", response_model=ResearchResponse)
async def start_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Start a new research run.
    
    The research runs asynchronously in the background.
    Use GET /v1/runs/{run_id} to check status.
    Use GET /v1/runs/{run_id}/stream for real-time updates.
    """
    run_id = str(uuid.uuid4())
    
    # Create run record
    repo = RunRepository(db)
    repo.create(
        run_id=run_id,
        objective=request.topic,
        depth=request.depth,
        constraints=request.constraints,
        session_id=request.session_id,
    )
    
    # Schedule background execution
    background_tasks.add_task(
        execute_research,
        run_id=run_id,
        topic=request.topic,
        depth=request.depth,
        constraints=request.constraints,
        session_id=request.session_id,
        db=db,
    )
    
    logger.info(f"Started research run {run_id}: {request.topic[:50]}...")
    
    return ResearchResponse(
        run_id=run_id,
        status="pending",
        message="Research started. Use /v1/runs/{run_id} to check status.",
    )
