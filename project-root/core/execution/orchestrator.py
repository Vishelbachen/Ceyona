from dataclasses import dataclass
from typing import Any, Dict

from core.kernel.execution_policy_kernel import ExecutionPolicyKernel

from llm.model_router import ModelRouter
from llm.prompt_engine import PromptEngine

from retrieval.retrieval_engine import RetrievalEngine
from context.assembler import ContextAssembler

from cognition.response_synthesizer import ResponseSynthesizer

from memory.conversation_history import ConversationHistory
from events.event_bus import EventBus


# =========================
# 🧩 INPUT CONTRACT
# =========================
@dataclass
class OrchestratorInput:
    user_id: str
    message: str
    metadata: Dict[str, Any] | None = None


# =========================
# 🧠 ORCHESTRATOR
# =========================
class Orchestrator:
    """
    Core execution pipeline coordinator.

    RULES:
    - NO decision making
    - NO business logic
    - ONLY deterministic flow orchestration
    """

    def __init__(
        self,
        epk: ExecutionPolicyKernel,
        model_router: ModelRouter,
        prompt_engine: PromptEngine,
        retrieval_engine: RetrievalEngine,
        context_assembler: ContextAssembler,
        response_synthesizer: ResponseSynthesizer,
        memory: ConversationHistory,
        event_bus: EventBus,
    ):
        self.epk = epk
        self.model_router = model_router
        self.prompt_engine = prompt_engine
        self.retrieval_engine = retrieval_engine
        self.context_assembler = context_assembler
        self.response_synthesizer = response_synthesizer
        self.memory = memory
        self.event_bus = event_bus

    # =========================
    # 🚀 MAIN ENTRY POINT
    # =========================
    async def execute(self, input: OrchestratorInput) -> Dict[str, Any]:

        # =========================
        # 1. EVENT: INPUT RECEIVED
        # =========================
        await self.event_bus.emit(
            "input_received",
            {"user_id": input.user_id, "message": input.message},
        )

        # =========================
        # 2. MEMORY LOAD (READ ONLY)
        # =========================
        history = await self.memory.get_history(input.user_id)

        # =========================
        # 3. FEATURE STATE (minimal placeholder)
        # =========================
        state = {
            "message": input.message,
            "history": history,
            "metadata": input.metadata or {},
        }

        # =========================
        # 4. EPK CHECK (GATE)
        # =========================
        decision = self.epk.evaluate(state)

        if decision == "DENY":
            return {
                "response": "Request denied by policy layer.",
                "status": "blocked",
            }

        if decision == "DEGRADED_MODE":
            state["mode"] = "safe_minimal"

        # =========================
        # 5. RETRIEVAL (OPTIONAL STEP - SAFE CALL)
        # =========================
        retrieval_context = await self.retrieval_engine.search(
            query=input.message
        )

        # =========================
        # 6. CONTEXT ASSEMBLY
        # =========================
        context = self.context_assembler.build(
            message=input.message,
            history=history,
            retrieval=retrieval_context,
        )

        # =========================
        # 7. PROMPT BUILDING
        # =========================
        prompt = self.prompt_engine.build(
            context=context,
            mode=decision,
        )

        # =========================
        # 8. MODEL ROUTING (LLM LAYER)
        # =========================
        llm_result = await self.model_router.route(
            prompt=prompt,
            mode=decision,
        )

        # =========================
        # 9. RESPONSE SYNTHESIS
        # =========================
        response = self.response_synthesizer.synthesize(
            llm_output=llm_result,
            context=context,
        )

        # =========================
        # 10. MEMORY WRITE
        # =========================
        await self.memory.save(
            user_id=input.user_id,
            user_message=input.message,
            assistant_response=response,
        )

        # =========================
        # 11. EVENT: OUTPUT GENERATED
        # =========================
        await self.event_bus.emit(
            "response_generated",
            {"user_id": input.user_id},
        )

        # =========================
        # FINAL OUTPUT
        # =========================
        return {
            "response": response,
            "status": "ok",
            "mode": decision,
        }