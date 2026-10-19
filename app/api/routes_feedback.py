"""
Feedback API endpoints.
POST /v1/feedback - Submit feedback for a run
"""
from typing import Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db, RunRepository, FeedbackRepository
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["feedback"])


class FeedbackRequest(BaseModel):
    """Request body for feedback."""
    run_id: str = Field(..., description="Run ID to provide feedback for")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional comment")


class FeedbackResponse(BaseModel):
    """Response for feedback submission."""
    id: int
    run_id: str
    rating: int
    message: str


class FeedbackStatsResponse(BaseModel):
    """Response for feedback statistics."""
    average_rating: float
    total_feedback: int


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
):
    """Submit feedback for a research run."""
    # Verify run exists
    run_repo = RunRepository(db)
    run = run_repo.get(request.run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Create feedback
    feedback_repo = FeedbackRepository(db)
    feedback = feedback_repo.create(
        run_id=request.run_id,
        rating=request.rating,
        comment=request.comment,
    )
    
    logger.info(f"Feedback submitted for run {request.run_id}: {request.rating}/5")
    
    return FeedbackResponse(
        id=feedback.id,
        run_id=feedback.run_id,
        rating=feedback.rating,
        message="Feedback submitted successfully",
    )


@router.get("/feedback/{run_id}")
async def get_run_feedback(run_id: str, db: Session = Depends(get_db)):
    """Get all feedback for a specific run."""
    feedback_repo = FeedbackRepository(db)
    feedbacks = feedback_repo.get_by_run(run_id)
    
    return {
        "run_id": run_id,
        "feedback": [f.to_dict() for f in feedbacks],
        "count": len(feedbacks),
    }


@router.get("/feedback", response_model=FeedbackStatsResponse)
async def get_feedback_stats(db: Session = Depends(get_db)):
    """Get overall feedback statistics."""
    feedback_repo = FeedbackRepository(db)
    avg_rating = feedback_repo.get_average_rating()
    
    return FeedbackStatsResponse(
        average_rating=round(avg_rating, 2),
        total_feedback=0,  # Would need count method
    )
