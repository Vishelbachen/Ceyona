from typing import Any, Dict, Optional


class FallbackHandler:
    """
    AI Platform v4.7 — Fallback Handler

    RESPONSIBILITY:
    - Handle LLM failures (timeouts, errors, invalid responses)
    - Provide deterministic fallback strategy selection
    - Ensure system continuity under failure

    STRICT RULES:
    - No reasoning
    - No response evaluation
    - No model selection intelligence
    - No retrieval / memory access
    - No orchestration decisions
    """

    def __init__(self):
        # deterministic fallback chain (fixed order)
        self.fallback_chain = ["FAST", "GENERAL", "HEAVY"]

    def handle_failure(
        self,
        mode: str,
        error: Exception,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Returns next fallback action (no intelligence).
        """

        next_mode = self._get_next_mode(mode)

        return {
            "status": "fallback_triggered",
            "failed_mode": mode,
            "next_mode": next_mode,
            "error": str(error),
            "original_payload": payload,
        }

    def _get_next_mode(self, current_mode: str) -> Optional[str]:
        """
        Deterministic fallback progression.
        """

        if current_mode not in self.fallback_chain:
            return None

        index = self.fallback_chain.index(current_mode)

        if index + 1 < len(self.fallback_chain):
            return self.fallback_chain[index + 1]

        return None

    def should_retry(self, attempt: int, max_attempts: int = 2) -> bool:
        """
        Simple retry policy (no adaptive logic).
        """

        return attempt < max_attempts