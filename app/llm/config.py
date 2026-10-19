"""
LLM routing config.

Resolution order for a call made with (layer, agent):
    agents[agent]  >  layers[layer]  >  default

"layer" is the tier of the system (knull, workers, verifier, memory, graph).
"agent" is the kind of agent (planner, researcher, writer, critic, verifier ...).
Config comes from a YAML file (LLM_CONFIG, default ./llm.yaml) or, if absent,
from a built-in default that routes everything to local Ollama (the original behaviour).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

PROVIDERS = ("openai", "anthropic", "gemini", "ollama", "mock")


class ModelSpec(BaseModel):
    provider: str
    model: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    def key(self) -> str:
        return f"{self.provider}:{self.model}"


class ProviderSettings(BaseModel):
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    timeout: float = 120.0


class LLMConfig(BaseModel):
    providers: dict[str, ProviderSettings] = Field(default_factory=dict)
    default: ModelSpec
    layers: dict[str, ModelSpec] = Field(default_factory=dict)
    agents: dict[str, ModelSpec] = Field(default_factory=dict)

    def resolve(self, layer: Optional[str] = None, agent: Optional[str] = None) -> ModelSpec:
        if agent and agent in self.agents:
            return self.agents[agent]
        if layer and layer in self.layers:
            return self.layers[layer]
        return self.default

    def provider_settings(self, name: str) -> ProviderSettings:
        defaults = {
            "openai": ProviderSettings(api_key_env="OPENAI_API_KEY"),
            "anthropic": ProviderSettings(api_key_env="ANTHROPIC_API_KEY"),
            "gemini": ProviderSettings(api_key_env="GEMINI_API_KEY"),
            "ollama": ProviderSettings(base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")),
            "mock": ProviderSettings(),
        }
        return self.providers.get(name) or defaults.get(name, ProviderSettings())

    def validate_providers(self) -> None:
        specs = [self.default, *self.layers.values(), *self.agents.values()]
        for s in specs:
            if s.provider not in PROVIDERS:
                raise ValueError(f"Unknown provider '{s.provider}'. Use one of {PROVIDERS}")


def default_config() -> LLMConfig:
    return LLMConfig(
        default=ModelSpec(
            provider="ollama",
            model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        )
    )


def load_llm_config(path: Optional[str] = None) -> LLMConfig:
    path = path or os.getenv("LLM_CONFIG", "llm.yaml")
    p = Path(path)
    if not p.exists():
        return default_config()
    import yaml

    data = yaml.safe_load(p.read_text()) or {}
    cfg = LLMConfig(**data)
    cfg.validate_providers()
    return cfg
