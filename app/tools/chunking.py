"""
Text chunking utilities for RAG.
"""
from typing import Optional


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
    separator: str = " ",
) -> list[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Input text
        chunk_size: Target size of each chunk (in characters)
        overlap: Number of characters to overlap between chunks
        separator: Word separator
    
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    # Clean text
    text = text.strip()
    
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end near chunk boundary
            best_break = end
            for punct in [".", "!", "?", "\n\n", "\n"]:
                idx = text.rfind(punct, start + chunk_size // 2, end)
                if idx > start:
                    best_break = idx + 1
                    break
            end = best_break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start with overlap
        start = end - overlap
        if start <= 0:
            start = end
    
    return chunks


def chunk_by_sentences(
    text: str,
    max_sentences: int = 5,
    min_chunk_chars: int = 100,
) -> list[str]:
    """
    Split text into chunks by sentences.
    
    Args:
        text: Input text
        max_sentences: Maximum sentences per chunk
        min_chunk_chars: Minimum characters in a chunk
    
    Returns:
        List of text chunks
    """
    import re
    
    if not text:
        return []
    
    # Simple sentence splitting
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        current_chunk.append(sentence)
        current_length += len(sentence)
        
        if len(current_chunk) >= max_sentences or current_length >= min_chunk_chars * max_sentences:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= min_chunk_chars:
                chunks.append(chunk_text)
            current_chunk = []
            current_length = 0
    
    # Add remaining
    if current_chunk:
        chunk_text = " ".join(current_chunk)
        if len(chunk_text) >= min_chunk_chars // 2:  # Lower threshold for last chunk
            chunks.append(chunk_text)
    
    return chunks


def create_chunk_metadata(
    chunk: str,
    source_id: str,
    source_title: str,
    source_url: str,
    chunk_index: int,
    source_type: str = "academic",
) -> dict:
    """
    Create metadata dict for a chunk.
    
    Args:
        chunk: The chunk text
        source_id: ID of the source document
        source_title: Title of the source
        source_url: URL of the source
        chunk_index: Index of this chunk within the source
        source_type: Type of source (arxiv, semantic_scholar, wikipedia)
    
    Returns:
        Metadata dictionary
    """
    return {
        "source_id": source_id,
        "source_title": source_title,
        "source_url": source_url,
        "source_type": source_type,
        "chunk_index": chunk_index,
        "char_count": len(chunk),
    }
