from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Literal, Protocol


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
# OPTIONAL DEPENDENCY PORTS (DI READY)
# =========================
class PricingPort(Protocol):
    def estimate_request_cost(self, *args, **kwargs) -> float: ...


class UsageSnapshotPort(Protocol):
    def record(self, user_id: str, cost: float) -> None: ...


# =========================
# USAGE STATE
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
# ACCESS CONTROLLER
# =========================
class AccessController:
    """
    BILLING POLICY ENGINE

    RESPONSIBILITY:
    - enforce subscription limits
    - enforce deterministic quota rules

    OPTIONAL INPUTS (future-safe):
    - PricingEngine (cost awareness)
    - UsageMeter (observability sync)
    """

    DAY_SECONDS = 86400
    MONTH_SECONDS = 2592000

    def __init__(
        self,
        pricing: Optional[PricingPort] = None,
        usage_meter: Optional[UsageSnapshotPort] = None,
    ):
        self._usage: Dict[str, UsageState] = {}

        # optional DI (future extensibility)
        self._pricing = pricing
        self._usage_meter = usage_meter

    # =========================
    # INTERNAL STATE
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
    # COMMIT
    # =========================
    def commit(
        self,
        user_id: str,
        *,
        cost: Optional[float] = None,
    ) -> None:

        state = self._state(user_id)
        self._reset(state)

        state.daily_count += 1
        state.monthly_count += 1

        # optional hooks (future observability + pricing alignment)
        if self._usage_meter and cost is not None:
            self._usage_meter.record(user_id, cost)

    # =========================
    # ADMIN RESET
    # =========================
    def reset(self, user_id: str) -> None:
        self._usage.pop(user_id, None)