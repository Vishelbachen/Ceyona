from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional

from core.kernel.execution_policy_kernel import ExecutionPolicyKernel, ExecutionContext
from core.kernel.cost_model import CostModel, CostFactors
from core.kernel.decision_matrix import DecisionMatrix, DecisionFactors
from core.kernel.policy_registry import PolicyRegistry

from llm.model_router import ModelRouter
from llm.prompt_engine import PromptEngine
from llm.fallback_handler import FallbackHandler

from agents.consensus_engine import ConsensusEngine
from cognition.intent_engine import IntentEngine
from cognition.reasoning_engine import ReasoningEngine
from cognition.response_synthesizer import ResponseSynthesizer

from memory.conversation_history import ConversationHistory
from events.event_bus import EventBus


# =========================
# REQUEST CONTEXT
# =========================
@dataclass
class OrchestratorInput:
    user_id: str
    user_input: str
    plan: str
    system_load: float
    wallet_balance: float
    risk_flag: bool = False


# =========================
# FINAL OUTPUT
# =========================
@dataclass
class OrchestratorOutput:
    response: str
    decision: str
    model_used: Optional[str] = None


# =========================
# ORCHESTRATOR (CONTROL PLANE)
# =========================
class Orchestrator:
    """
    ROLE:
    - central execution DAG
    - coordinates all system layers
    - NO domain logic inside

    RESPONSIBILITIES:
    - call EPK (policy gate)
    - compute cost
    - select model
    - build prompt
    - execute LLM with fallback
    - run agents if needed
    - synthesize final response
    - emit events

    STRICT RULES:
    - no persistence logic
    - no pricing logic
    - no LLM prompt design
    - no decision heuristics
    """

    def __init__(
        self,
        epk: ExecutionPolicyKernel,
        cost_model: CostModel,
        decision_matrix: DecisionMatrix,
        policy_registry: PolicyRegistry,
        model_router: ModelRouter,
        prompt_engine: PromptEngine,
        fallback: FallbackHandler,
        intent_engine: IntentEngine,
        reasoning_engine: ReasoningEngine,
        consensus_engine: ConsensusEngine,
        response_synth: ResponseSynthesizer,
        memory: ConversationHistory,
        event_bus: EventBus,
    ):

        self.epk = epk
        self.cost_model = cost_model
        self.decision_matrix = decision_matrix
        self.policy_registry = policy_registry

        self.model_router = model_router
        self.prompt_engine = prompt_engine
        self.fallback = fallback

        self.intent_engine = intent_engine
        self.reasoning_engine = reasoning_engine
        self.consensus_engine = consensus_engine
        self.response_synth = response_synth

        self.memory = memory
        self.events = event_bus

    # =========================
    # MAIN EXECUTION ENTRY
    # =========================
    async def run(self, inp: OrchestratorInput) -> OrchestratorOutput:

        # -------------------------
        # 1. LOAD POLICY
        # -------------------------
        policy = self.policy_registry.get(inp.plan)

        # -------------------------
        # 2. COST ESTIMATION
        # -------------------------
        cost = self.cost_model.estimate(
            CostFactors(
                tokens_estimate=len(inp.user_input) // 4,
                model_tier="general",
                use_retrieval=True,
                use_agents=True,
                llm_steps=1,
            )
        )

        # -------------------------
        # 3. POLICY MATRIX CHECK
        # -------------------------
        decision = self.decision_matrix.resolve(
            DecisionFactors(
                cost_bucket=cost.bucket,
                system_load="high" if inp.system_load > 0.85 else "low",
                user_tier=inp.plan,
                risk_level="risky" if inp.risk_flag else "safe",
            )
        )

        # -------------------------
        # 4. EPK GATE
        # -------------------------
        epk_result = self.epk.evaluate(
            ExecutionContext(
                user_id=inp.user_id,
                plan=inp.plan,
                estimated_cost=cost.raw_cost,
                usage_day_limit=100,
                usage_month_limit=1000,
                remaining_day=100,
                remaining_month=1000,
                system_load=inp.system_load,
                risk_flag=inp.risk_flag,
            )
        )

        if epk_result.decision == "DENY":
            return OrchestratorOutput(
                response="Request blocked by policy layer.",
                decision="DENY",
            )

        # -------------------------
        # 5. INTENT ANALYSIS
        # -------------------------
        intent = self.intent_engine.analyze(inp.user_input)

        # -------------------------
        # 6. MEMORY CONTEXT
        # -------------------------
        history = self.memory.load(inp.user_id)

        # -------------------------
        # 7. PROMPT BUILDING
        # -------------------------
        messages = self.prompt_engine.build_messages(
            system_prompt=intent.system_prompt,
            user_input=inp.user_input,
            history=history,
        )

        # -------------------------
        # 8. MODEL SELECTION
        # -------------------------
        model = self.model_router.resolve("general")

        # -------------------------
        # 9. LLM EXECUTION (WITH FALLBACK)
        # -------------------------
        llm_output = self.fallback.execute(
            tier="general",
            model=model,
            messages=messages,
        )

        # -------------------------
        # 10. REASONING POST-PROCESS
        # -------------------------
        reasoning = self.reasoning_engine.process(llm_output)

        # -------------------------
        # 11. AGENT CONSENSUS (IF NEEDED)
        # -------------------------
        final = self.consensus_engine.resolve(reasoning)

        # -------------------------
        # 12. RESPONSE SYNTHESIS
        # -------------------------
        response = self.response_synth.build(final)

        # -------------------------
        # 13. MEMORY WRITE
        # -------------------------
        self.memory.save(inp.user_id, inp.user_input, response)

        # -------------------------
        # 14. EVENT EMISSION
        # -------------------------
        self.events.emit(
            event_type="request_completed",
            payload={
                "user_id": inp.user_id,
                "decision": epk_result.decision,
                "model": model,
            },
        )

        # -------------------------
        # FINAL OUTPUT
        # -------------------------
        return OrchestratorOutput(
            response=response,
            decision=epk_result.decision,
            model_used=model,
        )