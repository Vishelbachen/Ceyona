from __future__ import annotations

from typing import Dict, Any, List, Optional


# =========================
# REASONING ENGINE
# =========================
class ReasoningEngine:
    """
    ROLE:
    - decompose complex tasks into structured steps
    - transform raw intent into reasoning plan
    - prepare input for agents layer

    STRICT RULES:
    - no agent selection authority
    - no orchestration decisions
    - no execution control
    - no access to external systems
    """

    def __init__(self, llm_client):
        self._llm = llm_client

    # =========================
    # MAIN ENTRYPOINT
    # =========================
    async def build_plan(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        structured = await self._llm.generate(
            model="general",
            prompt=self._build_prompt(text),
            context=context or {},
        )

        plan = self._parse_plan(structured)

        return {
            "plan": plan,
            "raw": structured,
            "complexity": self._estimate_complexity(plan),
        }

    # =========================
    # PROMPT BUILDER
    # =========================
    def _build_prompt(self, text: str) -> str:
        return (
            "Decompose the following task into structured reasoning steps.\n\n"
            "Return a step-by-step plan without solving it fully.\n\n"
            f"Input:\n{text}\n"
        )

    # =========================
    # PLAN PARSING
    # =========================
    def _parse_plan(self, raw: str) -> List[str]:
        """
        Converts model output into structured steps.
        """

        lines = [l.strip() for l in raw.split("\n") if l.strip()]

        # fallback safety: ensure non-empty plan
        return lines if lines else ["understand_input", "process", "respond"]

    # =========================
    # COMPLEXITY ESTIMATION
    # =========================
    def _estimate_complexity(self, plan: List[str]) -> str:
        """
        Simple heuristic classifier:
        more steps → higher complexity
        """

        if len(plan) <= 2:
            return "low"

        if len(plan) <= 5:
            return "medium"

        return "high"