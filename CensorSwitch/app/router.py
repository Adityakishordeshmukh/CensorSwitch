"""
Student A: smart routing + circuit breaker.

route_provider() currently just returns providers in order, skipping any that are
"tripped". Extend the scoring to factor in latency history and/or cost, not just
health.
"""

import time
from dataclasses import dataclass, field

from app.providers import PROVIDERS, ProviderError, call_provider


@dataclass
class _ProviderHealth:
    consecutive_failures: int = 0
    tripped_until: float = 0.0
    recent_latencies_ms: list[float] = field(default_factory=list)

    def is_tripped(self) -> bool:
        return time.time() < self.tripped_until


class Router:
    FAILURE_THRESHOLD = 3
    COOLDOWN_SECONDS = 30

    def __init__(self):
        self._health = {p: _ProviderHealth() for p in PROVIDERS}

    def _record_success(self, provider: str, latency_ms: float):
        health = self._health[provider]
        health.consecutive_failures = 0
        health.recent_latencies_ms.append(latency_ms)
        health.recent_latencies_ms = health.recent_latencies_ms[-20:]  # keep last 20

    def _record_failure(self, provider: str):
        health = self._health[provider]
        health.consecutive_failures += 1
        if health.consecutive_failures >= self.FAILURE_THRESHOLD:
            health.tripped_until = time.time() + self.COOLDOWN_SECONDS

    def _candidate_order(self, preferred: str | None) -> list[str]:
        candidates = [p for p in PROVIDERS if not self._health[p].is_tripped()]
        if preferred and preferred in candidates:
            candidates.remove(preferred)
            candidates.insert(0, preferred)
        return candidates or list(PROVIDERS)  # fall back to everything if all tripped

    async def route(self, prompt: str, preferred: str | None = None) -> tuple[str, str, float]:
        """Tries providers in order until one succeeds. Returns (provider, answer, latency_ms)."""
        last_error = None
        for provider in self._candidate_order(preferred):
            try:
                answer, latency_ms = await call_provider(provider, prompt)
                self._record_success(provider, latency_ms)
                return provider, answer, latency_ms
            except ProviderError as e:
                self._record_failure(provider)
                last_error = e
        raise last_error or ProviderError("all providers unavailable")

    def health_snapshot(self) -> dict:
        return {
            p: {
                "tripped": h.is_tripped(),
                "consecutive_failures": h.consecutive_failures,
                "avg_latency_ms": (
                    sum(h.recent_latencies_ms) / len(h.recent_latencies_ms)
                    if h.recent_latencies_ms
                    else None
                ),
            }
            for p, h in self._health.items()
        }


# Shared instance used by the gateway
router = Router()
