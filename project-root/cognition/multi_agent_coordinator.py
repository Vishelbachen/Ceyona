from __future__ import annotations

from typing import Dict, Any, List, Optional


# =========================
# MULTI-AGENT COORDINATOR
# =========================
class MultiAgentCoordinator:
    """
    ROLE:
    - map reasoning plan → agent execution strategy
    - distribute subtasks across available agents
    - prepare execution bundle for orchestrator

    STRICT RULES:
    - no execution control
    - no final decision making
    - no LLM routing authority
    - no access to payments/security
    """

    # =========================
    # MAIN ENTRYPOINT
    # =========================
    def distribute(
        self,
        plan: List[str],
        intent: str,
    ) -> Dict[str, Any]:

        strategy = self._build_strategy(plan, intent)

        return {
            "strategy": strategy,
            "execution_mode": self._infer_mode(intent, plan),
        }

    # =========================
    # STRATEGY BUILDER
    # =========================
    def _build_strategy(
        self,
        plan: List[str],
        intent: str,
    ) -> List[Dict[str, Any]]:

        strategy: List[Dict[str, Any]] = []

        for step in plan:
            agent = self._select_agent(step, intent)

            strategy.append({
                "step": step,
                "agent": agent,
            })

        return strategy

    # =========================
    # AGENT SELECTION (STATIC MAPPING ONLY)
    # =========================
    def _select_agent(self, step: str, intent: str) -> str:

        step = step.lower()

        if "code" in step or intent == "code":
            return "deep"

        if "creative" in step or intent == "creative":
            return "creative"

        if "quick" in step or intent == "chat":
            return "fast"

        # default fallback reasoning path
        return "deep"

    # =========================
    # MODE INFERENCE
    # =========================
    def _infer_mode(self, intent: str, plan: List[str]) -> str:

        if intent == "creative":
            return "diverse_generation"

        if len(plan) > 5:
            return "multi_agent_complex"

        return "standard"