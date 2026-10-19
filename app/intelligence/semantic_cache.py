"""
Semantic query cache using ChromaDB.
Avoids redundant LLM calls for similar queries.
"""
import hashlib
from datetime import datetime
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.core.logging import get_logger
from app.tools.embeddings import embed_single

logger = get_logger(__name__)

# Cache collection name
CACHE_COLLECTION = "query_cache"


class SemanticCache:
    """
    Cache LLM responses based on semantic similarity.
    If a similar query was asked before, return cached response.
    """
    
    def __init__(
        self,
        similarity_threshold: float = None,
        persist_dir: str = None,
    ):
        """
        Initialize semantic cache.
        
        Args:
            similarity_threshold: Minimum similarity for cache hit (0-1)
            persist_dir: ChromaDB persist directory
        """
        self.threshold = similarity_threshold or settings.cache_similarity_threshold
        persist_dir = persist_dir or settings.chroma_dir
        
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),  # must match app.tools.vectordb: chroma refuses two clients with different settings on one path
        )
        self._collection = self._client.get_or_create_collection(
            name=CACHE_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        
        logger.info(f"Semantic cache initialized (threshold={self.threshold}, count={self._collection.count()})")
    
    def get(self, query: str, context_key: str = "") -> Optional[str]:
        """
        Get cached response for a query.
        
        Args:
            query: The query string
            context_key: Optional context to narrow cache scope
        
        Returns:
            Cached response or None
        """
        if self._collection.count() == 0:
            return None
        
        # Generate query embedding
        query_embedding = embed_single(query)
        
        # Build filter
        where = {"context_key": context_key} if context_key else None
        
        # Search for similar queries
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=1,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        
        if not results["distances"] or not results["distances"][0]:
            return None
        
        distance = results["distances"][0][0]
        similarity = 1 - distance
        
        if similarity >= self.threshold:
            cached_response = results["metadatas"][0][0].get("response", "")
            cached_query = results["documents"][0][0]
            
            logger.debug(
                f"Cache HIT (similarity={similarity:.3f}): "
                f"'{query[:50]}...' matched '{cached_query[:50]}...'"
            )
            return cached_response
        
        logger.debug(f"Cache MISS (similarity={similarity:.3f})")
        return None
    
    def set(
        self,
        query: str,
        response: str,
        context_key: str = "",
        ttl_hours: int = 24,
    ):
        """
        Cache a query-response pair.
        
        Args:
            query: The query string
            response: The LLM response
            context_key: Optional context key
            ttl_hours: Time-to-live in hours (for future cleanup)
        """
        # Generate unique ID
        cache_id = hashlib.md5(f"{context_key}:{query}".encode()).hexdigest()
        
        # Generate embedding
        query_embedding = embed_single(query)
        
        # Store
        self._collection.upsert(
            ids=[cache_id],
            embeddings=[query_embedding],
            documents=[query],
            metadatas=[{
                "response": response,
                "context_key": context_key,
                "created_at": datetime.utcnow().isoformat(),
                "ttl_hours": ttl_hours,
            }],
        )
        
        logger.debug(f"Cached response for: '{query[:50]}...'")
    
    def invalidate(self, context_key: str = ""):
        """Invalidate cache entries by context key."""
        if not context_key:
            # Clear all
            self._client.delete_collection(CACHE_COLLECTION)
            self._collection = self._client.get_or_create_collection(
                name=CACHE_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("Cache cleared")
        else:
            # Delete by context key
            results = self._collection.get(
                where={"context_key": context_key},
                include=[],
            )
            if results["ids"]:
                self._collection.delete(ids=results["ids"])
                logger.info(f"Invalidated {len(results['ids'])} cache entries")
    
    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "count": self._collection.count(),
            "threshold": self.threshold,
        }


# Global cache instance (lazy)
_cache_instance = None


def get_cache() -> SemanticCache:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SemanticCache()
    return _cache_instance
