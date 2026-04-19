from app.contracts.message import OrchestratorRequest
from app.contracts.response import SuccessResponse, ErrorResponse
from app.engine.model_decision import resolve_model  # ✅ SINGLE ENTRY POINT
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

        # 🧠 MEMORY LOAD
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

        # 🧠 MODEL DECISION (CLEAN SINGLE PIPELINE)
        model, intent_result = resolve_model(text)

        logger.log(
            "INFO",
            "model_selected",
            trace_id=trace_id,
            model=model,
            intent=intent_result.intent,
            confidence=intent_result.confidence
        )

        # 🧠 PROMPT BUILD
        enriched_prompt = PromptBuilder.build(
            user_text=text,
            context=context,
            model=model
        )

        # 🧠 LLM CALL
        response = await run_llm(
            model=model,
            prompt=enriched_prompt,
            trace_id=trace_id
        )

        # 🧠 MEMORY SAVE
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

    except OrchestratorError as e:
        return ErrorResponse(
            error=e.to_dict()["error"],
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
            error=err.to_dict()["error"],
            trace_id=trace_id
        )