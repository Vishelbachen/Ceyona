from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Literal


# =========================
# PLAN TYPES
# =========================
PlanType = Literal["free", "pro", "premium"]


@dataclass
class PlanLimits:
    daily_requests: int
    monthly_requests: int
    monthly_price_ton: float


PLANS: Dict[PlanType, PlanLimits] = {
    "free": PlanLimits(50, 3000, 0.0),
    "pro": PlanLimits(200, 10000, 10.0),
    "premium": PlanLimits(1000, 50000, 25.0),
}


# =========================
# USAGE STATE (IN-MEMORY CACHE)
# =========================
@dataclass
class UsageState:
    daily_count: int = 0
    monthly_count: int = 0

    day_window_start: float = field(default_factory=lambda: time.time())
    month_window_start: float = field(default_factory=lambda: time.time())


# =========================
# ACCESS DECISION
# =========================
@dataclass
class AccessDecision:
    allowed: bool
    reason: str = "ok"
    remaining_daily: Optional[int] = None
    remaining_monthly: Optional[int] = None


# =========================
# ACCESS CONTROLLER (BILLING POLICY ENGINE)
# =========================
class AccessController:
    """
    ROLE:
    - enforce subscription-based limits
    - decide ALLOW / DENY based on plan rules

    DOES NOT:
    - track raw usage metrics (UsageMeter does that)
    - handle burst protection (RateLimiter)
    - compute pricing (PricingEngine)
    """

    DAY_SECONDS = 86400
    MONTH_SECONDS = 2592000

    def __init__(self):
        self._usage: Dict[str, UsageState] = {}

    # =========================
    # INTERNAL
    # =========================
    def _state(self, user_id: str) -> UsageState:
        if user_id not in self._usage:
            self._usage[user_id] = UsageState()
        return self._usage[user_id]

    def _reset(self, state: UsageState) -> None:
        now = time.time()

        if now - state.day_window_start >= self.DAY_SECONDS:
            state.daily_count = 0
            state.day_window_start = now

        if now - state.month_window_start >= self.MONTH_SECONDS:
            state.monthly_count = 0
            state.month_window_start = now

    # =========================
    # DECISION ENGINE
    # =========================
    def check(self, user_id: str, plan: PlanType = "free") -> AccessDecision:

        limits = PLANS[plan]
        state = self._state(user_id)

        self._reset(state)

        remaining_daily = limits.daily_requests - state.daily_count
        remaining_monthly = limits.monthly_requests - state.monthly_count

        if remaining_daily <= 0:
            return AccessDecision(
                allowed=False,
                reason="daily_limit_exceeded",
                remaining_daily=0,
                remaining_monthly=max(0, remaining_monthly),
            )

        if remaining_monthly <= 0:
            return AccessDecision(
                allowed=False,
                reason="monthly_limit_exceeded",
                remaining_daily=max(0, remaining_daily),
                remaining_monthly=0,
            )

        return AccessDecision(
            allowed=True,
            remaining_daily=remaining_daily,
            remaining_monthly=remaining_monthly,
        )

    # =========================
    # COMMIT (ONLY AFTER APPROVED EXECUTION)
    # =========================
    def commit(self, user_id: str) -> None:

        state = self._state(user_id)
        self._reset(state)

        state.daily_count += 1
        state.monthly_count += 1

    # =========================
    # ADMIN RESET
    # =========================
    def reset(self, user_id: str) -> None:
        self._usage.pop(user_id, None)