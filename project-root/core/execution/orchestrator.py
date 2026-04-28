from typing import Dict, Any

from core.kernel.execution_policy_kernel import ExecutionPolicyKernel
from core.kernel.decision_matrix import DecisionMatrix
from core.kernel.cost_model import CostModel
from core.kernel.policy_registry import PolicyRegistry


class Orchestrator:
    """
    AI Platform v4.7 — Execution Orchestrator

    RESPONSIBILITY:
    - Flow control only
    - No business logic
    """

    def __init__(
        self,
        settings,
        retrieval_engine,
        model_router,
        agents: dict,
        consensus_engine,
    ):
        self.settings = settings
        self.retrieval_engine = retrieval_engine
        self.model_router = model_router
        self.agents = agents
        self.consensus_engine = consensus_engine

        # kernel layer (CONSISTENT INIT)
        self.epk = ExecutionPolicyKernel(settings)
        self.decision_matrix = DecisionMatrix()
        self.cost_model = CostModel(settings)
        self.policy_registry = PolicyRegistry()

    async def handle_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execution pipeline entrypoint.
        """

        text = payload.get("text", "")

        # =========================
        # 1. ANALYSIS
        # =========================
        profile = self.decision_matrix.analyze(payload)

        # =========================
        # 2. POLICY DECISION
        # =========================
        decision = self.epk.evaluate({"text": text})
        tier = decision.tier

        policy = self.policy_registry.get(tier)

        # =========================
        # 3. COST
        # =========================
        cost = self.cost_model.estimate_from_payload(
            tier=tier,
            payload=payload,
        )

        # =========================
        # 4. AGENT SELECTION
        # =========================
        agent_name = policy.recommended_agents[0]
        agent = self.agents.get(agent_name)

        if not agent:
            raise RuntimeError(f"No agent found for tier={tier}")

        # =========================
        # 5. CONTEXT (FIXED BOUNDARY)
        # =========================
        context = {
            "text": text,
            "tier": tier,
            "policy": policy,
            "cost": cost,
            "profile": profile,
        }

        # =========================
        # 6. EXECUTION
        # =========================
        result = await agent.run(context)

        # =========================
        # 7. CONSENSUS
        # =========================
        final = self.consensus_engine.resolve(result)

        return {
            "tier": tier,
            "result": final,
            "cost": cost.total_cost,
        }