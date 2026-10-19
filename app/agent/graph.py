"""
LangGraph workflow for the research agent.
"""
import asyncio
import json
import time
from typing import Any

from langgraph.graph import StateGraph, END

from app.agent.state import ResearchState, create_initial_state, get_max_sources
from app.agent.supervisor import decide_next_agent, should_continue, get_agent_description
from app.agent.prompts import (
    PLANNER_PROMPT, SYNTHESIZER_PROMPT, CRITIC_PROMPT,
    format_sources_for_prompt, format_chunks_for_prompt
)
from app.llm.parsing import parse_json
from app.tools import (
    search_arxiv, search_semantic_scholar, search_wikipedia,
    chunk_text, create_chunk_metadata,
    chroma_upsert, chroma_query,
)
from app.intelligence import (
    classify_query, generate_sub_queries,
    KnowledgeGraph, extract_concepts_from_text,
    detect_trends, format_trend_summary,
)
from app.core import logger, broadcaster, SSEEvent, EventType
from app.core.config import settings
from app.llm import LLMError, llm_chat


# Initialize shared resources
knowledge_graph = KnowledgeGraph()


async def emit_event(run_id: str, event_type: EventType, data: dict):
    """Emit SSE event."""
    event = SSEEvent(type=event_type, run_id=run_id, data=data)
    await broadcaster.publish(event)


# ============== NODE FUNCTIONS ==============

async def intake_node(state: ResearchState) -> dict:
    """Validate and potentially clarify the research objective."""
    run_id = state["run_id"]
    start = time.time()
    
    await emit_event(run_id, EventType.NODE_STARTED, {"node": "intake"})
    
    try:
        # For now, accept all objectives (LLM clarification is optional)
        # A production system would use LLM to check if objective is clear
        
        objective = state["objective"]
        constraints = state.get("constraints", "")
        
        # Classify query for adaptive retrieval
        classification = classify_query(objective)
        
        logger.info(f"Query classified as: {classification.query_type.value}")
        
        duration = time.time() - start
        await emit_event(run_id, EventType.NODE_FINISHED, {
            "node": "intake", 
            "duration_ms": int(duration * 1000),
            "query_type": classification.query_type.value,
        })
        
        return {
            "status": "running",
            "current_node": "intake",
            "timings": {**state.get("timings", {}), "intake": duration},
        }
        
    except Exception as e:
        logger.error(f"Intake error: {e}")
        await emit_event(run_id, EventType.ERROR, {"node": "intake", "error": str(e)})
        return {"errors": [f"Intake error: {e}"]}


async def planner_node(state: ResearchState) -> dict:
    """Generate research plan with sub-queries."""
    run_id = state["run_id"]
    start = time.time()
    
    await emit_event(run_id, EventType.NODE_STARTED, {"node": "planner"})
    
    try:
        objective = state["objective"]
        constraints = state.get("constraints", "")
        depth = state.get("depth", "normal")
        
        # Use query classifier to generate smart sub-queries
        classification = classify_query(objective)
        sub_queries = generate_sub_queries(objective, classification)
        
        # Also try LLM for additional queries if available
        try:
            prompt = PLANNER_PROMPT.format(
                objective=objective,
                constraints=constraints,
                depth=depth,
            )
            response = await llm_chat([{"role": "user", "content": prompt}], layer="graph", agent="planner")
            
            # Tolerant parse: models often wrap JSON in prose or code fences
            plan_data = parse_json(response)
            if plan_data:
                llm_queries = [q for q in plan_data.get("sub_queries", []) if isinstance(q, str)]
                sub_queries = list(dict.fromkeys(sub_queries + llm_queries))[:5]
                done_criteria = plan_data.get("done_criteria", []) or ["Found at least 5 relevant sources"]
            else:
                done_criteria = ["Found at least 5 relevant sources"]
                
        except LLMError as e:
            logger.warning(f"LLM unavailable for planning: {e}")
            done_criteria = ["Found at least 5 relevant sources"]
        
        plan = {
            "sub_queries": sub_queries,
            "done_criteria": done_criteria,
            "query_type": classification.query_type.value,
        }
        
        duration = time.time() - start
        await emit_event(run_id, EventType.NODE_FINISHED, {
            "node": "planner",
            "duration_ms": int(duration * 1000),
            "num_queries": len(sub_queries),
        })
        
        return {
            "plan": plan,
            "queries": sub_queries,
            "current_node": "planner",
            "timings": {**state.get("timings", {}), "planner": duration},
        }
        
    except Exception as e:
        logger.error(f"Planner error: {e}")
        await emit_event(run_id, EventType.ERROR, {"node": "planner", "error": str(e)})
        return {"errors": [f"Planner error: {e}"]}


async def retriever_node(state: ResearchState) -> dict:
    """Search multiple sources for papers."""
    run_id = state["run_id"]
    start = time.time()
    
    await emit_event(run_id, EventType.NODE_STARTED, {"node": "retriever"})
    
    try:
        queries = state.get("queries", [])
        if not queries:
            queries = [state["objective"]]
        
        max_per_query = get_max_sources(state.get("depth", "normal")) // len(queries)
        max_per_query = max(2, max_per_query)
        
        all_sources = []
        
        for query in queries:
            await emit_event(run_id, EventType.TOOL_CALLED, {
                "tool": "search",
                "query": query,
            })
            
            # Search arXiv
            arxiv_results = await search_arxiv(query, max_results=max_per_query)
            for r in arxiv_results:
                all_sources.append(r.to_dict())
            
            # Search Semantic Scholar
            ss_results = await search_semantic_scholar(query, max_results=max_per_query)
            for r in ss_results:
                all_sources.append(r.to_dict())
            
            # Search Wikipedia for background
            wiki_results = await search_wikipedia(query, max_results=1)
            for r in wiki_results:
                all_sources.append(r.to_dict())
            
            # Emit source found events
            for source in all_sources[-5:]:  # Last 5 added
                await emit_event(run_id, EventType.SOURCE_FOUND, {
                    "title": source.get("title", "")[:100],
                    "source": source.get("source", "unknown"),
                })
        
        # Deduplicate by title (simple approach)
        seen_titles = set()
        unique_sources = []
        for s in all_sources:
            title_lower = s.get("title", "").lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_sources.append(s)
        
        duration = time.time() - start
        await emit_event(run_id, EventType.NODE_FINISHED, {
            "node": "retriever",
            "duration_ms": int(duration * 1000),
            "num_sources": len(unique_sources),
        })
        
        return {
            "sources": unique_sources,
            "current_node": "retriever",
            "loop_count": state.get("loop_count", 0) + 1,
            "timings": {**state.get("timings", {}), "retriever": duration},
        }
        
    except Exception as e:
        logger.error(f"Retriever error: {e}")
        await emit_event(run_id, EventType.ERROR, {"node": "retriever", "error": str(e)})
        return {"errors": [f"Retriever error: {e}"]}


async def reader_node(state: ResearchState) -> dict:
    """Process sources, chunk text, and store in vector DB."""
    run_id = state["run_id"]
    start = time.time()
    
    await emit_event(run_id, EventType.NODE_STARTED, {"node": "reader"})
    
    try:
        sources = state.get("sources", [])
        all_chunks = []
        
        for source in sources:
            source_id = source.get("id", source.get("title", "")[:20])
            title = source.get("title", "Untitled")
            url = source.get("url", "")
            
            # Use abstract as main text (avoiding heavy PDF parsing)
            text = source.get("abstract", "")
            if not text:
                continue
            
            # Chunk the text
            chunks = chunk_text(text, chunk_size=500, overlap=50)
            
            # Create metadata and store
            for i, chunk in enumerate(chunks):
                metadata = create_chunk_metadata(
                    chunk=chunk,
                    source_id=source_id,
                    source_title=title,
                    source_url=url,
                    chunk_index=i,
                    source_type=source.get("source", "academic"),
                )
                all_chunks.append({
                    "id": f"{source_id}_{i}",
                    "text": chunk,
                    **metadata,
                })
            
            # Add to knowledge graph
            concepts = extract_concepts_from_text(text)
            knowledge_graph.add_paper(
                paper_id=source_id,
                title=title,
                concepts=concepts,
                url=url,
                year=source.get("year", 0),
            )
            
            # Upsert to vector DB
            if chunks:
                chroma_upsert(
                    chunks=chunks,
                    metadatas=[create_chunk_metadata(c, source_id, title, url, i, source.get("source", "academic")) 
                               for i, c in enumerate(chunks)],
                    source_id=source_id,
                )
        
        duration = time.time() - start
        await emit_event(run_id, EventType.NODE_FINISHED, {
            "node": "reader",
            "duration_ms": int(duration * 1000),
            "num_chunks": len(all_chunks),
        })
        
        return {
            "chunks": all_chunks,
            "current_node": "reader",
            "timings": {**state.get("timings", {}), "reader": duration},
        }
        
    except Exception as e:
        logger.error(f"Reader error: {e}")
        await emit_event(run_id, EventType.ERROR, {"node": "reader", "error": str(e)})
        return {"errors": [f"Reader error: {e}"]}


async def synthesizer_node(state: ResearchState) -> dict:
    """Write the research report."""
    run_id = state["run_id"]
    start = time.time()
    
    await emit_event(run_id, EventType.NODE_STARTED, {"node": "synthesizer"})
    
    try:
        objective = state["objective"]
        constraints = state.get("constraints", "")
        sources = state.get("sources", [])
        chunks = state.get("chunks", [])
        
        # Query vector DB for most relevant chunks
        relevant_chunks = chroma_query(objective, k=10)
        
        # Format for prompt
        sources_text = format_sources_for_prompt(sources)
        chunks_text = format_chunks_for_prompt(
            relevant_chunks if relevant_chunks else chunks[:10]
        )
        
        prompt = SYNTHESIZER_PROMPT.format(
            objective=objective,
            constraints=constraints,
            sources_text=sources_text,
            chunks_text=chunks_text,
        )
        
        try:
            draft = await llm_chat([{"role": "user", "content": prompt}], layer="graph", agent="synthesizer")
        except LLMError as e:
            # Fallback: generate basic report from sources
            logger.warning(f"LLM unavailable for synthesis: {e}")
            draft = _generate_fallback_report(objective, sources)
        
        # Emit partial report
        await emit_event(run_id, EventType.PARTIAL_REPORT, {
            "draft_length": len(draft),
            "preview": draft[:500],
        })
        
        duration = time.time() - start
        await emit_event(run_id, EventType.NODE_FINISHED, {
            "node": "synthesizer",
            "duration_ms": int(duration * 1000),
        })
        
        return {
            "draft": draft,
            "current_node": "synthesizer",
            "timings": {**state.get("timings", {}), "synthesizer": duration},
        }
        
    except Exception as e:
        logger.error(f"Synthesizer error: {e}")
        await emit_event(run_id, EventType.ERROR, {"node": "synthesizer", "error": str(e)})
        return {"errors": [f"Synthesizer error: {e}"]}


async def critic_node(state: ResearchState) -> dict:
    """Analyze draft for gaps and contradictions."""
    run_id = state["run_id"]
    start = time.time()
    
    await emit_event(run_id, EventType.NODE_STARTED, {"node": "critic"})
    
    try:
        draft = state.get("draft", "")
        sources = state.get("sources", [])
        objective = state["objective"]
        
        sources_text = format_sources_for_prompt(sources)
        
        prompt = CRITIC_PROMPT.format(
            objective=objective,
            draft=draft,
            sources_text=sources_text,
        )
        
        try:
            response = await llm_chat([{"role": "user", "content": prompt}], layer="graph", agent="critic")
            
            # Tolerant parse: models often wrap JSON in prose or code fences
            critique_data = parse_json(response) or {
                "gaps": [],
                "contradictions": [],
                "follow_up_queries": [],
                "confidence": 0.8,
                "should_iterate": False,
            }
        except LLMError:
            # Skip critique if LLM unavailable
            critique_data = {
                "gaps": [],
                "contradictions": [],
                "follow_up_queries": [],
                "confidence": 0.7,
                "should_iterate": False,
            }
        
        # Don't iterate if we've done enough loops
        max_loops = 2 if state.get("depth") == "normal" else (1 if state.get("depth") == "quick" else 3)
        if state.get("loop_count", 0) >= max_loops:
            critique_data["should_iterate"] = False
        
        duration = time.time() - start
        await emit_event(run_id, EventType.NODE_FINISHED, {
            "node": "critic",
            "duration_ms": int(duration * 1000),
            "should_iterate": critique_data.get("should_iterate", False),
        })
        
        return {
            "critique": critique_data,
            "current_node": "critic",
            "queries": critique_data.get("follow_up_queries", []) if critique_data.get("should_iterate") else state.get("queries", []),
            "timings": {**state.get("timings", {}), "critic": duration},
        }
        
    except Exception as e:
        logger.error(f"Critic error: {e}")
        await emit_event(run_id, EventType.ERROR, {"node": "critic", "error": str(e)})
        return {"errors": [f"Critic error: {e}"]}


async def finalizer_node(state: ResearchState) -> dict:
    """Format and finalize the report."""
    run_id = state["run_id"]
    start = time.time()
    
    await emit_event(run_id, EventType.NODE_STARTED, {"node": "finalizer"})
    
    try:
        draft = state.get("draft", "")
        sources = state.get("sources", [])
        critique = state.get("critique", {})
        
        # Add trend analysis
        trend_analysis = detect_trends([s for s in sources if s])
        trend_section = format_trend_summary(trend_analysis)
        
        # Add critique summary if available
        critique_section = ""
        if critique.get("gaps"):
            critique_section += "\n\n## Identified Gaps\n"
            for gap in critique["gaps"][:3]:
                critique_section += f"- {gap}\n"
        
        if critique.get("contradictions"):
            critique_section += "\n\n## Noted Contradictions\n"
            for c in critique["contradictions"][:3]:
                critique_section += f"- {c}\n"
        
        # Compile final report
        final_report = draft
        
        # Add trend section before references
        if "## References" in final_report:
            final_report = final_report.replace(
                "## References",
                f"\n\n## Research Trends\n{trend_section}\n\n## References"
            )
        else:
            final_report += f"\n\n## Research Trends\n{trend_section}"
        
        # Add critique as its own appendix section (no string surgery inside the draft)
        if critique_section:
            final_report += f"\n\n## Critic Notes{critique_section}" 
        
        duration = time.time() - start
        
        await emit_event(run_id, EventType.FINAL_REPORT, {
            "report_length": len(final_report),
        })
        
        await emit_event(run_id, EventType.NODE_FINISHED, {
            "node": "finalizer",
            "duration_ms": int(duration * 1000),
        })
        
        return {
            "final_report": final_report,
            "status": "completed",
            "current_node": "finalizer",
            "timings": {**state.get("timings", {}), "finalizer": duration},
        }
        
    except Exception as e:
        logger.error(f"Finalizer error: {e}")
        await emit_event(run_id, EventType.ERROR, {"node": "finalizer", "error": str(e)})
        return {"errors": [f"Finalizer error: {e}"]}


def _generate_fallback_report(objective: str, sources: list[dict]) -> str:
    """Generate basic report when LLM is unavailable."""
    report = f"""# Research Report: {objective}

## TL;DR
• Found {len(sources)} relevant sources on this topic
• Sources span multiple databases (arXiv, Semantic Scholar, Wikipedia)
• Further analysis requires LLM processing

## Background
This is an automated research compilation on: {objective}

## Key Papers/Sources
"""
    for i, s in enumerate(sources[:10], 1):
        title = s.get("title", "Untitled")
        url = s.get("url", "")
        year = s.get("year", "N/A")
        report += f"{i}. [{title}]({url}) ({year})\n"
    
    report += """
## Disagreements/Contradictions
Unable to analyze without LLM processing.

## Gaps & Open Questions
- Full synthesis requires LLM availability
- PDF full-text analysis not performed

## Proposed Experiments / Next Steps
1. Configure an LLM provider (llm.yaml, or start Ollama with `ollama serve`)
2. Re-run research for full analysis

## References
"""
    for s in sources:
        report += f"- [{s.get('title', 'Untitled')}]({s.get('url', '')})\n"
    
    return report


# ============== ROUTING FUNCTION ==============

def route_next(state: ResearchState) -> str:
    """Determine next node based on state."""
    next_agent = decide_next_agent(state)
    logger.info(f"Routing to: {next_agent}")
    
    if next_agent == "FINISH":
        return END
    return next_agent


# ============== BUILD GRAPH ==============

def build_research_graph() -> StateGraph:
    """Build the LangGraph research workflow."""
    
    # Create graph
    graph = StateGraph(ResearchState)
    
    # Add nodes
    graph.add_node("intake", intake_node)
    graph.add_node("planner", planner_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("reader", reader_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("critic", critic_node)
    graph.add_node("finalizer", finalizer_node)
    
    # Set entry point
    graph.set_entry_point("intake")
    
    # Add conditional edges from each node
    for node in ["intake", "planner", "retriever", "reader", "synthesizer", "critic", "finalizer"]:
        graph.add_conditional_edges(node, route_next)
    
    return graph.compile()


# Create compiled graph
research_graph = build_research_graph()


async def run_research(
    objective: str,
    run_id: str,
    depth: str = "normal",
    constraints: str = None,
    session_id: str = None,
) -> ResearchState:
    """
    Run the research workflow.
    
    Args:
        objective: Research objective
        run_id: Unique run identifier
        depth: Research depth (quick, normal, deep)
        constraints: Optional constraints
        session_id: Optional session ID
    
    Returns:
        Final research state
    """
    # Create initial state
    initial_state = create_initial_state(
        objective=objective,
        run_id=run_id,
        depth=depth,
        constraints=constraints,
        session_id=session_id,
    )
    
    logger.info(f"Starting research run {run_id}: {objective[:50]}...")
    
    # Run the graph
    final_state = await research_graph.ainvoke(initial_state)
    
    logger.info(f"Research run {run_id} completed with status: {final_state.get('status')}")
    
    return final_state
