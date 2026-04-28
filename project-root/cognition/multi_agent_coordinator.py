from typing import Any, Dict, List


class MultiAgentCoordinator:
    """
    AI Platform v4.7 — Multi-Agent Coordinator

    RESPONSIBILITY:
    - Distribute structured tasks to multiple agents
    - Collect agent outputs
    - Provide unified structured response for downstream aggregation

    STRICT RULES:
    - No reasoning or decision-making
    - No agent selection logic (done by orchestrator/EPK)
    - No LLM calls directly
    - No retrieval / memory access
    """

    def distribute(
        self,
        agents: List[Any],
        payload: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Sends payload to multiple pre-selected agents.
        """

        results = []

        for agent in agents:
            result = agent.run(payload)
            results.append(
                {
                    "agent": getattr(agent, "__class__", type(agent)).__name__,
                    "output": result,
                }
            )

        return results

    async def distribute_async(
        self,
        agents: List[Any],
        payload: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Async version for concurrent agent execution.
        """

        results = []

        for agent in agents:
            result = await agent.run(payload)
            results.append(
                {
                    "agent": getattr(agent, "__class__", type(agent)).__name__,
                    "output": result,
                }
            )

        return results

    def merge_results(self, agent_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Simple deterministic merge of agent outputs.

        No ranking, no evaluation, no intelligence.
        """

        return {
            "agents_count": len(agent_outputs),
            "outputs": agent_outputs,
        }