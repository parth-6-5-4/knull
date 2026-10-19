"""
Safe URL fetching with best-effort text extraction.
Falls back to basic content if PDF parsing is too heavy.
"""
import httpx
from typing import Optional
from bs4 import BeautifulSoup

from app.core.logging import get_logger

logger = get_logger(__name__)

# Max content size to fetch (2MB)
MAX_CONTENT_SIZE = 2 * 1024 * 1024


async def safe_fetch_text(
    url: str,
    timeout: float = 30.0,
    max_chars: int = 10000,
) -> Optional[str]:
    """
    Safely fetch and extract text from a URL.
    
    Args:
        url: URL to fetch
        timeout: Request timeout
        max_chars: Maximum characters to return
    
    Returns:
        Extracted text or None
    """
    logger.debug(f"Fetching: {url}")
    
    try:
        headers = {
            "User-Agent": "ResearchCopilot/1.0 (Academic Research Tool)",
        }
        
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            # HEAD request first to check content type and size
            head_response = await client.head(url, headers=headers)
            
            content_type = head_response.headers.get("content-type", "")
            content_length = int(head_response.headers.get("content-length", 0))
            
            # Skip if too large
            if content_length > MAX_CONTENT_SIZE:
                logger.warning(f"Content too large: {content_length} bytes")
                return None
            
            # Skip PDFs (too heavy for light setup)
            if "pdf" in content_type.lower():
                logger.info(f"Skipping PDF: {url}")
                return None
            
            # Fetch content
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            # Extract text based on content type
            if "html" in content_type.lower():
                return _extract_html_text(response.text, max_chars)
            elif "text" in content_type.lower():
                return response.text[:max_chars]
            else:
                # Try HTML parsing anyway
                return _extract_html_text(response.text, max_chars)
                
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error fetching {url}: {e.response.status_code}")
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def _extract_html_text(html: str, max_chars: int) -> str:
    """Extract readable text from HTML."""
    try:
        soup = BeautifulSoup(html, "lxml")
        
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()
        
        # Get text
        text = soup.get_text(separator=" ", strip=True)
        
        # Clean up whitespace
        import re
        text = re.sub(r"\s+", " ", text)
        
        return text[:max_chars]
        
    except Exception as e:
        logger.warning(f"HTML extraction failed: {e}")
        return html[:max_chars]


async def fetch_arxiv_abstract(arxiv_url: str) -> Optional[str]:
    """
    Fetch abstract from arXiv abstract page.
    More reliable than PDF parsing.
    """
    # Convert PDF URL to abstract URL
    if "/pdf/" in arxiv_url:
        arxiv_url = arxiv_url.replace("/pdf/", "/abs/").replace(".pdf", "")
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(arxiv_url)
            response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "lxml")
        
        # Find abstract
        abstract_el = soup.find("blockquote", class_="abstract")
        if abstract_el:
            abstract = abstract_el.get_text(strip=True)
            # Remove "Abstract:" prefix if present
            if abstract.lower().startswith("abstract:"):
                abstract = abstract[9:].strip()
            return abstract
        
        return None
        
    except Exception as e:
        logger.warning(f"Failed to fetch arXiv abstract: {e}")
        return None
