"""
Ollama HTTP client for local LLM inference.
Supports streaming and robust error handling.
"""
import httpx
from typing import AsyncGenerator, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OllamaError(Exception):
    """Ollama client error."""
    pass


class OllamaClient:
    """Async client for Ollama API."""
    
    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        num_ctx: int = None,
        timeout: float = 120.0,
    ):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.num_ctx = num_ctx or settings.ollama_num_ctx
        self.timeout = timeout
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def chat(
        self,
        messages: list[dict],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
    ) -> str:
        """
        Send chat completion request.
        
        Args:
            messages: List of {"role": "...", "content": "..."} dicts
            model: Override default model
            temperature: Sampling temperature
            max_tokens: Max tokens in response
            
        Returns:
            Generated text response
        """
        model = model or self.model
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": self.num_ctx,
                "temperature": temperature,
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["message"]["content"]
                
        except httpx.ConnectError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}")
            raise OllamaError(
                f"Cannot connect to Ollama. Is it running? "
                f"Try: ollama serve"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API error: {e.response.text}")
            raise OllamaError(f"Ollama API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            raise OllamaError(str(e))
    
    async def chat_stream(
        self,
        messages: list[dict],
        model: str = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion response.
        
        Yields:
            Text chunks as they arrive
        """
        model = model or self.model
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "num_ctx": self.num_ctx,
                "temperature": temperature,
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            import json
                            data = json.loads(line)
                            if "message" in data:
                                yield data["message"].get("content", "")
                                
        except httpx.ConnectError:
            raise OllamaError(f"Cannot connect to Ollama at {self.base_url}")
        except Exception as e:
            logger.error(f"Ollama stream failed: {e}")
            raise OllamaError(str(e))
    
    async def is_available(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    # Check if our model is available (with or without tag)
                    model_base = self.model.split(":")[0]
                    return any(model_base in m for m in models)
            return False
        except Exception:
            return False


# Convenience functions
async def ollama_chat(
    messages: list[dict],
    model: str = None,
    base_url: str = None,
    num_ctx: int = None,
    temperature: float = 0.7,
) -> str:
    """Convenience function for chat completion."""
    client = OllamaClient(base_url=base_url, model=model, num_ctx=num_ctx)
    return await client.chat(messages, temperature=temperature)


async def check_ollama() -> dict:
    """Check Ollama status."""
    client = OllamaClient()
    available = await client.is_available()
    return {
        "available": available,
        "base_url": client.base_url,
        "model": client.model,
        "num_ctx": client.num_ctx,
    }
