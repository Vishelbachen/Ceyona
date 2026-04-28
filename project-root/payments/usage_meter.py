from typing import Dict, Any, List
from datetime import datetime


class UsageMeter:
    """
    AI Platform v4.7 — Usage Meter

    RESPONSIBILITY:
    - Track token usage per user/request
    - Record execution consumption metrics
    - Provide raw usage data for billing layer

    STRICT RULES:
    - No pricing calculations
    - No access control decisions
    - No LLM / retrieval / memory access
    - No orchestration logic
    """

    def __init__(self):
        # in-memory usage log (can be replaced by DB/warehouse)
        self._usage_log: List[Dict[str, Any]] = []

    def record_usage(
        self,
        user_id: str,
        tier: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ) -> str:
        """
        Stores a single usage event.
        """

        usage_id = f"usage_{len(self._usage_log) + 1}"

        entry = {
            "id": usage_id,
            "user_id": user_id,
            "tier": tier,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._usage_log.append(entry)

        return usage_id

    def get_user_usage(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Returns usage history for a specific user.
        """

        return [
            entry
            for entry in self._usage_log
            if entry["user_id"] == user_id
        ]

    def total_cost(self, user_id: str) -> float:
        """
        Aggregates total cost for a user.
        """

        return sum(
            entry["cost"]
            for entry in self._usage_log
            if entry["user_id"] == user_id
        )