"""
Student C: rate limiting + abuse detection.

TokenBucket below is a working minimal per-key rate limiter (in-memory).
Extend this with:
  - a sliding-window request counter to flag sudden spikes (abuse), not just
    steady-state overuse
  - persistence in Redis so limits survive a restart / work across multiple
    gateway instances
  - a "cooldown" or temporary block list for keys that repeatedly trip the limiter
"""

import time
from dataclasses import dataclass, field

from app.config import settings


@dataclass
class _Bucket:
    tokens: float
    last_refill: float = field(default_factory=time.time)


class TokenBucket:
    """Simple per-key token bucket. allow() returns True if the request is permitted."""

    def __init__(self, capacity: int | None = None, refill_per_sec: float | None = None):
        self.capacity = capacity or settings.rate_limit_capacity
        self.refill_per_sec = refill_per_sec or settings.rate_limit_refill_per_sec
        self._buckets: dict[str, _Bucket] = {}

    def _get_bucket(self, key: str) -> _Bucket:
        if key not in self._buckets:
            self._buckets[key] = _Bucket(tokens=self.capacity)
        return self._buckets[key]

    def allow(self, key: str) -> bool:
        bucket = self._get_bucket(key)
        now = time.time()

        # Refill based on time elapsed since last check
        elapsed = now - bucket.last_refill
        bucket.tokens = min(self.capacity, bucket.tokens + elapsed * self.refill_per_sec)
        bucket.last_refill = now

        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return True
        return False

    def remaining(self, key: str) -> float:
        return self._get_bucket(key).tokens


# Shared instance used by the gateway
rate_limiter = TokenBucket()
