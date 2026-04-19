from app.contracts.message import OrchestratorRequest
from app.contracts.response import SuccessResponse, ErrorResponse
from app.engine.model_router import select_model
from app.engine.model_policy import select_model_by_intent  # 🆕 INTENT-BASED ROUTING (future-ready)
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

        # 🧠 MEMORY LOAD (SAFE + CONTROLLED)
        context = []
        if memory:
            try:
                context = memory.build_context(user_id)

                logger.log(
                    "INFO",
                    "memory_loaded",
                    trace_id=trace_id,
                    context_size=len(context)
                )

            except Exception as e:
                logger.log(
                    "ERROR",
                    "memory_load_failed",
                    trace_id=trace_id,
                    error=str(e)
                )
                context = []

        # 🧠 MODEL SELECTION (CURRENT + READY FOR UPGRADE)
        # NOTE: сейчас fallback = rule-based router
        model = select_model(text)

        logger.log(
            "INFO",
            "model_selected",
            trace_id=trace_id,
            model=model
        )

        # 🧠 PROMPT BUILD (ISOLATED LAYER)
        enriched_prompt = PromptBuilder.build(
            user_text=text,
            context=context,
            model=model
        )

        # 🧠 LLM EXECUTION
        response = await run_llm(
            model=model,
            prompt=enriched_prompt,
            trace_id=trace_id
        )

        # 🧠 MEMORY SAVE (SAFE + NON-BLOCKING)
        if memory and getattr(memory, "store", None):
            try:
                memory.store.append_message(user_id, "user", text)
                memory.store.append_message(user_id, "assistant", response.content)

                logger.log("INFO", "memory_saved", trace_id=trace_id)

            except Exception as e:
                logger.log(
                    "ERROR",
                    "memory_save_failed",
                    trace_id=trace_id,
                    error=str(e)
                )

        logger.log("INFO", "orchestrator_done", trace_id=trace_id)

        return SuccessResponse(
            data=response.content,
            trace_id=trace_id
        )

    # ⚠️ DOMAIN ERRORS
    except OrchestratorError as e:
        return ErrorResponse(
            error=e.to_dict()["error"],
            trace_id=trace_id
        )

    # ⚠️ SAFE FALLBACK FOR ANY UNEXPECTED FAILURE
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
            error=err.to_dict()["error"],
            trace_id=trace_id
        )