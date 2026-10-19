"""Intelligence module exports."""
from app.intelligence.knowledge_graph import (
    KnowledgeGraph, 
    extract_concepts_from_text,
)
from app.intelligence.semantic_cache import (
    SemanticCache, 
    get_cache,
)
from app.intelligence.trend_detector import (
    TrendAnalysis,
    detect_trends,
    format_trend_summary,
)
from app.intelligence.query_classifier import (
    QueryType,
    QueryClassification,
    classify_query,
    generate_sub_queries,
)

__all__ = [
    # Knowledge Graph
    "KnowledgeGraph",
    "extract_concepts_from_text",
    # Semantic Cache
    "SemanticCache",
    "get_cache",
    # Trend Detection
    "TrendAnalysis",
    "detect_trends",
    "format_trend_summary",
    # Query Classification
    "QueryType",
    "QueryClassification",
    "classify_query",
    "generate_sub_queries",
]
