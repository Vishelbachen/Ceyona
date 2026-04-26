from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict
from threading import Lock


# =========================
# CONTEXT STATE
# =========================
@dataclass
class RateLimitState:
    requests: int = 0
    window_start: float = field(default_factory=lambda: time.time())


# =========================
# RATE LIMITER (SECURITY ONLY)
# =========================
class RateLimiter:
    """
    SECURITY LAYER COMPONENT (v4.7)

    ROLE:
    - protect system from abuse (spam, burst, flood)
    - enforce short-term request rate limits per user

    STRICT NON-RESPONSIBILITIES:
    - NO billing logic
    - NO subscription rules
    - NO model routing influence
    - NO business logic decisions

    DESIGN PRINCIPLE:
    - fail-closed under abuse
    - deterministic + stateless-feeling behavior
    """

    def __init__(
        self,
        max_requests_per_window: int = 60,
        window_seconds: int = 60,
        cleanup_ttl_seconds: int = 3600,
    ):
        self.max_requests = max_requests_per_window
        self.window = window_seconds
        self.cleanup_ttl = cleanup_ttl_seconds

        self._state: Dict[str, RateLimitState] = {}
        self._last_seen: Dict[str, float] = {}

        self._lock = Lock()

    # =========================
    # MAIN ENTRY
    # =========================
    def allow(self, user_id: str) -> bool:
        now = time.time()

        with self._lock:
            self._last_seen[user_id] = now

            state = self._state.get(user_id)

            # first request
            if not state:
                self._state[user_id] = RateLimitState(requests=1, window_start=now)
                return True

            # window reset
            if now - state.window_start > self.window:
                state.requests = 1
                state.window_start = now
                return True

            # increment
            state.requests += 1

            # check limit
            if state.requests > self.max_requests:
                return False

            return True

    # =========================
    # MAINTENANCE (ANTI MEMORY LEAK)
    # =========================
    def cleanup(self) -> None:
        """
        Removes stale user states to prevent unbounded memory growth.
        Should be called periodically (e.g., background task).
        """
        now = time.time()

        with self._lock:
            stale_users = [
                user_id
                for user_id, last_seen in self._last_seen.items()
                if now - last_seen > self.cleanup_ttl
            ]

            for user_id in stale_users:
                self._state.pop(user_id, None)
                self._last_seen.pop(user_id, None)

    # =========================
    # ADMIN / TEST UTILITY
    # =========================
    def reset(self, user_id: str) -> None:
        with self._lock:
            self._state.pop(user_id, None)
            self._last_seen.pop(user_id, None)

    # =========================
    # INTROSPECTION (DEBUG ONLY)
    # =========================
    def get_usage(self, user_id: str) -> dict:
        state = self._state.get(user_id)
        if not state:
            return {"requests": 0, "window_start": None}

        return {
            "requests": state.requests,
            "window_start": state.window_start,
        }