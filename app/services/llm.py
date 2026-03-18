"""
LLM-Provider-Abstraktion – Einheitliche Schnittstelle für Anthropic, OpenAI, Ollama.

Jedes Modell wird anhand seines Namens automatisch dem richtigen Provider
zugeordnet (z.B. "claude-*" → Anthropic, "gpt-*" → OpenAI, Rest → Ollama).

Nutzung:
    from app.services.llm import generate
    response = await generate("claude-sonnet-4-20250514", system="...", messages=[...])
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator

import httpx

from app.config import settings

# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

MODELS: dict[str, dict] = {
    # Anthropic
    "claude-sonnet-4-20250514": {"provider": "anthropic", "label": "Claude Sonnet 4"},
    "claude-haiku-4-5-20251001": {"provider": "anthropic", "label": "Claude Haiku 4.5"},
    # OpenAI
    "gpt-4o": {"provider": "openai", "label": "GPT-4o"},
    "gpt-4o-mini": {"provider": "openai", "label": "GPT-4o Mini"},
    "o3-mini": {"provider": "openai", "label": "o3-mini"},
    # Ollama (populated dynamically)
}


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    tokens_used: int = 0


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

async def _call_anthropic(model: str, system: str, messages: list[dict], max_tokens: int = 2048) -> LLMResponse:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    text = resp.content[0].text if resp.content else ""
    tokens = (resp.usage.input_tokens or 0) + (resp.usage.output_tokens or 0)
    return LLMResponse(content=text, model=model, provider="anthropic", tokens_used=tokens)


async def _call_openai(model: str, system: str, messages: list[dict], max_tokens: int = 2048) -> LLMResponse:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    oai_messages = [{"role": "system", "content": system}] + messages
    resp = await client.chat.completions.create(
        model=model,
        messages=oai_messages,
        max_tokens=max_tokens,
    )
    text = resp.choices[0].message.content or ""
    tokens = resp.usage.total_tokens if resp.usage else 0
    return LLMResponse(content=text, model=model, provider="openai", tokens_used=tokens)


async def _call_ollama(model: str, system: str, messages: list[dict], max_tokens: int = 2048) -> LLMResponse:
    url = f"{settings.ollama_base_url}/api/chat"
    ollama_messages = [{"role": "system", "content": system}] + messages
    payload = {
        "model": model,
        "messages": ollama_messages,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    text = data.get("message", {}).get("content", "")
    tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
    return LLMResponse(content=text, model=model, provider="ollama", tokens_used=tokens)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_provider(model: str) -> str:
    """Determine provider from model name."""
    if model in MODELS:
        return MODELS[model]["provider"]
    if model.startswith(("claude-", "anthropic/")):
        return "anthropic"
    if model.startswith(("gpt-", "o1", "o3")):
        return "openai"
    return "ollama"  # fallback: assume Ollama for unknown models


async def generate(model: str, system: str, messages: list[dict], max_tokens: int = 2048) -> LLMResponse:
    """Route to the correct provider and return a unified response."""
    provider = get_provider(model)
    if provider == "anthropic":
        return await _call_anthropic(model, system, messages, max_tokens)
    elif provider == "openai":
        return await _call_openai(model, system, messages, max_tokens)
    else:
        return await _call_ollama(model, system, messages, max_tokens)


async def list_ollama_models() -> list[str]:
    """Fetch available models from local Ollama instance."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


async def get_available_models() -> dict[str, dict]:
    """Return all available models based on configured API keys."""
    available: dict[str, dict] = {}

    if settings.anthropic_api_key:
        for k, v in MODELS.items():
            if v["provider"] == "anthropic":
                available[k] = v

    if settings.openai_api_key:
        for k, v in MODELS.items():
            if v["provider"] == "openai":
                available[k] = v

    ollama_models = await list_ollama_models()
    for m in ollama_models:
        available[m] = {"provider": "ollama", "label": f"Ollama: {m}"}

    return available
