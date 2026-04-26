from __future__ import annotations

from typing import Dict, Any, Optional


# =========================
# FAST AGENT
# =========================
class FastAgent:
    """
    ROLE:
    - ultra-low latency response generation
    - simple reasoning / structural transformation
    - preprocessing or lightweight answer synthesis

    STRICT RULES:
    - no access control logic
    - no pricing logic
    - no memory decisions
    - no orchestration
    - no multi-step reasoning control
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
        Fast-path execution:
        minimal reasoning depth, optimized for latency.
        """

        response = await self._llm.generate(
            model="fast",
            prompt=prompt,
            context=context or {},
        )

        return {
            "agent": "fast",
            "output": response,
            "confidence": 0.6,
            "mode": "low_latency",
        }