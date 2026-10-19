"""Tools module exports."""
from app.tools.ollama_client import OllamaClient, OllamaError, ollama_chat, check_ollama
from app.tools.arxiv import search_arxiv, ArxivSource, format_arxiv_for_context
from app.tools.semantic_scholar import search_semantic_scholar, SemanticScholarSource, get_paper_by_id
from app.tools.wikipedia import search_wikipedia, WikipediaSource, get_wikipedia_content
from app.tools.fetch import safe_fetch_text, fetch_arxiv_abstract
from app.tools.chunking import chunk_text, chunk_by_sentences, create_chunk_metadata
from app.tools.embeddings import embed_texts, embed_single, get_embedding_dimension, cosine_similarity
from app.tools.vectordb import (
    chroma_upsert, chroma_query, chroma_delete_source, 
    chroma_stats, chroma_reset, generate_chunk_id
)

__all__ = [
    # Ollama
    "OllamaClient",
    "OllamaError",
    "ollama_chat",
    "check_ollama",
    # Sources
    "search_arxiv",
    "ArxivSource",
    "format_arxiv_for_context",
    "search_semantic_scholar",
    "SemanticScholarSource",
    "get_paper_by_id",
    "search_wikipedia",
    "WikipediaSource",
    "get_wikipedia_content",
    # Fetch
    "safe_fetch_text",
    "fetch_arxiv_abstract",
    # Chunking
    "chunk_text",
    "chunk_by_sentences",
    "create_chunk_metadata",
    # Embeddings
    "embed_texts",
    "embed_single",
    "get_embedding_dimension",
    "cosine_similarity",
    # VectorDB
    "chroma_upsert",
    "chroma_query",
    "chroma_delete_source",
    "chroma_stats",
    "chroma_reset",
    "generate_chunk_id",
]
