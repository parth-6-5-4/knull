"""
ChromaDB vector database operations.
Persistent storage with deduplication.
"""
import hashlib
from pathlib import Path
from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.core.logging import get_logger
from app.tools.embeddings import embed_texts, embed_single

logger = get_logger(__name__)

# Lazy-loaded client
_client = None
_collection = None


def _get_client() -> chromadb.PersistentClient:
    """Get or create ChromaDB client."""
    global _client
    
    if _client is None:
        persist_dir = Path(settings.chroma_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initializing ChromaDB at: {persist_dir}")
        
        _client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )
    
    return _client


def _get_collection(name: str = "research_chunks") -> chromadb.Collection:
    """Get or create the main collection."""
    global _collection
    
    if _collection is None or _collection.name != name:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"Using collection '{name}' with {_collection.count()} documents")
    
    return _collection


def generate_chunk_id(source_id: str, chunk_index: int) -> str:
    """Generate unique ID for a chunk."""
    content = f"{source_id}:{chunk_index}"
    return hashlib.md5(content.encode()).hexdigest()


def chroma_upsert(
    chunks: list[str],
    metadatas: list[dict],
    source_id: str,
    collection_name: str = "research_chunks",
) -> int:
    """
    Upsert chunks into ChromaDB with deduplication.
    
    Args:
        chunks: List of text chunks
        metadatas: List of metadata dicts (one per chunk)
        source_id: ID of the source document
        collection_name: Collection name
    
    Returns:
        Number of chunks upserted
    """
    if not chunks:
        return 0
    
    collection = _get_collection(collection_name)
    
    # Generate IDs and embeddings
    ids = [generate_chunk_id(source_id, i) for i in range(len(chunks))]
    
    logger.debug(f"Generating embeddings for {len(chunks)} chunks")
    embeddings = embed_texts(chunks)
    
    # Upsert (ChromaDB handles duplicates by ID)
    collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    
    logger.info(f"Upserted {len(chunks)} chunks for source '{source_id}'")
    return len(chunks)


def chroma_query(
    query: str,
    k: int = 5,
    where: Optional[dict] = None,
    collection_name: str = "research_chunks",
) -> list[dict]:
    """
    Query ChromaDB for similar chunks.
    
    Args:
        query: Query text
        k: Number of results to return
        where: Optional filter
        collection_name: Collection name
    
    Returns:
        List of results with text, metadata, and distance
    """
    collection = _get_collection(collection_name)
    
    if collection.count() == 0:
        logger.warning("Collection is empty, no results")
        return []
    
    # Generate query embedding
    query_embedding = embed_single(query)
    
    # Query
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(k, collection.count()),
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    
    # Format results
    formatted = []
    if results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            formatted.append({
                "text": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0,
                "similarity": 1 - results["distances"][0][i] if results["distances"] else 1,
            })
    
    logger.debug(f"Query returned {len(formatted)} results")
    return formatted


def chroma_delete_source(source_id: str, collection_name: str = "research_chunks"):
    """Delete all chunks for a source."""
    collection = _get_collection(collection_name)
    
    # Get all IDs for this source
    results = collection.get(
        where={"source_id": source_id},
        include=[],
    )
    
    if results["ids"]:
        collection.delete(ids=results["ids"])
        logger.info(f"Deleted {len(results['ids'])} chunks for source '{source_id}'")


def chroma_stats(collection_name: str = "research_chunks") -> dict:
    """Get collection statistics."""
    collection = _get_collection(collection_name)
    
    return {
        "name": collection.name,
        "count": collection.count(),
        "metadata": collection.metadata,
    }


def chroma_reset(collection_name: str = "research_chunks"):
    """Reset (delete all documents from) a collection."""
    client = _get_client()
    try:
        client.delete_collection(collection_name)
        logger.info(f"Deleted collection '{collection_name}'")
    except Exception:  # chromadb raises ValueError (0.4) or NotFoundError (1.x)
        pass  # Collection doesn't exist
    
    global _collection
    _collection = None
