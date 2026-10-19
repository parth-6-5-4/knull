"""
Core configuration using Pydantic Settings.
Reads environment variables with sensible defaults for 8GB RAM optimization.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal


class Settings(BaseSettings):
    """Application configuration from environment variables."""
    
    # Ollama Configuration
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.2:3b")
    ollama_num_ctx: int = Field(default=4096, description="Context window size")
    
    # Embedding Model
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    
    # Storage Paths
    chroma_dir: str = Field(default="./chroma_data")
    sqlite_path: str = Field(default="./app_data/app.db")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    debug: bool = Field(default=True)
    
    # Research Defaults
    default_depth: Literal["quick", "normal", "deep"] = Field(default="normal")
    max_sources_quick: int = Field(default=5)
    max_sources_normal: int = Field(default=10)
    max_sources_deep: int = Field(default=20)
    max_retrieval_loops: int = Field(default=2)
    
    # Semantic Cache
    cache_similarity_threshold: float = Field(default=0.92)
    
    # Rate Limits
    semantic_scholar_rate_limit: int = Field(default=100)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def get_max_sources(self, depth: str) -> int:
        """Get max sources based on depth setting."""
        return {
            "quick": self.max_sources_quick,
            "normal": self.max_sources_normal,
            "deep": self.max_sources_deep
        }.get(depth, self.max_sources_normal)


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


# Convenience export
settings = get_settings()
