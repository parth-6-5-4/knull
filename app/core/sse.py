"""
Server-Sent Events (SSE) utilities for real-time streaming.
"""
import json
import asyncio
from datetime import datetime
from typing import AsyncGenerator, Any
from dataclasses import dataclass, asdict
from enum import Enum


class EventType(str, Enum):
    """SSE event types for research progress."""
    NODE_STARTED = "node_started"
    NODE_FINISHED = "node_finished"
    TOOL_CALLED = "tool_called"
    SOURCE_FOUND = "source_found"
    PARTIAL_REPORT = "partial_report"
    FINAL_REPORT = "final_report"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class SSEEvent:
    """Structured SSE event."""
    type: EventType
    run_id: str
    data: dict[str, Any]
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_sse(self) -> str:
        """Format as SSE message."""
        payload = {
            "type": self.type.value,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            **self.data
        }
        return f"data: {json.dumps(payload)}\n\n"


class SSEBroadcaster:
    """
    Manages SSE connections for a specific run.
    Allows multiple clients to receive the same events.
    """
    
    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._history: dict[str, list[SSEEvent]] = {}
    
    def subscribe(self, run_id: str) -> asyncio.Queue:
        """Subscribe to events for a run."""
        if run_id not in self._subscribers:
            self._subscribers[run_id] = []
            self._history[run_id] = []
        
        queue = asyncio.Queue()
        self._subscribers[run_id].append(queue)
        return queue
    
    def unsubscribe(self, run_id: str, queue: asyncio.Queue):
        """Unsubscribe from events."""
        if run_id in self._subscribers:
            try:
                self._subscribers[run_id].remove(queue)
            except ValueError:
                pass
    
    async def publish(self, event: SSEEvent):
        """Publish an event to all subscribers."""
        run_id = event.run_id
        
        # Store in history
        if run_id not in self._history:
            self._history[run_id] = []
        self._history[run_id].append(event)
        
        # Send to all subscribers
        if run_id in self._subscribers:
            for queue in self._subscribers[run_id]:
                await queue.put(event)
    
    def get_history(self, run_id: str) -> list[SSEEvent]:
        """Get event history for a run."""
        return self._history.get(run_id, [])
    
    def cleanup(self, run_id: str):
        """Clean up after run completes."""
        self._subscribers.pop(run_id, None)
        # Keep history for later retrieval


async def event_stream(
    broadcaster: SSEBroadcaster,
    run_id: str,
    timeout: float = 300.0
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for a run.
    Includes heartbeat to keep connection alive.
    """
    queue = broadcaster.subscribe(run_id)
    
    # Send history first
    for event in broadcaster.get_history(run_id):
        yield event.to_sse()
    
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield event.to_sse()
                
                # End stream on final events
                if event.type in (EventType.FINAL_REPORT, EventType.ERROR):
                    break
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                heartbeat = SSEEvent(
                    type=EventType.HEARTBEAT,
                    run_id=run_id,
                    data={"status": "alive"}
                )
                yield heartbeat.to_sse()
    finally:
        broadcaster.unsubscribe(run_id, queue)


# Global broadcaster instance
broadcaster = SSEBroadcaster()
