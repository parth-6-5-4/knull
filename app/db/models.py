"""
SQLAlchemy models for runs and feedback.
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Text, DateTime, 
    ForeignKey, CheckConstraint, JSON
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Run(Base):
    """Research run record."""
    __tablename__ = "runs"
    
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), nullable=True, index=True)
    
    # Request
    objective = Column(Text, nullable=False)
    constraints = Column(Text, nullable=True)
    depth = Column(String(10), default="normal")
    
    # Status
    status = Column(String(20), default="pending", index=True)
    # pending -> running -> completed | failed
    
    # Results (stored as JSON)
    plan = Column(JSON, nullable=True)
    sources = Column(JSON, nullable=True)
    final_report = Column(Text, nullable=True)
    
    # Metadata
    timings = Column(JSON, nullable=True)
    errors = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    feedback = relationship("Feedback", back_populates="run", lazy="dynamic")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "objective": self.objective,
            "constraints": self.constraints,
            "depth": self.depth,
            "status": self.status,
            "plan": self.plan,
            "sources": self.sources,
            "final_report": self.final_report,
            "timings": self.timings,
            "errors": self.errors,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Feedback(Base):
    """User feedback on a run."""
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False, index=True)
    
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="valid_rating"),
    )
    
    # Relationships
    run = relationship("Run", back_populates="feedback")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "run_id": self.run_id,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TraceSpan(Base):
    """Local observability trace span."""
    __tablename__ = "trace_spans"
    
    id = Column(String(36), primary_key=True)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False, index=True)
    parent_id = Column(String(36), nullable=True)
    
    name = Column(String(100), nullable=False)
    duration_ms = Column(Integer, nullable=True)
    
    span_metadata = Column("metadata", JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "run_id": self.run_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "duration_ms": self.duration_ms,
            "metadata": self.span_metadata,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
