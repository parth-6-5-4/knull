"""
Trend detection from research sources.
Identifies emerging concepts and publication patterns.
"""
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TrendAnalysis:
    """Result of trend analysis."""
    trend_direction: str  # "growing", "stable", "declining"
    emerging_concepts: list[str]
    peak_year: int
    year_distribution: dict[int, int]
    confidence: float
    
    def to_dict(self) -> dict:
        return {
            "trend_direction": self.trend_direction,
            "emerging_concepts": self.emerging_concepts,
            "peak_year": self.peak_year,
            "year_distribution": self.year_distribution,
            "confidence": self.confidence,
        }


def detect_trends(sources: list[dict], current_year: int = 2024) -> TrendAnalysis:
    """
    Analyze sources to detect research trends.
    
    Args:
        sources: List of source dicts with 'year', 'title', 'abstract'
        current_year: Current year for recency calculations
    
    Returns:
        TrendAnalysis object
    """
    if not sources:
        return TrendAnalysis(
            trend_direction="unknown",
            emerging_concepts=[],
            peak_year=0,
            year_distribution={},
            confidence=0.0,
        )
    
    # Extract years
    years = [s.get("year", 0) for s in sources if s.get("year", 0) > 0]
    
    if not years:
        return TrendAnalysis(
            trend_direction="unknown",
            emerging_concepts=[],
            peak_year=0,
            year_distribution={},
            confidence=0.0,
        )
    
    # Year distribution
    year_dist = defaultdict(int)
    for y in years:
        year_dist[y] += 1
    
    # Find peak year
    peak_year = max(year_dist.items(), key=lambda x: x[1])[0]
    
    # Calculate trend direction
    recent_threshold = current_year - 2  # Last 2 years
    recent_count = sum(1 for y in years if y >= recent_threshold)
    older_count = len(years) - recent_count
    
    if recent_count > older_count * 1.5:
        trend_direction = "growing"
    elif recent_count < older_count * 0.5:
        trend_direction = "declining"
    else:
        trend_direction = "stable"
    
    # Extract concepts from recent vs older papers
    recent_sources = [s for s in sources if s.get("year", 0) >= recent_threshold]
    older_sources = [s for s in sources if s.get("year", 0) < recent_threshold]
    
    recent_concepts = _extract_concepts_from_sources(recent_sources)
    older_concepts = _extract_concepts_from_sources(older_sources)
    
    # Emerging concepts: in recent but not (or less) in older
    emerging = []
    for concept, count in recent_concepts.items():
        old_count = older_concepts.get(concept, 0)
        if count > old_count * 2 or (old_count == 0 and count >= 2):
            emerging.append(concept)
    
    # Sort by frequency in recent papers
    emerging.sort(key=lambda c: -recent_concepts.get(c, 0))
    
    # Calculate confidence
    confidence = min(len(sources) / 10, 1.0)  # Higher confidence with more sources
    
    return TrendAnalysis(
        trend_direction=trend_direction,
        emerging_concepts=emerging[:5],
        peak_year=peak_year,
        year_distribution=dict(sorted(year_dist.items())),
        confidence=confidence,
    )


def _extract_concepts_from_sources(sources: list[dict]) -> dict[str, int]:
    """Extract concept frequency from sources."""
    from app.intelligence.knowledge_graph import extract_concepts_from_text
    
    concept_freq = defaultdict(int)
    
    for source in sources:
        text = f"{source.get('title', '')} {source.get('abstract', '')}"
        concepts = extract_concepts_from_text(text, max_concepts=5)
        for concept in concepts:
            concept_freq[concept] += 1
    
    return dict(concept_freq)


def format_trend_summary(analysis: TrendAnalysis) -> str:
    """Format trend analysis as readable text."""
    lines = []
    
    # Direction
    if analysis.trend_direction == "growing":
        lines.append("📈 **Research Activity: Growing**")
        lines.append("This topic shows increasing research interest in recent years.")
    elif analysis.trend_direction == "declining":
        lines.append("📉 **Research Activity: Declining**")
        lines.append("Research activity on this topic has slowed down recently.")
    else:
        lines.append("📊 **Research Activity: Stable**")
        lines.append("Research on this topic maintains consistent activity.")
    
    # Peak year
    if analysis.peak_year:
        lines.append(f"\n**Peak Year:** {analysis.peak_year}")
    
    # Emerging concepts
    if analysis.emerging_concepts:
        lines.append("\n**Emerging Concepts:**")
        for concept in analysis.emerging_concepts:
            lines.append(f"  • {concept}")
    
    # Year distribution
    if analysis.year_distribution:
        lines.append("\n**Publication Timeline:**")
        for year, count in sorted(analysis.year_distribution.items(), reverse=True)[:5]:
            bar = "█" * count
            lines.append(f"  {year}: {bar} ({count})")
    
    return "\n".join(lines)
