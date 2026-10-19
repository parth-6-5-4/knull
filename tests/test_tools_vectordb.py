"""
Tests for ChromaDB vector database operations.
"""
import pytest
import tempfile
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test database path before imports
os.environ["CHROMA_DIR"] = tempfile.mkdtemp()

from app.tools.vectordb import (
    chroma_upsert, chroma_query, chroma_delete_source,
    chroma_stats, chroma_reset, generate_chunk_id
)
from app.tools.chunking import create_chunk_metadata


class TestChromaDB:
    """Tests for ChromaDB operations."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset collection before each test."""
        chroma_reset("test_collection")
        yield
        chroma_reset("test_collection")
    
    def test_generate_chunk_id(self):
        """Test chunk ID generation."""
        id1 = generate_chunk_id("source1", 0)
        id2 = generate_chunk_id("source1", 1)
        id3 = generate_chunk_id("source1", 0)
        
        assert id1 != id2  # Different chunks
        assert id1 == id3  # Same source and index
    
    def test_chroma_upsert(self):
        """Test upserting chunks."""
        chunks = [
            "This is the first chunk about machine learning.",
            "This is the second chunk about neural networks.",
        ]
        metadatas = [
            create_chunk_metadata(c, "source1", "Test Paper", "http://test.com", i, "arxiv")
            for i, c in enumerate(chunks)
        ]
        
        count = chroma_upsert(chunks, metadatas, "source1", "test_collection")
        
        assert count == 2
    
    def test_chroma_query(self):
        """Test querying for similar chunks."""
        # Insert test data
        chunks = [
            "Transformer models use self-attention mechanisms for sequence processing.",
            "Convolutional neural networks are effective for image classification.",
            "Recurrent neural networks process sequential data with hidden states.",
        ]
        metadatas = [
            create_chunk_metadata(c, "source1", "Test Paper", "http://test.com", i, "arxiv")
            for i, c in enumerate(chunks)
        ]
        chroma_upsert(chunks, metadatas, "source1", "test_collection")
        
        # Query
        results = chroma_query("attention mechanism", k=2, collection_name="test_collection")
        
        assert len(results) <= 2
        if results:
            assert "text" in results[0]
            assert "metadata" in results[0]
            assert "similarity" in results[0]
            # First result should be about transformers/attention
            assert "attention" in results[0]["text"].lower() or "transformer" in results[0]["text"].lower()
    
    def test_chroma_upsert_deduplication(self):
        """Test that upserting same source twice doesn't duplicate."""
        chunks = ["Test chunk content."]
        metadatas = [create_chunk_metadata(chunks[0], "source1", "Test", "http://test.com", 0, "arxiv")]
        
        # Upsert twice
        chroma_upsert(chunks, metadatas, "source1", "test_collection")
        chroma_upsert(chunks, metadatas, "source1", "test_collection")
        
        stats = chroma_stats("test_collection")
        assert stats["count"] == 1  # Should not duplicate
    
    def test_chroma_delete_source(self):
        """Test deleting all chunks for a source."""
        chunks = ["Chunk one.", "Chunk two."]
        metadatas = [
            create_chunk_metadata(c, "source_to_delete", "Test", "http://test.com", i, "arxiv")
            for i, c in enumerate(chunks)
        ]
        chroma_upsert(chunks, metadatas, "source_to_delete", "test_collection")
        
        # Verify inserted
        stats = chroma_stats("test_collection")
        assert stats["count"] == 2
        
        # Delete
        chroma_delete_source("source_to_delete", "test_collection")
        
        # Verify deleted
        stats = chroma_stats("test_collection")
        assert stats["count"] == 0
    
    def test_chroma_query_empty_collection(self):
        """Test querying empty collection returns empty list."""
        results = chroma_query("test query", k=5, collection_name="test_collection")
        
        assert results == []
    
    def test_chroma_stats(self):
        """Test getting collection statistics."""
        stats = chroma_stats("test_collection")
        
        assert "name" in stats
        assert "count" in stats
        assert stats["name"] == "test_collection"
