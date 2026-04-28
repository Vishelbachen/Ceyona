from typing import Any, Dict, List


class ResponseSynthesizer:
    """
    AI Platform v4.7 — Response Synthesizer

    RESPONSIBILITY:
    - Merge outputs from agents / reasoning / retrieval
    - Produce structured response object
    - Normalize format for downstream delivery

    STRICT RULES:
    - No reasoning
    - No LLM calls
    - No ranking or evaluation
    - No retrieval / memory access
    - No agent selection logic
    """

    def synthesize(
        self,
        reasoning: Dict[str, Any],
        agent_results: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Deterministic response composition.
        """

        return {
            "status": "ok",
            "complexity": reasoning.get("complexity", "unknown"),
            "requires_tools": reasoning.get("requires_tools", False),

            "reasoning_steps": [
                step.__dict__ if hasattr(step, "__dict__") else step
                for step in reasoning.get("steps", [])
            ],

            "agents": agent_results,

            "metadata": {
                "intent": metadata.get("intent"),
                "tier": metadata.get("tier"),
                "cost": metadata.get("cost"),
            },

            "final_output": None,  # intentionally empty (LLM layer fills this later)
        }

    def format_for_transport(self, synthesized: Dict[str, Any]) -> Dict[str, Any]:
        """
        Minimal transport-safe normalization layer.
        """

        return {
            "ok": True,
            "data": synthesized,
        }