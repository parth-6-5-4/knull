"""
LangGraph state definitions.
"""
from typing import TypedDict, Literal, Optional, Annotated
from datetime import datetime
import operator


class Source(TypedDict, total=False):
    """Represents a source document."""
    id: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    year: int
    source: str  # arxiv, semantic_scholar, wikipedia
    citation_count: int


class Chunk(TypedDict, total=False):
    """Represents a text chunk."""
    id: str
    text: str
    source_id: str
    source_title: str
    source_url: str
    chunk_index: int


class Plan(TypedDict):
    """Research plan."""
    sub_queries: list[str]
    done_criteria: list[str]
    query_type: str


class Critique(TypedDict, total=False):
    """Critique of the draft report."""
    gaps: list[str]
    contradictions: list[str]
    follow_up_queries: list[str]
    confidence: float
    should_iterate: bool


class ResearchState(TypedDict, total=False):
    """
    Main state for the research agent.
    Tracks all information through the research workflow.
    """
    # Input
    objective: str
    constraints: Optional[str]
    depth: Literal["quick", "normal", "deep"]
    session_id: Optional[str]
    run_id: str
    
    # Planning
    plan: Optional[Plan]
    queries: list[str]
    
    # Sources & Chunks
    sources: Annotated[list[Source], operator.add]  # Accumulate sources
    chunks: list[Chunk]
    
    # Synthesis
    draft: Optional[str]
    critique: Optional[Critique]
    final_report: Optional[str]
    
    # Control
    loop_count: int
    current_node: str
    next_node: Optional[str]
    
    # Metadata
    timings: dict[str, float]
    errors: Annotated[list[str], operator.add]  # Accumulate errors
    status: str
    created_at: str


def create_initial_state(
    objective: str,
    run_id: str,
    depth: str = "normal",
    constraints: Optional[str] = None,
    session_id: Optional[str] = None,
) -> ResearchState:
    """Create initial state for a research run."""
    return ResearchState(
        # Input
        objective=objective,
        constraints=constraints,
        depth=depth,
        session_id=session_id,
        run_id=run_id,
        
        # Planning
        plan=None,
        queries=[],
        
        # Sources & Chunks
        sources=[],
        chunks=[],
        
        # Synthesis
        draft=None,
        critique=None,
        final_report=None,
        
        # Control
        loop_count=0,
        current_node="intake",
        next_node=None,
        
        # Metadata
        timings={},
        errors=[],
        status="pending",
        created_at=datetime.utcnow().isoformat(),
    )


def get_max_sources(depth: str) -> int:
    """Get max sources based on depth."""
    return {
        "quick": 5,
        "normal": 10,
        "deep": 20,
    }.get(depth, 10)


def get_max_loops(depth: str) -> int:
    """Get max retrieval loops based on depth."""
    return {
        "quick": 1,
        "normal": 2,
        "deep": 3,
    }.get(depth, 2)
