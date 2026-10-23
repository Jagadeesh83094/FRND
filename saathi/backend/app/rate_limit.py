"""In-process rate limiter for local/single-worker deployments.

For multi-worker/public production, use a shared store or API gateway. This is
not a substitute for verified authentication or provider quotas.
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
        for stale_key in list(_EVENTS):
            events = _EVENTS[stale_key]
            while events and events[0] <= cutoff:
                events.popleft()
            if not events:
                _EVENTS.pop(stale_key, None)

        events = _EVENTS[key]
        if len(events) >= limit:
            retry_after = max(1, int(window_seconds - (now - events[0])))
            raise HTTPException(
                status_code=429,
                detail=f"Too many {bucket} requests. Please wait and try again.",
                headers={"Retry-After": str(retry_after)},
            )
        events.append(now)
