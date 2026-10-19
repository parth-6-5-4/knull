"""
Tests for Knowledge Graph.
"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.intelligence.knowledge_graph import KnowledgeGraph, extract_concepts_from_text


class TestKnowledgeGraph:
    """Tests for KnowledgeGraph class."""
    
    @pytest.fixture
    def kg(self):
        """Create fresh knowledge graph."""
        return KnowledgeGraph()
    
    def test_add_paper(self, kg):
        """Test adding a paper to the graph."""
        kg.add_paper(
            paper_id="paper1",
            title="Test Paper",
            concepts=["machine learning", "neural networks"],
            url="http://test.com",
            year=2023,
        )
        
        stats = kg.stats()
        assert stats["num_papers"] == 1
        assert stats["num_concepts"] == 2
    
    def test_find_related_papers(self, kg):
        """Test finding related papers through shared concepts."""
        kg.add_paper("paper1", "Paper One", ["attention", "transformer"], "", 2023)
        kg.add_paper("paper2", "Paper Two", ["attention", "memory"], "", 2023)
        kg.add_paper("paper3", "Paper Three", ["cnn", "image"], "", 2023)
        
        related = kg.find_related_papers("paper1")
        
        # paper2 shares "attention" concept
        assert len(related) >= 1
        related_ids = [r["paper_id"] for r in related]
        assert "paper2" in related_ids
        # paper3 doesn't share concepts
        assert "paper3" not in related_ids
    
    def test_get_shared_concepts(self, kg):
        """Test getting shared concepts between papers."""
        kg.add_paper("paper1", "Paper One", ["ml", "ai", "nlp"], "", 2023)
        kg.add_paper("paper2", "Paper Two", ["ml", "cv"], "", 2023)
        
        shared = kg.get_shared_concepts("paper1", "paper2")
        
        assert "ml" in shared
        assert "ai" not in shared
        assert "cv" not in shared
    
    def test_get_paper_concepts(self, kg):
        """Test getting all concepts for a paper."""
        kg.add_paper("paper1", "Paper One", ["concept1", "concept2", "concept3"], "", 2023)
        
        concepts = kg.get_paper_concepts("paper1")
        
        assert len(concepts) == 3
        assert "concept1" in concepts
    
    def test_get_top_concepts(self, kg):
        """Test getting most common concepts."""
        kg.add_paper("paper1", "Paper One", ["common", "rare1"], "", 2023)
        kg.add_paper("paper2", "Paper Two", ["common", "rare2"], "", 2023)
        kg.add_paper("paper3", "Paper Three", ["common", "rare3"], "", 2023)
        
        top = kg.get_top_concepts(n=2)
        
        assert top[0][0] == "common"  # Most frequent
        assert top[0][1] == 3
    
    def test_clear(self, kg):
        """Test clearing the graph."""
        kg.add_paper("paper1", "Test", ["concept"], "", 2023)
        
        kg.clear()
        
        stats = kg.stats()
        assert stats["num_papers"] == 0
        assert stats["num_concepts"] == 0


class TestConceptExtraction:
    """Tests for concept extraction."""
    
    def test_extract_concepts_from_text(self):
        """Test extracting concepts from text."""
        text = "Machine learning and neural networks are used for image classification tasks."
        
        concepts = extract_concepts_from_text(text, max_concepts=5)
        
        assert isinstance(concepts, list)
        assert len(concepts) <= 5
        # Should extract meaningful words
        assert any(c in ["machine", "learning", "neural", "networks", "image", "classification"] for c in concepts)
    
    def test_extract_concepts_empty(self):
        """Test extraction from empty text."""
        concepts = extract_concepts_from_text("")
        
        assert concepts == []
    
    def test_extract_concepts_stopwords_removed(self):
        """Test that stopwords are removed."""
        text = "The model is very good and it works well."
        
        concepts = extract_concepts_from_text(text, max_concepts=10)
        
        # Common stopwords should not appear
        assert "the" not in concepts
        assert "and" not in concepts
        assert "very" not in concepts
