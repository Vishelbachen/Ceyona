from __future__ import annotations

from typing import Dict, Any, Optional


# =========================
# CREATIVE AGENT
# =========================
class CreativeAgent:
    """
    ROLE:
    - generate diverse / non-deterministic outputs
    - explore alternative phrasings and ideas
    - produce stylistically rich responses

    STRICT RULES:
    - no system decisions
    - no access control logic
    - no pricing logic
    - no memory authority
    """

    def __init__(self, llm_client):
        self._llm = llm_client

    # =========================
    # MAIN EXECUTION
    # =========================
    async def run(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Creative generation path:
        focuses on diversity, tone, and expression richness.
        """

        response = await self._llm.generate(
            model="general",
            prompt=self._build_creative_prompt(prompt),
            context=context or {},
            temperature=0.9,
        )

        return {
            "agent": "creative",
            "output": response,
            "confidence": 0.7,
            "mode": "creative_generation",
        }

    # =========================
    # PROMPT SHAPING
    # =========================
    def _build_creative_prompt(self, prompt: str) -> str:
        return (
            "Generate a creative, expressive and diverse response.\n"
            "Focus on originality, tone variation, and clarity.\n\n"
            f"Input:\n{prompt}\n\n"
            "Do not be repetitive. Offer a fresh perspective."
        )