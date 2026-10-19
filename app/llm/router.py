"""Router that sends each call to the SDK for the provider configured for its layer/agent."""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from app.core.logging import get_logger
from app.llm.config import LLMConfig, ModelSpec, load_llm_config

logger = get_logger(__name__)


class LLMError(Exception):
    """Any LLM call failure (missing key, SDK error, network)."""


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


def _split_system(messages: list[dict]) -> tuple[str, list[dict]]:
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    rest = [m for m in messages if m["role"] != "system"]
    return system, rest


# --- provider adapters -------------------------------------------------------------

async def _call_openai(spec: ModelSpec, messages, cfg: LLMConfig, temperature, max_tokens) -> LLMResponse:
    from openai import AsyncOpenAI

    ps = cfg.provider_settings("openai")
    key = os.getenv(ps.api_key_env or "OPENAI_API_KEY")
    if not key:
        raise LLMError(f"Missing {ps.api_key_env or 'OPENAI_API_KEY'}")
    client = AsyncOpenAI(api_key=key, base_url=ps.base_url, timeout=ps.timeout)
    kwargs = {"model": spec.model, "messages": messages}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens:
        kwargs["max_completion_tokens"] = max_tokens
    r = await client.chat.completions.create(**kwargs)
    u = r.usage
    return LLMResponse(r.choices[0].message.content or "", "openai", spec.model,
                       getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0)


async def _call_anthropic(spec: ModelSpec, messages, cfg: LLMConfig, temperature, max_tokens) -> LLMResponse:
    from anthropic import AsyncAnthropic

    ps = cfg.provider_settings("anthropic")
    key = os.getenv(ps.api_key_env or "ANTHROPIC_API_KEY")
    if not key:
        raise LLMError(f"Missing {ps.api_key_env or 'ANTHROPIC_API_KEY'}")
    client = AsyncAnthropic(api_key=key, base_url=ps.base_url, timeout=ps.timeout)
    system, rest = _split_system(messages)
    kwargs = {"model": spec.model, "messages": rest, "max_tokens": max_tokens or 2048}
    if system:
        kwargs["system"] = system
    # Some SDK/model generations no longer accept `temperature`; only send it if the SDK supports it.
    import inspect
    if temperature is not None and "temperature" in inspect.signature(client.messages.create).parameters:
        kwargs["temperature"] = temperature
    r = await client.messages.create(**kwargs)
    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    return LLMResponse(text, "anthropic", spec.model,
                       getattr(r.usage, "input_tokens", 0) or 0, getattr(r.usage, "output_tokens", 0) or 0)


async def _call_gemini(spec: ModelSpec, messages, cfg: LLMConfig, temperature, max_tokens) -> LLMResponse:
    from google import genai
    from google.genai import types

    ps = cfg.provider_settings("gemini")
    key = os.getenv(ps.api_key_env or "GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise LLMError(f"Missing {ps.api_key_env or 'GEMINI_API_KEY'}")
    client = genai.Client(api_key=key, http_options=types.HttpOptions(base_url=ps.base_url) if ps.base_url else None)
    system, rest = _split_system(messages)
    contents = [
        types.Content(role="model" if m["role"] == "assistant" else "user",
                      parts=[types.Part(text=m["content"])])
        for m in rest
    ]
    config = types.GenerateContentConfig(
        system_instruction=system or None,
        temperature=temperature,
        max_output_tokens=max_tokens,
    )
    r = await client.aio.models.generate_content(model=spec.model, contents=contents, config=config)
    um = getattr(r, "usage_metadata", None)
    return LLMResponse(r.text or "", "gemini", spec.model,
                       getattr(um, "prompt_token_count", 0) or 0,
                       getattr(um, "candidates_token_count", 0) or 0)


async def _call_ollama(spec: ModelSpec, messages, cfg: LLMConfig, temperature, max_tokens) -> LLMResponse:
    import httpx

    ps = cfg.provider_settings("ollama")
    base = ps.base_url or "http://localhost:11434"
    payload = {"model": spec.model, "messages": messages, "stream": False,
               "options": {"temperature": temperature if temperature is not None else 0.7}}
    if max_tokens:
        payload["options"]["num_predict"] = max_tokens
    try:
        async with httpx.AsyncClient(timeout=ps.timeout) as c:
            r = await c.post(f"{base}/api/chat", json=payload)
            r.raise_for_status()
            d = r.json()
    except httpx.ConnectError as e:
        raise LLMError(f"Cannot connect to Ollama at {base}. Is it running? (ollama serve)") from e
    except Exception as e:
        raise LLMError(f"Ollama request failed: {e}") from e
    return LLMResponse(d["message"]["content"], "ollama", spec.model,
                       d.get("prompt_eval_count", 0) or 0, d.get("eval_count", 0) or 0)


MockHandler = Callable[[ModelSpec, list[dict]], str]


class LLMRouter:
    def __init__(self, config: Optional[LLMConfig] = None, mock_handler: Optional[MockHandler] = None):
        self.config = config or load_llm_config()
        self.mock_handler = mock_handler
        self.calls: list[dict] = []  # light call log: layer/agent/provider/model/tokens

    async def _mock(self, spec, messages, *_a) -> LLMResponse:
        if not self.mock_handler:
            raise LLMError("mock provider selected but no mock_handler set")
        text = self.mock_handler(spec, messages)
        if asyncio.iscoroutine(text):
            text = await text
        n_in = sum(len(m["content"]) for m in messages) // 4
        return LLMResponse(text, "mock", spec.model, n_in, len(text) // 4)

    async def complete(self, messages: list[dict], layer: Optional[str] = None,
                       agent: Optional[str] = None, temperature: Optional[float] = None,
                       max_tokens: Optional[int] = None, retries: int = 2) -> LLMResponse:
        spec = self.config.resolve(layer, agent)
        temperature = temperature if temperature is not None else spec.temperature
        max_tokens = max_tokens or spec.max_tokens
        adapters = {"openai": _call_openai, "anthropic": _call_anthropic, "gemini": _call_gemini,
                    "ollama": _call_ollama, "mock": self._mock}
        fn = adapters[spec.provider]
        last: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                resp = await fn(spec, messages, self.config, temperature, max_tokens)
                self.calls.append({"layer": layer, "agent": agent, "provider": resp.provider,
                                   "model": resp.model, "in": resp.input_tokens, "out": resp.output_tokens})
                return resp
            except LLMError as e:
                if "Missing" in str(e) or "Cannot connect" in str(e):
                    raise  # not retryable
                last = e
            except ImportError as e:
                raise LLMError(f"SDK for provider '{spec.provider}' is not installed: {e}") from e
            except Exception as e:
                last = e
            await asyncio.sleep(min(2 ** attempt, 8))
        raise LLMError(f"{spec.provider}/{spec.model} failed: {last}") from last


_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


def set_router(r: Optional[LLMRouter]) -> None:
    global _router
    _router = r


async def llm_complete(messages, layer=None, agent=None, **kw) -> LLMResponse:
    return await get_router().complete(messages, layer=layer, agent=agent, **kw)


async def llm_chat(messages, layer=None, agent=None, **kw) -> str:
    """Drop-in replacement for the old ollama_chat(): returns text only."""
    return (await llm_complete(messages, layer=layer, agent=agent, **kw)).text
