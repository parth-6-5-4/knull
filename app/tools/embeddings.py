"""
Sentence-Transformers embeddings.
Lazy loading to minimize startup memory.
"""
from typing import Optional
import numpy as np

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Lazy-loaded model instance
_model = None
_model_name = None


def _get_model():
    """Lazy load the embedding model."""
    global _model, _model_name
    
    if _model is None or _model_name != settings.embedding_model:
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        
        from sentence_transformers import SentenceTransformer
        
        # Extract model name from path
        model_name = settings.embedding_model
        if "/" in model_name:
            model_name = model_name.split("/")[-1]
        
        _model = SentenceTransformer(model_name)
        _model_name = settings.embedding_model
        
        logger.info(f"Embedding model loaded: {len(_model.encode('test'))} dimensions")
    
    return _model


def embed_texts(
    texts: list[str],
    batch_size: int = 32,
    show_progress: bool = False,
) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.
    
    Args:
        texts: List of texts to embed
        batch_size: Batch size for encoding (memory optimization)
        show_progress: Show progress bar
    
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    model = _get_model()
    
    logger.debug(f"Embedding {len(texts)} texts (batch_size={batch_size})")
    
    # Encode in batches to manage memory
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        convert_to_numpy=True,
    )
    
    # Convert to list of lists for JSON serialization
    return embeddings.tolist()


def embed_single(text: str) -> list[float]:
    """Embed a single text."""
    if not text:
        return []
    
    result = embed_texts([text])
    return result[0] if result else []


def get_embedding_dimension() -> int:
    """Get the dimension of embeddings."""
    model = _get_model()
    return model.get_sentence_embedding_dimension()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(dot_product / (norm_a * norm_b))
