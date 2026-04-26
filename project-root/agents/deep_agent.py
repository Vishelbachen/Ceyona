from __future__ import annotations

from typing import Dict, Any, Optional


# =========================
# DEEP AGENT
# =========================
class DeepAgent:
    """
    ROLE:
    - multi-step reasoning execution
    - structured decomposition of complex tasks
    - coordination with heavy LLM models

    STRICT RULES:
    - no routing decisions
    - no access control
    - no pricing logic
    - no system orchestration
    """

    def __init__(self, llm_client):
        self._llm = llm_client

    # =========================
    # MAIN EXECUTION PIPELINE
    # =========================
    async def run(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Deep reasoning execution:
        - decomposition
        - structured inference
        - synthesis
        """

        # STEP 1: reasoning expansion
        expanded = await self._llm.generate(
            model="general",
            prompt=self._build_reasoning_prompt(prompt),
            context=context or {},
        )

        # STEP 2: refinement pass (heavy model if needed)
        refined = await self._llm.generate(
            model="heavy",
            prompt=self._build_refinement_prompt(expanded),
            context=context or {},
        )

        return {
            "agent": "deep",
            "output": refined,
            "raw_reasoning": expanded,
            "confidence": 0.85,
            "mode": "multi_step_reasoning",
        }

    # =========================
    # INTERNAL PROMPTING
    # =========================
    def _build_reasoning_prompt(self, prompt: str) -> str:
        return (
            "Break down the following task into structured reasoning steps:\n\n"
            f"{prompt}\n\n"
            "Return a structured decomposition."
        )

    def _build_refinement_prompt(self, reasoning: str) -> str:
        return (
            "Refine the following reasoning into a final high-quality answer:\n\n"
            f"{reasoning}\n\n"
            "Return only the final structured response."
        )