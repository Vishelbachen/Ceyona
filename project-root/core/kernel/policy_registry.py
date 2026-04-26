from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Optional


Decision = Literal["ALLOW", "DENY", "DEGRADED_MODE"]


# =========================
# POLICY PROFILE
# =========================
@dataclass(frozen=True)
class PolicyProfile:
    """
    Static policy configuration per plan or system mode.
    """

    name: str
    max_cost_bucket: str
    allow_agents: bool
    allow_retrieval: bool
    max_system_load: float
    default_decision: Decision


# =========================
# POLICY REGISTRY
# =========================
class PolicyRegistry:
    """
    ROLE:
    - store immutable policy profiles
    - provide lookup for orchestrator / EPK

    STRICT RULES:
    - no logic execution
    - no decision making
    - no runtime adaptation
    """

    def __init__(self):

        self._policies: Dict[str, PolicyProfile] = {
            # FREE TIER
            "free": PolicyProfile(
                name="free",
                max_cost_bucket="medium",
                allow_agents=False,
                allow_retrieval=True,
                max_system_load=0.7,
                default_decision="DEGRADED_MODE",
            ),

            # PRO TIER
            "pro": PolicyProfile(
                name="pro",
                max_cost_bucket="high",
                allow_agents=True,
                allow_retrieval=True,
                max_system_load=0.85,
                default_decision="ALLOW",
            ),

            # PREMIUM TIER
            "premium": PolicyProfile(
                name="premium",
                max_cost_bucket="high",
                allow_agents=True,
                allow_retrieval=True,
                max_system_load=0.95,
                default_decision="ALLOW",
            ),
        }

    # =========================
    # GET POLICY
    # =========================
    def get(self, plan: str) -> PolicyProfile:

        return self._policies.get(
            plan,
            self._policies["free"],  # safe fallback
        )

    # =========================
    # LIST ALL POLICIES
    # =========================
    def list(self) -> Dict[str, PolicyProfile]:
        return self._policies

    # =========================
    # EXTENSION HOOK (STATIC ONLY)
    # =========================
    def register(self, key: str, profile: PolicyProfile) -> None:
        """
        NOTE:
        Should only be used at bootstrap time.
        """
        self._policies[key] = profile