from __future__ import annotations

from typing import Dict, Any, Optional, Literal


# =========================
# SAFETY RESULT TYPES
# =========================
SafetyDecision = Literal["allow", "deny", "degrade"]


# =========================
# SAFETY AGENT
# =========================
class SafetyAgent:
    """
    ROLE:
    - evaluate safety of user input / system output
    - enforce policy constraints
    - act as final guard before response synthesis

    STRICT RULES:
    - no generation
    - no reasoning synthesis
    - no business logic
    - no access control decisions (only safety classification)
    """

    def __init__(self, llm_safety_client):
        self._llm = llm_safety_client

    # =========================
    # MAIN SAFETY CHECK
    # =========================
    async def evaluate(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        """
        Returns safety classification result.
        """

        result = await self._llm.generate(
            model="safety",
            prompt=self._build_safety_prompt(prompt),
            context=context or {},
        )

        decision = self._parse_decision(result)

        return {
            "agent": "safety",
            "decision": decision,
            "raw": result,
        }

    # =========================
    # PROMPT BUILDER
    # =========================
    def _build_safety_prompt(self, prompt: str) -> str:
        return (
            "Evaluate the following input for policy, safety, and harmful intent.\n\n"
            "Return one of:\n"
            "- allow\n"
            "- deny\n"
            "- degrade\n\n"
            f"Input:\n{prompt}\n"
        )

    # =========================
    # PARSE SAFETY OUTPUT
    # =========================
    def _parse_decision(self, result: str) -> SafetyDecision:

        normalized = result.strip().lower()

        if "deny" in normalized:
            return "deny"

        if "degrade" in normalized:
            return "degrade"

        return "allow"