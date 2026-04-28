from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class DecisionProfile:
    """
    Structured interpretation of request signals.
    """
    has_code: bool
    has_math: bool
    length: int
    intent_hint: str
    risk_level: str


class DecisionMatrix:
    """
    AI Platform v4.7 — Decision Matrix

    RESPONSIBILITY:
    - Convert raw payload signals into structured decision profile
    - Provide deterministic rule hints for EPK

    STRICT RULES:
    - No execution
    - No LLM calls
    - No retrieval
    - No agents
    - No cost logic (handled by EPK only)
    """

    def analyze(self, payload: Dict[str, Any]) -> DecisionProfile:
        """
        Converts raw input into structured feature profile.
        """

        text = payload.get("text", "") or ""

        length = len(text)

        has_code = "```" in text

        has_math = any(symbol in text for symbol in ["=", "+", "-", "*", "/", "^"])

        # lightweight heuristic intent signal (NOT NLP)
        intent_hint = self._infer_intent_hint(text)

        risk_level = self._infer_risk_level(text, has_code)

        return DecisionProfile(
            has_code=has_code,
            has_math=has_math,
            length=length,
            intent_hint=intent_hint,
            risk_level=risk_level,
        )

    def _infer_intent_hint(self, text: str) -> str:
        """
        Minimal keyword-based hinting only.
        No semantic understanding allowed.
        """

        lower = text.lower()

        if any(k in lower for k in ["how", "как", "explain", "объясни"]):
            return "explanation"

        if any(k in lower for k in ["code", "python", "javascript"]):
            return "coding"

        if any(k in lower for k in ["what", "что", "who", "кто"]):
            return "query"

        return "general"

    def _infer_risk_level(self, text: str, has_code: bool) -> str:
        """
        Determines operational risk category (not safety policy).
        """

        if has_code and len(text) > 500:
            return "high"

        if len(text) > 1000:
            return "medium"

        return "low"