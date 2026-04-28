from typing import Dict, Any

from core.kernel.execution_policy_kernel import ExecutionPolicyKernel
from core.kernel.decision_matrix import DecisionMatrix
from core.kernel.cost_model import CostModel
from core.kernel.policy_registry import PolicyRegistry


class Orchestrator:
    """
    AI Platform v4.7 — Execution Orchestrator
    """

    def __init__(
        self,
        settings,
        retrieval_engine,
        model_router,
        agents: dict,
        consensus_engine,
    ):
        # external systems
        self.settings = settings
        self.retrieval_engine = retrieval_engine
        self.model_router = model_router
        self.agents = agents
        self.consensus_engine = consensus_engine

        # kernel layer (FIXED: INSTANCE, not CLASS)
        self.epk = ExecutionPolicyKernel(self.settings)
        self.decision_matrix = DecisionMatrix()
        self.cost_model = CostModel(self.settings)
        self.policy_registry = PolicyRegistry()

    async def handle_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution pipeline entrypoint.
        """

        text = payload.get("text", "")

        # =========================
        # 1. FEATURE EXTRACTION
        # =========================
        profile = self.decision_matrix.analyze(payload)

        # =========================
        # 2. EPK DECISION
        # =========================
        decision = self.epk.evaluate({"text": text})
        tier = decision.tier

        # =========================
        # 3. POLICY LOOKUP
        # =========================
        policy = self.policy_registry.get(tier)

        # =========================
        # 4. COST ESTIMATION
        # =========================
        cost = self.cost_model.estimate_from_payload(
            tier=tier,
            payload=payload,
        )

        # =========================
        # 5. ROUTING
        # =========================
        agent_name = policy.recommended_agents[0]
        agent = self.agents.get(agent_name)

        if not agent:
            raise RuntimeError(f"No agent found for tier={tier}")

        # =========================
        # 6. EXECUTION
        # =========================
        result = await agent.run(
            {
                "text": text,
                "tier": tier,
                "policy": policy,
                "cost": cost,
                "profile": profile,
                "retrieval_engine": self.retrieval_engine,
                "model_router": self.model_router,
            }
        )

        # =========================
        # 7. CONSENSUS
        # =========================
        final = self.consensus_engine.resolve(result)

        return {
            "tier": tier,
            "result": final,
            "cost": cost.total_cost,
        }