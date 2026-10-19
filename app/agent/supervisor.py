"""
Supervisor logic for the research agent.
Decides which agent should work next based on current state.
"""
from typing import Literal

from app.agent.state import ResearchState, get_max_loops
from app.core.logging import get_logger

logger = get_logger(__name__)


AgentName = Literal["planner", "retriever", "ranker", "reader", "synthesizer", "critic", "finalizer", "FINISH"]


def decide_next_agent(state: ResearchState) -> AgentName:
    """
    Decide which agent should work next based on current state.
    
    This is a rule-based supervisor (no LLM call needed for routing).
    
    Args:
        state: Current research state
    
    Returns:
        Name of next agent to run
    """
    # Check for errors that should stop execution
    if len(state.get("errors", [])) > 5:
        logger.warning("Too many errors, stopping")
        return "FINISH"
    
    # If we have a final report, we're done
    if state.get("final_report"):
        return "FINISH"
    
    # No plan yet -> planner
    if not state.get("plan"):
        return "planner"
    
    # Plan exists but no sources -> retriever
    if not state.get("sources"):
        return "retriever"
    
    # Sources exist but not processed (no chunks) -> reader
    if state.get("sources") and not state.get("chunks"):
        return "reader"
    
    # Have chunks but no draft -> synthesizer
    if state.get("chunks") and not state.get("draft"):
        return "synthesizer"
    
    # Have draft but no critique -> critic
    if state.get("draft") and not state.get("critique"):
        return "critic"
    
    # Have critique - check if we need to iterate
    critique = state.get("critique", {})
    loop_count = state.get("loop_count", 0)
    max_loops = get_max_loops(state.get("depth", "normal"))
    
    if critique.get("should_iterate") and loop_count < max_loops:
        # Need more research
        logger.info(f"Critique suggests iteration (loop {loop_count + 1}/{max_loops})")
        return "retriever"
    
    # Have critique and done iterating -> finalizer
    if state.get("critique") and not state.get("final_report"):
        return "finalizer"
    
    # Default: done
    return "FINISH"


def get_agent_description(agent: AgentName) -> str:
    """Get human-readable description of agent."""
    descriptions = {
        "planner": "Planning research queries",
        "retriever": "Searching for sources",
        "ranker": "Ranking and filtering sources",
        "reader": "Processing and embedding sources",
        "synthesizer": "Writing research report",
        "critic": "Analyzing for gaps and contradictions",
        "finalizer": "Formatting final report",
        "FINISH": "Research complete",
    }
    return descriptions.get(agent, agent)


def should_continue(state: ResearchState) -> bool:
    """Check if research should continue."""
    # Stop conditions
    if state.get("final_report"):
        return False
    if len(state.get("errors", [])) > 5:
        return False
    if state.get("status") in ("completed", "failed"):
        return False
    return True
