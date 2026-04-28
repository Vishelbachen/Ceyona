from typing import Dict
import time


class RateLimiter:
    """
    AI Platform v4.7 — Rate Limiter

    RESPONSIBILITY:
    - Limit request frequency per user
    - Prevent abuse via simple threshold rules
    - Provide deterministic throttling

    STRICT RULES:
    - No behavioral analysis
    - No ML / anomaly detection
    - No LLM / retrieval / memory usage
    - No orchestrator interaction
    - No adaptive policies
    """

    def __init__(self, limit_per_minute: int = 60):
        self.limit_per_minute = limit_per_minute
        self._requests: Dict[str, list] = {}

    def allow_request(self, user_id: str) -> bool:
        """
        Checks whether request is allowed based on fixed limit.
        """

        now = time.time()
        window_start = now - 60

        if user_id not in self._requests:
            self._requests[user_id] = []

        # keep only last 60 seconds
        self._requests[user_id] = [
            timestamp for timestamp in self._requests[user_id]
            if timestamp >= window_start
        ]

        if len(self._requests[user_id]) >= self.limit_per_minute:
            return False

        self._requests[user_id].append(now)
        return True

    def reset(self, user_id: str) -> None:
        """
        Clears rate limit history for a user.
        """

        self._requests[user_id] = []