"""
Wikipedia search for background context.
"""
import httpx

# Wikipedia's API policy returns 403 for requests without a descriptive User-Agent.
WIKI_HEADERS = {"User-Agent": "ResearchCopilot/1.0 (Academic Research Tool; https://github.com/parth-6-5-4/agentic_research_copilot)"}
from dataclasses import dataclass
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WikipediaSource:
    """Represents a Wikipedia article."""
    id: str
    title: str
    extract: str
    url: str
    source: str = "wikipedia"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "abstract": self.extract,  # Use extract as abstract for consistency
            "url": self.url,
            "source": self.source,
        }


async def search_wikipedia(
    query: str,
    max_results: int = 3,
    extract_chars: int = 500,
    *, raise_on_error: bool = False,
) -> list[WikipediaSource]:
    """
    Search Wikipedia for relevant articles.
    
    Args:
        query: Search query
        max_results: Maximum results
        extract_chars: Max characters in extract
    
    Returns:
        List of WikipediaSource objects
    """
    logger.info(f"Searching Wikipedia: '{query}'")
    
    # First, search for matching titles
    search_url = "https://en.wikipedia.org/w/api.php"
    search_params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": max_results,
        "format": "json",
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=WIKI_HEADERS) as client:
            # Search
            response = await client.get(search_url, params=search_params)
            response.raise_for_status()
            search_data = response.json()
        
        search_results = search_data.get("query", {}).get("search", [])
        if not search_results:
            return []
        
        # Get extracts for found pages
        page_ids = [str(r["pageid"]) for r in search_results]
        
        extract_params = {
            "action": "query",
            "pageids": "|".join(page_ids),
            "prop": "extracts|info",
            "exintro": True,
            "explaintext": True,
            "exchars": extract_chars,
            "inprop": "url",
            "format": "json",
        }
        
        async with httpx.AsyncClient(timeout=15.0, headers=WIKI_HEADERS) as client:
            response = await client.get(search_url, params=extract_params)
            response.raise_for_status()
            extract_data = response.json()
        
        pages = extract_data.get("query", {}).get("pages", {})
        
        results = []
        for page_id, page in pages.items():
            if "extract" not in page:
                continue
            
            source = WikipediaSource(
                id=page_id,
                title=page.get("title", ""),
                extract=page.get("extract", "").strip(),
                url=page.get("fullurl", f"https://en.wikipedia.org/?curid={page_id}"),
            )
            results.append(source)
        
        logger.info(f"Found {len(results)} Wikipedia articles")
        return results
        
    except Exception as e:
        logger.error(f"Wikipedia search failed: {e}")
        if raise_on_error:
            raise
        return []


async def get_wikipedia_content(title: str, max_chars: int = 2000) -> Optional[str]:
    """
    Get full content of a Wikipedia article.
    
    Args:
        title: Article title
        max_chars: Maximum characters to return
    
    Returns:
        Article content or None
    """
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "extracts",
        "explaintext": True,
        "format": "json",
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=WIKI_HEADERS) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            content = page.get("extract", "")
            if content:
                return content[:max_chars]
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to get Wikipedia content: {e}")
        return None
