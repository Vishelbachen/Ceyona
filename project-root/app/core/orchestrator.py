from app.contracts.message import OrchestratorRequest
from app.contracts.response import SuccessResponse, ErrorResponse

from app.engine.model_decision import resolve_model
from app.engine.llm import run_llm
from app.engine.reasoning_verifier import ReasoningVerifier

from app.core.logger import logger
from app.core.errors import OrchestratorError
from app.memory.memory_service import MemoryService
from app.core.prompt_builder import PromptBuilder


# -------------------------
# MAIN FLOW
# -------------------------

async def handle_request(req: OrchestratorRequest, memory: MemoryService | None = None):

    trace_id = req.trace_id

    try:
        logger.log("INFO", "orchestrator_start", trace_id=trace_id)

        text = (req.user_message.text or "").strip()
        user_id = req.user_message.user_id

        if not text:
            raise ValueError("Empty user message")

        # -------------------------
        # MEMORY
        # -------------------------
        context = _load_memory(memory, user_id, trace_id)

        # -------------------------
        # MODEL DECISION
        # -------------------------
        model, intent_result = resolve_model(text)

        logger.log("INFO", "model_selected",
                   trace_id=trace_id,
                   model=model,
                   intent=intent_result.intent)

        # -------------------------
        # PROMPT
        # -------------------------
        prompt = PromptBuilder.build(
            user_text=text,
            context=context,
            model=model
        )

        # -------------------------
        # LLM CALL
        # -------------------------
        response = await run_llm(
            model=model,
            prompt=prompt,
            trace_id=trace_id
        )

        raw_text = (response.content or "").strip()

        # -------------------------
        # 🧠 VERIFIER (NEW CRITICAL STEP)
        # -------------------------

        task = _infer_task(text)

        verification = ReasoningVerifier.verify(
            task_type=task,
            question=text,
            answer=raw_text
        )

        logger.log(
            "INFO",
            "verification_done",
            trace_id=trace_id,
            is_valid=verification["is_valid"],
            issues=verification["issues"]
        )

        # -------------------------
        # OPTIONAL FIX (future retry system)
        # -------------------------
        if not verification["is_valid"]:
            raw_text = verification.get("corrected_answer") or raw_text

        # -------------------------
        # FINAL GUARD
        # -------------------------
        if not raw_text:
            raw_text = "Unable to generate response."

        # -------------------------
        # MEMORY SAVE
        # -------------------------
        _save_memory(memory, user_id, text, raw_text, trace_id)

        logger.log("INFO", "orchestrator_done", trace_id=trace_id)

        return SuccessResponse(
            data=raw_text,
            trace_id=trace_id
        )

    except Exception as e:
        logger.log("ERROR", "orchestrator_crash", trace_id=trace_id, error=str(e))

        err = OrchestratorError(
            code="ORCH_001",
            message=str(e),
            layer="orchestrator",
            trace_id=trace_id
        )

        return ErrorResponse(
            error=err.to_dict().get("error", str(e)),
            trace_id=trace_id
        )


# -------------------------
# TASK INFERENCE (lightweight, temporary)
# -------------------------

def _infer_task(text: str) -> str:
    t = text.lower()

    if any(x in t for x in ["prove", "solve", "equation", "math", "integral", "derivative"]):
        return "math"

    if any(x in t for x in ["code", "function", "class", "algorithm"]):
        return "coding"

    if any(x in t for x in ["physics", "chemistry"]):
        return "physics"

    return "general"


# -------------------------
# MEMORY HELPERS
# -------------------------

def _load_memory(memory, user_id, trace_id):
    if not memory:
        return []

    try:
        return memory.build_context(user_id) or []
    except Exception:
        return []


def _save_memory(memory, user_id, user_text, response_text, trace_id):
    if not memory:
        return

    try:
        if getattr(memory, "store", None):
            memory.store.append_message(user_id, "user", user_text)
            memory.store.append_message(user_id, "assistant", response_text)
    except Exception:
        pass