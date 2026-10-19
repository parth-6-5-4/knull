"""Provider-agnostic LLM layer (OpenAI, Anthropic, Gemini, Ollama, mock)."""
from app.llm.router import (
    LLMError, LLMResponse, LLMRouter, ModelSpec, get_router, set_router, llm_chat, llm_complete,
)
from app.llm.config import LLMConfig, load_llm_config

__all__ = [
    "LLMError", "LLMResponse", "LLMRouter", "ModelSpec", "LLMConfig",
    "load_llm_config", "get_router", "set_router", "llm_chat", "llm_complete",
]
