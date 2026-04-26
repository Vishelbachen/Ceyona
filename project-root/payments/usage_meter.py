from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Any


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

    day_start: float = field(default_factory=lambda: time.time())
    month_start: float = field(default_factory=lambda: time.time())


# =========================
# USAGE METER (OBSERVABILITY LAYER)
# =========================
class UsageMeter:
    """
    ROLE:
    - track real usage (requests + computed cost)
    - provide analytics for billing and optimization
    - feed future cost_model tuning / monitoring

    STRICT RULES:
    - DOES NOT enforce limits
    - DOES NOT block requests
    - DOES NOT influence routing / cognition / LLM
    """

    DAY_SECONDS = 86400
    MONTH_SECONDS = 2592000  # ~30 days

    def __init__(self):
        self._state: Dict[str, UsageSnapshot] = {}

    # =========================
    # INTERNAL
    # =========================
    def _get(self, user_id: str) -> UsageSnapshot:
        if user_id not in self._state:
            self._state[user_id] = UsageSnapshot()
        return self._state[user_id]

    def _reset_if_needed(self, state: UsageSnapshot) -> None:
        now = time.time()

        if now - state.day_start >= self.DAY_SECONDS:
            state.day_requests = 0
            state.day_cost = 0.0
            state.day_start = now

        if now - state.month_start >= self.MONTH_SECONDS:
            state.month_requests = 0
            state.month_cost = 0.0
            state.month_start = now

    # =========================
    # RECORD USAGE
    # =========================
    def record(self, user_id: str, cost: float) -> None:
        state = self._get(user_id)
        self._reset_if_needed(state)

        state.total_requests += 1
        state.total_cost += cost

        state.day_requests += 1
        state.day_cost += cost

        state.month_requests += 1
        state.month_cost += cost

    # =========================
    # READ SNAPSHOT
    # =========================
    def get_usage(self, user_id: str) -> Dict[str, Any]:
        state = self._get(user_id)
        self._reset_if_needed(state)

        return {
            "total_requests": state.total_requests,
            "total_cost": state.total_cost,
            "day_requests": state.day_requests,
            "day_cost": state.day_cost,
            "month_requests": state.month_requests,
            "month_cost": state.month_cost,
        }

    # =========================
    # RESET (ADMIN ONLY)
    # =========================
    def reset(self, user_id: str) -> None:
        self._state.pop(user_id, None)