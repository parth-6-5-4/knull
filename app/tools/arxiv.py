"""
arXiv API client for searching academic papers.
"""
import arxiv
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ArxivSource:
    """Represents an arXiv paper."""
    id: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    pdf_url: str
    year: int
    published: datetime
    categories: list[str]
    source: str = "arxiv"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "year": self.year,
            "published": self.published.isoformat(),
            "categories": self.categories,
            "source": self.source,
        }


async def search_arxiv(
    query: str,
    max_results: int = 10,
    sort_by: arxiv.SortCriterion = arxiv.SortCriterion.Relevance,
    sort_order: arxiv.SortOrder = arxiv.SortOrder.Descending,
) -> list[ArxivSource]:
    """
    Search arXiv for papers matching query.
    
    Args:
        query: Search query string
        max_results: Maximum number of results
        sort_by: Sort criterion (Relevance, LastUpdatedDate, SubmittedDate)
        sort_order: Sort order (Ascending, Descending)
    
    Returns:
        List of ArxivSource objects
    """
    logger.info(f"Searching arXiv: '{query}' (max_results={max_results})")
    
    try:
        # Create search
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        
        # Fetch results (arxiv library is sync, but lightweight)
        results = []
        client = arxiv.Client()
        
        for paper in client.results(search):
            source = ArxivSource(
                id=paper.entry_id.split("/")[-1],
                title=paper.title.replace("\n", " ").strip(),
                authors=[a.name for a in paper.authors[:5]],  # Limit authors
                abstract=paper.summary.replace("\n", " ").strip(),
                url=paper.entry_id,
                pdf_url=paper.pdf_url,
                year=paper.published.year,
                published=paper.published,
                categories=paper.categories[:3],  # Limit categories
            )
            results.append(source)
        
        logger.info(f"Found {len(results)} papers for '{query}'")
        return results
        
    except Exception as e:
        logger.error(f"arXiv search failed: {e}")
        return []


def format_arxiv_for_context(sources: list[ArxivSource]) -> str:
    """Format sources as context for LLM."""
    if not sources:
        return "No sources found."
    
    lines = []
    for i, s in enumerate(sources, 1):
        authors_str = ", ".join(s.authors[:3])
        if len(s.authors) > 3:
            authors_str += " et al."
        
        lines.append(
            f"[{i}] {s.title} ({s.year})\n"
            f"    Authors: {authors_str}\n"
            f"    Abstract: {s.abstract[:300]}...\n"
            f"    URL: {s.url}\n"
        )
    
    return "\n".join(lines)
