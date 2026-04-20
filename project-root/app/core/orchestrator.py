from app.contracts.message import OrchestratorRequest
from app.contracts.response import SuccessResponse, ErrorResponse

from app.engine.model_decision import resolve_model
from app.engine.llm import run_llm

from app.core.logger import logger
from app.core.errors import OrchestratorError
from app.memory.memory_service import MemoryService
from app.core.prompt_builder import PromptBuilder


# -------------------------
# MAIN FLOW
# -------------------------

async def handle_request(
    req: OrchestratorRequest,
    memory: MemoryService | None = None
):

    trace_id = req.trace_id

    try:
        logger.log("INFO", "orchestrator_start", trace_id=trace_id)

        text = (req.user_message.text or "").strip()
        user_id = req.user_message.user_id

        if not text:
            raise ValueError("Empty user message")

        # -------------------------
        # MEMORY LOAD (ISOLATED)
        # -------------------------
        context = _load_memory(memory, user_id, trace_id)

        # -------------------------
        # MODEL DECISION (BRAIN)
        # -------------------------
        model, intent_result = resolve_model(text)

        logger.log(
            "INFO",
            "model_selected",
            trace_id=trace_id,
            model=model,
            intent=intent_result.intent
        )

        # -------------------------
        # PROMPT BUILD
        # -------------------------
        prompt = PromptBuilder.build(
            user_text=text,
            context=context,
            model=model
        )

        # -------------------------
        # LLM EXECUTION
        # -------------------------
        response = await run_llm(
            model=model,
            prompt=prompt,
            trace_id=trace_id
        )

        raw_text = (response.content or "").strip()

        # -------------------------
        # FINAL VALIDATION GATE
        # -------------------------
        if not raw_text:
            logger.log("ERROR", "empty_llm_response", trace_id=trace_id, model=model)
            raw_text = "Unable to generate response. Please try again."

        # -------------------------
        # MEMORY SAVE (ISOLATED)
        # -------------------------
        _save_memory(memory, user_id, text, raw_text, trace_id)

        logger.log("INFO", "orchestrator_done", trace_id=trace_id)

        return SuccessResponse(
            data=raw_text,
            trace_id=trace_id
        )

    except OrchestratorError as e:
        return ErrorResponse(
            error=e.to_dict().get("error", str(e)),
            trace_id=trace_id
        )

    except Exception as e:
        logger.log(
            "ERROR",
            "orchestrator_crash",
            trace_id=trace_id,
            error=str(e)
        )

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
# MEMORY ISOLATION LAYER
# -------------------------

def _load_memory(memory, user_id, trace_id):
    if not memory:
        return []

    try:
        context = memory.build_context(user_id) or []

        logger.log(
            "INFO",
            "memory_loaded",
            trace_id=trace_id,
            context_size=len(context)
        )

        return context

    except Exception as e:
        logger.log(
            "ERROR",
            "memory_load_failed",
            trace_id=trace_id,
            error=str(e)
        )
        return []


def _save_memory(memory, user_id, user_text, response_text, trace_id):
    if not memory:
        return

    try:
        if hasattr(memory, "store") and memory.store:
            memory.store.append_message(user_id, "user", user_text)
            memory.store.append_message(user_id, "assistant", response_text)

            logger.log("INFO", "memory_saved", trace_id=trace_id)

    except Exception as e:
        logger.log(
            "ERROR",
            "memory_save_failed",
            trace_id=trace_id,
            error=str(e)
        )