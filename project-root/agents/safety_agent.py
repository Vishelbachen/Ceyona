from typing import Any, Dict


class SafetyAgent:
    """
    AI Platform v4.7 — Safety Agent

    RESPONSIBILITY:
    - Post-routing safety validation of execution
    - Light content risk tagging (non-blocking in core flow)
    - Ensure output compliance signals

    STRICT RULES:
    - No decision-making for routing/tier
    - No LLM calls
    - No retrieval access
    - No memory access
    - No system control authority
    """

    def __init__(self, model_router):
        self.model_router = model_router

    async def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safety evaluation pass (non-blocking signal layer).
        """

        text = payload.get("text", "")
        output = payload.get("output", "")

        risk_score = self._risk_score(text, output)
        flagged = risk_score > 0.7

        return {
            "agent": "safety",
            "risk_score": risk_score,
            "flagged": flagged,
            "mode": "SAFETY_CHECK",
        }

    def _risk_score(self, input_text: str, output_text: str) -> float:
        """
        Lightweight heuristic scoring only.
        No semantic understanding allowed.
        """

        score = 0.0

        combined = (input_text + " " + output_text).lower()

        # simple heuristic signals only
        if any(word in combined for word in ["hack", "exploit", "attack"]):
            score += 0.4

        if any(word in combined for word in ["delete", "destroy", "bypass"]):
            score += 0.3

        if len(output_text) > 2000:
            score += 0.1

        return min(score, 1.0)