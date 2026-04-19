from app.contracts.message import OrchestratorRequest
from app.contracts.response import SuccessResponse, ErrorResponse
from app.engine.model_router import select_model
from app.engine.llm import run_llm
from app.core.logger import logger
from app.core.errors import OrchestratorError

from app.memory.memory_service import MemoryService


async def handle_request(
    req: OrchestratorRequest,
    memory: MemoryService | None = None
):
    trace_id = req.trace_id
    user_id = req.user_id

    try:
        logger.log("INFO", "orchestrator_start", trace_id=trace_id)

        text = req.user_message.text

        # 🧠 MEMORY LOAD (SAFE)
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

        # 🧠 MODEL SELECTION
        model = select_model(text)

        logger.log(
            "INFO",
            "model_selected",
            trace_id=trace_id,
            model=model
        )

        # 🔥 CRITICAL FIX: STRING PROMPT (NO DICT)
        enriched_prompt = f"""
USER MESSAGE:
{text}

CONTEXT:
{context}
"""

        # 🧠 LLM CALL
        response = await run_llm(
            model=model,
            prompt=enriched_prompt,
            trace_id=trace_id
        )

        # 🧠 MEMORY SAVE (SAFE)
        if memory:
            try:
                memory.store.append_message(user_id, "user", text)
                memory.store.append_message(user_id, "assistant", response.content)

                logger.log(
                    "INFO",
                    "memory_saved",
                    trace_id=trace_id
                )
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
        logger.log(
            "ERROR",
            "orchestrator_error",
            trace_id=trace_id,
            error=str(e)
        )

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