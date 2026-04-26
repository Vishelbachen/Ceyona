from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


# =========================
# USAGE STATE
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
# USAGE METER (OBSERVABILITY FOR PAYMENTS)
# =========================
class UsageMeter:
    """
    ROLE:
    - track real system consumption (requests + compute cost)
    - provide analytics layer for payments & access control
    - feed future optimization / cost_model tuning

    DOES NOT:
    - block requests
    - enforce limits
    - decide routing
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
    # COMMIT USAGE
    # =========================
    def record(
        self,
        user_id: str,
        cost: float,
    ) -> None:

        state = self._get(user_id)
        self._reset_if_needed(state)

        # global
        state.total_requests += 1
        state.total_cost += cost

        # daily
        state.day_requests += 1
        state.day_cost += cost

        # monthly
        state.month_requests += 1
        state.month_cost += cost

    # =========================
    # READ API
    # =========================
    def get_usage(self, user_id: str) -> Dict[str, Optional[float]]:
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
    # RESET (ADMIN / DEBUG)
    # =========================
    def reset(self, user_id: str) -> None:
        if user_id in self._state:
            del self._state[user_id]