from dataclasses import dataclass

from app.settings import Settings


@dataclass
class ExecutionDecision:
    """
    Result of EPK evaluation.
    """
    tier: str  # FAST | GENERAL | HEAVY
    reason: str
    estimated_cost: float


class ExecutionPolicyKernel:
    """
    AI Platform v4.7 — Execution Policy Kernel (EPK)

    RESPONSIBILITY:
    - Evaluate request complexity
    - Apply economic model rules
    - Select execution tier (FAST / GENERAL / HEAVY)

    STRICT RULES:
    - NO LLM calls
    - NO retrieval
    - NO memory access
    - NO agents
    - NO orchestration
    - PURE stateless decision engine
    """

    def __init__(self, settings: Settings):
        self.settings = settings

        self.rates = {
            "FAST": {
                "input": 0.25,
                "output": 0.9,
                "max_tokens": settings.MAX_TOKENS_FAST,
            },
            "GENERAL": {
                "input": 2.5,
                "output": 10,
                "max_tokens": settings.MAX_TOKENS_GENERAL,
            },
            "HEAVY": {
                "input": 8,
                "output": 30,
                "max_tokens": settings.MAX_TOKENS_HEAVY,
            },
        }

    def _estimate_complexity(self, payload: dict) -> str:
        """
        Lightweight heuristic ONLY.
        No semantic understanding, just signals.
        """

        text = payload.get("text", "")
        length = len(text or "")

        has_code = "```" in text
        has_math = any(c in text for c in ["=", "+", "-", "*", "/"])
        long_query = length > 300

        if has_code or long_query:
            return "HEAVY"

        if has_math:
            return "GENERAL"

        return "FAST"

    def _estimate_cost(self, tier: str, tokens: int = 100) -> float:
        """
        Simple deterministic cost estimate.
        """

        rates = self.rates[tier]
        return (tokens / 1_000_000) * (rates["input"] + rates["output"])

    def evaluate(self, payload: dict) -> ExecutionDecision:
        """
        Main EPK entrypoint.

        Input:
            payload = {
                "text": str,
                ...
            }
        """

        tier = self._estimate_complexity(payload)

        estimated_cost = self._estimate_cost(
            tier=tier,
            tokens=self.rates[tier]["max_tokens"],
        )

        return ExecutionDecision(
            tier=tier,
            reason=f"auto-selected by heuristic rules: {tier}",
            estimated_cost=estimated_cost,
        )