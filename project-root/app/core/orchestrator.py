from app.contracts.message import OrchestratorRequest
from app.contracts.response import SuccessResponse, ErrorResponse
from app.engine.model_router import select_model
from app.engine.llm import run_llm
from app.core.logger import logger
from app.core.errors import OrchestratorError

# NEW (memory layer)
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

        # 🧠 1. LOAD MEMORY CONTEXT (SAFE ADDITION)
        context = []
        if memory:
            context = memory.build_context(user_id)

            logger.log(
                "INFO",
                "memory_loaded",
                trace_id=trace_id,
                context_size=len(context)
            )

        # 🧠 2. MODEL SELECTION (UNCHANGED)
        model = select_model(text)

        logger.log(
            "INFO",
            "model_selected",
            trace_id=trace_id,
            model=model
        )

        # 🧠 3. BUILD PROMPT WITH CONTEXT
        # (LLM stays stateless — we just enrich input)
        enriched_prompt = {
            "message": text,
            "context": context
        }

        # 🧠 4. LLM CALL (UNCHANGED CONTRACT)
        response = await run_llm(
            model=model,
            prompt=enriched_prompt,
            trace_id=trace_id
        )

        # 🧠 5. SAVE MEMORY (POST-LLM SIDE EFFECT ONLY)
        if memory:
            memory.store.append_message(user_id, "user", text)
            memory.store.append_message(user_id, "assistant", response.content)

            logger.log(
                "INFO",
                "memory_saved",
                trace_id=trace_id
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
            "orchestrator_error",
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