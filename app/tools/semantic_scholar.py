"""
Semantic Scholar API client.
Free tier: 100 requests per 5 minutes.
"""
import httpx
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import asyncio

from app.core.logging import get_logger

logger = get_logger(__name__)

# Rate limiter
_last_request_time = 0
_request_interval = 3.0  # seconds between requests (conservative)


@dataclass
class SemanticScholarSource:
    """Represents a Semantic Scholar paper."""
    id: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    year: int
    citation_count: int
    venue: Optional[str]
    source: str = "semantic_scholar"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "url": self.url,
            "year": self.year,
            "citation_count": self.citation_count,
            "venue": self.venue,
            "source": self.source,
        }


async def _rate_limit():
    """Simple rate limiter."""
    global _last_request_time
    import time
    
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < _request_interval:
        await asyncio.sleep(_request_interval - elapsed)
    _last_request_time = time.time()


async def search_semantic_scholar(
    query: str,
    max_results: int = 10,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
) -> list[SemanticScholarSource]:
    """
    Search Semantic Scholar for papers.
    
    Args:
        query: Search query
        max_results: Maximum results (API limit: 100)
        year_from: Filter papers from this year
        year_to: Filter papers up to this year
    
    Returns:
        List of SemanticScholarSource objects
    """
    logger.info(f"Searching Semantic Scholar: '{query}'")
    
    await _rate_limit()
    
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    params = {
        "query": query,
        "limit": min(max_results, 100),
        "fields": "paperId,title,abstract,authors,year,citationCount,venue,url",
    }
    
    if year_from and year_to:
        params["year"] = f"{year_from}-{year_to}"
    elif year_from:
        params["year"] = f"{year_from}-"
    elif year_to:
        params["year"] = f"-{year_to}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(base_url, params=params)
            
            if response.status_code == 429:
                logger.warning("Semantic Scholar rate limit hit")
                return []
            
            response.raise_for_status()
            data = response.json()
        
        results = []
        for paper in data.get("data", []):
            if not paper.get("abstract"):
                continue  # Skip papers without abstracts
            
            source = SemanticScholarSource(
                id=paper.get("paperId", ""),
                title=paper.get("title", "").strip(),
                authors=[a.get("name", "") for a in paper.get("authors", [])[:5]],
                abstract=paper.get("abstract", "").strip(),
                url=paper.get("url", f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}"),
                year=paper.get("year", 0) or 0,
                citation_count=paper.get("citationCount", 0) or 0,
                venue=paper.get("venue"),
            )
            results.append(source)
        
        logger.info(f"Found {len(results)} papers from Semantic Scholar")
        return results
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Semantic Scholar API error: {e}")
        return []
    except Exception as e:
        logger.error(f"Semantic Scholar search failed: {e}")
        return []


async def get_paper_by_id(paper_id: str) -> Optional[SemanticScholarSource]:
    """Get paper details by Semantic Scholar ID."""
    await _rate_limit()
    
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
    params = {
        "fields": "paperId,title,abstract,authors,year,citationCount,venue,url"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            paper = response.json()
        
        return SemanticScholarSource(
            id=paper.get("paperId", ""),
            title=paper.get("title", "").strip(),
            authors=[a.get("name", "") for a in paper.get("authors", [])[:5]],
            abstract=paper.get("abstract", "").strip(),
            url=paper.get("url", f"https://www.semanticscholar.org/paper/{paper_id}"),
            year=paper.get("year", 0) or 0,
            citation_count=paper.get("citationCount", 0) or 0,
            venue=paper.get("venue"),
        )
        
    except Exception as e:
        logger.error(f"Failed to get paper {paper_id}: {e}")
        return None
