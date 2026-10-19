"""
Evaluation runner for Hive Lite.
Runs golden prompts and computes quality metrics.
"""
import json
import time
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent import run_research


def load_golden_prompts(path: str = "eval/golden.json") -> list[dict]:
    """Load golden evaluation prompts."""
    with open(path, "r") as f:
        return json.load(f)


def check_sections_present(report: str, required_sections: list[str]) -> dict:
    """Check if required sections are present in report."""
    report_lower = report.lower()
    results = {}
    
    section_markers = {
        "TL;DR": ["tl;dr", "## tl;dr", "tldr"],
        "Background": ["## background", "background"],
        "Key Papers": ["## key papers", "key papers", "## key findings"],
        "Disagreements": ["## disagreements", "contradictions", "## disagreements/contradictions"],
        "Gaps & Open Questions": ["## gaps", "open questions", "## gaps & open questions"],
        "References": ["## references", "references"],
    }
    
    for section in required_sections:
        markers = section_markers.get(section, [section.lower()])
        found = any(marker in report_lower for marker in markers)
        results[section] = found
    
    return results


def check_citations_present(report: str, min_citations: int = 5) -> dict:
    """Check if report has sufficient citations with links."""
    import re
    
    # Look for markdown links
    link_pattern = r'\[([^\]]+)\]\((https?://[^\)]+)\)'
    links = re.findall(link_pattern, report)
    
    # Look for numbered references
    ref_pattern = r'\[\d+\]'
    refs = re.findall(ref_pattern, report)
    
    total_citations = len(links) + len(refs)
    
    return {
        "citation_count": total_citations,
        "has_links": len(links) > 0,
        "meets_minimum": total_citations >= min_citations,
    }


def evaluate_report(report: str, required_sections: list[str]) -> dict:
    """Evaluate a single report."""
    if not report:
        return {
            "sections_present": {},
            "sections_score": 0.0,
            "citations": {"citation_count": 0, "has_links": False, "meets_minimum": False},
            "has_gaps_section": False,
            "has_next_steps": False,
            "report_length": 0,
        }
    
    sections = check_sections_present(report, required_sections)
    sections_score = sum(sections.values()) / len(sections) if sections else 0.0
    
    citations = check_citations_present(report)
    
    report_lower = report.lower()
    has_gaps = any(marker in report_lower for marker in ["gaps", "open question", "unknown"])
    has_next_steps = any(marker in report_lower for marker in ["next step", "proposed experiment", "future"])
    
    return {
        "sections_present": sections,
        "sections_score": sections_score,
        "citations": citations,
        "has_gaps_section": has_gaps,
        "has_next_steps": has_next_steps,
        "report_length": len(report),
    }


async def run_single_eval(prompt: dict, timeout: int = 300) -> dict:
    """Run evaluation for a single prompt."""
    prompt_id = prompt["id"]
    topic = prompt["topic"]
    constraints = prompt.get("constraints")
    depth = prompt.get("depth", "normal")
    required_sections = prompt.get("required_sections", ["TL;DR", "References"])
    
    print(f"\n{'='*60}")
    print(f"Evaluating: {prompt_id}")
    print(f"Topic: {topic[:60]}...")
    print(f"{'='*60}")
    
    start_time = time.time()
    error = None
    final_state = None
    
    try:
        final_state = await asyncio.wait_for(
            run_research(
                objective=topic,
                run_id=f"eval_{prompt_id}_{int(time.time())}",
                depth=depth,
                constraints=constraints,
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        error = "Timeout"
    except Exception as e:
        error = str(e)
    
    duration = time.time() - start_time
    
    # Extract results
    report = final_state.get("final_report", "") if final_state else ""
    sources = final_state.get("sources", []) if final_state else []
    status = final_state.get("status", "failed") if final_state else "failed"
    
    # Evaluate
    evaluation = evaluate_report(report, required_sections)
    
    result = {
        "prompt_id": prompt_id,
        "topic": topic,
        "depth": depth,
        "status": status,
        "duration_seconds": round(duration, 2),
        "sources_count": len(sources),
        "report_length": len(report),
        "error": error,
        "evaluation": evaluation,
        "passed": (
            evaluation["sections_score"] >= 0.8 and
            evaluation["citations"]["meets_minimum"] and
            status == "completed"
        ),
    }
    
    # Print summary
    print(f"Status: {status}")
    print(f"Duration: {duration:.1f}s")
    print(f"Sources: {len(sources)}")
    print(f"Sections score: {evaluation['sections_score']:.0%}")
    print(f"Citations: {evaluation['citations']['citation_count']}")
    print(f"Passed: {'✅' if result['passed'] else '❌'}")
    
    return result


async def run_evaluation(
    golden_path: str = "eval/golden.json",
    output_path: str = "eval/results.json",
    limit: Optional[int] = None,
    timeout: int = 300,
):
    """Run full evaluation suite."""
    print("="*60)
    print("AGENTIC RESEARCH COPILOT - EVALUATION")
    print("="*60)
    print(f"Started: {datetime.now().isoformat()}")
    
    # Load prompts
    prompts = load_golden_prompts(golden_path)
    if limit:
        prompts = prompts[:limit]
    
    print(f"Prompts to evaluate: {len(prompts)}")
    
    # Run evaluations
    results = []
    for prompt in prompts:
        result = await run_single_eval(prompt, timeout)
        results.append(result)
    
    # Compute summary
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    avg_duration = sum(r["duration_seconds"] for r in results) / len(results) if results else 0
    avg_sources = sum(r["sources_count"] for r in results) / len(results) if results else 0
    avg_sections_score = sum(r["evaluation"]["sections_score"] for r in results) / len(results) if results else 0
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_prompts": len(prompts),
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / len(prompts) if prompts else 0,
        "average_duration_seconds": round(avg_duration, 2),
        "average_sources_count": round(avg_sources, 1),
        "average_sections_score": round(avg_sections_score, 2),
    }
    
    # Save results
    output = {
        "summary": summary,
        "results": results,
    }
    
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    print(f"Total: {len(prompts)}")
    print(f"Passed: {passed} ({summary['pass_rate']:.0%})")
    print(f"Failed: {failed}")
    print(f"Avg Duration: {avg_duration:.1f}s")
    print(f"Avg Sources: {avg_sources:.1f}")
    print(f"Avg Sections Score: {avg_sections_score:.0%}")
    print(f"\nResults saved to: {output_path}")
    
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run evaluation suite")
    parser.add_argument("--golden", default="eval/golden.json", help="Path to golden prompts")
    parser.add_argument("--output", default="eval/results.json", help="Output path for results")
    parser.add_argument("--limit", type=int, help="Limit number of prompts to evaluate")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout per prompt in seconds")
    
    args = parser.parse_args()
    
    asyncio.run(run_evaluation(
        golden_path=args.golden,
        output_path=args.output,
        limit=args.limit,
        timeout=args.timeout,
    ))
