from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict


# =========================
# STATE
# =========================
@dataclass
class RateLimitState:
    requests: int = 0
    window_start: float = field(default_factory=lambda: time.time())


# =========================
# RATE LIMITER
# =========================
class RateLimiter:
    """
    ROLE:
    - protect system from abuse (spam / flood / burst traffic)
    - enforce short-term request rate limits per user

    STRICT RULES:
    - DOES NOT enforce billing
    - DOES NOT track subscriptions
    - DOES NOT influence model routing
    - DOES NOT interact with payments or memory
    """

    def __init__(
        self,
        max_requests_per_window: int = 60,
        window_seconds: int = 60,
        max_requests_per_minute: int | None = None,  # 👈 COMPAT FIX (bootstrap legacy)
    ):
        # 🔧 compatibility layer
        if max_requests_per_minute is not None:
            max_requests_per_window = max_requests_per_minute

        self.max_requests = max_requests_per_window
        self.window = window_seconds

        self._state: Dict[str, RateLimitState] = {}

    # =========================
    # INTERNAL
    # =========================
    def _get_state(self, user_id: str) -> RateLimitState:
        if user_id not in self._state:
            self._state[user_id] = RateLimitState()
        return self._state[user_id]

    def _reset_if_needed(self, state: RateLimitState) -> None:
        now = time.time()

        if now - state.window_start >= self.window:
            state.requests = 0
            state.window_start = now

    # =========================
    # MAIN CHECK
    # =========================
    def allow(self, user_id: str) -> bool:
        state = self._get_state(user_id)
        self._reset_if_needed(state)

        state.requests += 1

        if state.requests > self.max_requests:
            return False

        return True

    # =========================
    # RESET (ADMIN / TEST ONLY)
    # =========================
    def reset(self, user_id: str) -> None:
        self._state.pop(user_id, None)