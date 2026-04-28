from typing import Dict, Any

from core.kernel.execution_policy_kernel import ExecutionPolicyKernel
from core.kernel.decision_matrix import DecisionMatrix
from core.kernel.cost_model import CostModel
from core.kernel.policy_registry import PolicyRegistry


class Orchestrator:
    """
    AI Platform v4.7 — Execution Orchestrator

    RESPONSIBILITY:
    - Coordinate execution flow
    - Call EPK for tier decision
    - Fetch policy from registry
    - Route to agents / retrieval / memory
    - Aggregate final response

    STRICT RULES:
    - No business logic decisions inside
    - No heuristic routing
    - No LLM calls directly
    - No retrieval / memory direct access
    """

    def __init__(
        self,
        retrieval_engine,
        model_router,
        agents: dict,
        consensus_engine,
    ):
        # external systems
        self.retrieval_engine = retrieval_engine
        self.model_router = model_router
        self.agents = agents
        self.consensus_engine = consensus_engine

        # kernel layer
        self.epk = ExecutionPolicyKernel
        self.decision_matrix = DecisionMatrix()
        self.cost_model = CostModel
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
        epk = ExecutionPolicyKernel(self.epk.settings)
        decision = epk.evaluate({"text": text})

        tier = decision.tier

        # =========================
        # 3. POLICY LOOKUP
        # =========================
        policy = self.policy_registry.get(tier)

        # =========================
        # 4. COST ESTIMATION
        # =========================
        cost = self.cost_model(self.epk.settings).estimate_from_payload(
            tier=tier,
            payload=payload,
        )

        # =========================
        # 5. ROUTING (NO LOGIC DECISIONS HERE)
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
        # 7. CONSENSUS (optional aggregation layer)
        # =========================
        final = self.consensus_engine.resolve(result)

        return {
            "tier": tier,
            "result": final,
            "cost": cost.total_cost,
        }