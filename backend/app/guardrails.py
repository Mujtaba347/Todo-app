"""Shared protections: rate limiting and client identification.

The limiter is in-memory, which is correct for a single server process
(Render free plan / local). With several instances, move it to Redis.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, window: float, now: float) -> deque:
        q = self._hits[key]
        while q and now - q[0] > window:
            q.popleft()
        return q

    def retry_after(self, key: str, limit: int, window: float) -> int:
        """Seconds until the key may try again (0 = allowed). Does not record a hit."""
        now = time.monotonic()
        with self._lock:
            q = self._prune(key, window, now)
            if len(q) < limit:
                return 0
            return int(window - (now - q[0])) + 1

    def add(self, key: str) -> None:
        with self._lock:
            self._hits[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def check(self, key: str, limit: int, window: float, message: str = "Too many requests") -> None:
        """Record a hit; raise 429 if the limit is exceeded."""
        wait = self.retry_after(key, limit, window)
        if wait:
            raise HTTPException(429, f"{message}. Try again in {wait}s.", headers={"Retry-After": str(wait)})
        self.add(key)


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
