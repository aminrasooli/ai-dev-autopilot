"""Minimal in-process rate limiter — a courtesy ceiling on our own call rate.

This is NOT a substitute for the account-level rate limits Anthropic
enforces server-side; it exists so a runaway local loop (a bug, not an
attack) can't hammer the API before the budget ledger even has a chance to
catch it.
"""

from __future__ import annotations

import threading
import time
from collections import deque


class SlidingWindowLimiter:
    def __init__(self, max_calls: int, window_s: float = 60.0):
        self.max_calls = max_calls
        self.window_s = window_s
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self, *, block: bool = True) -> bool:
        """Return True once a call is permitted. If block=False, return
        False immediately instead of sleeping when the window is full."""
        while True:
            with self._lock:
                now = time.monotonic()
                while self._calls and now - self._calls[0] > self.window_s:
                    self._calls.popleft()
                if len(self._calls) < self.max_calls:
                    self._calls.append(now)
                    return True
                wait_s = self.window_s - (now - self._calls[0])
            if not block:
                return False
            time.sleep(max(wait_s, 0.05))
