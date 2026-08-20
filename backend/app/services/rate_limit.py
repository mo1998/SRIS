"""Lightweight in-memory fixed-window rate limiting.

Used for candidate-facing endpoints that are otherwise cheap to hammer
(e.g. starting a response or submitting answers). State lives in-process only,
which is acceptable for a per-instance throttle; each backend replica enforces
its own budget.
"""

import threading
import time
from collections import defaultdict, deque
from typing import DefaultDict, Deque

_lock = threading.Lock()
_buckets: DefaultDict[str, Deque[float]] = defaultdict(deque)


def check_rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    """Record one call for ``key``; return True if within the budget."""
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        events = _buckets[key]
        while events and events[0] < cutoff:
            events.popleft()
        if len(events) >= limit:
            return False
        events.append(now)
        return True


def reset_rate_limits() -> None:
    """Clear all rate-limit state (used by tests)."""
    with _lock:
        _buckets.clear()