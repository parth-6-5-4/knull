"""
Tests for arXiv search tool.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tools.arxiv import search_arxiv, ArxivSource, format_arxiv_for_context


class TestArxivSource:
    """Tests for ArxivSource dataclass."""
    
    def test_to_dict(self):
        """Test ArxivSource serialization."""
        source = ArxivSource(
            id="2301.12345",
            title="Test Paper",
            authors=["Author One", "Author Two"],
            abstract="This is a test abstract.",
            url="https://arxiv.org/abs/2301.12345",
            pdf_url="https://arxiv.org/pdf/2301.12345.pdf",
            year=2023,
            published=datetime(2023, 1, 15),
            categories=["cs.AI", "cs.LG"],
        )
        
        d = source.to_dict()
        
        assert d["id"] == "2301.12345"
        assert d["title"] == "Test Paper"
        assert d["year"] == 2023
        assert d["source"] == "arxiv"
        assert len(d["authors"]) == 2


@pytest.mark.asyncio
async def test_search_arxiv_returns_list():
    """Test that search_arxiv returns a list."""
    # This is an integration test that hits the real arXiv API
    # Use a common query that should return results
    results = await search_arxiv("transformer attention", max_results=3)
    
    assert isinstance(results, list)
    # arXiv should have papers on transformers
    if results:  # May fail if no network
        assert isinstance(results[0], ArxivSource)
        assert results[0].title
        assert results[0].url


@pytest.mark.asyncio
async def test_search_arxiv_respects_max_results():
    """Test that max_results is respected."""
    results = await search_arxiv("machine learning", max_results=2)
    
    assert len(results) <= 2


@pytest.mark.asyncio
async def test_search_arxiv_handles_empty_query():
    """Test handling of problematic queries."""
    results = await search_arxiv("xyzqwertyuiopasdfghjklzxcvbnm12345")
    
    assert isinstance(results, list)
    # Unlikely to find results for random string


def test_format_arxiv_for_context():
    """Test formatting sources for LLM context."""
    sources = [
        ArxivSource(
            id="2301.12345",
            title="Paper One",
            authors=["Alice", "Bob", "Charlie", "David"],
            abstract="Abstract one " * 50,  # Long abstract
            url="https://arxiv.org/abs/2301.12345",
            pdf_url="https://arxiv.org/pdf/2301.12345.pdf",
            year=2023,
            published=datetime(2023, 1, 15),
            categories=["cs.AI"],
        ),
    ]
    
    formatted = format_arxiv_for_context(sources)
    
    assert "Paper One" in formatted
    assert "2023" in formatted
    assert "Alice" in formatted
    assert "..." in formatted  # Truncation


def test_format_arxiv_for_context_empty():
    """Test formatting with no sources."""
    formatted = format_arxiv_for_context([])
    
    assert "No sources" in formatted
