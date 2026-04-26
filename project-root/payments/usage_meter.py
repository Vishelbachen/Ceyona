from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


# =========================
# USAGE SNAPSHOT
# =========================
@dataclass
class UsageSnapshot:
    total_requests: int = 0
    total_cost: float = 0.0

    day_requests: int = 0
    day_cost: float = 0.0

    month_requests: int = 0
    month_cost: float = 0.0

    last_day_reset: float = field(default_factory=lambda: time.time())
    last_month_reset: float = field(default_factory=lambda: time.time())


# =========================
# USAGE METER (TELEMETRY LAYER ONLY)
# =========================
class UsageMeter:
    """
    ROLE:
    - record real system usage (requests + cost)
    - provide telemetry for billing + analytics
    - feed observability / optimization

    DOES NOT:
    - enforce limits
    - make decisions
    - control access
    """

    DAY_SECONDS = 86400
    MONTH_SECONDS = 2592000

    def __init__(self):
        self._state: Dict[str, UsageSnapshot] = {}

    # =========================
    # INTERNAL
    # =========================
    def _get(self, user_id: str) -> UsageSnapshot:
        if user_id not in self._state:
            self._state[user_id] = UsageSnapshot()
        return self._state[user_id]

    def _maybe_reset(self, state: UsageSnapshot) -> None:

        now = time.time()

        # daily reset
        if now - state.last_day_reset >= self.DAY_SECONDS:
            state.day_requests = 0
            state.day_cost = 0.0
            state.last_day_reset = now

        # monthly reset
        if now - state.last_month_reset >= self.MONTH_SECONDS:
            state.month_requests = 0
            state.month_cost = 0.0
            state.last_month_reset = now

    # =========================
    # RECORD USAGE
    # =========================
    def record(self, user_id: str, cost: float) -> None:

        state = self._get(user_id)
        self._maybe_reset(state)

        state.total_requests += 1
        state.total_cost += cost

        state.day_requests += 1
        state.day_cost += cost

        state.month_requests += 1
        state.month_cost += cost

    # =========================
    # READ ONLY API
    # =========================
    def get_usage(self, user_id: str) -> Dict[str, float]:

        state = self._get(user_id)
        self._maybe_reset(state)

        return {
            "total_requests": state.total_requests,
            "total_cost": state.total_cost,
            "day_requests": state.day_requests,
            "day_cost": state.day_cost,
            "month_requests": state.month_requests,
            "month_cost": state.month_cost,
        }

    # =========================
    # ADMIN RESET
    # =========================
    def reset(self, user_id: str) -> None:
        self._state.pop(user_id, None)