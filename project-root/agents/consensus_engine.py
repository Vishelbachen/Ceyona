from __future__ import annotations

from typing import Dict, Any, List, Optional


# =========================
# CONSENSUS ENGINE
# =========================
class ConsensusEngine:
    """
    ROLE:
    - aggregate outputs from multiple agents
    - resolve conflicts between fast / deep / creative agents
    - produce final unified response candidate

    STRICT RULES:
    - no LLM calling (pure logic layer)
    - no safety evaluation
    - no routing decisions upstream
    - no system control authority
    """

    # =========================
    # MAIN ENTRYPOINT
    # =========================
    def resolve(
        self,
        agent_outputs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Takes multiple agent outputs and returns a single consensus result.
        """

        if not agent_outputs:
            return {
                "status": "empty",
                "output": None,
                "confidence": 0.0,
            }

        # STEP 1: prioritize deep > creative > fast
        ranked = self._rank(agent_outputs)

        # STEP 2: select best candidate
        best = ranked[0]

        # STEP 3: optional merge context from others
        merged_context = self._merge_context(agent_outputs)

        return {
            "status": "consensus_resolved",
            "output": best.get("output"),
            "agent": best.get("agent"),
            "confidence": best.get("confidence", 0.5),
            "context": merged_context,
        }

    # =========================
    # RANKING STRATEGY
    # =========================
    def _rank(self, outputs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

        priority = {
            "deep": 3,
            "creative": 2,
            "fast": 1,
        }

        return sorted(
            outputs,
            key=lambda x: priority.get(x.get("agent", ""), 0),
            reverse=True,
        )

    # =========================
    # CONTEXT MERGING (LIGHTWEIGHT)
    # =========================
    def _merge_context(
        self,
        outputs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        return {
            "agents_used": [o.get("agent") for o in outputs],
            "count": len(outputs),
        }