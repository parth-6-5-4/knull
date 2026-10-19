"""
Hive Lite - FastAPI Application
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import research_router, runs_router, feedback_router, export_router, hive_router
from app.db import init_db
from app.core import settings, logger
from app.tools import check_ollama, chroma_stats
from app.llm import get_router
import os


def llm_status() -> dict:
    cfg = get_router().config
    specs = [cfg.default, *cfg.layers.values(), *cfg.agents.values()]
    used = sorted({x.provider for x in specs})
    envs = {'openai': 'OPENAI_API_KEY', 'anthropic': 'ANTHROPIC_API_KEY', 'gemini': 'GEMINI_API_KEY'}
    keys = {p: bool(os.getenv(cfg.provider_settings(p).api_key_env or envs[p])) for p in used if p in envs}
    f = lambda m: f'{m.provider}:{m.model}'
    return {
        'default': f(cfg.default),
        'layers': {k: f(v) for k, v in cfg.layers.items()},
        'agents': {k: f(v) for k, v in cfg.agents.items()},
        'providers_in_use': used,
        'keys_present': keys,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Hive Lite...")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Report LLM routing; only probe Ollama if a route uses it
    llm = llm_status()
    logger.info(f"LLM routing: default={llm['default']} layers={llm['layers']} agents={llm['agents']}")
    if "ollama" in llm["providers_in_use"]:
        ollama_status = await check_ollama()
        if not ollama_status["available"]:
            logger.warning(
                f"Ollama not available at {ollama_status['base_url']}. "
                "Run 'ollama serve' or route those layers to another provider in llm.yaml."
            )
    for prov, ok in llm["keys_present"].items():
        if not ok:
            logger.warning(f"Provider '{prov}' is routed but its API key env var is not set")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Hive Lite",
    description="""
    An AI-powered research assistant that:
    - Takes a research objective
    - Searches academic sources (arXiv, Semantic Scholar, Wikipedia)
    - Synthesizes a structured report with citations
    - Identifies gaps and contradictions
    
    Optimized for local execution on MacBook Pro M2 (8GB RAM).
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(research_router)
app.include_router(runs_router)
app.include_router(feedback_router)
app.include_router(export_router)
app.include_router(hive_router)


@app.get("/")
async def root():
    """Health check and API info."""
    return {
        "name": "Hive Lite",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    llm = llm_status()
    ollama_status = await check_ollama() if "ollama" in llm["providers_in_use"] else {"available": None, "note": "not routed"}
    
    try:
        chroma = chroma_stats()
    except Exception:
        chroma = {"error": "ChromaDB not initialized"}
    
    return {
        "status": "healthy",
        "components": {
            "ollama": ollama_status,
            "llm": llm,
            "chromadb": chroma,
            "database": "connected",
        },
        "config": {
            "model": settings.ollama_model,
            "context_window": settings.ollama_num_ctx,
            "embedding_model": settings.embedding_model,
        }
    }
