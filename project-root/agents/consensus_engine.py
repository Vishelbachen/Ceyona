from typing import Any, Dict, List


class ConsensusEngine:
    """
    AI Platform v4.7 — Consensus Engine

    RESPONSIBILITY:
    - Aggregate outputs from multiple sources (agents/safety/retrieval)
    - Produce unified structured result
    - Provide deterministic merge strategy

    STRICT RULES:
    - No reasoning or evaluation of correctness
    - No LLM calls
    - No retrieval access
    - No memory access
    - No routing decisions
    """

    def resolve(self, agent_result: Any) -> Dict[str, Any]:
        """
        Simple normalization of single or multiple agent outputs.
        """

        if isinstance(agent_result, list):
            return self._merge_multiple(agent_result)

        return self._wrap_single(agent_result)

    def _wrap_single(self, result: Any) -> Dict[str, Any]:
        """
        Wrap single agent output into standard format.
        """

        return {
            "type": "single",
            "result": result,
            "consensus": None,
        }

    def _merge_multiple(self, results: List[Any]) -> Dict[str, Any]:
        """
        Deterministic merge without evaluation or ranking.
        """

        return {
            "type": "multi",
            "results": results,
            "consensus": {
                "count": len(results),
                "strategy": "append-only",
            },
        }