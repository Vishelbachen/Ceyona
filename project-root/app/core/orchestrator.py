from app.engine.model_decision import resolve_model
from app.engine.llm import run_llm
from app.engine.reasoning_verifier import ReasoningVerifier

from app.core.prompt_builder import PromptBuilder
from app.core.logger import logger
from app.core.errors import OrchestratorError


async def handle_request(req, memory=None):
    trace_id = req.trace_id

    try:
        text = (req.user_message.text or "").strip()
        user_id = req.user_message.user_id

        if not text:
            raise ValueError("empty input")

        context = memory.build_context(user_id) if memory else []

        model, intent = resolve_model(text)

        prompt = PromptBuilder.build(text, context, model)

        response = await run_llm(model, prompt, trace_id=trace_id)

        result = response.content.strip()

        # -------------------------
        # VERIFIER (v1 integration)
        # -------------------------
        task_type = intent.intent

        verification = ReasoningVerifier.verify(
            task_type,
            text,
            result
        )

        if not verification["is_valid"]:
            logger.log("WARN", "verifier_failed", trace_id=trace_id)

        final = verification["corrected_answer"] or result

        if memory:
            memory.store.append_message(user_id, "user", text)
            memory.store.append_message(user_id, "assistant", final)

        return {
            "data": final,
            "trace_id": trace_id
        }

    except Exception as e:
        logger.log("ERROR", "orchestrator_error", trace_id=trace_id, error=str(e))
        raise OrchestratorError(str(e))