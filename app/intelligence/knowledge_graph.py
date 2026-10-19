"""
Knowledge Graph for connecting papers by concepts.
Uses NetworkX for graph operations.
"""
import networkx as nx
from typing import Optional
from collections import defaultdict

from app.core.logging import get_logger

logger = get_logger(__name__)


class KnowledgeGraph:
    """
    Graph connecting papers through shared concepts.
    Enables multi-hop reasoning for finding related work.
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self._concept_papers = defaultdict(set)  # concept -> set of paper_ids
        self._paper_concepts = defaultdict(set)  # paper_id -> set of concepts
    
    def add_paper(
        self,
        paper_id: str,
        title: str,
        concepts: list[str],
        url: str = "",
        year: int = 0,
    ):
        """
        Add a paper and its concepts to the graph.
        
        Args:
            paper_id: Unique paper identifier
            title: Paper title
            concepts: List of concepts/keywords
            url: Paper URL
            year: Publication year
        """
        # Add paper node
        self.graph.add_node(
            paper_id,
            type="paper",
            title=title,
            url=url,
            year=year,
        )
        
        # Add concept nodes and edges
        for concept in concepts:
            concept_lower = concept.lower().strip()
            if not concept_lower:
                continue
            
            # Add concept node if new
            if not self.graph.has_node(concept_lower):
                self.graph.add_node(concept_lower, type="concept")
            
            # Add edge: paper -> concept
            self.graph.add_edge(paper_id, concept_lower)
            
            # Update indexes
            self._concept_papers[concept_lower].add(paper_id)
            self._paper_concepts[paper_id].add(concept_lower)
        
        logger.debug(f"Added paper '{paper_id}' with {len(concepts)} concepts")
    
    def find_related_papers(
        self,
        paper_id: str,
        max_hops: int = 2,
        max_results: int = 10,
    ) -> list[dict]:
        """
        Find papers related through shared concepts.
        
        Args:
            paper_id: Source paper ID
            max_hops: Maximum graph hops (2 = shares a concept)
            max_results: Maximum results
        
        Returns:
            List of related papers with distance
        """
        if not self.graph.has_node(paper_id):
            return []
        
        # Get all reachable nodes within max_hops
        # Edges are directed paper -> concept, so traverse the undirected view
        # to reach other papers through a shared concept.
        lengths = nx.single_source_shortest_path_length(
            self.graph.to_undirected(as_view=True), paper_id, cutoff=max_hops
        )
        
        # Filter to papers only
        related = []
        for node, distance in lengths.items():
            if distance == 0:
                continue  # Skip self
            if self.graph.nodes[node].get("type") == "paper":
                related.append({
                    "paper_id": node,
                    "title": self.graph.nodes[node].get("title", ""),
                    "url": self.graph.nodes[node].get("url", ""),
                    "distance": distance,
                })
        
        # Sort by distance, then by year
        related.sort(key=lambda x: (x["distance"], -self.graph.nodes[x["paper_id"]].get("year", 0)))
        
        return related[:max_results]
    
    def find_papers_by_concept(self, concept: str) -> list[str]:
        """Find all papers containing a concept."""
        concept_lower = concept.lower().strip()
        return list(self._concept_papers.get(concept_lower, set()))
    
    def get_shared_concepts(self, paper_id1: str, paper_id2: str) -> list[str]:
        """Get concepts shared between two papers."""
        concepts1 = self._paper_concepts.get(paper_id1, set())
        concepts2 = self._paper_concepts.get(paper_id2, set())
        return list(concepts1 & concepts2)
    
    def get_paper_concepts(self, paper_id: str) -> list[str]:
        """Get all concepts for a paper."""
        return list(self._paper_concepts.get(paper_id, set()))
    
    def get_concept_frequency(self) -> dict[str, int]:
        """Get frequency of each concept across papers."""
        return {concept: len(papers) for concept, papers in self._concept_papers.items()}
    
    def get_top_concepts(self, n: int = 10) -> list[tuple[str, int]]:
        """Get most common concepts."""
        freq = self.get_concept_frequency()
        return sorted(freq.items(), key=lambda x: -x[1])[:n]
    
    def stats(self) -> dict:
        """Get graph statistics."""
        papers = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "paper"]
        concepts = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "concept"]
        
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "num_papers": len(papers),
            "num_concepts": len(concepts),
            "avg_concepts_per_paper": len(self.graph.edges()) / len(papers) if papers else 0,
        }
    
    def clear(self):
        """Clear the graph."""
        self.graph.clear()
        self._concept_papers.clear()
        self._paper_concepts.clear()


def extract_concepts_from_text(text: str, max_concepts: int = 10) -> list[str]:
    """
    Extract key concepts from text using simple heuristics.
    For production, consider using KeyBERT or similar.
    
    Args:
        text: Input text
        max_concepts: Maximum concepts to extract
    
    Returns:
        List of concepts
    """
    import re
    
    # Simple keyword extraction
    # Remove common words and extract noun phrases
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "of", "to", "in",
        "for", "on", "with", "at", "by", "from", "as", "into", "through",
        "during", "before", "after", "above", "below", "between", "under",
        "again", "further", "then", "once", "here", "there", "when", "where",
        "why", "how", "all", "each", "few", "more", "most", "other", "some",
        "such", "no", "nor", "not", "only", "own", "same", "so", "than",
        "too", "very", "just", "but", "and", "or", "if", "because", "until",
        "while", "this", "that", "these", "those", "we", "our", "they", "their",
        "its", "which", "who", "what", "it",
    }
    
    # Tokenize and filter
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Count word frequency
    word_freq = defaultdict(int)
    for word in words:
        if word not in stopwords:
            word_freq[word] += 1
    
    # Get top words
    top_words = sorted(word_freq.items(), key=lambda x: -x[1])
    concepts = [word for word, _ in top_words[:max_concepts]]
    
    return concepts
