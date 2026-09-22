"""
Thin wrappers around real LLM providers. Runs in mock mode (no network calls) when
no API key is set, so the rest of the pipeline is fully testable without spending
API credits. Fill in `_call_openai` / `_call_anthropic` with real httpx calls when
you're ready to demo with live traffic.
"""

import asyncio
import random
import time

from app.config import settings

PROVIDERS = ["openai", "anthropic"]

# Rough $ per 1K tokens, for the "cost saved by caching" dashboard number.
# Placeholder figures -- replace with each provider's current pricing.
COST_PER_1K_TOKENS = {"openai": 0.002, "anthropic": 0.003}


class ProviderError(Exception):
    pass


async def call_provider(provider: str, prompt: str) -> tuple[str, float]:
    """Returns (answer, latency_ms). Raises ProviderError on failure."""
    start = time.time()

    if provider == "openai" and settings.openai_api_key:
        answer = await _call_openai(prompt)
    elif provider == "anthropic" and settings.anthropic_api_key:
        answer = await _call_anthropic(prompt)
    else:
        answer = await _mock_call(provider, prompt)

    latency_ms = (time.time() - start) * 1000
    return answer, latency_ms


async def _mock_call(provider: str, prompt: str) -> str:
    """Simulates a provider call with realistic-ish latency, for dev/demo without keys."""
    await asyncio.sleep(random.uniform(0.15, 0.5))
    if random.random() < 0.02:  # occasional simulated failure for circuit-breaker testing
        raise ProviderError(f"{provider} timed out")
    return f"[mock {provider} response] Here's an answer to: {prompt[:60]}"


async def _call_openai(prompt: str) -> str:
    # TODO: real call, e.g. via httpx to https://api.openai.com/v1/chat/completions
    raise NotImplementedError


async def _call_anthropic(prompt: str) -> str:
    # TODO: real call, e.g. via httpx to https://api.anthropic.com/v1/messages
    raise NotImplementedError


def estimate_cost(provider: str, prompt: str, answer: str) -> float:
    approx_tokens = (len(prompt) + len(answer)) / 4  # rough chars-to-tokens estimate
    return (approx_tokens / 1000) * COST_PER_1K_TOKENS.get(provider, 0.002)
