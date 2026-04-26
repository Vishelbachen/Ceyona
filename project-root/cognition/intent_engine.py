from __future__ import annotations

from typing import Dict, Any, Literal, Optional


# =========================
# INTENT TYPES
# =========================
IntentType = Literal[
    "chat",
    "reasoning",
    "creative",
    "code",
    "search",
    "system",
    "unknown",
]


# =========================
# INTENT ENGINE
# =========================
class IntentEngine:
    """
    ROLE:
    - classify user intent from input
    - provide structured signal for orchestrator
    - NOT responsible for execution decisions

    STRICT RULES:
    - no agent selection authority
    - no LLM routing decisions
    - no business logic
    """

    def __init__(self, llm_classifier):
        self._llm = llm_classifier

    # =========================
    # MAIN CLASSIFICATION
    # =========================
    async def classify(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        raw = await self._llm.generate(
            model="general",
            prompt=self._build_prompt(text),
            context=context or {},
        )

        intent = self._parse_intent(raw)

        return {
            "intent": intent,
            "raw": raw,
            "confidence": self._estimate_confidence(raw),
        }

    # =========================
    # PROMPT BUILDER
    # =========================
    def _build_prompt(self, text: str) -> str:
        return (
            "Classify the user intent into one of:\n"
            "chat, reasoning, creative, code, search, system, unknown\n\n"
            f"Input:\n{text}\n\n"
            "Return only the intent label."
        )

    # =========================
    # PARSING
    # =========================
    def _parse_intent(self, raw: str) -> IntentType:
        normalized = raw.strip().lower()

        for intent in [
            "chat",
            "reasoning",
            "creative",
            "code",
            "search",
            "system",
        ]:
            if intent in normalized:
                return intent  # type: ignore

        return "unknown"

    # =========================
    # CONFIDENCE ESTIMATION
    # =========================
    def _estimate_confidence(self, raw: str) -> float:
        """
        Simple heuristic:
        longer / cleaner response → higher confidence
        """

        if not raw:
            return 0.0

        score = len(raw.strip()) / 50.0
        return max(0.1, min(score, 1.0))