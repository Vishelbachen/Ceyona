from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AgentResult:
    agent: str
    output: Any
    confidence: float


@dataclass
class ConsensusResult:
    final_output: Any
    confidence: float
    breakdown: Dict[str, Any]


class ConsensusEngine:
    """
    Consensus layer for multi-agent system.

    ROLE:
    - aggregate outputs
    - normalize conflicting results
    - compute weighted confidence

    DOES NOT:
    - generate content
    - decide strategy
    - call LLM
    - access retrieval/memory
    """

    def resolve(
        self,
        intent: Any,
        reasoning: Any,
        agent_results: List[AgentResult],
    ) -> ConsensusResult:

        if not agent_results:
            return ConsensusResult(
                final_output="No agent results available",
                confidence=0.0,
                breakdown={}
            )

        # =========================
        # 1. WEIGHTED SELECTION
        # =========================
        weighted_scores = []

        for r in agent_results:
            weight = self._agent_weight(r.agent)
            score = r.confidence * weight

            weighted_scores.append((r, score))

        # =========================
        # 2. PICK BEST RESULT
        # =========================
        best_result = max(weighted_scores, key=lambda x: x[1])[0]

        # =========================
        # 3. CONFIDENCE AGGREGATION
        # =========================
        avg_confidence = sum(r.confidence for r in agent_results) / len(agent_results)

        final_confidence = self._normalize_confidence(
            best_result.confidence,
            avg_confidence
        )

        # =========================
        # 4. BUILD BREAKDOWN
        # =========================
        breakdown = {
            "intent": getattr(intent, "intent", None),
            "reasoning_confidence": getattr(reasoning, "confidence", None),
            "agents": [
                {
                    "agent": r.agent,
                    "confidence": r.confidence,
                }
                for r in agent_results
            ],
            "selected_agent": best_result.agent,
        }

        return ConsensusResult(
            final_output=best_result.output,
            confidence=final_confidence,
            breakdown=breakdown
        )

    # =========================
    # ⚖️ INTERNAL WEIGHTS
    # =========================
    def _agent_weight(self, agent_name: str) -> float:
        if agent_name == "safety":
            return 1.2  # safety always dominates

        if agent_name == "deep":
            return 1.0

        if agent_name == "fast":
            return 0.7

        if agent_name == "creative":
            return 0.8

        return 1.0

    # =========================
    # 📊 NORMALIZATION
    # =========================
    def _normalize_confidence(
        self,
        best_conf: float,
        avg_conf: float
    ) -> float:

        # blend best + stability of system
        final = (best_conf * 0.7) + (avg_conf * 0.3)

        return max(0.05, min(final, 0.99))