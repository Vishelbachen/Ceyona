from app.contracts.message import OrchestratorRequest
from app.contracts.response import SuccessResponse, ErrorResponse

from app.engine.model_decision import resolve_model
from app.engine.llm import run_llm
from app.core.logger import logger
from app.core.errors import OrchestratorError
from app.memory.memory_service import MemoryService
from app.core.prompt_builder import PromptBuilder
from app.core.reasoning_verifier import ReasoningVerifier
from app.engine.task_classifier import classify


async def handle_request(req: OrchestratorRequest, memory: MemoryService | None = None):

    trace_id = req.trace_id

    try:
        logger.log("INFO", "orchestrator_start", trace_id=trace_id)

        text = (req.user_message.text or "").strip()
        user_id = req.user_message.user_id

        if not text:
            raise ValueError("Empty input")

        context = memory.build_context(user_id) if memory else []

        model, intent = resolve_model(text)
        task_type = classify(text)

        prompt = PromptBuilder.build(
            user_text=text,
            context=context,
            model=model
        )

        # 🔥 CORE LOOP (retry + verifier)
        max_attempts = 2
        final_answer = None

        for attempt in range(max_attempts):

            response = await run_llm(
                model=model,
                prompt=prompt,
                trace_id=trace_id
            )

            result = response.content

            check = ReasoningVerifier.verify(
                task_type=task_type,
                question=text,
                answer=result
            )

            if check["is_valid"]:
                final_answer = result
                break

            logger.log(
                "WARN",
                "verifier_failed",
                trace_id=trace_id,
                issues=check["issues"]
            )

        if not final_answer:
            final_answer = result  # fallback last attempt

        if memory:
            memory.store.append_message(user_id, "user", text)
            memory.store.append_message(user_id, "assistant", final_answer)

        return SuccessResponse(
            data=final_answer,
            trace_id=trace_id
        )

    except Exception as e:
        logger.log("ERROR", "orchestrator_crash", trace_id=trace_id, error=str(e))

        return ErrorResponse(
            error={"message": str(e)},
            trace_id=trace_id
        )