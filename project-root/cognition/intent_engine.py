from dataclasses import dataclass
from typing import Dict, Any, Literal


IntentType = Literal[
    "question",
    "coding",
    "explanation",
    "creative",
    "command",
    "unknown",
]


@dataclass(frozen=True)
class IntentResult:
    """
    Structured intent classification output.
    """
    intent: IntentType
    confidence: float
    raw_signal: str


class IntentEngine:
    """
    AI Platform v4.7 — Intent Engine

    RESPONSIBILITY:
    - Lightweight intent classification
    - Produce structured signal for downstream EPK / orchestrator

    STRICT RULES:
    - No execution logic
    - No routing decisions
    - No LLM calls
    - No retrieval / memory access
    """

    def classify(self, payload: Dict[str, Any]) -> IntentResult:
        """
        Deterministic rule-based intent classification.
        """

        text = (payload.get("text") or "").lower()

        # =========================
        # SIGNAL EXTRACTION (RULE-BASED ONLY)
        # =========================

        if any(k in text for k in ["how", "explain", "what", "why", "как", "почему", "что"]):
            return IntentResult(
                intent="question",
                confidence=0.7,
                raw_signal="keyword_question",
            )

        if "```" in text or "python" in text or "code" in text:
            return IntentResult(
                intent="coding",
                confidence=0.8,
                raw_signal="code_signal_detected",
            )

        if any(k in text for k in ["write", "story", "poem", "create", "напиши", "история"]):
            return IntentResult(
                intent="creative",
                confidence=0.75,
                raw_signal="creative_keywords",
            )

        if any(k in text for k in ["run", "execute", "send", "delete", "запусти", "удали"]):
            return IntentResult(
                intent="command",
                confidence=0.7,
                raw_signal="command_keywords",
            )

        if any(k in text for k in ["explain", "объясни"]):
            return IntentResult(
                intent="explanation",
                confidence=0.7,
                raw_signal="explanation_signal",
            )

        return IntentResult(
            intent="unknown",
            confidence=0.4,
            raw_signal="no_clear_signal",
        )