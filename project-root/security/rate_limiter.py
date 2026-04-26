from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict


# =========================
# CONTEXT
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
    Security-level traffic protection

    ROLE:
    - prevent abuse (burst / spam / flood)
    - enforce short-term request rate limits

    DOES NOT:
    - enforce billing limits
    - decide subscription plans
    - influence model selection
    """

    def __init__(
        self,
        max_requests_per_minute: int = 60,
        window_seconds: int = 60,
    ):
        self.max_requests = max_requests_per_minute
        self.window = window_seconds

        self.state: Dict[str, RateLimitState] = {}

    # =========================
    # MAIN CHECK
    # =========================
    def allow(self, user_id: str) -> bool:

        now = time.time()
        state = self.state.get(user_id)

        if not state:
            self.state[user_id] = RateLimitState(requests=1, window_start=now)
            return True

        # reset window
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
    # OPTIONAL RESET (ADMIN / TEST)
    # =========================
    def reset(self, user_id: str) -> None:
        if user_id in self.state:
            del self.state[user_id]