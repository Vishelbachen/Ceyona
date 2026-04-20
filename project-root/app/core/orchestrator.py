from app.contracts.message import OrchestratorRequest
from app.contracts.response import SuccessResponse, ErrorResponse
from app.engine.model_decision import resolve_model
from app.engine.llm import run_llm
from app.core.logger import logger
from app.core.errors import OrchestratorError
from app.memory.memory_service import MemoryService
from app.core.prompt_builder import PromptBuilder


async def handle_request(
    req: OrchestratorRequest,
    memory: MemoryService | None = None
):

    trace_id = req.trace_id

    try:
        logger.log("INFO", "orchestrator_start", trace_id=trace_id)

        user_id = req.user_message.user_id
        text = (req.user_message.text or "").strip()

        if not text:
            raise ValueError("Empty user message")

        # -------------------------
        # MEMORY LOAD (SAFE + ISOLATED)
        # -------------------------
        context = []

        if memory:
            try:
                context = memory.build_context(user_id) or []
                logger.log("INFO", "memory_loaded", trace_id=trace_id, context_size=len(context))
            except Exception as e:
                logger.log("ERROR", "memory_load_failed", trace_id=trace_id, error=str(e))

        # -------------------------
        # MODEL DECISION
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
        # (future: intent-aware injection possible)
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

        raw_text = _safe_response(getattr(response, "content", None))

        # -------------------------
        # FINAL GUARD
        # -------------------------
        if not raw_text:
            logger.log("ERROR", "empty_llm_response", trace_id=trace_id, model=model)
            raw_text = "Unable to generate response. Please try again."

        # -------------------------
        # MEMORY SAVE (SAFE)
        # -------------------------
        if memory:
            try:
                if hasattr(memory, "store") and memory.store:
                    memory.store.append_message(user_id, "user", text)
                    memory.store.append_message(user_id, "assistant", raw_text)

                    logger.log("INFO", "memory_saved", trace_id=trace_id)

            except Exception as e:
                logger.log("ERROR", "memory_save_failed", trace_id=trace_id, error=str(e))

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
# SAFETY LAYER
# -------------------------
def _safe_response(text: str | None) -> str:
    if not text:
        return ""

    return text.strip()