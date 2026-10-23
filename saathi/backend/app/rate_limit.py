"""Small in-process rate limiter for development/single-worker deployments.

For multi-worker or public production deployments, replace this with a shared
store (for example Redis) and configure trusted proxy handling at the edge.
This is a safety net, not a substitute for authentication or provider quotas.
"""
from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request

_EVENTS: dict[str, deque[float]] = defaultdict(deque)
_LOCK = Lock()


def enforce_rate_limit(request: Request, *, bucket: str, limit: int, window_seconds: int = 60) -> None:
    host = request.client.host if request.client else "unknown"
    key = f"{bucket}:{host}"
    now = monotonic()
    cutoff = now - window_seconds

    with _LOCK:
        events = _EVENTS[key]
        while events and events[0] <= cutoff:
            events.popleft()
        if len(events) >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"Too many {bucket} requests. Please wait and try again.",
                headers={"Retry-After": str(window_seconds)},
            )
        events.append(now)

        # Opportunistic cleanup to prevent stale client keys accumulating.
        if len(_EVENTS) > 5000:
            stale = [k for k, values in _EVENTS.items() if not values or values[-1] <= cutoff]
            for stale_key in stale[:1000]:
                _EVENTS.pop(stale_key, None)
