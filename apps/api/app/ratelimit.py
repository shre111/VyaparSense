"""Fixed-window rate limiting for the credential endpoints (ADR-006).

Brute-force protection for ``/auth/login`` and ``/auth/signup``: a per-IP cap on
attempts within a rolling 60s window. Over the cap → ``429`` with ``Retry-After``.

In-memory and per-process — fine for the current single-instance deploy. A
Redis-backed limiter is the multi-instance scale-up (mirrors ``forecast_queue``,
ADR-011). This is one defense among several still pending before launch (CSRF,
Postgres RLS, full security review).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from fastapi import HTTPException, Request, status

from app.config import get_settings

_WINDOW_SECONDS = 60.0


@dataclass
class FixedWindowLimiter:
    """A per-key fixed-window counter. Not thread-safe across event loops, but
    adequate for a single Uvicorn process; swap for Redis when scaling out."""

    limit: int
    window_seconds: float = _WINDOW_SECONDS
    _hits: dict[str, tuple[float, int]] = field(default_factory=dict)

    def allow(self, key: str) -> bool:
        """Record an attempt for ``key``; return ``False`` if it's over the cap."""
        now = time.monotonic()
        start, count = self._hits.get(key, (now, 0))
        if now - start >= self.window_seconds:
            start, count = now, 0
        if count >= self.limit:
            self._hits[key] = (start, count)
            return False
        self._hits[key] = (start, count + 1)
        return True

    def retry_after(self, key: str) -> int:
        """Whole seconds until ``key``'s current window resets (>= 1)."""
        start, _ = self._hits.get(key, (time.monotonic(), 0))
        return max(1, int(self.window_seconds - (time.monotonic() - start)))

    def reset(self) -> None:
        self._hits.clear()


_auth_limiter = FixedWindowLimiter(limit=get_settings().auth_rate_limit_per_minute)


def rate_limit_auth(request: Request) -> None:
    """Dependency: cap credential attempts per client IP. Raises ``429`` when over."""
    key = request.client.host if request.client else "unknown"
    if not _auth_limiter.allow(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many attempts; please try again shortly",
            headers={"Retry-After": str(_auth_limiter.retry_after(key))},
        )


def reset_rate_limits() -> None:
    """Clear all counters — for tests (each test starts with a fresh window)."""
    _auth_limiter.reset()
