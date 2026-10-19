"""
Local observability tracing.
SQLite-based tracing without LangSmith dependency.
"""
import time
import uuid
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, Any
from dataclasses import dataclass, field

from app.db import get_db_context, TraceRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Span:
    """A trace span."""
    id: str
    run_id: str
    name: str
    parent_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    metadata: dict = field(default_factory=dict)
    error: Optional[str] = None
    
    @property
    def duration_ms(self) -> Optional[int]:
        if self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return None


class LocalTracer:
    """
    Local tracing for observability without external dependencies.
    Stores spans in SQLite for later analysis.
    """
    
    def __init__(self):
        self._active_spans: dict[str, Span] = {}
    
    def start_span(
        self,
        run_id: str,
        name: str,
        parent_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Start a new trace span.
        
        Args:
            run_id: Research run ID
            name: Span name
            parent_id: Optional parent span ID
            metadata: Optional metadata
        
        Returns:
            Span ID
        """
        span_id = uuid.uuid4().hex[:16]
        
        span = Span(
            id=span_id,
            run_id=run_id,
            name=name,
            parent_id=parent_id,
            metadata=metadata or {},
        )
        
        self._active_spans[span_id] = span
        logger.debug(f"Started span: {name} ({span_id})")
        
        return span_id
    
    def end_span(
        self,
        span_id: str,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        """
        End a trace span and persist to database.
        
        Args:
            span_id: Span ID to end
            error: Optional error message
            metadata: Optional additional metadata
        """
        span = self._active_spans.pop(span_id, None)
        if not span:
            logger.warning(f"Span not found: {span_id}")
            return
        
        span.end_time = time.time()
        span.error = error
        if metadata:
            span.metadata.update(metadata)
        
        # Persist to database
        try:
            with get_db_context() as db:
                repo = TraceRepository(db)
                repo.create(
                    span_id=span.id,
                    run_id=span.run_id,
                    name=span.name,
                    parent_id=span.parent_id,
                    duration_ms=span.duration_ms,
                    metadata=span.metadata,
                    error=span.error,
                )
        except Exception as e:
            logger.error(f"Failed to persist span: {e}")
        
        logger.debug(f"Ended span: {span.name} ({span_id}) - {span.duration_ms}ms")
    
    @contextmanager
    def trace(
        self,
        run_id: str,
        name: str,
        parent_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        """
        Context manager for tracing a block of code.
        
        Usage:
            with tracer.trace(run_id, "my_operation") as span_id:
                # do work
                pass
        """
        span_id = self.start_span(run_id, name, parent_id, metadata)
        error = None
        try:
            yield span_id
        except Exception as e:
            error = str(e)
            raise
        finally:
            self.end_span(span_id, error=error)
    
    def get_trace(self, run_id: str) -> list[dict]:
        """
        Get all spans for a run.
        
        Args:
            run_id: Research run ID
        
        Returns:
            List of span dictionaries
        """
        try:
            with get_db_context() as db:
                repo = TraceRepository(db)
                spans = repo.get_by_run(run_id)
                return [s.to_dict() for s in spans]
        except Exception as e:
            logger.error(f"Failed to get trace: {e}")
            return []
    
    def format_trace(self, run_id: str) -> str:
        """
        Format trace as readable text.
        
        Args:
            run_id: Research run ID
        
        Returns:
            Formatted trace string
        """
        spans = self.get_trace(run_id)
        if not spans:
            return "No trace data available."
        
        lines = [f"Trace for run: {run_id}", "=" * 50]
        
        # Sort by created_at
        spans.sort(key=lambda s: s.get("created_at", ""))
        
        total_duration = sum(s.get("duration_ms", 0) or 0 for s in spans)
        
        for span in spans:
            name = span.get("name", "unknown")
            duration = span.get("duration_ms", 0)
            error = span.get("error")
            
            status = "❌" if error else "✅"
            lines.append(f"{status} {name}: {duration}ms")
            
            if error:
                lines.append(f"   Error: {error}")
        
        lines.append("=" * 50)
        lines.append(f"Total: {total_duration}ms")
        
        return "\n".join(lines)


# Global tracer instance
tracer = LocalTracer()
