"""
Query classifier for adaptive retrieval strategies.
Classifies queries to choose optimal search approach.
"""
import re
from enum import Enum
from dataclasses import dataclass
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class QueryType(str, Enum):
    """Types of research queries."""
    FACTUAL = "factual"         # "What is X?"
    COMPARATIVE = "comparative"  # "X vs Y", "Compare X and Y"
    EXPLORATORY = "exploratory"  # "Latest developments in X"
    METHODOLOGICAL = "methodological"  # "How to do X"
    HISTORICAL = "historical"    # "History of X", "Evolution of X"


@dataclass
class QueryClassification:
    """Result of query classification."""
    query_type: QueryType
    confidence: float
    extracted_terms: list[str]
    suggested_sources: list[str]
    max_results_multiplier: float
    
    def to_dict(self) -> dict:
        return {
            "query_type": self.query_type.value,
            "confidence": self.confidence,
            "extracted_terms": self.extracted_terms,
            "suggested_sources": self.suggested_sources,
            "max_results_multiplier": self.max_results_multiplier,
        }


# Pattern definitions
COMPARATIVE_PATTERNS = [
    r"\bvs\.?\b",
    r"\bversus\b",
    r"\bcompare\b",
    r"\bcomparison\b",
    r"\bdifference\s+between\b",
    r"\badvantages?\s+and\s+disadvantages?\b",
    r"\bpros?\s+and\s+cons?\b",
    r"\bbetter\s+than\b",
]

FACTUAL_PATTERNS = [
    r"^what\s+is\b",
    r"^what\s+are\b",
    r"^define\b",
    r"^explain\b",
    r"\bdefinition\s+of\b",
    r"^who\s+(invented|created|discovered)\b",
]

METHODOLOGICAL_PATTERNS = [
    r"^how\s+to\b",
    r"^how\s+do\b",
    r"^how\s+can\b",
    r"\bstep\s+by\s+step\b",
    r"\bimplementation\b",
    r"\btutorial\b",
    r"\bguide\s+to\b",
]

HISTORICAL_PATTERNS = [
    r"\bhistory\s+of\b",
    r"\bevolution\s+of\b",
    r"\borigin\s+of\b",
    r"\bdevelopment\s+of\b",
    r"\bhow\s+.*\s+evolved\b",
    r"\btimeline\b",
]

EXPLORATORY_PATTERNS = [
    r"\blatest\b",
    r"\brecent\b",
    r"\bcurrent\s+state\b",
    r"\bstate\s+of\s+the\s+art\b",
    r"\btrends?\b",
    r"\bfuture\s+of\b",
    r"\bemerging\b",
    r"\badvances?\s+in\b",
]


def classify_query(query: str) -> QueryClassification:
    """
    Classify a research query to determine optimal retrieval strategy.
    
    Args:
        query: The research query
    
    Returns:
        QueryClassification with type and recommendations
    """
    query_lower = query.lower().strip()
    
    # Check patterns in order of specificity
    scores = {
        QueryType.COMPARATIVE: _check_patterns(query_lower, COMPARATIVE_PATTERNS),
        QueryType.FACTUAL: _check_patterns(query_lower, FACTUAL_PATTERNS),
        QueryType.METHODOLOGICAL: _check_patterns(query_lower, METHODOLOGICAL_PATTERNS),
        QueryType.HISTORICAL: _check_patterns(query_lower, HISTORICAL_PATTERNS),
        QueryType.EXPLORATORY: _check_patterns(query_lower, EXPLORATORY_PATTERNS),
    }
    
    # Find best match
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    
    # Default to exploratory if no strong match
    if best_score == 0:
        best_type = QueryType.EXPLORATORY
        best_score = 0.5
    
    # Extract relevant terms
    terms = _extract_terms(query, best_type)
    
    # Get recommendations based on type
    sources, multiplier = _get_recommendations(best_type)
    
    classification = QueryClassification(
        query_type=best_type,
        confidence=min(best_score, 1.0),
        extracted_terms=terms,
        suggested_sources=sources,
        max_results_multiplier=multiplier,
    )
    
    logger.debug(f"Classified query as {best_type.value} (confidence={best_score:.2f})")
    return classification


def _check_patterns(text: str, patterns: list[str]) -> float:
    """Check how many patterns match and return score."""
    matches = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
    return min(matches * 0.5, 1.0)  # Cap at 1.0


def _extract_terms(query: str, query_type: QueryType) -> list[str]:
    """Extract key terms based on query type."""
    terms = []
    
    if query_type == QueryType.COMPARATIVE:
        # Extract comparison terms
        vs_match = re.search(r"(\w+(?:\s+\w+)?)\s+(?:vs\.?|versus)\s+(\w+(?:\s+\w+)?)", query, re.IGNORECASE)
        if vs_match:
            terms.extend([vs_match.group(1).strip(), vs_match.group(2).strip()])
        
        compare_match = re.search(r"compare\s+(\w+(?:\s+\w+)?)\s+(?:and|with)\s+(\w+(?:\s+\w+)?)", query, re.IGNORECASE)
        if compare_match:
            terms.extend([compare_match.group(1).strip(), compare_match.group(2).strip()])
    
    else:
        # General term extraction - remove common words
        stopwords = {"what", "is", "are", "the", "a", "an", "how", "to", "do", "can", "of", "in", "for"}
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
        terms = [w for w in words if w not in stopwords][:5]
    
    return terms


def _get_recommendations(query_type: QueryType) -> tuple[list[str], float]:
    """Get source recommendations and result multiplier for query type."""
    recommendations = {
        QueryType.FACTUAL: (
            ["wikipedia", "arxiv"],
            0.8,  # Fewer results needed
        ),
        QueryType.COMPARATIVE: (
            ["arxiv", "semantic_scholar"],
            1.5,  # More results for comparison
        ),
        QueryType.EXPLORATORY: (
            ["arxiv", "semantic_scholar", "wikipedia"],
            1.2,
        ),
        QueryType.METHODOLOGICAL: (
            ["arxiv", "semantic_scholar"],
            1.0,
        ),
        QueryType.HISTORICAL: (
            ["wikipedia", "semantic_scholar"],
            1.0,
        ),
    }
    
    return recommendations.get(query_type, (["arxiv", "semantic_scholar"], 1.0))


def generate_sub_queries(query: str, classification: QueryClassification) -> list[str]:
    """
    Generate sub-queries based on classification.
    
    Args:
        query: Original query
        classification: Query classification
    
    Returns:
        List of sub-queries to search
    """
    sub_queries = []
    
    if classification.query_type == QueryType.COMPARATIVE:
        # Search for each term separately, then combined
        for term in classification.extracted_terms:
            sub_queries.append(term)
        if len(classification.extracted_terms) >= 2:
            sub_queries.append(f"{classification.extracted_terms[0]} {classification.extracted_terms[1]} comparison")
    
    elif classification.query_type == QueryType.HISTORICAL:
        base_terms = " ".join(classification.extracted_terms)
        sub_queries.append(f"{base_terms} history")
        sub_queries.append(f"{base_terms} evolution")
        sub_queries.append(f"{base_terms} origins")
    
    elif classification.query_type == QueryType.METHODOLOGICAL:
        base_terms = " ".join(classification.extracted_terms)
        sub_queries.append(f"{base_terms} method")
        sub_queries.append(f"{base_terms} implementation")
        sub_queries.append(f"{base_terms} algorithm")
    
    else:
        # Default: use query as-is plus variations
        sub_queries.append(query)
        if classification.extracted_terms:
            sub_queries.append(" ".join(classification.extracted_terms))
    
    # Ensure we always have at least the original query
    if query not in sub_queries:
        sub_queries.insert(0, query)
    
    return sub_queries[:5]  # Limit to 5 sub-queries
