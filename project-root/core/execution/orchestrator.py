from typing import Dict, Any


class Orchestrator:
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

        self.epk = ExecutionPolicyKernel(settings)
        self.decision_matrix = DecisionMatrix()
        self.cost_model = CostModel(settings)
        self.policy_registry = PolicyRegistry()

    async def handle_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:

        text = payload.get("text") or ""

        # =========================
        # 1. ANALYSIS (SAFE)
        # =========================
        profile = self.decision_matrix.analyze(payload)

        # =========================
        # 2. POLICY DECISION (SAFE GUARDS)
        # =========================
        decision = self.epk.evaluate({"text": text})

        if not decision:
            raise RuntimeError("EPK returned None decision")

        tier = getattr(decision, "tier", None)

        if not tier:
            tier = "FAST"  # fallback safety gate

        policy = self.policy_registry.get(tier)

        if not policy:
            raise RuntimeError(f"No policy for tier={tier}")

        if not policy.recommended_agents:
            raise RuntimeError(f"Empty agent list for tier={tier}")

        # =========================
        # 3. COST (SAFE)
        # =========================
        cost = self.cost_model.estimate_from_payload(
            tier=tier,
            payload=payload,
        )

        # =========================
        # 4. AGENT
        # =========================
        agent_name = policy.recommended_agents[0]
        agent = self.agents.get(agent_name)

        if not agent:
            raise RuntimeError(f"Agent not found: {agent_name}")

        # =========================
        # 5. CONTEXT
        # =========================
        context = {
            "text": text,
            "tier": tier,
            "policy": policy,
            "cost": cost,
            "profile": profile,
        }

        # =========================
        # 6. EXECUTION (ISOLATED CRASH PROTECTION)
        # =========================
        try:
            result = await agent.run(context)
        except Exception as e:
            raise RuntimeError(f"Agent execution failed: {str(e)}")

        # =========================
        # 7. CONSENSUS
        # =========================
        final = self.consensus_engine.resolve(result)

        return {
            "tier": tier,
            "result": final,
            "cost": cost.total_cost,
        }