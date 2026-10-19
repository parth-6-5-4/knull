"""
Repository pattern for database operations.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.models import Run, Feedback, TraceSpan


class RunRepository:
    """Repository for Run operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        run_id: str,
        objective: str,
        depth: str = "normal",
        constraints: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Run:
        """Create a new run."""
        run = Run(
            id=run_id,
            objective=objective,
            depth=depth,
            constraints=constraints,
            session_id=session_id,
            status="pending",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run
    
    def get(self, run_id: str) -> Optional[Run]:
        """Get a run by ID."""
        return self.db.query(Run).filter(Run.id == run_id).first()
    
    def get_by_session(self, session_id: str, limit: int = 10) -> list[Run]:
        """Get runs by session ID."""
        return (
            self.db.query(Run)
            .filter(Run.session_id == session_id)
            .order_by(desc(Run.created_at))
            .limit(limit)
            .all()
        )
    
    def update_status(self, run_id: str, status: str) -> Optional[Run]:
        """Update run status."""
        run = self.get(run_id)
        if run:
            run.status = status
            run.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(run)
        return run
    
    def update_results(
        self,
        run_id: str,
        plan: Optional[dict] = None,
        sources: Optional[list] = None,
        final_report: Optional[str] = None,
        timings: Optional[dict] = None,
        errors: Optional[list] = None,
    ) -> Optional[Run]:
        """Update run results."""
        run = self.get(run_id)
        if run:
            if plan is not None:
                run.plan = plan
            if sources is not None:
                run.sources = sources
            if final_report is not None:
                run.final_report = final_report
            if timings is not None:
                run.timings = timings
            if errors is not None:
                run.errors = errors
            run.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(run)
        return run
    
    def list_recent(self, limit: int = 20) -> list[Run]:
        """List recent runs."""
        return (
            self.db.query(Run)
            .order_by(desc(Run.created_at))
            .limit(limit)
            .all()
        )


class FeedbackRepository:
    """Repository for Feedback operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        run_id: str,
        rating: int,
        comment: Optional[str] = None,
    ) -> Feedback:
        """Create feedback for a run."""
        feedback = Feedback(
            run_id=run_id,
            rating=rating,
            comment=comment,
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback
    
    def get_by_run(self, run_id: str) -> list[Feedback]:
        """Get all feedback for a run."""
        return (
            self.db.query(Feedback)
            .filter(Feedback.run_id == run_id)
            .order_by(desc(Feedback.created_at))
            .all()
        )
    
    def get_average_rating(self) -> float:
        """Get average rating across all feedback."""
        from sqlalchemy import func
        result = self.db.query(func.avg(Feedback.rating)).scalar()
        return float(result) if result else 0.0


class TraceRepository:
    """Repository for TraceSpan operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        span_id: str,
        run_id: str,
        name: str,
        parent_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> TraceSpan:
        """Create a trace span."""
        span = TraceSpan(
            id=span_id,
            run_id=run_id,
            parent_id=parent_id,
            name=name,
            duration_ms=duration_ms,
            span_metadata=metadata,
            error=error,
        )
        self.db.add(span)
        self.db.commit()
        self.db.refresh(span)
        return span
    
    def get_by_run(self, run_id: str) -> list[TraceSpan]:
        """Get all spans for a run."""
        return (
            self.db.query(TraceSpan)
            .filter(TraceSpan.run_id == run_id)
            .order_by(TraceSpan.created_at)
            .all()
        )
    
    def update_duration(self, span_id: str, duration_ms: int) -> Optional[TraceSpan]:
        """Update span duration."""
        span = self.db.query(TraceSpan).filter(TraceSpan.id == span_id).first()
        if span:
            span.duration_ms = duration_ms
            self.db.commit()
            self.db.refresh(span)
        return span
